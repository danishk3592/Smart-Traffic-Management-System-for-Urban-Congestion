"""Run one controller episode through the project signal-safety layer."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from Ai.common.config import load_config
from Ai.common.junction import controlled_route_movements
from Ai.common.metrics import summarize_run
from Ai.common.sumo_client import SumoClient
from Ai.common.traffic_state import SumoSensorReader
from Ai.controllers.base import Action
from Ai.controllers.fallback import FallbackController
from Ai.controllers.fixed_time import FixedTimeController
from Ai.controllers.registry import get_controller
from Ai.controllers.safety import Accepted, Rejected, SignalSafetyLayer
from scripts.make_scenarios import ScenarioBuilder

logger = logging.getLogger(__name__)

STEP_FIELDS = (
    "run_id", "controller", "scenario", "seed", "sim_time", "intersection_id",
    "approach", "vehicles", "halting", "mean_speed", "wait_time", "phase",
    "phase_elapsed", "signal_state", "action", "action_accepted", "congestion",
)
TRIP_FIELDS = (
    "run_id", "controller", "scenario", "seed", "vehicle_id", "vtype",
    "scheduled_depart", "actual_depart", "depart_delay", "arrival", "duration",
    "trip_time", "waiting_time", "time_loss", "route_length", "completed",
    "route_through_junction", "first_controlled_movement",
    "n_controlled_junctions_on_route", "passed_controlled_junction",
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


def _dispatch(safety: SignalSafetyLayer, action: object) -> Accepted | Rejected:
    """Apply one typed action through the sole TLS actuator."""
    if not isinstance(action, Action):
        return Rejected("controller output is not an Action")
    if action.kind == "hold":
        return Accepted("hold")
    if action.kind == "switch":
        return safety.request_switch()
    if action.kind == "extend" and action.seconds is not None:
        return safety.request_extend(action.seconds)
    if action.kind == "approach" and action.approach:
        return safety.request_green_for_approach(action.approach)
    return Rejected("controller output is malformed")


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
) -> dict[str, Any]:
    """Run cached demand closed-loop and write non-overwriting step/trip CSVs."""
    root = Path(__file__).resolve().parents[2]
    config = load_config(root / "config" / "stms.yaml")
    builder = ScenarioBuilder(root)
    route_file = builder.ensure_routes(scenario, int(seed))
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
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"_{controller_name}_{scenario}_s{seed}"
    destination = Path(out_dir).expanduser().resolve() if out_dir else root / "results" / "raw" / run_id
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing run output: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
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
                    if isinstance(controller, FallbackController) and controller.fallback_active and not was_fallback:
                        fallback_activations += 1
                    result = _dispatch(safety, action)
                    if isinstance(result, Rejected) and isinstance(controller, FallbackController):
                        was_fallback = controller.fallback_active
                        action = controller.on_rejection(state, result.reason)
                        if controller.fallback_active and not was_fallback:
                            fallback_activations += 1
                        result = _dispatch(safety, action)
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
        sim_end_time = client.sim_time
        client.close()
        tripinfo = _read_tripinfo(client.tripinfo_output)
        trip_rows = _trip_rows(
            run_id, controller_name, scenario, int(seed), catalog, tripinfo,
            departed_at, live_metrics, crossed, sim_end_time,
        )
        elapsed_wall = time.perf_counter() - started
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
        "avg_queue": _mean_csv_field(step_path, "halting"),
        "avg_wait": _mean_csv_field(step_path, "wait_time"),
        "controller_parameters": controller_parameters,
        "out_dir": str(destination),
    }
    (destination / "run.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summarize_run(destination, family="single")
    logger.info("Episode completed: %s", json.dumps(result, sort_keys=True))
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
    if args.family != "single":
        parser.error("network episodes are added in roadmap task T7.2")
    controller = get_controller(args.controller)
    result = run_episode(controller, args.scenario, args.seed, args.out, args.gui)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
