from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from Ai.common.config import load_config
from Ai.common.metrics import classify_ai_coverage
from Ai.evaluation.evaluate import (
    NETWORK_PINNED_MODEL,
    _network_complete_cell,
    _network_controller_config_hash,
    merge_comparison_milestones,
)
from Ai.evaluation.metrics import RunData, build_comparison_rows
from scripts.make_scenarios import ScenarioBuilder


def _record(controller: str, scenario: str, seed: int, trips: list[dict[str, str]]) -> RunData:
    return RunData(
        run={
            "run_id": f"{scenario}-{seed}-{controller}", "controller": controller,
            "scenario": scenario, "seed": seed, "sim_end_time": 3600, "teleports": 0,
            "family": "network",
        },
        summary={
            "run_id": f"{scenario}-{seed}-{controller}", "family": "network",
            "avg_queue": "2", "throughput_veh_per_min": "1", "frac_time_high_congestion": "0.1",
        },
        trips=trips,
    )


def _trip(vehicle_id: str, duration: float | None, *, depart: float = 0) -> dict[str, str]:
    return {
        "vehicle_id": vehicle_id, "scheduled_depart": str(depart),
        "depart_delay": "0", "duration": "" if duration is None else str(duration),
        "waiting_time": "0", "time_loss": "0", "completed": str(duration is not None),
        "route_through_junction": "True",
    }


def _find(rows: list[dict], *, aggregation: str, scenario: str, controller: str,
          metric: str, scope: str = "all", trip_basis: str = "common") -> dict:
    return next(row for row in rows if (
        row["aggregation"], row["scenario"], row["controller"], row["metric"],
        row["scope"], row["trip_basis"],
    ) == (aggregation, scenario, controller, metric, scope, trip_basis))


def test_m2_headline_is_four_non_low_scenarios_and_common_trip_target() -> None:
    records = []
    scenarios = ("net_balanced", "net_low", "net_medium", "net_heavy", "net_rush_hour")
    for scenario in scenarios:
        for seed in (5000, 5001):
            baseline = 1000 if scenario == "net_low" else 100
            rl_time = 0 if scenario == "net_low" else 90
            for controller, duration in (("fixed", baseline), ("rule", baseline - 5), ("rl", rl_time)):
                records.append(_record(controller, scenario, seed, [_trip("common", duration)]))

    rows = build_comparison_rows(records, seed_set="dev", controllers=("fixed", "rule", "rl"), family="network")
    headline = _find(rows, aggregation="headline", scenario="headline", controller="rl",
                     metric="travel_time_improvement_vs_fixed_pct")
    low = _find(rows, aggregation="low", scenario="net_low", controller="rl",
                metric="travel_time_improvement_vs_fixed_pct")
    assert headline["milestone"] == "M2"
    assert headline["improvement_vs_fixed_pct"] == pytest.approx(10.0)
    assert headline["target_met"] is True
    assert low["improvement_vs_fixed_pct"] == 100.0
    assert headline["n_seeds"] == 2


def test_m2_common_set_and_censored_completion_are_both_reported() -> None:
    records = []
    for controller, trips in (
        ("fixed", [_trip("a", 100), _trip("b", None, depart=100)]),
        ("rule", [_trip("a", 110), _trip("b", 90, depart=100)]),
        ("rl", [_trip("a", 80), _trip("b", None, depart=100)]),
    ):
        records.append(_record(controller, "net_medium", 5000, trips))
    rows = build_comparison_rows(records, seed_set="dev", controllers=("fixed", "rule", "rl"), family="network")
    common = _find(rows, aggregation="scenario", scenario="net_medium", controller="rl",
                   metric="travel_time", trip_basis="common")
    censored = _find(rows, aggregation="scenario", scenario="net_medium", controller="rl",
                     metric="travel_time", trip_basis="all")
    completion = _find(rows, aggregation="scenario", scenario="net_medium", controller="rl",
                       metric="completion_rate", trip_basis="all")
    assert common["mean"] == 80
    assert common["n_trips_basis"] == 1
    assert censored["mean"] == pytest.approx((80 + 3500) / 2)
    assert completion["completion_rate_mean"] == 0.5


@pytest.mark.parametrize(("shares", "expected"), [
    ([0.95, 0.96], "full"), ([0.95, 0.94], "partial"), ([0.2, 0.94], "none"),
])
def test_ai_coverage_uses_configured_per_junction_threshold(shares: list[float], expected: str) -> None:
    coverage, statuses = classify_ai_coverage(shares, 0.95)
    assert coverage == expected
    assert all(status in {"rl", "rl_fallback"} for status in statuses)


def test_network_model_config_hash_pins_accepted_candidate() -> None:
    config = load_config()
    original = _network_controller_config_hash(config, "rl")
    config["rl_net"]["model_path"] = NETWORK_PINNED_MODEL.as_posix()
    assert _network_controller_config_hash(config, "rl") == original


