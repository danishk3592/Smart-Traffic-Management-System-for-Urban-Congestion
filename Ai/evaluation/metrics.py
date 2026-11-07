"""Deterministic M1/M2 aggregation using Section 11 and DEC-12 rules."""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunData:
    """Minimal immutable inputs required to aggregate one completed episode."""

    run: dict[str, Any]
    summary: dict[str, str]
    trips: list[dict[str, str]]

    @property
    def key(self) -> tuple[str, int, str]:
        """Return the scenario, seed and controller key."""
        return str(self.run["scenario"]), int(self.run["seed"]), str(self.run["controller"])


@dataclass(frozen=True)
class CellValue:
    """A per-episode value plus its trip denominator and completion rate."""

    value: float | None
    n_trips: int
    completion_rate: float


METRIC_DIRECTIONS = {
    "travel_time": "lower",
    "completion_rate": "higher",
    "completed_trips": "higher",
    "unfinished_trips": "lower",
    "waiting_time": "lower",
    "time_loss": "lower",
    "queue": "lower",
    "throughput": "higher",
    "congestion": "lower",
    "teleports": "lower",
}
TRIP_METRICS = {"travel_time", "completion_rate", "completed_trips", "unfinished_trips", "waiting_time", "time_loss"}
WEIGHTED_POOLED_METRICS = {"travel_time", "completion_rate", "waiting_time", "time_loss"}
AGGREGATIONS = (
    ("scenario", None),
    ("headline", ("balanced", "directional_ns", "directional_ew", "medium", "heavy", "rush_hour")),
    ("primary", ("medium", "heavy", "rush_hour")),
    ("low", ("low",)),
    ("pooled", ("balanced", "directional_ns", "directional_ew", "low", "medium", "heavy", "rush_hour")),
)
NETWORK_SCENARIOS = ("net_balanced", "net_low", "net_medium", "net_heavy", "net_rush_hour")
NETWORK_AGGREGATIONS = (
    ("scenario", None),
    ("headline", ("net_balanced", "net_medium", "net_heavy", "net_rush_hour")),
    ("primary", ("net_medium", "net_heavy", "net_rush_hour")),
    ("low", ("net_low",)),
    ("pooled", NETWORK_SCENARIOS),
)


def _truth(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def _trip_time(row: dict[str, str], run: dict[str, Any], *, censored: bool) -> float:
    if censored and not _truth(row["completed"]):
        return max(0.0, float(run["sim_end_time"]) - float(row["scheduled_depart"]))
    if not _truth(row["completed"]):
        raise ValueError("completed-trip travel time requested for an unfinished trip")
    return float(row["depart_delay"]) + float(row["duration"])


def _mean(values: Iterable[float]) -> float | None:
    data = list(values)
    return statistics.fmean(data) if data else None


def _scope_trips(record: RunData, scope: str) -> list[dict[str, str]]:
    if scope == "all":
        return record.trips
    return [row for row in record.trips if _truth(row["route_through_junction"])]


def per_episode_values(
    records: Iterable[RunData], controllers: tuple[str, ...]
) -> dict[tuple[str, int, str, str, str, str], CellValue]:
    """Create per-run metrics; common travel time uses trips completed by every controller."""
    grouped: dict[tuple[str, int], dict[str, RunData]] = defaultdict(dict)
    for record in records:
        scenario, seed, controller = record.key
        grouped[(scenario, seed)][controller] = record

    result: dict[tuple[str, int, str, str, str, str], CellValue] = {}
    for (scenario, seed), cell in grouped.items():
        present = tuple(controller for controller in controllers if controller in cell)
        if not present:
            continue
        for scope in ("all", "junction"):
            trips_by_controller = {name: _scope_trips(cell[name], scope) for name in present}
            common_ids: set[str] | None = None
            for name in present:
                completed_ids = {
                    row["vehicle_id"] for row in trips_by_controller[name] if _truth(row["completed"])
                }
                common_ids = completed_ids if common_ids is None else common_ids & completed_ids

            for controller in present:
                record = cell[controller]
                trips = trips_by_controller[controller]
                completed = [row for row in trips if _truth(row["completed"])]
                completion_rate = len(completed) / len(trips) if trips else 0.0
                lookup = {row["vehicle_id"]: row for row in trips}
                common_times = (
                    [_trip_time(lookup[vehicle_id], record.run, censored=False) for vehicle_id in sorted(common_ids or ())]
                )
                censored_times = [_trip_time(row, record.run, censored=True) for row in trips]
                summary = record.summary
                episode_metrics: dict[tuple[str, str], CellValue] = {
                    ("travel_time", "common"): CellValue(_mean(common_times), len(common_times), completion_rate),
                    ("travel_time", "all"): CellValue(_mean(censored_times), len(trips), completion_rate),
                    ("completion_rate", "all"): CellValue(completion_rate, len(trips), completion_rate),
                    ("completed_trips", "all"): CellValue(float(len(completed)), len(trips), completion_rate),
                    ("unfinished_trips", "all"): CellValue(float(len(trips) - len(completed)), len(trips), completion_rate),
                    ("waiting_time", "all"): CellValue(_mean(float(row["waiting_time"]) for row in trips), len(trips), completion_rate),
                    ("time_loss", "all"): CellValue(_mean(float(row["time_loss"]) for row in trips), len(trips), completion_rate),
                }
                # Traffic-signal-level measures use the controlled-junction scope once.
                if scope == "junction":
                    episode_metrics.update({
                        ("queue", "all"): CellValue(float(summary["avg_queue"]), len(trips), completion_rate),
                        ("throughput", "all"): CellValue(float(summary["throughput_veh_per_min"]), len(trips), completion_rate),
                        ("congestion", "all"): CellValue(float(summary["frac_time_high_congestion"]), len(trips), completion_rate),
                        ("teleports", "all"): CellValue(float(record.run["teleports"]), len(trips), completion_rate),
                    })
                for (metric, trip_basis), value in episode_metrics.items():
                    result[(scenario, seed, controller, scope, metric, trip_basis)] = value
    return result


def improvement(reference: float, candidate: float, metric: str) -> float | None:
    """Return sign-correct percent improvement for a metric."""
    if reference == 0:
        return 0.0 if candidate == 0 else None
    direction = METRIC_DIRECTIONS.get(
        metric.removesuffix("_improvement_vs_fixed_pct").removesuffix("_improvement_vs_rule_pct"),
        "lower",
    )
    delta = reference - candidate if direction == "lower" else candidate - reference
    return delta / abs(reference) * 100.0


def _bootstrap_ci(values: list[float], seed: int) -> tuple[float | None, float | None]:
    """Return a reproducible percentile 95% bootstrap interval for a mean."""
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    samples = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(4000))
    low = samples[int(0.025 * (len(samples) - 1))]
    high = samples[int(0.975 * (len(samples) - 1))]
    return low, high


