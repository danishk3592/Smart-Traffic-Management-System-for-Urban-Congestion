"""Resumable network rule tuning and fixed/rule validation baseline grid."""

from __future__ import annotations

import concurrent.futures
import csv
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from Ai.common.config import load_config
from Ai.common.metrics import common_completed_trip_times
from Ai.common.run_episode import run_episode
from Ai.controllers.network import get_network_controller
from scripts.make_scenarios import ScenarioBuilder

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("net_balanced", "net_low", "net_medium", "net_heavy", "net_rush_hour")
SEEDS = (3000, 3001, 3002)
SETTINGS = ((6, 30.0), (8, 45.0), (10, 60.0))
STATE_PATH = ROOT / "results" / "raw" / "t44_network_baselines_progress.json"
COMMON_PATH = ROOT / "results" / "summary" / "t44_network_common_trips.csv"
REPORT_PATH = ROOT / "docs" / "rule_tuning.md"


def _load() -> dict[str, dict[str, Any]]:
    try:
        return {row["key"]: row for row in json.loads(STATE_PATH.read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _save(records: dict[str, dict[str, Any]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(list(records.values()), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, STATE_PATH)


def _summary_for(record: dict[str, Any]) -> dict[str, str]:
    with (Path(record["out_dir"]) / "summary.csv").open(encoding="utf-8", newline="") as stream:
        return next(csv.DictReader(stream))


def _valid(record: dict[str, Any], *, controller: str, scenario: str, seed: int) -> bool:
    try:
        directory = Path(record["out_dir"])
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        with (directory / "summary.csv").open(encoding="utf-8", newline="") as stream:
            summary = next(csv.DictReader(stream))
        with (directory / "junctions.csv").open(encoding="utf-8", newline="") as stream:
            junctions = list(csv.DictReader(stream))
        intended = list(load_config(ROOT / "config" / "stms.yaml")["network"]["controlled_tls"])
        numeric_fields = (
            "n_trips", "n_trips_junction", "n_completed", "n_unfinished", "completion_rate",
            "avg_travel_time_completed", "avg_travel_time_censored", "avg_wait", "avg_time_loss",
            "avg_queue", "avg_speed", "throughput_veh_per_min", "frac_time_high_congestion",
            "teleports", "sim_end_time", "wall_clock_s", "avg_junction_queue_mean",
            "worst_junction_avg_queue",
        )
        return (run["controller"] == controller and run["scenario"] == scenario
                and int(run["seed"]) == seed and int(summary["n_tls_controlled"]) == len(intended)
                and len(junctions) == 12 and len({row["tls_id"] for row in junctions}) == 12
                and {row["tls_id"] for row in junctions} == set(intended)
                and all(math.isfinite(float(summary[field])) for field in numeric_fields)
                and (directory / "trips.csv").is_file())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _run_cell(cell: tuple[str, str, str, int, int | None, float | None]) -> dict[str, Any]:
    key, controller_name, scenario, seed, queue_threshold, wait_threshold = cell
    config = load_config(ROOT / "config" / "stms.yaml")
    if queue_threshold is not None:
        config["rule"]["queue_threshold"] = queue_threshold
        config["rule"]["wait_threshold_s"] = wait_threshold
    controller = get_network_controller(controller_name, config["network"]["tls_configs"], config)
    label = f"t44_{key.replace(':', '_')}"
    destination = ROOT / "results" / "raw" / f"{label}_{datetime.now():%Y%m%d-%H%M%S-%f}"
    result = run_episode(controller, scenario, seed, destination, family="network")
    return {"key": key, "controller": controller_name, "scenario": scenario, "seed": seed,
            "queue_threshold": queue_threshold, "wait_threshold_s": wait_threshold,
            "out_dir": str(destination), "result": result, "complete": True}


def _parallel(cells: list[tuple[str, str, str, int, int | None, float | None]],
              records: dict[str, dict[str, Any]], *, max_workers: int = 4) -> None:
    started = time.perf_counter()
    pending = []
    for key, controller, scenario, seed, queue, wait in cells:
        existing = records.get(key)
        if existing and _valid(existing, controller=controller, scenario=scenario, seed=seed):
            continue
        if not existing:
            for run_file in (ROOT / "results" / "raw").glob("*/run.json"):
                try:
                    run = json.loads(run_file.read_text(encoding="utf-8"))
                    if (run.get("controller"), run.get("scenario"), int(run.get("seed", -1))) != (controller, scenario, seed):
                        continue
                    parameters = run.get("controller_parameters", {})
                    if controller == "rule" and queue is not None and any(
                        item.get("queue_threshold") != queue or item.get("wait_threshold_s") != wait
                        for item in parameters.values()
                    ):
                        continue
                    candidate = {"key": key, "controller": controller, "scenario": scenario,
                                 "seed": seed, "out_dir": str(run_file.parent), "result": run,
                                 "queue_threshold": queue, "wait_threshold_s": wait, "complete": True}
                    if _valid(candidate, controller=controller, scenario=scenario, seed=seed):
                        records[key] = candidate
                        _save(records)
                        existing = candidate
                        break
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    continue
        if existing and _valid(existing, controller=controller, scenario=scenario, seed=seed):
            continue
        pending.append((key, (key, controller, scenario, seed, queue, wait)))
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_cell, cell): key for key, cell in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            key = futures[future]
            record = future.result()
            if not _valid(record, controller=record["controller"], scenario=record["scenario"], seed=record["seed"]):
                raise RuntimeError(f"network baseline cell failed artifact validation: {key}")
            record["key"] = key
            records[key] = record
            _save(records)
            elapsed = time.perf_counter() - started
            rate = index / elapsed if elapsed > 0 else 0.0
            eta = (len(pending) - index) / rate if rate else 0.0
            print(f"[{index}/{len(pending)}] completed {key}; eta_s={eta:.0f}; {record['result']['out_dir']}", flush=True)


def _write_tuning(records: dict[str, dict[str, Any]], selected: tuple[int, float] | None) -> None:
    prior = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.is_file() else "# Rule controller validation tuning (T1.3)\n"
    if "## Part 2 — Network validation tuning" in prior:
        prior = prior.split("## Part 2 — Network validation tuning", maxsplit=1)[0].rstrip() + "\n\n"
    rows = ["# Rule controller validation tuning", "",
            "Network `net_medium`; validation seeds 3000–3002; three shared threshold settings. Selection minimizes mean network queue, with waiting and completed travel time retained as context.", "",
            "| Queue threshold | Wait threshold (s) | Seed | Network queue | Network wait (s) | Completed/trips | Teleports | Wall time (s) | Run |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for queue, wait in SETTINGS:
        for seed in SEEDS:
            record = records.get(f"tune:q{queue}:w{wait:g}:net_medium:{seed}")
            if record:
                result = record["result"]
                summary = _summary_for(record)
                rows.append(f"| {queue} | {wait:g} | {seed} | {float(summary['avg_queue']):.3f} | {float(summary['avg_wait']):.3f} | {result['n_completed']}/{result['n_trips']} | {result['teleports']} | {result['wall_clock_s']:.1f} | `{result['run_id']}` |")
            else:
                rows.append(f"| {queue} | {wait:g} | {seed} | pending | pending | pending | pending | pending | — |")
    rows += ["", f"Tuning coverage: {sum(f'tune:q{q}:w{w:g}:net_medium:{s}' in records for q, w in SETTINGS for s in SEEDS)}/9."]
    if selected:
        rows.append(f"Selected shared network thresholds: queue `{selected[0]}`, wait `{selected[1]:g}s`.")
    REPORT_PATH.write_text(prior + "## Part 2 — Network validation tuning\n\n" + "\n".join(rows) + "\n", encoding="utf-8")


def _write_common_trip_summary(records: dict[str, dict[str, Any]]) -> None:
    """Persist paired fixed/rule travel times on completed IDs shared by each cell pair."""
    fields = ("scenario", "seed", "n_common", "fixed_run_id", "rule_run_id",
              "fixed_mean_travel_time", "rule_mean_travel_time")
    rows = []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            fixed = records[f"base:fixed:{scenario}:{seed}"]
            rule = records[f"base:rule:{scenario}:{seed}"]
            common = common_completed_trip_times([fixed["out_dir"], rule["out_dir"]])
            means = common["mean_travel_time_by_run"]
            fixed_id = fixed["result"]["run_id"]
            rule_id = rule["result"]["run_id"]
            rows.append({
                "scenario": scenario, "seed": seed, "n_common": common["n_common"],
                "fixed_run_id": fixed_id, "rule_run_id": rule_id,
                "fixed_mean_travel_time": means[fixed_id],
                "rule_mean_travel_time": means[rule_id],
            })
    COMMON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if COMMON_PATH.exists():
        raise FileExistsError(f"refusing to overwrite existing common-trip summary: {COMMON_PATH}")
    with COMMON_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    builder = ScenarioBuilder(ROOT, family="network")
    for scenario in SCENARIOS:
        for seed in SEEDS:
            builder.get_cached_routes(scenario, seed)
    records = _load()
    tune = [(f"tune:q{queue}:w{wait:g}:net_medium:{seed}", "rule", "net_medium", seed, queue, wait)
            for queue, wait in SETTINGS for seed in SEEDS]
    _parallel(tune, records)
    scores = {}
    for queue, wait in SETTINGS:
        runs = [records[f"tune:q{queue}:w{wait:g}:net_medium:{seed}"] for seed in SEEDS]
        scores[(queue, wait)] = sum(float(_summary_for(run)["avg_queue"]) for run in runs) / len(runs)
    selected = min(scores, key=scores.get)
    _write_tuning(records, selected)
    baseline = [(f"base:{controller}:{scenario}:{seed}", controller, scenario, seed,
                 selected[0] if controller == "rule" else None,
                 selected[1] if controller == "rule" else None)
                for controller in ("fixed", "rule") for scenario in SCENARIOS for seed in SEEDS]
    _parallel(baseline, records)
    _write_tuning(records, selected)
    _write_common_trip_summary(records)
    print(json.dumps({"tuning_cells": 9, "baseline_cells": 30,
                      "selected_thresholds": selected, "record": str(STATE_PATH)}, indent=2))


if __name__ == "__main__":
    main()
