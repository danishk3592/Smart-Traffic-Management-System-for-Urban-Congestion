"""Synthetic exact checks for the M1 evaluator's paired and censored metrics."""

from __future__ import annotations

from typing import Any

import pytest

from Ai.evaluation import evaluate
from Ai.evaluation.evaluate import _complete_for_cell
from Ai.evaluation.metrics import RunData, build_comparison_rows, improvement, per_episode_values


def _record(controller: str, scenario: str, seed: int, trips: list[dict[str, Any]]) -> RunData:
    run = {
        "run_id": f"{controller}_{scenario}_{seed}", "controller": controller,
        "scenario": scenario, "seed": seed, "sim_end_time": 1000.0, "teleports": 2,
    }
    summary = {
        "run_id": run["run_id"], "family": "single", "n_trips": str(len(trips)),
        "avg_queue": "12", "throughput_veh_per_min": "3.5",
        "frac_time_high_congestion": "0.25",
    }
    rows = []
    for trip in trips:
        rows.append({
            "vehicle_id": str(trip["vehicle_id"]),
            "scheduled_depart": str(trip.get("scheduled_depart", 0)),
            "depart_delay": str(trip.get("depart_delay", 0)),
            "duration": str(trip["duration"]) if trip.get("completed") else "",
            "waiting_time": str(trip.get("waiting_time", 0)),
            "time_loss": str(trip.get("time_loss", 0)),
            "completed": str(bool(trip.get("completed"))),
            "route_through_junction": str(bool(trip.get("route_through_junction"))),
        })
    return RunData(run=run, summary=summary, trips=rows)


def _trip(
    vehicle_id: str,
    duration: float | None,
    *,
    junction: bool,
    depart: float = 0,
    waiting: float = 0,
    loss: float = 0,
) -> dict[str, Any]:
    return {
        "vehicle_id": vehicle_id, "duration": duration,
        "completed": duration is not None, "route_through_junction": junction,
        "scheduled_depart": depart, "waiting_time": waiting, "time_loss": loss,
    }


@pytest.fixture
def paired_records() -> list[RunData]:
    controller_trips = {
        "fixed": [_trip("a", 100, junction=True), _trip("b", 200, junction=True),
                  _trip("c", 300, junction=False), _trip("d", None, junction=True, depart=100)],
        "rule": [_trip("a", 110, junction=True), _trip("b", 210, junction=True),
                 _trip("c", None, junction=False), _trip("d", 90, junction=True, depart=100)],
        "rl": [_trip("a", 80, junction=True), _trip("b", 180, junction=True),
               _trip("c", 500, junction=False), _trip("d", 200, junction=True, depart=100)],
    }
    return [_record(name, "medium", 5000, trips) for name, trips in controller_trips.items()]


def _find(
    rows: list[dict[str, Any]], *, aggregation: str, scenario: str,
    controller: str, metric: str, scope: str, trip_basis: str,
) -> dict[str, Any]:
    return next(row for row in rows if (
        row["aggregation"], row["scenario"], row["controller"], row["metric"],
        row["scope"], row["trip_basis"],
    ) == (aggregation, scenario, controller, metric, scope, trip_basis))


def test_common_trip_uses_only_ids_completed_by_every_controller(paired_records: list[RunData]) -> None:
    cells = per_episode_values(paired_records, ("fixed", "rule", "rl"))
    fixed = cells[("medium", 5000, "fixed", "junction", "travel_time", "common")]
    rl = cells[("medium", 5000, "rl", "junction", "travel_time", "common")]
    assert fixed.n_trips == rl.n_trips == 2
    assert fixed.value == 150
    assert rl.value == 130


def test_censored_time_completion_rate_and_common_trip_improvement(paired_records: list[RunData]) -> None:
    rows = build_comparison_rows(
        paired_records, seed_set="dev", controllers=("fixed", "rule", "rl"),
    )
    fixed_censored = _find(rows, aggregation="scenario", scenario="medium", controller="fixed",
                           metric="travel_time", scope="all", trip_basis="all")
    rl_censored = _find(rows, aggregation="scenario", scenario="medium", controller="rl",
                        metric="travel_time", scope="all", trip_basis="all")
    rl_completion = _find(rows, aggregation="scenario", scenario="medium", controller="rl",
                          metric="completion_rate", scope="all", trip_basis="all")
    rl_common = _find(rows, aggregation="scenario", scenario="medium", controller="rl",
                      metric="travel_time", scope="junction", trip_basis="common")
    paired_ci = _find(rows, aggregation="scenario", scenario="medium", controller="rl",
                      metric="travel_time_improvement_vs_fixed_pct", scope="junction", trip_basis="common")

    assert fixed_censored["mean"] == 375
    assert rl_censored["mean"] == 240
    assert rl_completion["mean"] == 1
    assert rl_common["mean"] == 130
    assert rl_common["improvement_vs_fixed_pct"] == pytest.approx(100 * (150 - 130) / 150)
    assert paired_ci["mean"] == pytest.approx(100 * (150 - 130) / 150)
    assert paired_ci["ci95_low"] == paired_ci["ci95_high"] == paired_ci["mean"]


