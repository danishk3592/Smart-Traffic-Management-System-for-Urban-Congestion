"""Build the frozen T4.10 per-junction PPO/rule gate from validation artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import fmean
from typing import Any

from Ai.common.config import load_config

MODEL_SHA256 = "758711e7f28e29e69b59af6eade30ba679c3160daadf39e09ed89287f5037757"
SCENARIOS = ("net_medium", "net_heavy")
SEEDS = (3000, 3001, 3002)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def evaluate_tls_gate(
    *, ppo_mean_queue: float, fixed_mean_queue: float,
    ppo_mean_wait: float, fixed_mean_wait: float,
    actions: set[str], tolerance_pct: float = 5.0,
) -> dict[str, Any]:
    """Apply the frozen T4.10 non-regression and action-diversity criteria."""
    queue_pass = ppo_mean_queue <= fixed_mean_queue * (1 + tolerance_pct / 100) if fixed_mean_queue > 0 else ppo_mean_queue == 0
    wait_pass = ppo_mean_wait <= fixed_mean_wait * (1 + tolerance_pct / 100) if fixed_mean_wait > 0 else ppo_mean_wait == 0
    action_pass = len(actions) >= 2
    return {
        "queue_regression_pct": (ppo_mean_queue / fixed_mean_queue - 1) * 100 if fixed_mean_queue else None,
        "queue_pass": queue_pass,
        "wait_regression_pct": (ppo_mean_wait / fixed_mean_wait - 1) * 100 if fixed_mean_wait else None,
        "wait_pass": wait_pass,
        "actions": sorted(actions), "action_diversity_pass": action_pass,
        "ppo_eligible": queue_pass and wait_pass and action_pass,
    }


def build_hybrid_gate(root: Path, *, output: Path | None = None) -> dict[str, Any]:
    """Validate the six T4.7 candidate/fixed pairs, then freeze eligible TLS IDs."""
    config = load_config(root / "config" / "stms.yaml")
    intended = tuple(str(tls) for tls in config["network"]["controlled_tls"])
    candidate: dict[tuple[str, int], tuple[Path, dict[str, Any]]] = {}
    fixed: dict[tuple[str, int], tuple[Path, dict[str, Any]]] = {}
    for directory in (root / "results" / "raw").iterdir():
        run_path = directory / "run.json"
        if not directory.is_dir() or not run_path.is_file():
            continue
        try:
            run = json.loads(run_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        key = (str(run.get("scenario")), int(run.get("seed", -1)))
        if run.get("family") != "network" or key[0] not in SCENARIOS or key[1] not in SEEDS:
            continue
        controller = str(run.get("controller"))
        if controller == "rl" and run.get("controller_diagnostics", {}).get("model_sha256") == MODEL_SHA256:
            candidate.setdefault(key, (directory, run))
        if (controller == "fixed" and run.get("controller_parameters")
                and all(float(value.get("green_seconds", -1)) == float(config["fixed"]["green_s"])
                        for value in run["controller_parameters"].values())):
            fixed.setdefault(key, (directory, run))

    expected_pairs = {(scenario, seed) for scenario in SCENARIOS for seed in SEEDS}
    if set(candidate) != expected_pairs or set(fixed) != expected_pairs:
        raise ValueError(
            f"T4.10 requires exactly six frozen-model/fixed validation pairs; "
            f"candidate missing={sorted(expected_pairs - set(candidate))}, "
            f"fixed missing={sorted(expected_pairs - set(fixed))}"
        )

    accum: dict[str, dict[str, list[float]]] = {
        tls: {"ppo_queue": [], "fixed_queue": [], "ppo_wait": [], "fixed_wait": []}
        for tls in intended
    }
    actions: dict[str, set[str]] = {tls: set() for tls in intended}
    provenance: list[dict[str, Any]] = []
    for key in sorted(expected_pairs):
        ppo_dir, ppo_run = candidate[key]
        fixed_dir, fixed_run = fixed[key]
        for directory, run in ((ppo_dir, ppo_run), (fixed_dir, fixed_run)):
            expected_files = ("summary.csv", "trips.csv", "junctions.csv")
            if any(not (directory / name).is_file() for name in expected_files):
                raise ValueError(f"Incomplete gate cell: {directory}")
            if int(run.get("n_completed", -1)) != int(run.get("n_trips", 0)):
                raise ValueError(f"Gate cell has incomplete trips: {directory}")
            tls_rows = _csv(directory / "junctions.csv")
            if {row["tls_id"] for row in tls_rows} != set(intended):
                raise ValueError(f"Gate cell does not cover the frozen TLS set: {directory}")
        ppo_trips = {row["vehicle_id"] for row in _csv(ppo_dir / "trips.csv")}
        fixed_trips = {row["vehicle_id"] for row in _csv(fixed_dir / "trips.csv")}
        if ppo_trips != fixed_trips:
            raise ValueError(f"Candidate/fixed trip identities differ for {key}")
        ppo_rows = {row["tls_id"]: row for row in _csv(ppo_dir / "junctions.csv")}
        fixed_rows = {row["tls_id"]: row for row in _csv(fixed_dir / "junctions.csv")}
        for tls in intended:
            ppo_row, fixed_row = ppo_rows[tls], fixed_rows[tls]
            for field, target in (("avg_queue", "queue"), ("avg_wait", "wait")):
                accum[tls][f"ppo_{target}"].append(float(ppo_row[field]))
                accum[tls][f"fixed_{target}"].append(float(fixed_row[field]))
            histogram = json.loads(ppo_row["action_histogram"])
            actions[tls].update(name for name, count in histogram.items() if int(count) > 0)
        provenance.append({
            "scenario": key[0], "seed": key[1],
            "ppo_run_id": ppo_run["run_id"], "fixed_run_id": fixed_run["run_id"],
            "ppo_run_sha256": _sha256(ppo_dir / "run.json"),
            "ppo_junctions_sha256": _sha256(ppo_dir / "junctions.csv"),
            "fixed_run_sha256": _sha256(fixed_dir / "run.json"),
            "fixed_junctions_sha256": _sha256(fixed_dir / "junctions.csv"),
        })

    rows: list[dict[str, Any]] = []
    eligible: list[str] = []
    for tls in intended:
        values = accum[tls]
        ppo_q, fixed_q = fmean(values["ppo_queue"]), fmean(values["fixed_queue"])
        ppo_w, fixed_w = fmean(values["ppo_wait"]), fmean(values["fixed_wait"])
        gate = evaluate_tls_gate(
            ppo_mean_queue=ppo_q, fixed_mean_queue=fixed_q,
            ppo_mean_wait=ppo_w, fixed_mean_wait=fixed_w,
            actions=actions[tls],
        )
        passed = bool(gate["ppo_eligible"])
        if passed:
            eligible.append(tls)
        rows.append({
            "tls_id": tls, "ppo_mean_queue": ppo_q, "fixed_mean_queue": fixed_q,
            **gate, "ppo_mean_wait": ppo_w, "fixed_mean_wait": fixed_w,
        })

    model_path = root / "Ai" / "rl" / "models" / "ppo_net_v2_rejection_penalty_005" / "evaluations" / "best_model.zip"
    if _sha256(model_path) != MODEL_SHA256:
        raise ValueError("T4.10 candidate model identity differs from the accepted T4.7 checkpoint")
    result = {
        "schema_version": 1, "criteria": {
            "scenarios": list(SCENARIOS), "seeds": list(SEEDS),
            "max_queue_regression_pct": 5.0, "max_wait_regression_pct": 5.0,
            "minimum_distinct_policy_actions": 2,
        },
        "model_path": model_path.relative_to(root).as_posix(), "model_sha256": MODEL_SHA256,
        "tls_list_hash": config["network"]["tls_list_hash"],
        "per_junction": rows, "ppo_tls_ids": eligible,
        "rule_tls_ids": [tls for tls in intended if tls not in eligible],
        "source_cells": provenance,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(output.suffix + ".pending")
        tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(output)
    return result
