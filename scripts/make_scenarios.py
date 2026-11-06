"""Build deterministic, cached SUMO scenarios and measure their native programs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

import sumolib
import yaml

from Ai.common.config import load_config
from Ai.common.junction import controlled_movements, route_uses_controlled_movement
from Ai.common.sumo_client import SumoClient

GENERATOR_VERSION = "1"
SCENARIOS = (
    "balanced",
    "directional_ns",
    "directional_ew",
    "low",
    "medium",
    "heavy",
    "rush_hour",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bearing(edge: Any) -> float:
    shape = edge.getShape()
    if len(shape) < 2:
        return 0.0
    start, end = shape[-2:]
    return math.degrees(math.atan2(end[0] - start[0], end[1] - start[1])) % 360


def _angular_distance(first: float, second: float) -> float:
    return abs((first - second + 180) % 360 - 180)


def _edge_ids(path: list[Any] | None) -> list[str] | None:
    if not path:
        return None
    return [edge.getID() for edge in path]


def _xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _write_if_changed(path: Path, data: bytes) -> None:
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    os.replace(temp_path, path)


def _backup_existing(path: Path) -> None:
    if not path.is_file():
        return
    digest = _sha256(path)[:12]
    backup = path.with_name(f"{path.stem}.stale_{digest}{path.suffix}")
    if not backup.exists():
        shutil.copy2(path, backup)


class ScenarioBuilder:
    """Generate, cache and measure scenarios from one verified SUMO network."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(__file__).resolve().parents[1]).resolve()
        self.config = load_config(self.root / "config" / "stms.yaml")
        self.demand = self.config["demand"]
        self.sumo = self.config["sumo"]
        self.net_path = (self.root / self.sumo["config"]).resolve()
        sumo_xml = ET.parse(self.net_path).getroot()
        net_value = sumo_xml.find("input/net-file").get("value")
        self.net_path = (self.net_path.parent / net_value).resolve()
        self.net = sumolib.net.readNet(str(self.net_path), withPrograms=True)
        self.tls_id = self.sumo["tls_id"]
        self.movements = controlled_movements(self.net, self.tls_id)
        self.movement_pairs = {
            (item["from_edge"], item["to_edge"]) for item in self.movements
        }
        self.edges = sorted(
            (edge for edge in self.net.getEdges()
             if not edge.getFunction() and edge.getLength() >= 25),
            key=lambda edge: edge.getID(),
        )
        self.edge_by_id = {edge.getID(): edge for edge in self.edges}
        self._catalogs: dict[str, tuple[list[tuple[str, str, tuple[str, ...]]],
                                        list[tuple[str, str, tuple[str, ...]]]]] = {}
        self.duarouter = shutil.which("duarouter")
        if self.duarouter is None:
            raise FileNotFoundError("duarouter executable is not available on PATH")
        if not self.movement_pairs:
            raise ValueError(f"No controlled movements found for configured TLS {self.tls_id}")

    def _scenario_values(self, scenario: str) -> dict[str, Any]:
        try:
            values = self.demand["scenarios"][scenario]
        except KeyError as exc:
            raise ValueError(f"Unknown scenario: {scenario}") from exc
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        if not isinstance(values.get("vehicles"), int) or values["vehicles"] < 1:
            raise ValueError(f"Invalid vehicle count for scenario {scenario}")
        return values

    def _origin_edges(self, scenario: str) -> list[Any]:
        if scenario not in {"directional_ns", "directional_ew"}:
            return self.edges
        axis = 0.0 if scenario == "directional_ns" else 90.0

        def score(edge: Any) -> tuple[float, str]:
            angle = _bearing(edge)
            return min(_angular_distance(angle, axis), _angular_distance(angle, axis + 180)), edge.getID()

        ordered = sorted(self.edges, key=score)
        return ordered[: max(1, len(ordered) // 2)]

    def _candidate_catalog(
        self, scenario: str
    ) -> tuple[list[tuple[str, str, tuple[str, ...]]],
               list[tuple[str, str, tuple[str, ...]]]]:
        if scenario in self._catalogs:
            return self._catalogs[scenario]
        target = int(self.demand.get("candidate_pool_size", 300))
        rng = random.Random(741_000 + SCENARIOS.index(scenario))
        origins = self._origin_edges(scenario)
        destinations = self.edges
        movements = self.movements
        through: list[tuple[str, str, tuple[str, ...]]] = []
        other: list[tuple[str, str, tuple[str, ...]]] = []
        through_seen: set[tuple[str, str, tuple[str, ...]]] = set()
        other_seen: set[tuple[str, str]] = set()
        attempts = 0
        max_attempts = target * 1000

        while len(through) < target or len(other) < target:
            attempts += 1
            if attempts > max_attempts:
                raise RuntimeError(
                    f"Could not find enough shortest-path pairs for {scenario}: "
                    f"through={len(through)}/{target}, other={len(other)}/{target}"
                )
            origin = rng.choice(origins)
            destination = rng.choice(destinations)
            if origin == destination:
                continue

            if len(through) < target:
                movement = rng.choice(movements)
                from_id, to_id = movement["from_edge"], movement["to_edge"]
                if origin.getID() in {from_id, to_id} or destination.getID() in {from_id, to_id}:
                    continue
                prefix, _ = self.net.getShortestPath(origin, self.net.getEdge(from_id))
                suffix, _ = self.net.getShortestPath(self.net.getEdge(to_id), destination)
                if prefix is None or suffix is None:
                    continue
                route = _edge_ids(prefix) + [to_id] + (_edge_ids(suffix) or [])[1:]
                if not route_uses_controlled_movement(route, self.movements):
                    raise RuntimeError("Internal error: forced movement missing from candidate path")
                key = (origin.getID(), destination.getID(), (from_id, to_id))
                if key not in through_seen:
                    through.append(key)
                    through_seen.add(key)

            if len(other) < target:
                path, _ = self.net.getShortestPath(origin, destination)
                route = _edge_ids(path)
                if route and not route_uses_controlled_movement(route, self.movements):
                    pair = (origin.getID(), destination.getID())
                    if pair not in other_seen:
                        other.append((pair[0], pair[1], ()))
                        other_seen.add(pair)

        self._catalogs[scenario] = (through, other)
        return through, other

    def _departures(
        self, scenario: str, count: int, rng: random.Random
    ) -> list[float]:
        horizon = int(self.demand["scenario_horizon_s"])
        scenario_values = self._scenario_values(scenario)
        if scenario != "rush_hour":
            times = [rng.random() * horizon for _ in range(count)]
        else:
            start, end = scenario_values["peak_window_s"]
            peak_share = float(scenario_values["peak_trip_share"])
            times = []
            for _ in range(count):
                if rng.random() < peak_share:
                    times.append(rng.uniform(start, end))
                elif rng.random() < 0.5:
                    times.append(rng.uniform(0, start))
                else:
                    times.append(rng.uniform(end, horizon))
        return sorted(round(value, 3) for value in times)

    def _type_choices(self, rng: random.Random, count: int) -> list[str]:
        mixture = self.demand["vehicle_mix"]
        names = sorted(mixture)
        weights = [float(mixture[name]) for name in names]
        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("demand.vehicle_mix must have positive, non-negative weights")
        total = sum(weights)
        return [rng.choices(names, weights=[weight / total for weight in weights])[0]
                for _ in range(count)]

    def _trips_xml(self, scenario: str, seed: int) -> bytes:
        values = self._scenario_values(scenario)
        count = int(values["vehicles"])
        rng = random.Random(seed)
        share = float(values.get("junction_share", self.demand["junction_share_target"]))
        if not 0 <= share <= 1:
            raise ValueError(f"Invalid junction share for scenario {scenario}")
        through_count = round(count * share)
        through_pool, other_pool = self._candidate_catalog(scenario)
        chosen_through = [rng.choice(through_pool) for _ in range(through_count)]
        chosen_other = [rng.choice(other_pool) for _ in range(count - through_count)]
        selected = [(item, True) for item in chosen_through]
        selected.extend((item, False) for item in chosen_other)
        departures = self._departures(scenario, count, rng)
        type_names = self._type_choices(rng, count)
        rng.shuffle(selected)

        root = ET.Element("routes")
        for name in sorted(self.demand["vehicle_mix"]):
            ET.SubElement(
                root,
                "vType",
                {"id": name, "vClass": name},
            )
        for index, ((origin, destination, via), is_through) in enumerate(selected):
            attrs = {
                "id": f"veh_{scenario}_{seed}_{index:06d}",
                "type": type_names[index],
                "depart": f"{departures[index]:.3f}",
                "from": origin,
                "to": destination,
                "departLane": "best",
                "departSpeed": "max",
            }
            if is_through:
                attrs["via"] = " ".join(via)
            ET.SubElement(root, "trip", attrs)
        return _xml_bytes(root)

    def _scenario_config(self, scenario: str) -> Path:
        scenario_dir = self.root / "SUMO" / "scenarios" / scenario
        scenario_dir.mkdir(parents=True, exist_ok=True)
        root = ET.Element("configuration")
        inputs = ET.SubElement(root, "input")
        ET.SubElement(inputs, "net-file", {"value": "../../No_Polygon_Map/osm.net.xml"})
        ET.SubElement(inputs, "route-files", {"value": "seed_1000/routes.rou.xml"})
        time = ET.SubElement(root, "time")
        ET.SubElement(time, "begin", {"value": "0"})
        ET.SubElement(
            time, "end", {"value": str(int(self.demand["scenario_max_sim_s"]))}
        )
        processing = ET.SubElement(root, "processing")
        ET.SubElement(
            processing,
            "time-to-teleport",
            {"value": str(int(self.sumo["time_to_teleport_s"]))},
        )
        report = ET.SubElement(root, "report")
        ET.SubElement(report, "no-step-log", {"value": "true"})
        ET.SubElement(report, "duration-log.statistics", {"value": "false"})
        path = scenario_dir / f"{scenario}.sumocfg"
        _write_if_changed(path, _xml_bytes(root))
        return path

    def _config_hash(self, scenario: str) -> str:
        parameters = {
            "generator_version": GENERATOR_VERSION,
            "net_sha256": _sha256(self.net_path),
            "scenario": scenario,
            "parameters": self._scenario_values(scenario),
            "horizon_s": self.demand["scenario_horizon_s"],
            "vehicle_mix": self.demand["vehicle_mix"],
            "tls_id": self.tls_id,
            "movements": self.movements,
        }
        return _stable_hash(parameters)

    def get_cached_routes(self, scenario: str, seed: int) -> Path:
        """Validate and return a training route cache without writing or routing."""
        values = self._scenario_values(scenario)
        seed = int(seed)
        if seed < 0:
            raise ValueError("seed must be non-negative")
        seed_dir = self.root / "SUMO" / "scenarios" / scenario / f"seed_{seed}"
        route_path = seed_dir / "routes.rou.xml"
        manifest_path = seed_dir / "manifest.json"
        if not route_path.is_file() or not manifest_path.is_file():
            raise FileNotFoundError(
                f"validated cached routes missing for {scenario}/seed_{seed}; "
                "prepare the training pool before starting the environment"
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise TypeError("route manifest must be a JSON object")
            route_hash = _sha256(route_path)
            expected = {
                "generator_version": GENERATOR_VERSION,
                "config_hash": self._config_hash(scenario),
                "net_sha256": _sha256(self.net_path),
                "scenario": scenario,
                "seed": seed,
                "route_sha256": route_hash,
            }
            mismatches = [
                key for key, value in expected.items()
                if manifest.get(key) != value
            ]
            if mismatches:
                raise ValueError(
                    f"invalid route cache for {scenario}/seed_{seed}; "
                    f"manifest mismatch: {', '.join(mismatches)}"
                )
            root = ET.parse(route_path).getroot()
            vehicles = root.findall("vehicle")
            expected_count = int(values["vehicles"])
            if (
                len(vehicles) != expected_count
                or manifest.get("vehicle_count") != expected_count
            ):
                raise ValueError(
                    f"invalid route cache for {scenario}/seed_{seed}; "
                    f"expected {expected_count} vehicles, found {len(vehicles)}"
                )
            for vehicle in vehicles:
                route = vehicle.find("route")
                edges = route.get("edges", "").split() if route is not None else []
                if not edges or any(self.net.getEdge(edge) is None for edge in edges):
                    raise ValueError(
                        f"invalid route cache for {scenario}/seed_{seed}; "
                        f"vehicle {vehicle.get('id')} has a missing or unknown route edge"
                    )
        except (OSError, json.JSONDecodeError, ET.ParseError) as exc:
            raise ValueError(
                f"invalid route cache for {scenario}/seed_{seed}: {exc}"
            ) from exc
        return route_path

    def ensure_routes(self, scenario: str, seed: int, *, force: bool = False) -> Path:
        """Return a cached route file, regenerating it when its manifest becomes stale."""
        values = self._scenario_values(scenario)
        del values
        seed = int(seed)
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self._scenario_config(scenario)
        seed_dir = self.root / "SUMO" / "scenarios" / scenario / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        route_path = seed_dir / "routes.rou.xml"
        manifest_path = seed_dir / "manifest.json"
        config_hash = self._config_hash(scenario)

        if not force and route_path.is_file() and manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if (
                    manifest.get("config_hash") == config_hash
                    and manifest.get("route_sha256") == _sha256(route_path)
                ):
                    return route_path
            except (OSError, json.JSONDecodeError):
                pass

        trip_bytes = self._trips_xml(scenario, seed)
        trips_path = seed_dir / "trips.trips.xml"
        route_temp = seed_dir / ".routes.pending.rou.xml"
        trips_temp = seed_dir / ".trips.pending.trips.xml"
        alt_fd, alt_name = tempfile.mkstemp(
            prefix=f"stms_{scenario}_{seed}_", suffix=".rou.alt.xml"
        )
        os.close(alt_fd)
        alt_temp = Path(alt_name)
        trips_temp.write_bytes(trip_bytes)
        command = [
            self.duarouter,
            "--net-file",
            str(self.net_path),
            "--route-files",
            str(trips_temp),
            "--output-file",
            str(route_temp),
            "--alternatives-output",
            str(alt_temp),
            "--max-alternatives",
            "1",
            "--seed",
            str(seed),
            "--routing-algorithm",
            "dijkstra",
            "--no-step-log",
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False, timeout=600
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"duarouter failed for {scenario}/seed_{seed}: "
                    f"{completed.stderr[-2000:]} {completed.stdout[-1000:]}"
                )
            route_root = ET.parse(route_temp).getroot()
            route_elements = route_root.findall("vehicle")
            actual_count = len(route_elements)
            if actual_count != int(self._scenario_values(scenario)["vehicles"]):
                raise RuntimeError(
                    f"duarouter emitted {actual_count} vehicles; expected "
                    f"{self._scenario_values(scenario)['vehicles']}"
                )
            for vehicle in route_elements:
                route_element = vehicle.find("route")
                if route_element is None or not route_element.get("edges"):
                    raise RuntimeError(f"duarouter emitted a vehicle without a route: {vehicle.get('id')}")
            canonical = _xml_bytes(route_root)
            planned_share = self._route_share(route_elements)
            if (
                scenario in {"balanced", "directional_ns", "directional_ew", "medium", "heavy", "rush_hour"}
                and planned_share < float(self.demand["junction_share_min"])
            ):
                raise RuntimeError(
                    f"{scenario} junction share {planned_share:.3f} is below "
                    f"demand.junction_share_min={self.demand['junction_share_min']}"
                )
            if force and route_path.is_file() and route_path.read_bytes() != canonical:
                raise RuntimeError(
                    f"Forced regeneration was not byte-identical for {scenario}/seed_{seed}; "
                    "the existing route cache was preserved."
                )

            route_hash = hashlib.sha256(canonical).hexdigest()
            manifest = {
                "generator_version": GENERATOR_VERSION,
                "config_hash": config_hash,
                "net_sha256": _sha256(self.net_path),
                "scenario": scenario,
                "seed": seed,
                "vehicle_count": actual_count,
                "planned_junction_trips": sum(
                    route_uses_controlled_movement(
                        route_element.get("edges", "").split(), self.movements
                    )
                    for vehicle in route_elements
                    for route_element in [vehicle.find("route")]
                ),
                "planned_junction_share": round(planned_share, 6),
                "trip_input_sha256": hashlib.sha256(trip_bytes).hexdigest(),
                "route_sha256": route_hash,
            }
            manifest_bytes = (
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")

            if route_path.is_file() and route_path.read_bytes() != canonical:
                _backup_existing(route_path)
            if trips_path.is_file() and trips_path.read_bytes() != trip_bytes:
                _backup_existing(trips_path)
            if manifest_path.is_file() and manifest_path.read_bytes() != manifest_bytes:
                _backup_existing(manifest_path)
            _write_if_changed(route_path, canonical)
            _write_if_changed(trips_path, trip_bytes)
            _write_if_changed(manifest_path, manifest_bytes)
        finally:
            for temp_path in (route_temp, trips_temp, alt_temp):
                if temp_path.exists():
                    temp_path.unlink()
        return route_path

    def _route_share(self, vehicles: list[ET.Element]) -> float:
        if not vehicles:
            return 0.0
        count = 0
        for vehicle in vehicles:
            route = vehicle.find("route")
            if route is not None and route_uses_controlled_movement(
                route.get("edges", "").split(), self.movements
            ):
                count += 1
        return count / len(vehicles)

    def measure(self, scenario: str, seed: int = 1000) -> dict[str, Any]:
        """Measure demand, completion, teleports, backlog and pilot queue natively."""
        route_path = self.ensure_routes(scenario, seed)
        route_root = ET.parse(route_path).getroot()
        vehicles = route_root.findall("vehicle")
        planned_through = self._route_share(vehicles)
        scenario_config = self._scenario_config(scenario)
        relative_config = scenario_config.relative_to(self.root).as_posix()
        with tempfile.TemporaryDirectory(prefix="stms_scenario_config_") as temp_dir:
            yaml_path = Path(temp_dir) / "sumo.yaml"
            yaml_path.write_text(
                yaml.safe_dump(
                    {"sumo": {"config": relative_config, "tls_id": self.tls_id}},
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            teleports: set[str] = set()
            arrived_ids: set[str] = set()
            departed_ids: set[str] = set()
            queue_total = 0
            queue_max = 0
            congested_steps = 0
            pending_max = 0
            pending_at_horizon = 0
            horizon_recorded = False
            step_count = 0
            with SumoClient(config_path=yaml_path, seed=seed) as client:
                conn = client.connection
                lane_ids = [
                    lane for approach in self.config["intersection"]["approaches"]
                    for lane in approach["lanes"]
                ]
                max_sim_s = int(self.demand["scenario_max_sim_s"])
                horizon = int(self.demand["scenario_horizon_s"])
                while (
                    client.sim_time < max_sim_s
                    and conn.simulation.getMinExpectedNumber() > 0
                ):
                    client.step()
                    step_count += 1
                    queue = sum(
                        int(conn.lane.getLastStepHaltingNumber(lane_id))
                        for lane_id in lane_ids
                    )
                    queue_total += queue
                    queue_max = max(queue_max, queue)
                    congested_steps += queue >= 5
                    pending_max = max(pending_max, len(conn.simulation.getPendingVehicles()))
                    arrived_ids.update(conn.simulation.getArrivedIDList())
                    departed_ids.update(conn.simulation.getDepartedIDList())
                    if client.sim_time >= horizon and not horizon_recorded:
                        pending_at_horizon = len(conn.simulation.getPendingVehicles())
                        horizon_recorded = True
                    teleports.update(conn.simulation.getStartingTeleportIDList())
                arrived = len(arrived_ids)
                departed = len(departed_ids)
                min_expected = int(conn.simulation.getMinExpectedNumber())
                sim_time = client.sim_time
            sumo_log = client.sumo_output

        total = len(vehicles)
        warnings = [line for line in sumo_log.splitlines() if "warning" in line.casefold()]
        return {
            "scenario": scenario,
            "seed": seed,
            "total_trips": total,
            "planned_junction_trips": sum(
                route_uses_controlled_movement(
                    item.find("route").get("edges", "").split(), self.movements
                )
                for item in vehicles
                if item.find("route") is not None
            ),
            "planned_junction_share": round(planned_through, 6),
            "departed": departed,
            "arrived": arrived,
            "unfinished": max(0, total - arrived),
            "completion_rate": round(arrived / total if total else 0.0, 6),
            "teleported_unique": len(teleports),
            "teleport_share": round(len(teleports) / total if total else 0.0, 6),
            "simulated_s": sim_time,
            "min_expected_at_end": min_expected,
            "pending_max": pending_max,
            "pending_at_horizon": pending_at_horizon,
            "mean_pilot_halting": round(queue_total / max(1, step_count), 4),
            "max_pilot_halting": queue_max,
            "congested_time_share": round(congested_steps / max(1, step_count), 6),
            "warning_lines": len(warnings),
            "warnings": warnings,
        }


_DEFAULT_BUILDER: ScenarioBuilder | None = None


def get_cached_routes(scenario: str, seed: int) -> Path:
    """Return a validated cached route file; never generate or rewrite demand."""
    global _DEFAULT_BUILDER
    if _DEFAULT_BUILDER is None:
        _DEFAULT_BUILDER = ScenarioBuilder()
    return _DEFAULT_BUILDER.get_cached_routes(scenario, seed)


def ensure_routes(scenario: str, seed: int) -> Path:
    """Reuse valid cached routes or generate them from the recorded demand config."""
    global _DEFAULT_BUILDER
    if _DEFAULT_BUILDER is None:
        _DEFAULT_BUILDER = ScenarioBuilder()
    return _DEFAULT_BUILDER.ensure_routes(scenario, seed)


def _write_measurements(results: list[dict[str, Any]], root: Path) -> None:
    lines = [
        "# Scenario generation and native-program measurements", "",
        f"Measured with SUMO's native signal programs on {date.today().isoformat()}. Planned junction share uses the shared controlled-movement definition from Ai.common.junction. Congestion indicators count pilot halting vehicles; congested-time share is the fraction of simulated seconds with at least five halting vehicles across configured approach lanes. Teleport share uses unique vehicles that started teleporting divided by planned trips.", "",
        "| Scenario | Seed | Trips | Planned junction trips | Junction share | Arrived | Completion | Unique teleports | Teleport share | Pending max | Pending at 3600 s | Mean pilot halting | Max pilot halting | Congested-time share | Simulated seconds | SUMO warnings |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['scenario']} | {row['seed']} | {row['total_trips']} | "
            f"{row['planned_junction_trips']} | {row['planned_junction_share']:.3f} | "
            f"{row['arrived']} | {row['completion_rate']:.3f} | "
            f"{row['teleported_unique']} | {row['teleport_share']:.3f} | "
            f"{row['pending_max']} | {row['pending_at_horizon']} | "
            f"{row['mean_pilot_halting']:.2f} | {row['max_pilot_halting']} | "
            f"{row['congested_time_share']:.3f} | {row['simulated_s']:.0f} | "
            f"{row['warning_lines']} |"
        )
    lines += ["", "## Stop-gate checks", ""]
    for row in results:
        if row["scenario"] in {"medium", "heavy", "rush_hour"}:
            lines.append(
                f"- {row['scenario']}: junction share {row['planned_junction_share']:.3f} "
                f"(minimum 0.300); teleport share {row['teleport_share']:.3f} "
                f"(design target <0.010)."
            )
    lines += [
        "",
        (
            "The low scenario is reported honestly even if its measured share is below 0.300. "
            "Teleport shares are recorded here; T1.4 repeats the fixed-time gate under the "
            "specified controller and scenario protocol."
        ),
        "",
    ]
    (root / "docs" / "scenarios.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Generate and measure all seven scenarios")
    group.add_argument("--train-pool", action="store_true", help="Pre-generate the configured training pool")
    parser.add_argument("--scenario", choices=SCENARIOS, help="Generate one scenario without measuring it")
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    builder = ScenarioBuilder(root)
    selected_modes = sum((args.all, args.train_pool, args.scenario is not None))
    if selected_modes != 1:
        parser.error("choose exactly one of --all, --train-pool, or --scenario")
    if not args.all and not args.train_pool and not args.scenario:
        parser.error("choose --all, --train-pool, or --scenario")

    if args.train_pool:
        pool = builder.demand["train_pool"]
        seeds = range(
            int(pool["seed_min"]),
            int(pool["seed_min"]) + int(pool["seeds_per_scenario"]),
        )
        total = len(pool["scenarios"]) * len(seeds)
        completed = 0
        started_at = time.monotonic()
        for scenario in pool["scenarios"]:
            for seed in seeds:
                path = builder.ensure_routes(scenario, seed)
                completed += 1
                elapsed = time.monotonic() - started_at
                eta = elapsed / completed * (total - completed)
                print(
                    f"[{completed}/{total}] cached {scenario}/seed_{seed}; "
                    f"elapsed={elapsed:.0f}s ETA={eta:.0f}s: {path}",
                    flush=True,
                )
        print(f"Pre-generated {completed} cached training route files.", flush=True)
        return 0

    if args.seed < 0:
        parser.error("--seed must be non-negative")
    scenarios = [args.scenario] if args.scenario else SCENARIOS
    for scenario in scenarios:
        route_path = builder.ensure_routes(scenario, args.seed, force=args.force)
        print(f"Cached {scenario}/seed_{args.seed}: {route_path}")
    if args.scenario:
        return 0
    if args.force:
        print("Forced regeneration matched the existing route-file SHA256 for all seven scenarios.")
        return 0

    measurements = []
    for index, scenario in enumerate(SCENARIOS, start=1):
        print(f"[{index}/{len(SCENARIOS)}] measuring {scenario} with its native SUMO program")
        row = builder.measure(scenario, args.seed)
        measurements.append(row)
        print(
            f"  trips={row['total_trips']} share={row['planned_junction_share']:.3f} "
            f"arrived={row['arrived']} teleport_share={row['teleport_share']:.4f} "
            f"pending_max={row['pending_max']} queue_mean={row['mean_pilot_halting']:.2f}"
        )
        if (
            scenario in {"medium", "heavy", "rush_hour"}
            and row["planned_junction_share"] < float(builder.demand["junction_share_min"])
        ):
            _write_measurements(measurements, root)
            raise RuntimeError(
                f"{scenario} junction share is below 30%; stop and review the routing mix."
            )
    _write_measurements(measurements, root)
    over_five_percent = [
        row["scenario"] for row in measurements if row["teleport_share"] > 0.05
    ]
    if over_five_percent:
        print(
            "Native baseline exceeds 5% teleports in "
            f"{over_five_percent}; preserving as a failed baseline result. "
            "Per the approved roadmap amendment, evaluate this criterion after PPO is connected."
        )
    print(f"Wrote measured scenario table to {root / 'docs' / 'scenarios.md'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
