"""Exact small-fixture checks for T1.4 metrics definitions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from Ai.common.metrics import SUMMARY_FIELDS, summarize_run
from Ai.common.run_episode import _route_catalog, _trip_rows


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_summary_exact_completed_censored_and_route_membership(tmp_path: Path) -> None:
    run = {
        "run_id": "fixture", "controller": "fixed", "scenario": "tiny", "seed": 7,
        "sim_end_time": 100, "wall_clock_s": 2.5, "teleports": 1,
    }
    (tmp_path / "run.json").write_text(json.dumps(run), encoding="utf-8")
    trip_fields = (
        "vehicle_id", "scheduled_depart", "depart_delay", "duration", "trip_time", "waiting_time",
        "time_loss", "route_length", "completed", "route_through_junction",
        "passed_controlled_junction",
    )
    _write_csv(tmp_path / "trips.csv", trip_fields, [
        {"vehicle_id": "through", "scheduled_depart": 10, "depart_delay": 2, "duration": 18,
         "trip_time": 20, "waiting_time": 4, "time_loss": 5, "route_length": 200,
         "completed": True, "route_through_junction": True, "passed_controlled_junction": True},
        # An approach-edge-only route is not a junction trip.
        {"vehicle_id": "approach_only", "scheduled_depart": 20, "depart_delay": 0, "duration": "",
         "trip_time": 80, "waiting_time": 3, "time_loss": 4, "route_length": 100,
         "completed": False, "route_through_junction": False, "passed_controlled_junction": False},
        {"vehicle_id": "unfinished_through", "scheduled_depart": 30, "depart_delay": 5, "duration": "",
         "trip_time": 70, "waiting_time": 6, "time_loss": 7, "route_length": 300,
         "completed": False, "route_through_junction": True, "passed_controlled_junction": False},
    ])
    _write_csv(tmp_path / "steps.csv", ("sim_time", "approach", "halting", "congestion"), [
        {"sim_time": 0, "approach": "A", "halting": 2, "congestion": "High"},
        {"sim_time": 0, "approach": "B", "halting": 4, "congestion": "Low"},
        {"sim_time": 5, "approach": "A", "halting": 4, "congestion": "Low"},
        {"sim_time": 5, "approach": "B", "halting": 6, "congestion": "Low"},
    ])

    result = summarize_run(tmp_path)

    assert tuple(result) == SUMMARY_FIELDS
    assert result["n_trips"] == 3
    assert result["n_trips_junction"] == 2
    assert result["n_completed"] == 1
    assert result["n_unfinished"] == 2
    assert result["completion_rate"] == 1 / 3
    assert result["completion_rate_junction"] == 1 / 2
    assert result["avg_travel_time_completed"] == 20
    assert result["avg_travel_time_censored"] == 170 / 3
    assert result["avg_travel_time_junction_completed"] == 20
    assert result["avg_travel_time_junction_censored"] == 45
    assert result["avg_wait"] == 13 / 3
    assert result["avg_time_loss"] == 16 / 3
    assert result["avg_depart_delay"] == 7 / 3
    assert result["avg_queue"] == 8
    assert result["throughput_veh_per_min"] == 0.6
    assert result["frac_time_high_congestion"] == 0.5
    assert result["family"] == "single"
    assert result["n_tls_controlled"] == 1
    assert result["n_tls_ai"] == 0
    assert result["ai_coverage"] == "none"
    assert result["avg_junction_queue_mean"] == ""
    with (tmp_path / "summary.csv").open(encoding="utf-8", newline="") as stream:
        written = next(csv.DictReader(stream))
    assert list(written) == list(SUMMARY_FIELDS)
    assert "nan" not in {str(value).lower() for value in written.values()}


def test_route_membership_requires_a_controlled_edge_pair(tmp_path: Path) -> None:
    route_file = tmp_path / "routes.rou.xml"
    route_file.write_text(
        '<routes><vehicle id="through" depart="0"><route edges="in out"/></vehicle>'
        '<vehicle id="approach_only" depart="1"><route edges="in side"/></vehicle></routes>',
        encoding="utf-8",
    )

    class Edge:
        def getLength(self) -> float:
            return 10.0

    class Net:
        def getEdge(self, edge_id: str) -> Edge:
            return Edge()

    movements = [{"from_edge": "in", "to_edge": "out"}]
    catalog = _route_catalog(route_file, Net(), movements)
    assert catalog["through"]["route_through_junction"] is True
    assert catalog["through"]["first_controlled_movement"] == "in->out"
    assert catalog["approach_only"]["route_through_junction"] is False
    assert catalog["approach_only"]["first_controlled_movement"] == ""


def test_trip_rows_censor_departure_backlog_and_unfinished_tripinfo() -> None:
    catalog = {
        "backlog": {"vtype": "car", "scheduled_depart": 20, "route_length": 100,
                    "route_through_junction": False, "first_controlled_movement": "",
                    "n_controlled_junctions_on_route": 0},
        "active": {"vtype": "car", "scheduled_depart": 25, "route_length": 500,
                   "route_through_junction": True, "first_controlled_movement": "in->out",
                   "n_controlled_junctions_on_route": 1},
    }
    rows = _trip_rows(
        "fixture", "fixed", "tiny", 1, catalog,
        {
            "backlog": {"depart": "-1", "arrival": "-1", "duration": "0",
                        "waitingTime": "0", "timeLoss": "0", "routeLength": "0"},
            "active": {"depart": "30", "arrival": "-1", "duration": "50",
                       "departDelay": "5", "waitingTime": "12", "timeLoss": "14",
                       "routeLength": "450"},
        },
        {}, {}, set(), 100,
    )
    backlog, active = rows
    assert backlog["actual_depart"] == ""
    assert backlog["depart_delay"] == 80
    assert backlog["trip_time"] == 80
    assert active["actual_depart"] == 30
    assert active["trip_time"] == 75
    assert active["waiting_time"] == 12
    assert active["time_loss"] == 14
    assert active["route_length"] == 450
    assert active["completed"] is False
