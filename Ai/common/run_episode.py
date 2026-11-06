"""Run one controller episode through the project signal-safety layer."""

from __future__ import annotations

import argparse
import contextvars
import csv
import json
import logging
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Ai.common.config import load_config
from Ai.common.junction import controlled_movements, controlled_route_movements
from Ai.common.metrics import classify_ai_coverage, summarize_run
from Ai.common.network_state import NetworkSensorReader
from Ai.common.sumo_client import SumoClient
from Ai.common.traffic_state import SumoSensorReader
from Ai.controllers.base import Action
from Ai.controllers.fallback import FallbackController
from Ai.controllers.fixed_time import FixedTimeController
from Ai.controllers.network import classify_hybrid_coverage, get_network_controller
from Ai.controllers.registry import get_controller
from Ai.controllers.safety import Accepted, NetworkSafetyManager, Rejected, SignalSafetyLayer
from scripts.make_scenarios import ScenarioBuilder

logger = logging.getLogger(__name__)
_STATUS_PATH: contextvars.ContextVar[Path | None] = contextvars.ContextVar("status_path", default=None)


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    """Atomically publish the latest observational status for a run."""
    payload["updated_utc"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(5):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            # Windows can briefly deny replacement while another process has
            # the status file open for polling. Preserve atomic publication and
            # retry the transient sharing/access failure.
            time.sleep(0.05 * (attempt + 1))


def _set_status(state: str, *, sim_time: float | None = None, error: str | None = None) -> None:
    path = _STATUS_PATH.get()
    if path is None:
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["state"] = state
        if sim_time is not None:
            payload["sim_time"] = sim_time
        payload["error"] = error[:300] if error else None
        _write_status(path, payload)
    except OSError:
        logger.exception("Could not update run status file %s", path)

STEP_FIELDS = (
    "run_id", "controller", "scenario", "seed", "sim_time", "intersection_id",
    "approach", "vehicles", "halting", "mean_speed", "wait_time", "phase",
    "phase_elapsed", "signal_state", "action", "action_accepted",
    "requested_action_accepted", "fallback_action_accepted", "fallback_used",
    "safety_rejection_reason", "congestion",
)
TRIP_FIELDS = (
    "run_id", "controller", "scenario", "seed", "vehicle_id", "vtype",
    "scheduled_depart", "actual_depart", "depart_delay", "arrival", "duration",
    "trip_time", "waiting_time", "time_loss", "route_length", "completed",
    "route_through_junction", "first_controlled_movement",
    "n_controlled_junctions_on_route", "passed_controlled_junction",
)
NETWORK_JUNCTION_FIELDS = (
    "run_id", "controller", "scenario", "seed", "tls_id", "controlled_by",
    "avg_queue", "max_queue", "avg_wait", "frac_time_high_congestion",
    "throughput_veh_per_min", "n_switches", "n_forced_max_green",
    "n_illegal_actions", "illegal_action_rate", "n_hold_overridden", "hold_overridden_rate",
    "fallback_activations", "rejection_reason_counts", "n_ticks", "ppo_tick_share", "action_histogram",
    "applied_action_histogram", "phase_usage", "mean_green_by_phase_s",
)


def _route_catalog(route_file: Path, net: Any, movements: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Read fixed route membership and expected vehicle metadata from XML."""
    root = ET.parse(route_file).getroot()
    catalog: dict[str, dict[str, Any]] = {}
    for vehicle in root.findall("vehicle"):
        route = vehicle.find("route")
        if route is None or not route.get("edges"):
            raise ValueError(f"Vehicle {vehicle.get('id')} has no explicit route")
        edges = route.get("edges", "").split()
        controlled = controlled_route_movements(edges, movements)
        length = sum(float(net.getEdge(edge).getLength()) for edge in edges)
        vehicle_id = vehicle.get("id")
        if not vehicle_id:
            raise ValueError("Route file contains a vehicle without an id")
        catalog[vehicle_id] = {
            "vtype": vehicle.get("type", "DEFAULT_VEHTYPE"),
            "scheduled_depart": float(vehicle.get("depart", 0)),
            "edges": edges,
            "route_length": length,
            "route_through_junction": bool(controlled),
            "first_controlled_movement": f"{controlled[0][0]}->{controlled[0][1]}" if controlled else "",
            "n_controlled_junctions_on_route": int(bool(controlled)),
        }
    return catalog


def _read_tripinfo(xml_text: str) -> dict[str, dict[str, str]]:
    """Return SUMO tripinfo records keyed by vehicle id."""
    if not xml_text.strip():
        return {}
    root = ET.fromstring(xml_text)
    return {item.attrib["id"]: item.attrib for item in root.findall("tripinfo") if item.get("id")}


def _dispatch(
    safety: SignalSafetyLayer, action: object, *, hold_seconds: float | None = None
) -> Accepted | Rejected:
    """Apply one typed action through the sole TLS actuator."""
    if not isinstance(action, Action):
        return Rejected("controller output is not an Action")
    if action.kind == "hold":
        if hold_seconds is not None:
            return safety.request_extend(hold_seconds)
        return Accepted("hold")
    if action.kind == "switch":
        return safety.request_switch()
    if action.kind == "extend" and action.seconds is not None:
        return safety.request_extend(action.seconds)
    if action.kind == "approach" and action.approach:
        return safety.request_green_for_approach(action.approach)
    return Rejected("controller output is malformed")


def _dispatch_network_action(
    controller: Any,
    safety: NetworkSafetyManager,
    tls_id: str,
    state: Any,
    action: Action,
    *,
    hold_seconds: float | None = None,
) -> tuple[Accepted | Rejected, Accepted | Rejected | None, str | None]:
    """Return the original safety result separately from any fallback result."""
    requested = safety.request(
        tls_id,
        action.kind,
        hold_seconds if action.kind == "hold" else action.seconds,
    )
    if isinstance(requested, Rejected) and hasattr(controller, "on_rejection"):
        replacement = controller.on_rejection(tls_id, state, requested.reason)
        fallback_result = safety.request(tls_id, replacement.kind, replacement.seconds)
        return requested, fallback_result, requested.reason
    return requested, None, None


def _trip_rows(
    run_id: str,
    controller_name: str,
    scenario: str,
    seed: int,
    catalog: dict[str, dict[str, Any]],
    tripinfo: dict[str, dict[str, str]],
    departed_at: dict[str, float],
    live_metrics: dict[str, dict[str, float]],
    crossed: set[str],
    sim_end_time: float,
) -> list[dict[str, Any]]:
    """Build Section 11 per-trip rows, including vehicles not completed by the cap."""
    rows: list[dict[str, Any]] = []
    for vehicle_id, meta in catalog.items():
        info = tripinfo.get(vehicle_id, {})
        info_depart = float(info["depart"]) if info.get("depart", "").lstrip("-").replace(".", "", 1).isdigit() else None
        actual = info_depart if info_depart is not None and info_depart >= 0 else departed_at.get(vehicle_id)
        arrival = float(info["arrival"]) if info.get("arrival", "").lstrip("-").replace(".", "", 1).isdigit() and float(info["arrival"]) >= 0 else None
        completed = arrival is not None
        scheduled = float(meta["scheduled_depart"])
        depart_delay = (
            float(info.get("departDelay", max(0.0, (actual or scheduled) - scheduled)))
            if actual is not None else max(0.0, sim_end_time - scheduled)
        )
        duration = float(info.get("duration", arrival - actual if completed and actual is not None else 0.0)) if completed else ""
        trip_time = arrival - scheduled if completed else max(0.0, sim_end_time - scheduled)
        rows.append({
            "run_id": run_id,
            "controller": controller_name,
            "scenario": scenario,
            "seed": seed,
            "vehicle_id": vehicle_id,
            "vtype": info.get("vType", meta["vtype"]),
            "scheduled_depart": scheduled,
            "actual_depart": actual if actual is not None else "",
            "depart_delay": depart_delay,
            "arrival": arrival if arrival is not None else "",
            "duration": duration,
            "trip_time": trip_time,
            "waiting_time": float(info.get("waitingTime", live_metrics.get(vehicle_id, {}).get("waitingTime", 0.0))),
            "time_loss": float(info.get("timeLoss", live_metrics.get(vehicle_id, {}).get("timeLoss", 0.0))),
            "route_length": float(info.get("routeLength", live_metrics.get(vehicle_id, {}).get("routeLength", meta["route_length"]))),
            "completed": completed,
            "route_through_junction": meta["route_through_junction"],
            "first_controlled_movement": meta["first_controlled_movement"],
            "n_controlled_junctions_on_route": meta["n_controlled_junctions_on_route"],
            "passed_controlled_junction": vehicle_id in crossed,
        })
    return rows


def run_episode(
    controller: Any,
    scenario: str,
    seed: int,
    out_dir: str | Path | None = None,
    gui: bool = False,
    family: str = "single",
) -> dict[str, Any]:
    """Run cached demand closed-loop and write non-overwriting step/trip CSVs."""
    token = _STATUS_PATH.set(None)
    try:
        result = _run_episode(controller, scenario, seed, out_dir, gui, family)
        _set_status("finished", sim_time=float(result.get("sim_end_time", 0)))
        return result
    except Exception as exc:
        _set_status("failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        _STATUS_PATH.reset(token)


def _run_episode(
    controller: Any,
    scenario: str,
    seed: int,
    out_dir: str | Path | None = None,
    gui: bool = False,
    family: str = "single",
) -> dict[str, Any]:
    """Implementation shared by both families; status publication is observational."""
    if family == "network":
        return _run_network_episode(controller, scenario, seed, out_dir=out_dir, gui=gui)
    if family != "single":
        raise ValueError(f"Unknown evaluation family {family!r}")
    root = Path(__file__).resolve().parents[2]
    config = load_config(root / "config" / "stms.yaml")
    builder = ScenarioBuilder(root)
    route_file = builder.ensure_routes(scenario, int(seed), write_config=False)
    tls = dict(config["intersection"])
    tls["tls_id"] = str(config["sumo"]["tls_id"])
    tls["min_green_s"] = float(config["signal"]["min_green_s"])
    tls["max_green_s"] = float(config["signal"]["max_green_s"])
    tls["all_red_phases"] = tls.get("all_red_phases", [])
    controller_name = str(getattr(controller, "name", "controller"))
    policy = controller.controller if isinstance(controller, FallbackController) else controller
    controller_parameters = {
        key: getattr(policy, key)
        for key in ("queue_threshold", "wait_threshold_s", "green_seconds")
        if hasattr(policy, key)
    }
    model_path = getattr(policy, "model_path", None)
    if model_path is not None:
        controller_parameters["model_path"] = str(model_path)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"_{controller_name}_{scenario}_s{seed}"
    destination = Path(out_dir).expanduser().resolve() if out_dir else root / "results" / "raw" / run_id
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing run output: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    _STATUS_PATH.set(destination / "status.json")
    _write_status(destination / "status.json", {
        "schema_version": 1, "run_id": run_id, "state": "running", "family": "single",
        "controller": controller_name, "scenario": scenario, "seed": int(seed),
        "sim_time": 0.0, "max_sim_s": float(config["sumo"]["max_sim_s"]),
        "n_tls_controlled": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
        "updated_utc": "", "error": None,
    })
    step_path = destination / "steps.csv"
    trip_path = destination / "trips.csv"
    movements = list(tls["movements"])
    with SumoClient(seed=seed, label=f"episode_{run_id}", route_file=route_file) as client:
        catalog = _route_catalog(route_file, client.net, movements)
        safety = SignalSafetyLayer(client, tls)
        sensors = SumoSensorReader(tls, config["congestion"]["thresholds"])
        controller.reset()
        fixed = controller if isinstance(controller, FixedTimeController) else FixedTimeController(
            tls, float(config["fixed"]["green_s"])
        )
        if not isinstance(controller, FallbackController):
            controller = FallbackController(controller, fixed)
        decision_interval = max(1.0, float(getattr(controller, "decision_interval_s", 1.0)))
        next_decision = 0.0
        last_action = "hold"
        last_accepted = True
        fallback_activations = 0
        decisions = 0
        safety_rejections = 0
        accepted_switches = 0
        policy_actions: Counter[str] = Counter()
        fallback_actions: Counter[str] = Counter()
        phase_usage: Counter[str] = Counter()
        departed_at: dict[str, float] = {}
        live_metrics: dict[str, dict[str, float]] = {}
        crossed: set[str] = set()
        teleported: set[str] = set()
        previous_edge: dict[str, str] = {}
        started = time.perf_counter()
        max_sim = float(config["sumo"]["max_sim_s"])
        log_interval = float(config["logging"]["step_log_every_s"])
        with step_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=STEP_FIELDS)
            writer.writeheader()
            while client.sim_time < max_sim and client.connection.simulation.getMinExpectedNumber() > 0:
                state = sensors.read(client)
                if state.sim_time + 1e-9 >= next_decision:
                    was_fallback = isinstance(controller, FallbackController) and controller.fallback_active
                    action = controller.decide(state)
                    in_fallback = isinstance(controller, FallbackController) and controller.fallback_active
                    if in_fallback and not was_fallback:
                        fallback_activations += 1
                    decisions += 1
                    if state.phase in safety.green_phases:
                        phase_usage[str(state.phase)] += 1
                    if isinstance(action, Action):
                        (fallback_actions if in_fallback else policy_actions)[action.kind] += 1
                    hold_seconds = (
                        decision_interval
                        if controller_name == "rl" and not in_fallback
                        else None
                    )
                    result = _dispatch(safety, action, hold_seconds=hold_seconds)
                    if isinstance(result, Rejected):
                        safety_rejections += 1
                    if isinstance(result, Rejected) and isinstance(controller, FallbackController):
                        was_fallback = controller.fallback_active
                        action = controller.on_rejection(state, result.reason)
                        if controller.fallback_active and not was_fallback:
                            fallback_activations += 1
                        fallback_actions[action.kind if isinstance(action, Action) else "invalid"] += 1
                        result = _dispatch(safety, action)
                    if isinstance(result, Accepted) and isinstance(action, Action) and action.kind == "switch":
                        accepted_switches += 1
                    last_action = (
                        f"fallback:{action.kind}"
                        if isinstance(controller, FallbackController) and controller.fallback_active
                        and isinstance(action, Action)
                        else action.kind if isinstance(action, Action) else "invalid"
                    )
                    last_accepted = isinstance(result, Accepted)
                    next_decision = state.sim_time + decision_interval
                client.step()
                safety_result = safety.tick()
                if isinstance(safety_result, Rejected):
                    raise RuntimeError(  # noqa: TRY004 - indicates a live TLS invariant failure
                        f"Signal safety layer rejected live state: {safety_result.reason}"
                    )
                sim_time = client.sim_time
                for vehicle_id in client.connection.simulation.getDepartedIDList():
                    departed_at[vehicle_id] = sim_time
                teleported.update(client.connection.simulation.getStartingTeleportIDList())
                for vehicle_id in client.connection.vehicle.getIDList():
                    road = str(client.connection.vehicle.getRoadID(vehicle_id))
                    if not road.startswith(":"):
                        previous = previous_edge.get(vehicle_id)
                        if previous is not None and any(
                            item["from_edge"] == previous and item["to_edge"] == road for item in movements
                        ):
                            crossed.add(vehicle_id)
                        previous_edge[vehicle_id] = road
                if abs(sim_time / log_interval - round(sim_time / log_interval)) < 1e-7:
                    snapshot = sensors.read(client)
                    signal_state = client.connection.trafficlight.getRedYellowGreenState(tls["tls_id"])
                    for approach in snapshot.approaches:
                        writer.writerow({
                            "run_id": run_id,
                            "controller": controller_name,
                            "scenario": scenario,
                            "seed": seed,
                            "sim_time": sim_time,
                            "intersection_id": tls["tls_id"],
                            "approach": approach.name,
                            "vehicles": approach.vehicle_count,
                            "halting": approach.halting,
                            "mean_speed": approach.mean_speed,
                            "wait_time": approach.waiting_time,
                            "phase": snapshot.phase,
                            "phase_elapsed": snapshot.phase_elapsed_s,
                            "signal_state": signal_state,
                            "action": last_action,
                            "action_accepted": last_accepted,
                            "congestion": approach.congestion,
                        })
                    stream.flush()
                    _set_status("running", sim_time=sim_time)
        sim_end_time = client.sim_time
        green_durations = {
            str(phase): list(durations)
            for phase, durations in safety.green_durations_by_phase.items()
        }
        final_phase = safety._current_phase()
        if final_phase in safety.green_phases and safety.elapsed_green > 0:
            green_durations[str(final_phase)].append(safety.elapsed_green)
        green_summary = {
            phase: {
                "count": len(durations),
                "mean_green_s": sum(durations) / len(durations) if durations else None,
            }
            for phase, durations in green_durations.items()
        }
        forced_switches = safety.forced_max_green_switches
        total_switches = accepted_switches + forced_switches
        elapsed_wall = time.perf_counter() - started
        client.close()
        tripinfo = _read_tripinfo(client.tripinfo_output)
        trip_rows = _trip_rows(
            run_id, controller_name, scenario, int(seed), catalog, tripinfo,
            departed_at, live_metrics, crossed, sim_end_time,
        )
    with trip_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=TRIP_FIELDS)
        writer.writeheader()
        writer.writerows(trip_rows)
    crossing_mismatches = {
        row["vehicle_id"] for row in trip_rows
        if row["completed"] and row["route_through_junction"] and not row["passed_controlled_junction"]
    }
    result = {
        "run_id": run_id,
        "controller": controller_name,
        "scenario": scenario,
        "seed": int(seed),
        "sim_end_time": sim_end_time,
        "wall_clock_s": elapsed_wall,
        "n_trips": len(trip_rows),
        "n_completed": sum(bool(item["completed"]) for item in trip_rows),
        "teleports": len(teleported),
        "teleported_vehicle_ids": sorted(teleported),
        "completed_route_junction_crossing_mismatches": sorted(crossing_mismatches),
        "crossing_mismatch_teleported_ids": sorted(crossing_mismatches & teleported),
        "crossing_mismatch_without_recorded_teleport": sorted(crossing_mismatches - teleported),
        "fallback_activations": fallback_activations,
        "controller_diagnostics": {
            "decision_count": decisions,
            "policy_action_histogram": {
                action: policy_actions[action] for action in ("hold", "switch", "extend", "approach")
            },
            "fallback_action_histogram": {
                action: fallback_actions[action] for action in ("hold", "switch", "extend", "approach", "invalid")
            },
            "phase_usage_histogram": {
                str(phase): phase_usage[str(phase)] for phase in safety.green_phases
            },
            "mean_green_per_phase": green_summary,
            "safety_rejection_count": safety_rejections,
            "safety_rejection_rate": safety_rejections / decisions if decisions else 0.0,
            "accepted_switches": accepted_switches,
            "forced_max_green_switches": forced_switches,
            "forced_max_green_switch_rate": forced_switches / total_switches if total_switches else 0.0,
        },
        "avg_queue": _mean_csv_field(step_path, "halting"),
        "avg_wait": _mean_csv_field(step_path, "wait_time"),
        "controller_parameters": controller_parameters,
        "out_dir": str(destination),
    }
    (destination / "run.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summarize_run(destination, family="single")
    logger.info("Episode completed: %s", json.dumps(result, sort_keys=True))
    return result


def _run_network_episode(
    controller: Any,
    scenario: str,
    seed: int,
    *,
    out_dir: str | Path | None = None,
    gui: bool = False,
) -> dict[str, Any]:
    """Control every frozen intended TLS and write multi-junction step diagnostics."""
    root = Path(__file__).resolve().parents[2]
    config = load_config(root / "config" / "stms.yaml")
    network = config["network"]
    tls_configs = list(network["tls_configs"])
    if [str(item["tls_id"]) for item in tls_configs] != list(network["controlled_tls"]):
        raise ValueError("network TLS config order differs from the frozen intended list")
    builder = ScenarioBuilder(root, family="network")
    route_file = builder.get_cached_routes(scenario, int(seed))
    controller_name = str(getattr(controller, "name", "controller"))
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"_{controller_name}_{scenario}_s{seed}"
    destination = Path(out_dir).expanduser().resolve() if out_dir else root / "results" / "raw" / run_id
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing run output: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    _STATUS_PATH.set(destination / "status.json")
    _write_status(destination / "status.json", {
        "schema_version": 1, "run_id": run_id, "state": "running", "family": "network",
        "controller": controller_name, "scenario": scenario, "seed": int(seed),
        "sim_time": 0.0, "max_sim_s": float(config["sumo"]["max_sim_s"]),
        "n_tls_controlled": len(tls_configs), "started_utc": datetime.now(timezone.utc).isoformat(),
        "updated_utc": "", "error": None,
    })
    step_path = destination / "steps.csv"
    junction_path = destination / "junctions.csv"
    static_file = root / "SUMO" / "derived" / "network_static_tls.add.xml"
    static_programs = {
        str(item["tls_id"]): str(item["static_program_id"])
        for item in tls_configs if item.get("static_program_id")
    }
    extras = (static_file,) if static_programs else ()
    decision_interval = max(1.0, float(getattr(controller, "decision_interval_s", 1.0)))
    thresholds = config["congestion"]["thresholds"]
    controller.reset()
    samples: dict[str, list[dict[str, float]]] = {str(item["tls_id"]): [] for item in tls_configs}
    stats = {
        tls_id: {
            "switches": 0, "illegal": 0, "fallback": 0, "actions": 0, "ticks": 0,
            "rejection_reasons": Counter(),
        }
        for tls_id in samples
    }
    movement_tls: dict[tuple[str, str], set[str]] = {}
    departed_at: dict[str, float] = {}
    live_metrics: dict[str, dict[str, float]] = {}
    crossed: set[str] = set()
    teleported: set[str] = set()
    previous_edge: dict[str, str] = {}
    catalog: dict[str, dict[str, Any]] = {}
    last_actions = {tls_id: "hold" for tls_id in samples}
    last_accepted = {tls_id: True for tls_id in samples}
    last_requested_accepted = {tls_id: True for tls_id in samples}
    last_fallback_accepted: dict[str, bool | str] = {tls_id: "" for tls_id in samples}
    last_fallback_used = {tls_id: False for tls_id in samples}
    last_rejection_reason = {tls_id: "" for tls_id in samples}
    started = time.perf_counter()
    with SumoClient(
        seed=seed, label=f"network_{run_id}", route_file=route_file,
        extra_additional_files=extras,
    ) as client:
        movements_by_tls = {
            str(item["tls_id"]): controlled_movements(client.net, str(item["tls_id"]))
            for item in tls_configs
        }
        movements = [movement for group in movements_by_tls.values() for movement in group]
        for tls_id, tls_movements in movements_by_tls.items():
            for movement in tls_movements:
                pair = (str(movement["from_edge"]), str(movement["to_edge"]))
                movement_tls.setdefault(pair, set()).add(tls_id)
        safety = NetworkSafetyManager(
            client, tls_configs, excluded_tls=network["excluded_tls"],
            static_program_ids=static_programs,
        )
        sensors = NetworkSensorReader(tls_configs, thresholds)
        catalog = _route_catalog(route_file, client.net, movements)
        for metadata in catalog.values():
            pairs = controlled_route_movements(metadata["edges"], movements)
            metadata["n_controlled_junctions_on_route"] = len(
                {tls for pair in pairs for tls in movement_tls.get(pair, set())}
            )
        next_decision = 0.0
        max_sim = float(config["sumo"]["max_sim_s"])
        with step_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=STEP_FIELDS)
            writer.writeheader()
            while client.sim_time < max_sim and client.connection.simulation.getMinExpectedNumber() > 0:
                state = sensors.read(client)
                if state.sim_time + 1e-9 >= next_decision:
                    actions = controller.decide(state)
                    for tls_id in samples:
                        action = actions.get(tls_id, Action("hold"))
                        fallback = getattr(controller, "controllers", {}).get(tls_id)
                        was_fallback = bool(getattr(fallback, "fallback_active", False))
                        requested, fallback_result, rejection_reason = _dispatch_network_action(
                            controller,
                            safety,
                            tls_id,
                            state,
                            action,
                            hold_seconds=(
                                decision_interval
                                if action.kind == "hold"
                                and (
                                    controller_name == "rl"
                                    or tls_id in getattr(controller, "ppo_tls_ids", ())
                                )
                                else None
                            ),
                        )
                        stats[tls_id]["actions"] += 1
                        if isinstance(requested, Rejected):
                            stats[tls_id]["illegal"] += 1
                            stats[tls_id]["rejection_reasons"][requested.reason] += 1
                        result = fallback_result if fallback_result is not None else requested
                        now_fallback = bool(getattr(fallback, "fallback_active", False))
                        fallback_used = now_fallback or fallback_result is not None
                        if fallback_used and not was_fallback:
                            stats[tls_id]["fallback"] += 1
                        if action.kind == "switch" and isinstance(requested, Accepted):
                            stats[tls_id]["switches"] += 1
                        last_actions[tls_id] = action.kind
                        last_accepted[tls_id] = isinstance(result, Accepted)
                        last_requested_accepted[tls_id] = isinstance(requested, Accepted)
                        last_fallback_accepted[tls_id] = (
                            isinstance(fallback_result, Accepted)
                            if fallback_result is not None else ""
                        )
                        last_fallback_used[tls_id] = fallback_used
                        last_rejection_reason[tls_id] = rejection_reason or ""
                    next_decision = state.sim_time + decision_interval

                client.step()
                for vehicle_id in client.connection.simulation.getDepartedIDList():
                    departed_at[vehicle_id] = client.sim_time
                teleported.update(client.connection.simulation.getStartingTeleportIDList())
                for vehicle_id in client.connection.vehicle.getIDList():
                    road = str(client.connection.vehicle.getRoadID(vehicle_id))
                    if not road.startswith(":"):
                        previous = previous_edge.get(vehicle_id)
                        if previous is not None and (previous, road) in movement_tls:
                            crossed.add(vehicle_id)
                        previous_edge[vehicle_id] = road
                tick_results = safety.tick_all()
                rejected = {tls_id: result.reason for tls_id, result in tick_results.items() if isinstance(result, Rejected)}
                if rejected:
                    raise RuntimeError(f"Network signal safety invariant failed: {rejected}")
                for tls_id in samples:
                    if controller_name in {"rl", "hybrid"} and hasattr(controller, "record_tick"):
                        controller.record_tick(tls_id)
                if abs(client.sim_time / float(config["logging"]["step_log_every_s"])
                       - round(client.sim_time / float(config["logging"]["step_log_every_s"]))) < 1e-7:
                    snapshot = sensors.read(client)
                    for tls_id, junction in snapshot.junctions.items():
                        for approach in junction.approaches:
                            writer.writerow({
                                "run_id": run_id, "controller": controller_name,
                                "scenario": scenario, "seed": int(seed), "sim_time": client.sim_time,
                                "intersection_id": tls_id, "approach": approach.name,
                                "vehicles": approach.vehicle_count, "halting": approach.halting,
                                "mean_speed": approach.mean_speed, "wait_time": approach.waiting_time,
                                "phase": junction.phase, "phase_elapsed": junction.phase_elapsed_s,
                                "signal_state": client.connection.trafficlight.getRedYellowGreenState(tls_id),
                                "action": last_actions[tls_id], "action_accepted": last_accepted[tls_id],
                                "requested_action_accepted": last_requested_accepted[tls_id],
                                "fallback_action_accepted": last_fallback_accepted[tls_id],
                                "fallback_used": last_fallback_used[tls_id],
                                "safety_rejection_reason": last_rejection_reason[tls_id],
                                "congestion": approach.congestion,
                            })
                        values = [
                            {"queue": float(item.halting or 0), "wait": float(item.waiting_time or 0),
                             "congested": 1.0 if item.congestion == "High" else 0.0}
                            for item in junction.approaches
                        ]
                        samples[tls_id].append({
                            "queue": sum(item["queue"] for item in values),
                            "wait": sum(item["wait"] for item in values) / max(1, len(values)),
                            "congested": float(any(item["congested"] for item in values)),
                            "throughput": float(junction.totals.get("throughput_veh_min", 0.0)),
                        })
                        stats[tls_id]["ticks"] += 1
                    stream.flush()
                    _set_status("running", sim_time=client.sim_time)
        sim_end_time = client.sim_time
        mean_green_by_tls: dict[str, dict[str, float | None]] = {}
        for tls_id, layer in safety.layers.items():
            durations = {phase: list(values) for phase, values in layer.green_durations_by_phase.items()}
            current_phase = layer._current_phase()
            if current_phase in layer.green_phases and layer.elapsed_green > 0:
                durations[current_phase].append(layer.elapsed_green)
            mean_green_by_tls[tls_id] = {
                str(phase): (sum(values) / len(values) if values else None)
                for phase, values in durations.items()
            }
        client.close()
        tripinfo = _read_tripinfo(client.tripinfo_output)
    trip_rows = _trip_rows(run_id, controller_name, scenario, int(seed), catalog,
                           tripinfo, departed_at, live_metrics, crossed, sim_end_time)
    trip_path = destination / "trips.csv"
    with trip_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=TRIP_FIELDS)
        writer.writeheader()
        writer.writerows(trip_rows)
    wall_clock = time.perf_counter() - started
    controller_parameters = {}
    for tls_id, wrapped in getattr(controller, "controllers", {}).items():
        policy = getattr(wrapped, "controller", wrapped)
        controller_parameters[tls_id] = {
            key: getattr(policy, key)
            for key in ("queue_threshold", "wait_threshold_s", "green_seconds")
            if hasattr(policy, key)
        }
    network_diagnostics = controller.diagnostics() if hasattr(controller, "diagnostics") else {}
    tls_diagnostics = network_diagnostics.get("per_junction", {})
    if controller_name == "hybrid":
        ai_coverage, coverage_statuses = classify_hybrid_coverage(
            tuple(samples), tuple(getattr(controller, "ppo_tls_ids", ())), tls_diagnostics,
            float(config["eval"]["ai_coverage_min_share"]),
        )
    elif controller_name == "rl":
        ai_coverage, coverage_statuses = classify_ai_coverage(
            [float(tls_diagnostics.get(tls_id, {}).get("ppo_tick_share", 0.0)) for tls_id in samples],
            float(config["eval"]["ai_coverage_min_share"]),
        )
    else:
        ai_coverage, coverage_statuses = "none", [controller_name] * len(samples)
    n_tls_ai = sum(status == "rl" for status in coverage_statuses)
    coverage_by_tls = dict(zip(samples, coverage_statuses, strict=True))
    with junction_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=NETWORK_JUNCTION_FIELDS)
        writer.writeheader()
        for tls_id, observations in samples.items():
            count = len(observations)
            averages = {
                field: (sum(item[field] for item in observations) / count) if count else 0.0
                for field in ("queue", "wait", "congested", "throughput")
            }
            mean_green = mean_green_by_tls[tls_id]
            policy = tls_diagnostics.get(tls_id, {})
            ppo_tick_share = float(policy.get("ppo_tick_share", 0.0))
            controlled_by = coverage_by_tls[tls_id]
            decisions = stats[tls_id]["actions"]
            hold_overridden = int(policy.get("hold_overridden", 0))
            writer.writerow({
                "run_id": run_id, "controller": controller_name, "scenario": scenario, "seed": int(seed),
                "tls_id": tls_id, "controlled_by": controlled_by, "avg_queue": averages["queue"],
                "max_queue": max((item["queue"] for item in observations), default=0.0),
                "avg_wait": averages["wait"], "frac_time_high_congestion": averages["congested"],
                "throughput_veh_per_min": averages["throughput"], "n_switches": stats[tls_id]["switches"],
                "n_forced_max_green": safety.layers[tls_id].forced_max_green_switches,
                "n_illegal_actions": stats[tls_id]["illegal"],
                "illegal_action_rate": stats[tls_id]["illegal"] / decisions if decisions else 0.0,
                "n_hold_overridden": hold_overridden,
                "hold_overridden_rate": hold_overridden / decisions if decisions else 0.0,
                "fallback_activations": stats[tls_id]["fallback"], "n_ticks": stats[tls_id]["ticks"],
                "rejection_reason_counts": json.dumps(
                    dict(sorted(stats[tls_id]["rejection_reasons"].items())), sort_keys=True
                ),
                "ppo_tick_share": ppo_tick_share,
                "action_histogram": json.dumps(policy.get("action_histogram", {}), sort_keys=True),
                "applied_action_histogram": json.dumps(policy.get("applied_action_histogram", {}), sort_keys=True),
                "phase_usage": json.dumps(policy.get("phase_usage", {}), sort_keys=True),
                "mean_green_by_phase_s": json.dumps(mean_green, sort_keys=True),
            })
    result = {
        "run_id": run_id, "family": "network", "controller": controller_name,
        "scenario": scenario, "seed": int(seed), "sim_end_time": sim_end_time,
        "wall_clock_s": wall_clock, "n_trips": len(trip_rows),
        "n_completed": sum(bool(item["completed"]) for item in trip_rows),
        "teleports": len(teleported), "teleported_vehicle_ids": sorted(teleported),
        "n_tls_controlled": len(samples), "n_tls_ai": n_tls_ai,
        "ai_coverage": ai_coverage, "controller_parameters": controller_parameters,
        "controller_diagnostics": network_diagnostics,
        "out_dir": str(destination),
    }
    (destination / "run.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summarize_run(destination, family="network")
    return result


def _mean_csv_field(path: Path, field: str) -> float:
    """Return the arithmetic mean for a numeric column in a step log."""
    with path.open(encoding="utf-8", newline="") as stream:
        values = [float(row[field]) for row in csv.DictReader(stream) if row.get(field) not in {None, ""}]
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    """Run one fixed or rule-based episode from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["single", "network"], default="single")
    parser.add_argument("--controller", choices=["fixed", "rule", "rl"], required=True)
    parser.add_argument("--scenario", default="medium")
    parser.add_argument("--seed", type=int, default=3000)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    if args.family == "network":
        config = load_config()
        controller = get_network_controller(
            args.controller, list(config["network"]["tls_configs"]), config
        )
    else:
        controller = get_controller(args.controller)
    result = run_episode(controller, args.scenario, args.seed, args.out, args.gui, family=args.family)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
