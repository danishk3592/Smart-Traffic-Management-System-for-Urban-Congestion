"""Inventory every SUMO traffic light, verify suitability, and freeze the intended set."""

from __future__ import annotations

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from Ai.common.config import load_config
from Ai.common.junction import controlled_movements
from Ai.common.sumo_client import SumoClient
from scripts.inspect_tls import _conflicts, _count_crossings, _is_clearance, classify_phase

ROOT = Path(__file__).resolve().parents[1]


def _network_path(config_path: Path) -> Path:
    config_root = ET.parse(config_path).getroot()
    node = config_root.find("input/net-file")
    if node is None or not node.get("value"):
        raise ValueError(f"SUMO config has no net-file: {config_path}")
    path = Path(node.get("value", ""))
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()


def _phases(tls: Any, program_id: str) -> list[Any]:
    program = tls.getPrograms()[program_id]
    return list(program.getPhases())


def _program_config(phases: list[Any], approaches: list[dict[str, Any]], tls_id: str) -> dict[str, Any]:
    green = [
        index for index, phase in enumerate(phases)
        if classify_phase(str(phase.state)) == "green" and not _is_clearance(str(phase.state))
    ]
    yellow = [index for index, phase in enumerate(phases) if _is_clearance(str(phase.state))]
    yellow_after: dict[int, int] = {}
    for index in green:
        following = (index + 1) % len(phases)
        if following not in yellow:
            raise ValueError(f"Green phase {index} at {tls_id} has no immediately following yellow phase")
        next_green = next(
            ((following + offset) % len(phases) for offset in range(1, len(phases) + 1)
             if (following + offset) % len(phases) in green),
            None,
        )
        if next_green is None:
            raise ValueError(f"Green phase {index} at {tls_id} has no cyclic successor")
        yellow_after[index] = following
    if len(green) < 2:
        raise ValueError(f"{tls_id} has fewer than two verified green phases")
    return {
        "tls_id": tls_id,
        "green_phases": green,
        "yellow_after": yellow_after,
        "all_red_phases": [
            index for index, phase in enumerate(phases)
            if not any(char in "GgYy" for char in phase.state)
        ],
        "min_green_s": 10,
        "max_green_s": 60,
        "approaches": approaches,
    }


def _write_static_actuated_copy(rows: list[dict[str, Any]]) -> Path | None:
    actuated = [row for row in rows if row["program_type"] == "actuated" and row["suitable"]]
    if not actuated:
        return None
    target = ROOT / "SUMO" / "derived" / "network_static_tls.add.xml"
    target.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("additional")
    for row in actuated:
        logic = ET.SubElement(
            root, "tlLogic", id=row["tls_id"], type="static", programID="stms_static", offset="0"
        )
        for phase in row["phase_data"]:
            duration = phase.get("duration")
            if duration is None or not math.isfinite(float(duration)) or float(duration) <= 0:
                raise ValueError(f"Cannot make fixed-duration static copy for {row['tls_id']}")
            ET.SubElement(logic, "phase", duration=str(float(duration)), state=phase["state"])
    payload = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    if target.exists():
        if target.read_bytes() != payload:
            raise FileExistsError(f"Refusing to overwrite existing static TLS copy: {target}")
    else:
        target.write_bytes(payload)
    return target