def test_merging_m2_keeps_existing_m1_rows_unchanged() -> None:
    original = [
        {"milestone": "M1", "scenario": "headline", "mean": "1.234"},
        {"milestone": "M1", "scenario": "low", "mean": "9.876"},
        {"milestone": "M2", "scenario": "old", "mean": "0"},
    ]
    new_m2 = [{"milestone": "M2", "scenario": "headline", "mean": "4.321"}]
    merged = merge_comparison_milestones(original, new_m2)
    assert merged == [*original[:2], *new_m2]


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_resume_skips_only_complete_lineage_matching_network_cell(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    (tmp_path / "config").mkdir()
    shutil.copy2(repo / "config" / "stms.yaml", tmp_path / "config" / "stms.yaml")
    config = load_config(tmp_path / "config" / "stms.yaml")
    scenario, seed, controller = "net_balanced", 5000, "fixed"
    route = tmp_path / "SUMO" / "scenarios" / scenario / f"seed_{seed}" / "routes.rou.xml"
    route.parent.mkdir(parents=True)
    route.write_bytes(b"<routes/>\n")
    route_hash = hashlib.sha256(route.read_bytes()).hexdigest()
    config_hash = hashlib.sha256((tmp_path / "config" / "stms.yaml").read_bytes()).hexdigest()
    run_dir = tmp_path / "results" / "raw" / "cell"
    run_dir.mkdir(parents=True)
    run_id = "cell-fixed-net_balanced-s5000"
    run = {
        "run_id": run_id, "family": "network", "controller": controller,
        "scenario": scenario, "seed": seed, "sim_end_time": 10,
        "out_dir": str(run_dir), "teleports": 0,
    }
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    summary_fields = ("run_id", "family", "config_hash", "n_trips", "n_completed", "n_unfinished",
                      "n_tls_controlled", "ai_coverage", "completion_rate", "avg_travel_time_censored", "wall_clock_s")
    _write_csv(run_dir / "summary.csv", summary_fields, [{
        "run_id": run_id, "family": "network", "config_hash": config_hash,
        "n_trips": 1, "n_completed": 1, "n_unfinished": 0,
        "n_tls_controlled": len(config["network"]["controlled_tls"]), "ai_coverage": "none",
        "completion_rate": 1, "avg_travel_time_censored": 1, "wall_clock_s": 1,
    }])
    trip_fields = ("run_id", "vehicle_id", "scheduled_depart", "depart_delay", "duration", "waiting_time",
                   "time_loss", "completed", "route_through_junction")
    _write_csv(run_dir / "trips.csv", trip_fields, [{
        "run_id": run_id, "vehicle_id": "v", "scheduled_depart": 0, "depart_delay": 0,
        "duration": 1, "waiting_time": 0, "time_loss": 0, "completed": "True",
        "route_through_junction": "False",
    }])
    (run_dir / "steps.csv").write_text("run_id\ncell\n", encoding="utf-8")
    junction_fields = ("run_id", "tls_id", "avg_queue", "avg_wait", "n_ticks", "ppo_tick_share",
                       "n_illegal_actions", "n_forced_max_green")
    _write_csv(run_dir / "junctions.csv", junction_fields, [{
        "run_id": run_id, "tls_id": tls, "avg_queue": 0, "avg_wait": 0, "n_ticks": 1,
        "ppo_tick_share": 0, "n_illegal_actions": 0, "n_forced_max_green": 0,
    } for tls in config["network"]["controlled_tls"]])
    metadata = {
        "family": "network", "seed_set": "dev", "route_file": route.relative_to(tmp_path).as_posix(),
        "route_sha256": route_hash, "config_sha256": config_hash, "model_path": None,
        "model_sha256": None, "controller_config_sha256": _network_controller_config_hash(config, controller),
    }
    (run_dir / "evaluation.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert _network_complete_cell(
        tmp_path, scenario=scenario, seed=seed, controller=controller, route_hash=route_hash,
        config_hash=config_hash, controller_config_hash=metadata["controller_config_sha256"], model_hash=None,
    ) == run_dir
    assert _network_complete_cell(
        tmp_path, scenario=scenario, seed=seed, controller=controller, route_hash=route_hash,
        config_hash=config_hash, controller_config_hash=metadata["controller_config_sha256"],
        model_hash=None, seed_set="final",
    ) is None
    metadata["route_sha256"] = "incorrect"
    (run_dir / "evaluation.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert _network_complete_cell(
        tmp_path, scenario=scenario, seed=seed, controller=controller, route_hash=route_hash,
        config_hash=config_hash, controller_config_hash=metadata["controller_config_sha256"], model_hash=None,
    ) is None


def test_route_cache_validation_can_preserve_existing_scenario_config(tmp_path: Path) -> None:
    builder = object.__new__(ScenarioBuilder)
    builder.root = tmp_path
    builder._scenario_values = lambda scenario: {"scenario": scenario}
    builder._config_hash = lambda scenario: "frozen-config"
    builder._scenario_config = lambda scenario, seed: (_ for _ in ()).throw(
        AssertionError("scenario config must not be rewritten")
    )
    scenario, seed = "net_balanced", 5000
    scenario_dir = tmp_path / "SUMO" / "scenarios" / scenario
    seed_dir = scenario_dir / f"seed_{seed}"
    seed_dir.mkdir(parents=True)
    config_path = scenario_dir / f"{scenario}.sumocfg"
    config_path.write_bytes(b"owner-preserved scenario config\n")
    original_config = config_path.read_bytes()
    route = seed_dir / "routes.rou.xml"
    route.write_bytes(b"<routes/>\n")
    route_hash = hashlib.sha256(route.read_bytes()).hexdigest()
    (seed_dir / "manifest.json").write_text(json.dumps({
        "config_hash": "frozen-config", "route_sha256": route_hash,
    }), encoding="utf-8")

    assert builder.ensure_routes(scenario, seed, write_config=False) == route
    assert config_path.read_bytes() == original_config
