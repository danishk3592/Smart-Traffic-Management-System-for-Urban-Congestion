"""Inspect the configured pilot TLS and rank traffic at all signalized junctions."""

from __future__ import annotations

import argparse
import itertools
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

import traci.constants as tc
import yaml

from Ai.common.config import load_config
from Ai.common.junction import controlled_movements
from Ai.common.sumo_client import SumoClient


def classify_phase(state: str) -> str:
    """Classify green, yellow and clearance phases from signal-state characters."""
    green = any(char in "gG" for char in state)
    yellow = any(char in "yY" for char in state)
    if green and yellow:
        return "mixed"
    if green:
        return "green"
    if yellow:
        return "yellow"
    return "red/all-red"


def _is_clearance(state: str) -> bool:
    return any(char in "yY" for char in state)


def _bearing(edge: Any) -> float:
    shape = edge.getShape()
    start, end = shape[-2:] if len(shape) > 1 else (
        edge.getFromNode().getCoord(),
        edge.getToNode().getCoord(),
    )
    return round(math.degrees(math.atan2(end[0] - start[0], end[1] - start[1])) % 360, 2)


def _conflicts(
    net: Any, net_path: Path, tls_id: str,
    movements: list[dict[str, Any]], phases: list[Any]
) -> tuple[list[str], list[str]]:
    nodes = [node for node in net.getNodes() if node.getTLSID() == tls_id]
    if not nodes:
        raise RuntimeError(f"No SUMO junction request/foe information for {tls_id}")
    root = ET.parse(net_path).getroot()
    junction = next((item for item in root.findall("junction") if item.get("id") == tls_id), None)
    if junction is None:
        raise RuntimeError(f"Junction request data is missing for {tls_id}")
    responses = {
        int(item.get("index", "-1")): item.get("response", "")
        for item in junction.findall("request")
    }

    def yields_to(first: int, second: int) -> bool:
        response = responses.get(first, "")
        bit = len(response) - second - 1
        return 0 <= bit < len(response) and response[bit] == "1"

    links = sorted({idx for item in movements for idx in item["link_indices"]})
    failures, permissive = [], []
    for phase_index, phase in enumerate(phases):
        green = [idx for idx in links if idx < len(phase.state) and phase.state[idx] in "gG"]
        for first, second in itertools.combinations(green, 2):
            if any(node.areFoes(first, second) or node.areFoes(second, first) for node in nodes):
                pair = f"phase {phase_index}: links {first}({phase.state[first]}) and {second}({phase.state[second]})"
                if phase.state[first] == "G" and phase.state[second] == "G":
                    failures.append(pair + " are simultaneous protected greens")
                elif yields_to(first, second) or yields_to(second, first):
                    permissive.append(pair + " are foes and SUMO request response grants yielding")
                else:
                    failures.append(pair + " are foes without a SUMO yielding response")
    return failures, permissive