def inspect(duration_s: int = 1800) -> dict[str, Any]:
    """Run the unchanged native demand once and assess all TLS against it."""
    if duration_s < 1800:
        raise ValueError("Network TLS suitability requires at least 1800 simulation seconds")
    config = load_config()
    sumo_config = Path(config["sumo"]["config"])
    if not sumo_config.is_absolute():
        sumo_config = (ROOT / sumo_config).resolve()
    net_path = _network_path(sumo_config)
    minimum_traffic = int(config["network"]["min_veh_per_1800s"])

    with SumoClient(seed=1000) as client:
        net = client.net
        tls_ids = sorted(client.connection.trafficlight.getIDList())
        if not tls_ids:
            raise RuntimeError("SUMO reported no traffic-light systems")
        crossings, teleports, _ = _count_crossings(client, duration_s)
        rows = []
        for tls_id in tls_ids:
            tls = net.getTLS(tls_id)
            runtime = client.connection.trafficlight
            program_id = runtime.getProgram(tls_id)
            phases = _phases(tls, program_id)
            program_type = tls.getPrograms()[program_id].getType()
            movements = controlled_movements(net, tls_id)
            conflicts, permissive = _conflicts(net, net_path, tls_id, movements, phases)
            approaches = sorted({str(item["from_edge"]) for item in movements})
            approach_details = []
            for edge_id in approaches:
                edge = net.getEdge(edge_id)
                shape = edge.getShape()
                start, end = shape[-2:] if len(shape) > 1 else (
                    edge.getFromNode().getCoord(), edge.getToNode().getCoord()
                )
                bearing = round(math.degrees(math.atan2(end[0] - start[0], end[1] - start[1])) % 360, 2)
                approach_details.append({
                    "name": f"approach_{len(approach_details) + 1}",
                    "incoming_edge": edge_id,
                    "lanes": sorted(lane.getID() for lane in edge.getLanes()),
                    "bearing": bearing,
                })
            approach_details.sort(key=lambda item: item["bearing"])
            for index, item in enumerate(approach_details, start=1):
                item["name"] = f"approach_{index}"
            green_phases = [
                index for index, phase in enumerate(phases)
                if classify_phase(str(phase.state)) == "green" and not _is_clearance(str(phase.state))
            ]
            yellow_phases = [index for index, phase in enumerate(phases) if _is_clearance(str(phase.state))]
            nodes = [node for node in net.getNodes() if node.getTLSID() == tls_id]
            if not nodes:
                conflicts.append("no SUMO junction nodes are associated with this TLS")
            phase_data = [{"duration": float(p.duration), "state": str(p.state)} for p in phases]
            static_convertible = program_type == "static" or all(
                math.isfinite(item["duration"]) and item["duration"] > 0 for item in phase_data
            )
            traffic = len(crossings[tls_id])
            reasons = []
            if len(green_phases) < 2:
                reasons.append(f"only {len(green_phases)} verified green phase(s), need at least 2")
            if conflicts:
                reasons.append("protected foe conflict or missing junction conflict data")
            if not static_convertible:
                reasons.append("program cannot be converted to fixed-duration static phases")
            if traffic < minimum_traffic:
                reasons.append(f"{traffic} native crossings in {duration_s}s, below {minimum_traffic}")
            suitable = not reasons
            node_ids = [node.getID() for node in nodes]
            member_count = max((len(re.findall(r"\d+", node_id)) for node_id in node_ids), default=1)
            coords = [node.getCoord() for node in nodes]
            center = [round(sum(point[i] for point in coords) / len(coords), 2) for i in (0, 1)] if coords else None
            row = {
                "tls_id": tls_id,
                "program_id": program_id,
                "program_type": program_type,
                "phase_data": phase_data,
                "green_phases": green_phases,
                "yellow_phases": yellow_phases,
                "approaches": approaches,
                "approach_details": approach_details,
                "approach_count": len(approaches),
                "movement_count": len(movements),
                "joined_cluster": member_count > 1,
                "node_ids": node_ids,
                "center": center,
                "protected_conflicts": conflicts,
                "permissive_foe_overlaps": permissive,
                "native_crossings": traffic,
                "static_convertible": static_convertible,
                "suitable": suitable,
                "reason": "; ".join(reasons) if reasons else "meets all suitability criteria",
                "phase_data_detail": [
                    {"index": i, "duration_s": p["duration"], "state": p["state"]}
                    for i, p in enumerate(phase_data)
                ],
            }
            row["tls_config"] = _program_config(phases, approach_details, tls_id) if suitable else None
            rows.append(row)

    return {"rows": rows, "duration_s": duration_s, "teleports": len(teleports), "net_path": net_path,
            "config": config}


