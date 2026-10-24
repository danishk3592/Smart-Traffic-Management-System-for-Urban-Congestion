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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def summarize_run(run_dir: str | Path, *, family: str = "single") -> dict[str, Any]:
    """Create summary.csv for a run; single-family network-only fields are blank."""
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
        "throughput_veh_per_min": len(crossed) / (float(run["sim_end_time"]) / 60.0)
        if float(run["sim_end_time"]) > 0 else 0.0,
        "frac_time_high_congestion": sum(
            any(level == "high" for level in levels)
            for levels in congestion_by_time.values()
        ) / len(congestion_by_time) if congestion_by_time else 0.0,
        "teleports": run["teleports"], "sim_end_time": run["sim_end_time"],
        "wall_clock_s": run["wall_clock_s"], "family": family,
        "n_tls_controlled": 1 if family == "single" else "",
        "n_tls_ai": 0 if family == "single" else "",
        "ai_coverage": "none" if family == "single" else "",
        "avg_junction_queue_mean": "", "worst_junction_avg_queue": "",
    }
    with (directory / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerow(result)
    return result