def _count_crossings(
    client: SumoClient, duration_s: int
) -> tuple[dict[str, set[str]], set[str], set[str]]:
    """Count unique vehicles from subscribed transitions between controlled edge pairs."""
    conn = client.connection
    tls_ids = sorted(conn.trafficlight.getIDList())
    pair_tls: dict[tuple[str, str], set[str]] = defaultdict(set)
    for tls_id in tls_ids:
        for movement in controlled_movements(client.net, tls_id):
            pair_tls[(movement["from_edge"], movement["to_edge"])].add(tls_id)
    counts = {tls_id: set() for tls_id in tls_ids}
    last_edge: dict[str, str] = {}
    subscribed: set[str] = set()
    teleports: set[str] = set()
    teleports_first_600: set[str] = set()

    def observe(vehicle_id: str, road_id: str) -> None:
        if not road_id or road_id.startswith(":"):
            return
        previous = last_edge.get(vehicle_id)
        if previous and previous != road_id:
            for tls_id in pair_tls.get((previous, road_id), ()):
                counts[tls_id].add(vehicle_id)
        last_edge[vehicle_id] = road_id

    for vehicle_id in conn.vehicle.getIDList():
        conn.vehicle.subscribe(vehicle_id, (tc.VAR_ROAD_ID,))
        subscribed.add(vehicle_id)
        observe(vehicle_id, conn.vehicle.getRoadID(vehicle_id))

    while client.sim_time < duration_s:
        client.step()
        for vehicle_id, result in (conn.vehicle.getAllSubscriptionResults() or {}).items():
            observe(vehicle_id, str(result.get(tc.VAR_ROAD_ID, "")))
        for vehicle_id in conn.simulation.getDepartedIDList():
            if vehicle_id not in subscribed:
                conn.vehicle.subscribe(vehicle_id, (tc.VAR_ROAD_ID,))
                subscribed.add(vehicle_id)
                observe(vehicle_id, conn.vehicle.getRoadID(vehicle_id))
        started_teleports = set(conn.simulation.getStartingTeleportIDList())
        teleports.update(started_teleports)
        if client.sim_time <= 600:
            teleports_first_600.update(started_teleports)
        for vehicle_id in conn.simulation.getArrivedIDList():
            last_edge.pop(vehicle_id, None)
            subscribed.discard(vehicle_id)
    return counts, teleports, teleports_first_600


