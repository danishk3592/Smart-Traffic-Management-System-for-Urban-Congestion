"""Network metric arithmetic and route-comparison tests."""

import csv
import json
from pathlib import Path

import pytest

from Ai.common.metrics import SUMMARY_FIELDS, common_completed_trip_times, summarize_run


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _run_dir(root: Path, run_id: str, controller: str, trips: list[dict[str, object]]) -> Path:
    path = root / run_id
    path.mkdir()
    (path / "run.json").write_text(json.dumps({
        "run_id": run_id, "controller": controller, "scenario": "net_medium", "seed": 3000,
        "sim_end_time": 100.0, "wall_clock_s": 5.0, "teleports": 2,
        "n_tls_controlled": 12, "n_tls_ai": 0, "ai_coverage": "none",
    }), encoding="utf-8")
    _write_csv(path / "trips.csv", (
        "vehicle_id", "completed", "route_through_junction", "trip_time", "scheduled_depart",
        "depart_delay", "duration", "waiting_time", "time_loss", "route_length",
        "passed_controlled_junction",
    ), trips)
    _write_csv(path / "steps.csv", ("sim_time", "halting", "congestion"), [
        {"sim_time": 0, "halting": 5, "congestion": "Low"},
        {"sim_time": 0, "halting": 7, "congestion": "High"},
        {"sim_time": 1, "halting": 2, "congestion": "Low"},
        {"sim_time": 1, "halting": 4, "congestion": "Low"},
    ])
    _write_csv(path / "junctions.csv", (
        "tls_id", "avg_queue", "frac_time_high_congestion",
    ), [
        {"tls_id": f"tls_{i}", "avg_queue": queue, "frac_time_high_congestion": share}
        for i, queue, share in ((1, 4, 0.25), (2, 9, 0.5))
    ])
    return path


def test_network_summary_uses_all_network_trip_and_junction_metrics(tmp_path: Path) -> None:
    trips = [
        {"vehicle_id": "a", "completed": True, "route_through_junction": True,
         "trip_time": 20, "scheduled_depart": 0, "depart_delay": 0, "duration": 20,
         "waiting_time": 4, "time_loss": 6, "route_length": 100, "passed_controlled_junction": True},
        {"vehicle_id": "b", "completed": False, "route_through_junction": False,
         "trip_time": 100, "scheduled_depart": 0, "depart_delay": 0, "duration": "",
         "waiting_time": 8, "time_loss": 10, "route_length": 50, "passed_controlled_junction": False},
    ]
    path = _run_dir(tmp_path, "fixed", "fixed", trips)

    result = summarize_run(path, family="network")

    assert tuple(result) == SUMMARY_FIELDS
    assert result["n_trips"] == 2
    assert result["n_completed"] == 1
    assert result["n_unfinished"] == 1
    assert result["completion_rate"] == 0.5
    assert result["avg_travel_time_completed"] == 20
    assert result["avg_travel_time_censored"] == 60
    assert result["avg_wait"] == 6
    assert result["avg_time_loss"] == 8
    assert result["avg_queue"] == 9
    assert result["avg_speed"] == pytest.approx(9.9)
    assert result["throughput_veh_per_min"] == 0.6
    assert result["frac_time_high_congestion"] == 0.5
    assert result["teleports"] == 2
    assert result["n_tls_controlled"] == 12
    assert result["avg_junction_queue_mean"] == 6.5
    assert result["worst_junction_avg_queue"] == 9
    assert (path / "summary.csv").is_file()


def test_common_completed_trip_times_intersects_vehicle_ids(tmp_path: Path) -> None:
    first = _run_dir(tmp_path, "fixed", "fixed", [
        {"vehicle_id": "shared", "completed": True, "trip_time": 20},
        {"vehicle_id": "fixed_only", "completed": True, "trip_time": 30},
    ])
    second = _run_dir(tmp_path, "rule", "rule", [
        {"vehicle_id": "shared", "completed": True, "trip_time": 25},
        {"vehicle_id": "rule_only", "completed": True, "trip_time": 40},
    ])

    result = common_completed_trip_times([first, second])

    assert result["n_common"] == 1
    assert result["vehicle_ids"] == ["shared"]
    assert result["mean_travel_time_by_run"] == {"fixed": 20.0, "rule": 25.0}


def test_common_completed_trip_times_rejects_empty_intersection(tmp_path: Path) -> None:
    first = _run_dir(tmp_path, "fixed", "fixed", [
        {"vehicle_id": "a", "completed": True, "trip_time": 20},
    ])
    second = _run_dir(tmp_path, "rule", "rule", [
        {"vehicle_id": "b", "completed": True, "trip_time": 25},
    ])

    with pytest.raises(ValueError, match="no completed vehicle IDs"):
        common_completed_trip_times([first, second])