def test_improvement_sign_is_correct_for_cost_and_benefit_metrics() -> None:
    assert improvement(100, 80, "travel_time") == 20
    assert improvement(100, 120, "throughput") == 20
    assert improvement(0, 1, "throughput") is None


def test_low_is_excluded_from_headline_and_rows_are_reproducible() -> None:
    records = []
    for scenario in ("balanced", "directional_ns", "directional_ew", "low", "medium", "heavy", "rush_hour"):
        fixed_time = 1000 if scenario == "low" else 100
        rl_time = 0 if scenario == "low" else 90
        for controller, duration in (("fixed", fixed_time), ("rule", fixed_time), ("rl", rl_time)):
            records.append(_record(controller, scenario, 5000, [_trip("v", duration, junction=True)]))
    first = build_comparison_rows(records, seed_set="dev", controllers=("fixed", "rule", "rl"))
    second = build_comparison_rows(records, seed_set="dev", controllers=("fixed", "rule", "rl"))
    headline = _find(first, aggregation="headline", scenario="headline", controller="rl",
                     metric="travel_time", scope="junction", trip_basis="common")
    low = _find(first, aggregation="low", scenario="low", controller="rl",
                metric="travel_time", scope="junction", trip_basis="common")
    assert headline["improvement_vs_fixed_pct"] == 10
    assert headline["target_met"] is True
    assert low["improvement_vs_fixed_pct"] == 100
    assert first == second


def test_resume_accepts_legacy_single_run_without_top_level_family(tmp_path) -> None:
    run_id = "fixed_heavy_6000"
    (tmp_path / "run.json").write_text(
        '{"run_id":"fixed_heavy_6000","controller":"fixed",'
        '"scenario":"heavy","seed":6000}\n',
        encoding="utf-8",
    )
    (tmp_path / "summary.csv").write_text(
        "run_id,family,n_trips,config_hash\n"
        f"{run_id},single,1,config-hash\n",
        encoding="utf-8",
    )
    (tmp_path / "trips.csv").write_text(
        "vehicle_id\nveh_1\n", encoding="utf-8",
    )
    (tmp_path / "steps.csv").write_text("sim_time\n1\n", encoding="utf-8")
    (tmp_path / "evaluation.json").write_text(
        '{"seed_set":"final","route_sha256":"route-hash",'
        '"config_sha256":"config-hash","model_sha256":null,"family":"single"}\n',
        encoding="utf-8",
    )

    assert _complete_for_cell(
        tmp_path,
        scenario="heavy",
        seed=6000,
        controller="fixed",
        seed_set="final",
        route_hash="route-hash",
        config_hash="config-hash",
        model_hash=None,
    )


def test_single_evaluation_rejects_config_drift_before_episode(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed config must not start cells with stale preflight lineage."""
    monkeypatch.setattr(evaluate, "_sha256", lambda _path: "changed-config")
    monkeypatch.setattr(
        evaluate, "get_controller",
        lambda *_args, **_kwargs: pytest.fail("controller built after config drift"),
    )
    with pytest.raises(RuntimeError, match="changed after evaluation preflight"):
        evaluate._run_one(
            scenario="medium", seed=6000, controller_name="fixed", seed_set="final",
            route_path=tmp_path / "routes.rou.xml", route_hash="route",
            config_hash="preflight-config", config={}, model_path=tmp_path / "model.zip",
            model_hash="",
        )


def test_single_evaluation_rejects_config_drift_after_episode(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An episode run across config edits must remain unlineaged."""
    hashes = iter(("preflight-config", "changed-config"))
    monkeypatch.setattr(evaluate, "_sha256", lambda _path: next(hashes))
    monkeypatch.setattr(evaluate, "get_controller", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        evaluate, "run_episode", lambda *_args, **_kwargs: {"out_dir": str(tmp_path)},
    )
    with pytest.raises(RuntimeError, match="preserving unlineaged output"):
        evaluate._run_one(
            scenario="medium", seed=6000, controller_name="fixed", seed_set="final",
            route_path=tmp_path / "routes.rou.xml", route_hash="route",
            config_hash="preflight-config", config={}, model_path=tmp_path / "model.zip",
            model_hash="",
        )
    assert not (tmp_path / "evaluation.json").exists()


def test_network_evaluation_rejects_config_drift_after_episode(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Network cells enforce the same before/after config fingerprint."""
    hashes = iter(("preflight-config", "changed-config"))
    monkeypatch.setattr(evaluate, "_sha256", lambda _path: next(hashes))
    monkeypatch.setattr(evaluate, "get_network_controller", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        evaluate, "run_episode", lambda *_args, **_kwargs: {"out_dir": str(tmp_path)},
    )
    with pytest.raises(RuntimeError, match="preserving unlineaged output"):
        evaluate._run_network_one(
            root=tmp_path, scenario="net_medium", seed=6000, controller_name="fixed",
            route_path=tmp_path / "routes.rou.xml", route_hash="route",
            config_hash="preflight-config", controller_config_hash="controller-config",
            config={}, tls_configs=[], model_path=tmp_path / "model.zip", model_hash="",
            seed_set="final",
        )
    assert not (tmp_path / "evaluation.json").exists()