def _details(net: Any, tls_id: str, program_id: str, program_type: str,
             phases: list[Any], movements: list[dict[str, Any]],
             conflicts: list[str], permissive: list[str]) -> tuple[list[dict[str, Any]], str]:
    nodes = [node for node in net.getNodes() if node.getTLSID() == tls_id]
    if not nodes:
        raise RuntimeError(f"No junction node found for {tls_id}")
    incoming = sorted({item["from_edge"] for item in movements})
    approaches = []
    for index, edge_id in enumerate(incoming, start=1):
        edge = net.getEdge(edge_id)
        approaches.append({
            "name": f"approach_{index}",
            "lanes": sorted(lane.getID() for lane in edge.getLanes()),
            "incoming_edge": edge_id,
            "bearing": _bearing(edge),
        })
    approaches.sort(key=lambda row: row["bearing"])
    for index, approach in enumerate(approaches, start=1):
        approach["name"] = f"approach_{index}"

    coords = [coord for node in nodes for coord in node.getShape()]
    if not coords:
        coords = [node.getCoord() for node in nodes]
    centers = [node.getCoord() for node in nodes]
    center = (round(sum(p[0] for p in centers) / len(centers), 2),
              round(sum(p[1] for p in centers) / len(centers), 2))
    bbox = (round(min(p[0] for p in coords), 2), round(min(p[1] for p in coords), 2),
            round(max(p[0] for p in coords), 2), round(max(p[1] for p in coords), 2))
    joined_ids = [node.getID() for node in nodes]
    member_count = max((len(re.findall(r"\d+", node_id)) for node_id in joined_ids), default=1)
    xmin, ymin, xmax, ymax = net.getBoundary()
    edge_distance = round(min(center[0] - xmin, xmax - center[0],
                              center[1] - ymin, ymax - center[1]), 2)

    green = [i for i, phase in enumerate(phases)
             if classify_phase(phase.state) == "green" and not _is_clearance(phase.state)]
    yellow = [i for i, phase in enumerate(phases) if _is_clearance(phase.state)]
    yellow_after = {
        i: next((j for j in yellow if j > i), yellow[0] if yellow else None) for i in green
    }
    lines = [
        f"## Configured pilot: {tls_id}", "",
        f"- Runtime program: {program_id} ({program_type}).",
        f"- Joined cluster: {'yes' if member_count > 1 else 'no'}; net node(s): {', '.join(joined_ids)}; numeric IDs in generated cluster name: {member_count}.",
        f"- Approaches: {len(approaches)}.",
        f"- Center (SUMO x,y): {center}; junction bounding box: {bbox}.",
        f"- Distance to nearest map bounding-box edge: {edge_distance} m.", "",
        "### Running native program phases", "",
        "| Phase | Duration (s) | State | Classification |",
        "|---:|---:|---|---|",
    ]
    lines.extend(
        f"| {i} | {phase.duration:g} | {phase.state} | {classify_phase(phase.state)} |"
        for i, phase in enumerate(phases)
    )
    lines += ["", "### Approaches", "",
              "| Name | Incoming edge | Lanes | Bearing (degrees clockwise from north) |",
              "|---|---|---|---:|"]
    lines.extend(
        f"| {row['name']} | {row['incoming_edge']} | {', '.join(row['lanes'])} | {row['bearing']} |"
        for row in approaches
    )
    lines += ["", "### Distinct controlled movements", "",
              "| From edge | To edge | TLS link indices |", "|---|---|---|"]
    lines.extend(
        f"| {item['from_edge']} | {item['to_edge']} | {', '.join(map(str, item['link_indices']))} |"
        for item in movements
    )
    lines += ["", "### Foe/conflict check", "",
              "Method: SUMO junction request foe bitsets and response/yield bitsets; all simultaneous G/g links are checked."]
    lines.append("**PASS:** no protected G/G foe pairs; lowercase g overlaps have a network yield response."
                 if not conflicts else "**FAIL:** " + "; ".join(conflicts))
    if permissive:
        lines.append(f"Permissive/yielding foe overlaps: {len(permissive)}.")
        lines.extend(f"- {item}" for item in permissive)
    lines += ["", f"Green phases: {green}; yellow phases: {yellow}; yellow_after: {yellow_after}."]
    return approaches, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=1800)
    args = parser.parse_args()
    if args.duration < 1800:
        parser.error("T0.3 requires at least 1800 seconds for suitability ranking")

    root = Path(__file__).resolve().parents[1]
    config = load_config()
    tls_id = config["sumo"]["tls_id"]
    sumo_config = Path(config["sumo"]["config"])
    if not sumo_config.is_absolute():
        sumo_config = (root / sumo_config).resolve()
    sumo_xml = ET.parse(sumo_config).getroot()
    net_value = sumo_xml.find("input/net-file").get("value")
    net_path = Path(net_value)
    if not net_path.is_absolute():
        net_path = (sumo_config.parent / net_path).resolve()
    with SumoClient(seed=1000) as client:
        net = client.net
        conn = client.connection
        tls_ids = sorted(conn.trafficlight.getIDList())
        if tls_id not in tls_ids:
            raise RuntimeError(f"Configured pilot TLS is not present: {tls_id}")
        active_id = conn.trafficlight.getProgram(tls_id)
        logic = next(logic for logic in conn.trafficlight.getAllProgramLogics(tls_id)
                     if logic.programID == active_id)
        selected_phases = list(logic.phases)
        selected_movements = controlled_movements(net, tls_id)
        conflicts, permissive = _conflicts(
            net, net_path, tls_id, selected_movements, selected_phases
        )
        approaches, selected_details = _details(
            net, tls_id, active_id, net.getTLS(tls_id).getPrograms()[active_id].getType(),
            selected_phases, selected_movements, conflicts, permissive
        )
        counts, teleports, teleports_first_600 = _count_crossings(client, args.duration)
    warning_lines = [line for line in client.sumo_output.splitlines()
                     if "warning" in line.casefold()]
    warnings_first_600 = []
    for line in warning_lines:
        match = re.search(r"time=([0-9]+(?:\.[0-9]+)?)", line)
        if match and float(match.group(1)) <= 600:
            warnings_first_600.append(line)

    rows = []
    for current_id in tls_ids:
        tls = net.getTLS(current_id)
        program_id, program = next(iter(tls.getPrograms().items()))
        movements = controlled_movements(net, current_id)
        phases = program.getPhases()
        rows.append({
            "tls_id": current_id, "program_type": program.getType(),
            "program_id": program_id,
            "approaches": len({item["from_edge"] for item in movements}),
            "green_phases": sum(
                classify_phase(p.state) == "green" and not _is_clearance(p.state)
                for p in phases
            ),
            "vehicles": len(counts[current_id]),
        })
    rows.sort(key=lambda row: (-row["vehicles"], row["tls_id"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    median = sorted(row["vehicles"] for row in rows)[len(rows) // 2]
    selected = next(row for row in rows if row["tls_id"] == tls_id)

    report = [
        "# SUMO traffic-light inspection", "",
        "Measured 2026-10-20 using the existing network and demand, native programs, seed 1000. The same uninterrupted run included the first 600 s and continued to 1800 s. SUMO reports and edgeData outputs were redirected to a temporary directory; the protected source map was not written.",
        "Unique vehicles are counted from subscribed road-ID transitions matching a controlled from-edge to to-edge pair.", "",
        "## Suitability ranking", "",
        "| Rank | TLS ID | Program type | Program ID | Approaches | Green phases | Unique vehicles crossing |",
        "|---:|---|---|---|---:|---:|---:|",
    ]
    report.extend(
        f"| {row['rank']} | {row['tls_id']} | {row['program_type']} | {row['program_id']} | "
        f"{row['approaches']} | {row['green_phases']} | {row['vehicles']} |"
        for row in rows
    )
    report += ["", f"Median count: {median}; configured pilot rank: {selected['rank']}; count: {selected['vehicles']}.",
               "", selected_details, "", "## Run evidence", "",
               f"- Simulation duration: {args.duration} s.",
               f"- Unique IDs starting a teleport in first 600 s: {len(teleports_first_600)}; over 1800 s: {len(teleports)}.",
               f"- Warning lines in first 600 s: {len(warnings_first_600)}; over 1800 s: {len(warning_lines)}."]
    report.extend(f"  - {line.strip()}" for line in warning_lines)
    report_path = root / "docs" / "tls_inspection.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Inspected {len(tls_ids)} TLS for {args.duration} s.")
    print(f"Pilot rank={selected['rank']}/{len(rows)}, count={selected['vehicles']}, "
          f"approaches={len(approaches)}, green phases="
          f"{sum(classify_phase(p.state) == 'green' for p in selected_phases)}, "
        f"protected foe conflicts={len(conflicts)}, yielding foe overlaps={len(permissive)}, "
        f"teleports={len(teleports)}, "
          f"warnings={len(warning_lines)}.")

    green_count = sum(
        classify_phase(p.state) == "green" and not _is_clearance(p.state)
        for p in selected_phases
    )
    if conflicts or len(approaches) < 3 or green_count < 2 or selected["vehicles"] < median:
        print("T0.3 stop condition reached; inspect docs/tls_inspection.md before choosing a pilot.")
        return 2

    config_path = root / "config" / "stms.yaml"
    config["intersection"]["approaches"] = approaches
    config["intersection"]["green_phases"] = [
        i for i, phase in enumerate(selected_phases)
        if classify_phase(phase.state) == "green" and not _is_clearance(phase.state)
    ]
    yellow = [i for i, phase in enumerate(selected_phases) if _is_clearance(phase.state)]
    config["intersection"]["yellow_after"] = {
        green: next((j for j in yellow if j > green), yellow[0] if yellow else None)
        for green in config["intersection"]["green_phases"]
    }
    config["intersection"]["movements"] = selected_movements
    text = config_path.read_text(encoding="utf-8")
    intersection_yaml = yaml.safe_dump(
        {"intersection": config["intersection"]}, sort_keys=False
    ).rstrip()
    text, replacements = re.subn(
        r"(?ms)^intersection:\n.*?(?=^logging:)",
        intersection_yaml + "\n",
        text,
        count=1,
    )
    if replacements != 1:
        raise RuntimeError("Could not locate the intersection section in config/stms.yaml")
    config_path.write_text(text, encoding="utf-8")
    print(f"Wrote {report_path} and inspected intersection data to {config_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