def _aggregation_seed_values(
    cells: dict[tuple[str, int, str, str, str, str], CellValue],
    *,
    scenarios: tuple[str, ...],
    seed: int,
    controller: str,
    scope: str,
    metric: str,
    trip_basis: str,
    pooled: bool,
) -> tuple[float | None, int, float | None]:
    observations = [
        cells[(scenario, seed, controller, scope, metric, trip_basis)]
        for scenario in scenarios
        if (scenario, seed, controller, scope, metric, trip_basis) in cells
        and cells[(scenario, seed, controller, scope, metric, trip_basis)].value is not None
    ]
    if not observations:
        return None, 0, None
    values = [float(item.value) for item in observations]
    n_trips = sum(item.n_trips for item in observations)
    if pooled:
        if metric in WEIGHTED_POOLED_METRICS:
            weights = [item.n_trips for item in observations]
            value = sum(v * w for v, w in zip(values, weights, strict=True)) / sum(weights) if sum(weights) else None
        elif metric in {"completed_trips", "unfinished_trips", "teleports"}:
            value = sum(values)
        else:
            value = statistics.fmean(values)
    else:
        value = statistics.fmean(values)
    completion = statistics.fmean(item.completion_rate for item in observations)
    return value, n_trips, completion


def build_comparison_rows(
    records: Iterable[RunData],
    *,
    seed_set: str,
    controllers: tuple[str, ...],
    target_reduction_pct: float = 10.0,
    bootstrap_seed: int = 91731,
    family: str = "single",
    target_controllers: tuple[str, ...] = ("rl",),
) -> list[dict[str, Any]]:
    """Aggregate M1 or M2 data using the corresponding frozen scenario family."""
    if family not in {"single", "network"}:
        raise ValueError(f"Unknown evaluation family {family!r}")
    all_records = list(records)
    cells = per_episode_values(all_records, controllers)
    available_scenarios = {key[0] for key in cells}
    seeds = sorted({key[1] for key in cells})
    aggregations = NETWORK_AGGREGATIONS if family == "network" else AGGREGATIONS
    milestone = "M2" if family == "network" else "M1"
    rows: list[dict[str, Any]] = []
    metric_specs = (
        ("travel_time", "all", "common"), ("travel_time", "all", "all"),
        ("travel_time", "junction", "common"), ("travel_time", "junction", "all"),
        ("completion_rate", "all", "all"), ("completion_rate", "junction", "all"),
        ("completed_trips", "all", "all"), ("completed_trips", "junction", "all"),
        ("unfinished_trips", "all", "all"), ("unfinished_trips", "junction", "all"),
        ("waiting_time", "all", "all"), ("waiting_time", "junction", "all"),
        ("time_loss", "all", "all"), ("time_loss", "junction", "all"),
        ("queue", "junction", "all"), ("throughput", "junction", "all"),
        ("congestion", "junction", "all"), ("teleports", "junction", "all"),
    )
    for aggregation, configured_scenarios in aggregations:
        if aggregation == "scenario":
            aggregation_cases = [(scenario, (scenario,)) for scenario in sorted(available_scenarios)]
        elif family == "network" and aggregation == "low":
            selected = tuple(scenario for scenario in configured_scenarios or () if scenario in available_scenarios)
            aggregation_cases = [("net_low", selected)] if selected else []
        else:
            selected = tuple(scenario for scenario in configured_scenarios or () if scenario in available_scenarios)
            aggregation_cases = [(aggregation, selected)] if selected else []
        for scenario_label, included_scenarios in aggregation_cases:
            if not included_scenarios:
                continue
            pooled = aggregation == "pooled"
            for metric, scope, trip_basis in metric_specs:
                by_controller: dict[str, dict[int, tuple[float, int, float | None]]] = {}
                for controller in controllers:
                    by_controller[controller] = {
                        seed: _aggregation_seed_values(
                            cells, scenarios=included_scenarios, seed=seed, controller=controller,
                            scope=scope, metric=metric, trip_basis=trip_basis, pooled=pooled,
                        )
                        for seed in seeds
                    }
                ref_fixed = by_controller.get("fixed", {})
                ref_rule = by_controller.get("rule", {})
                improvement_values: dict[str, dict[str, list[float]]] = {}
                for controller in controllers:
                    pairs_fixed: list[float] = []
                    pairs_rule: list[float] = []
                    for seed, (value, _, _) in by_controller[controller].items():
                        if value is None:
                            continue
                        fixed_value = ref_fixed.get(seed, (None, 0, None))[0]
                        rule_value = ref_rule.get(seed, (None, 0, None))[0]
                        if fixed_value is not None:
                            result_fixed = improvement(fixed_value, value, metric)
                            if result_fixed is not None:
                                pairs_fixed.append(result_fixed)
                        if rule_value is not None:
                            result_rule = improvement(rule_value, value, metric)
                            if result_rule is not None:
                                pairs_rule.append(result_rule)
                    improvement_values[controller] = {"fixed": pairs_fixed, "rule": pairs_rule}

                for controller in controllers:
                    observations = by_controller[controller]
                    values = [value for value, _, _ in observations.values() if value is not None]
                    if not values:
                        continue
                    metric_mean = statistics.fmean(values)
                    metric_std = statistics.stdev(values) if len(values) > 1 else 0.0
                    ci_low, ci_high = _bootstrap_ci(values, bootstrap_seed + len(rows))
                    n_trips_basis = sum(count for _, count, _ in observations.values())
                    completion_by_seed = {
                        seed: _aggregation_seed_values(
                            cells, scenarios=included_scenarios, seed=seed, controller=controller,
                            scope=scope, metric="completion_rate", trip_basis="all", pooled=pooled,
                        )[0]
                        for seed in seeds
                    }
                    completion_values = [value for value in completion_by_seed.values() if value is not None]
                    fixed_improvements = improvement_values[controller]["fixed"]
                    rule_improvements = improvement_values[controller]["rule"]
                    mean_fixed_imp = statistics.fmean(fixed_improvements) if fixed_improvements else None
                    mean_rule_imp = statistics.fmean(rule_improvements) if rule_improvements else None
                    target_met: bool | None = None
                    if (controller in target_controllers and metric == "travel_time"
                            and mean_fixed_imp is not None):
                        target_met = mean_fixed_imp >= target_reduction_pct
                    row = {
                        "milestone": milestone, "scenario": scenario_label, "aggregation": aggregation,
                        "controller": controller, "metric": metric, "scope": scope,
                        "trip_basis": trip_basis, "mean": metric_mean, "std": metric_std,
                        "ci95_low": ci_low, "ci95_high": ci_high,
                        "n_seeds": len(values), "n_trips_basis": n_trips_basis,
                        "completion_rate_mean": statistics.fmean(completion_values) if completion_values else None,
                        "seed_set": seed_set, "improvement_vs_fixed_pct": mean_fixed_imp,
                        "improvement_vs_rule_pct": mean_rule_imp,
                        "target_met": target_met,
                    }
                    rows.append(row)
                    # These explicit rows carry the paired-bootstrap interval for per-seed improvements.
                    for baseline, samples in (("fixed", fixed_improvements), ("rule", rule_improvements)):
                        if not samples:
                            continue
                        imp_mean = statistics.fmean(samples)
                        imp_std = statistics.stdev(samples) if len(samples) > 1 else 0.0
                        paired_low, paired_high = _bootstrap_ci(samples, bootstrap_seed + len(rows))
                        rows.append({
                            **row,
                            "metric": f"{metric}_improvement_vs_{baseline}_pct",
                            "mean": imp_mean,
                            "std": imp_std,
                            "ci95_low": paired_low,
                            "ci95_high": paired_high,
                            "n_seeds": len(samples),
                        })
    return rows
