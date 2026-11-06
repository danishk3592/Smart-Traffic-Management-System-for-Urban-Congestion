"""Section 11 run metrics, computed from immutable episode CSV artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path
from statistics import fmean
from typing import Any

SUMMARY_FIELDS = (
    "run_id", "controller", "scenario", "seed", "git_commit", "config_hash", "metrics_version",
    "n_trips", "n_trips_junction", "n_completed", "n_unfinished", "completion_rate",
    "completion_rate_junction", "avg_travel_time_completed", "avg_travel_time_censored",
    "avg_travel_time_junction_completed", "avg_travel_time_junction_censored", "avg_wait",
    "avg_time_loss", "avg_depart_delay", "avg_queue", "avg_speed", "throughput_veh_per_min",
    "frac_time_high_congestion", "teleports", "sim_end_time", "wall_clock_s", "family",
    "n_tls_controlled", "n_tls_ai", "ai_coverage", "avg_junction_queue_mean",
    "worst_junction_avg_queue",
)


def classify_ai_coverage(ppo_tick_shares: list[float], minimum_share: float) -> tuple[str, list[str]]:
    """Classify per-TLS PPO ownership using the configured final coverage threshold."""
    if not 0.0 <= minimum_share <= 1.0:
        raise ValueError("minimum_share must be in [0, 1]")
    if any(not 0.0 <= share <= 1.0 for share in ppo_tick_shares):
        raise ValueError("PPO tick shares must be in [0, 1]")
    statuses = ["rl" if share >= minimum_share else "rl_fallback" for share in ppo_tick_shares]
    n_ai = sum(status == "rl" for status in statuses)
    coverage = "full" if statuses and n_ai == len(statuses) else "partial" if n_ai else "none"
    return coverage, statuses


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def common_completed_trip_times(run_dirs: list[str | Path]) -> dict[str, Any]:
    """Compute completed-trip travel times on IDs shared by every supplied run."""
    if len(run_dirs) < 2:
        raise ValueError("common-trip comparison requires at least two runs")
    runs: list[tuple[str, dict[str, float], tuple[str, int]]] = []
    for run_dir in run_dirs:
        directory = Path(run_dir)
        metadata = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        trips = _read_csv(directory / "trips.csv")
        completed = {
            row["vehicle_id"]: float(row["trip_time"])
            for row in trips if _bool(row["completed"])
        }
        runs.append((str(metadata["run_id"]), completed,
                     (str(metadata["scenario"]), int(metadata["seed"]))))
    if len({item[2] for item in runs}) != 1:
        raise ValueError("common-trip runs must use the same scenario and seed")
    if len({item[0] for item in runs}) != len(runs):
        raise ValueError("common-trip run IDs must be unique")
    common_ids = set.intersection(*(set(item[1]) for item in runs))
    if not common_ids:
        raise ValueError("runs have no completed vehicle IDs in common")
    return {
        "scenario": runs[0][2][0],
        "seed": runs[0][2][1],
        "vehicle_ids": sorted(common_ids),
        "n_common": len(common_ids),
        "mean_travel_time_by_run": {
            run_id: _mean([trip_times[vehicle_id] for vehicle_id in sorted(common_ids)])
            for run_id, trip_times, _ in runs
        },
    }


def summarize_run(run_dir: str | Path, *, family: str = "single") -> dict[str, Any]:
    """Create the one-row Section 11 summary from immutable episode files."""
    directory = Path(run_dir)
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    trips = _read_csv(directory / "trips.csv")
    steps = _read_csv(directory / "steps.csv")
    junction = [row for row in trips if _bool(row["route_through_junction"])]
    completed = [row for row in trips if _bool(row["completed"])]
    completed_junction = [row for row in junction if _bool(row["completed"])]

    def trip_time(row: dict[str, str], *, censored: bool) -> float:
        if censored and not _bool(row["completed"]):
            return max(0.0, float(run["sim_end_time"]) - float(row["scheduled_depart"]))
        return float(row["depart_delay"]) + float(row["duration"])

    crossed = [row for row in trips if _bool(row["passed_controlled_junction"])]
    queues_by_time: dict[str, list[float]] = {}
    congestion_by_time: dict[str, list[str]] = {}
    for index, row in enumerate(steps):
        sim_time = row.get("sim_time", str(index))
        queues_by_time.setdefault(sim_time, []).append(float(row["halting"]))
        congestion_by_time.setdefault(sim_time, []).append(row.get("congestion", "").lower())
    junction_rows = _read_csv(directory / "junctions.csv") if family == "network" else []
    if family == "network" and not junction_rows:
        raise ValueError("network summary requires per-TLS junction.csv rows")
    config_path = directory.parents[2] / "config" / "stms.yaml"
    if not config_path.exists():
        config_path = Path(__file__).resolve().parents[2] / "config" / "stms.yaml"
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    n = len(trips)
    nj = len(junction)
    result: dict[str, Any] = {
        "run_id": run["run_id"], "controller": run["controller"], "scenario": run["scenario"],
        "seed": run["seed"], "git_commit": commit, "config_hash": config_hash,
        "metrics_version": 1, "n_trips": n, "n_trips_junction": nj,
        "n_completed": len(completed), "n_unfinished": n - len(completed),
        "completion_rate": len(completed) / n if n else 0.0,
        "completion_rate_junction": len(completed_junction) / nj if nj else 0.0,
        "avg_travel_time_completed": _mean([trip_time(row, censored=False) for row in completed]),
        "avg_travel_time_censored": _mean([trip_time(row, censored=True) for row in trips]),
        "avg_travel_time_junction_completed": _mean([trip_time(row, censored=False) for row in completed_junction]),
        "avg_travel_time_junction_censored": _mean([trip_time(row, censored=True) for row in junction]),
        "avg_wait": _mean([float(row["waiting_time"]) for row in trips]),
        "avg_time_loss": _mean([float(row["time_loss"]) for row in trips]),
        "avg_depart_delay": _mean([float(row["depart_delay"]) for row in trips]),
        "avg_queue": _mean([sum(values) for values in queues_by_time.values()]),
        "avg_speed": _mean([
            float(row["route_length"]) / max(trip_time(row, censored=True), 1e-9) * 3.6
            for row in trips if float(row["route_length"]) > 0
        ]),
        "throughput_veh_per_min": (
            len(completed) if family == "network" else len(crossed)
        ) / (float(run["sim_end_time"]) / 60.0) if float(run["sim_end_time"]) > 0 else 0.0,
        "frac_time_high_congestion": sum(
            any(level == "high" for level in levels)
            for levels in congestion_by_time.values()
        ) / len(congestion_by_time) if congestion_by_time else 0.0,
        "teleports": run["teleports"], "sim_end_time": run["sim_end_time"],
        "wall_clock_s": run["wall_clock_s"], "family": family,
        "n_tls_controlled": 1 if family == "single" else int(run["n_tls_controlled"]),
        "n_tls_ai": 0 if family == "single" else int(run["n_tls_ai"]),
        "ai_coverage": "none" if family == "single" else str(run["ai_coverage"]),
        "avg_junction_queue_mean": _mean([float(row["avg_queue"]) for row in junction_rows])
        if family == "network" else "",
        "worst_junction_avg_queue": max(
            (float(row["avg_queue"]) for row in junction_rows), default=0.0
        ) if family == "network" else "",
    }
    with (directory / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerow(result)
    return result
