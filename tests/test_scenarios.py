"""Fast deterministic checks for scenario demand construction."""

import random

from scripts.make_scenarios import (
    SCENARIOS,
    ScenarioBuilder,
    _congestion_time_shares,
    _stable_hash,
)


def test_all_configured_scenarios_have_positive_counts() -> None:
    builder = ScenarioBuilder()
    assert set(builder.demand["scenarios"]) == set(SCENARIOS)
    assert all(builder._scenario_values(name)["vehicles"] > 0 for name in SCENARIOS)


def test_seeded_departures_and_rush_hour_ramp_are_reproducible() -> None:
    builder = ScenarioBuilder()
    first = builder._departures("rush_hour", 1000, random.Random(42))
    second = builder._departures("rush_hour", 1000, random.Random(42))
    assert first == second
    start, end = builder._scenario_values("rush_hour")["peak_window_s"]
    peak_share = sum(start <= value <= end for value in first) / len(first)
    assert 0.50 <= peak_share <= 0.60


def test_directional_scenarios_bias_the_origin_edge_bearings() -> None:
    builder = ScenarioBuilder()
    balanced = builder._origin_edges("balanced")
    north_south = builder._origin_edges("directional_ns")
    east_west = builder._origin_edges("directional_ew")
    assert len(north_south) == len(east_west) == len(balanced) // 2
    assert [edge.getID() for edge in north_south] != [edge.getID() for edge in east_west]


def test_through_candidate_pool_contains_a_controlled_movement() -> None:
    builder = ScenarioBuilder()
    builder.demand["candidate_pool_size"] = 8
    through, other = builder._candidate_catalog("balanced")
    assert len(through) == len(other) == 8
    assert all(
        (movement[0], movement[1]) in builder.movement_pairs
        for _, _, movement in through
    )


def test_hash_changes_when_demand_parameters_change() -> None:
    assert _stable_hash({"vehicles": 100}) != _stable_hash({"vehicles": 101})


def test_network_congestion_shares_use_configured_queue_bands() -> None:
    thresholds = {"low_max_halting": 4, "medium_max_halting": 12, "high_min_halting": 13}
    assert _congestion_time_shares([0, 4, 5, 12, 13], thresholds) == (0.4, 0.2)
    assert _congestion_time_shares([], thresholds) == (0.0, 0.0)