def main() -> int:
    result = inspect()
    rows = result["rows"]
    pilot = result["config"]["sumo"]["tls_id"]
    if not any(row["tls_id"] == pilot and row["suitable"] for row in rows):
        raise RuntimeError("Configured M1 pilot TLS is not in the suitable intended set")
    static_path = _write_static_actuated_copy(rows)
    intended = sorted(row["tls_id"] for row in rows if row["suitable"])
    excluded = sorted(row["tls_id"] for row in rows if not row["suitable"])
    list_payload = json.dumps(intended, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    list_hash = hashlib.sha256(list_payload).hexdigest()
    max_approaches = max(row["approach_count"] for row in rows if row["suitable"])
    max_phases = max(len(row["green_phases"]) for row in rows if row["suitable"])
    configs = [row["tls_config"] for row in rows if row["suitable"]]
    for row, tls_config in zip((r for r in rows if r["suitable"]), configs, strict=True):
        tls_config["min_green_s"] = float(result["config"]["signal"]["min_green_s"])
        tls_config["max_green_s"] = float(result["config"]["signal"]["max_green_s"])
        tls_config["program_type"] = row["program_type"]
        tls_config["program_id"] = row["program_id"]
        tls_config["static_program_id"] = "stms_static" if row["program_type"] == "actuated" else None

    network = result["config"]["network"]
    network.update(
        controlled_tls=intended, excluded_tls=excluded, max_approaches=max_approaches,
        max_phases=max_phases, tls_list_hash=list_hash,
        frozen_utc=network.get("frozen_utc") if network.get("tls_list_hash") == list_hash and network.get("frozen_utc")
        else datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        tls_configs=configs,
    )
    config_path = ROOT / "config" / "stms.yaml"
    source = config_path.read_text(encoding="utf-8")
    block = yaml.safe_dump({"network": network}, sort_keys=False, allow_unicode=True).rstrip()
    updated, count = re.subn(r"(?ms)^network:\n.*?(?=^rl_net:)", block + "\n\n", source, count=1)
    if count != 1:
        raise RuntimeError("Could not replace network section in config/stms.yaml")
    config_path.write_text(updated, encoding="utf-8")

    report = [
        "# Network traffic-light inventory and frozen intended set", "",
        f"Measured using the existing SUMO network and unchanged native demand, seed 1000, for {result['duration_s']} s.",
        f"Native-program teleports observed: {result['teleports']}. The source map under `SUMO/No_Polygon_Map/` was not written.",
        f"Intended TLS count: {len(intended)}; excluded: {len(excluded)}; list SHA-256: `{list_hash}`.",
        f"Frozen UTC: `{network['frozen_utc']}`. Maximum approaches: {max_approaches}; maximum green phases: {max_phases}.",
        "", "| TLS ID | Program | Approaches | Green phases | Crossings/1800 s | Protected foes | Suitability | Reason |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        status = "intended" if row["suitable"] else "excluded"
        report.append(
            f"| `{row['tls_id']}` | {row['program_type']} | {row['approach_count']} | {len(row['green_phases'])} | "
            f"{row['native_crossings']} | {len(row['protected_conflicts'])} | {status} | {row['reason']} |"
        )
    report += ["", "## Per-TLS detail", ""]
    for row in rows:
        report += ["", f"### `{row['tls_id']}`", "",
                   f"- Joined cluster: {row['joined_cluster']}; SUMO node IDs: {', '.join(row['node_ids'])}; center: {row['center']}.",
                   f"- Movements: {row['movement_count']}; permissive/yielding foe overlaps: {len(row['permissive_foe_overlaps'])}.",
                   f"- Phases (index: duration s, state): {row['phase_data_detail']}."]
        if row["protected_conflicts"]:
            report.extend(f"- Conflict: {item}." for item in row["protected_conflicts"])
    if static_path:
        report += ["", f"Actuated intended programs were copied with unchanged phase states and nominal durations to `{static_path.relative_to(ROOT).as_posix()}`."]
    report += ["", "The intended list is frozen before network evaluation. This inventory run used the native programs; all-intended-TLS TraCI speed measurement is recorded with T4.2 once the safety manager can control each junction."]
    (ROOT / "docs" / "network_tls.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Inspected {len(rows)} TLS for {result['duration_s']} s; intended={len(intended)}, excluded={len(excluded)}, hash={list_hash}")
    print(f"Wrote docs/network_tls.md and frozen network configuration. Native teleports={result['teleports']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
