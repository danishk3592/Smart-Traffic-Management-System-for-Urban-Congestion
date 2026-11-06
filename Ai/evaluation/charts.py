"""Create the simulated M1 figures from comparison.csv values."""

from __future__ import annotations

from pathlib import Path
from typing import Any

CONTROLLER_ORDER = ("fixed", "rule", "rl")
SCENARIO_ORDER = ("balanced", "directional_ns", "directional_ew", "low", "medium", "heavy", "rush_hour")


def _pyplot() -> Any:
    """Load pyplot after selecting a headless backend."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot

    return pyplot


def _rows(
    rows: list[dict[str, Any]], metric: str, scope: str, trip_basis: str
) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if row["aggregation"] == "scenario" and row["metric"] == metric
        and row["scope"] == scope and row["trip_basis"] == trip_basis
    ]


def _plot_metric(
    rows: list[dict[str, Any]],
    *,
    metric: str,
    scopes: tuple[str, ...],
    trip_basis: str,
    title: str,
    ylabel: str,
    path: Path,
    percent: bool = False,
) -> None:
    plt = _pyplot()
    fig, axes = plt.subplots(1, len(scopes), figsize=(7 * len(scopes), 4.5), squeeze=False)
    for axis, scope in zip(axes[0], scopes, strict=True):
        selected = _rows(rows, metric, scope, trip_basis)
        x_values = [scenario for scenario in SCENARIO_ORDER if any(row["scenario"] == scenario for row in selected)]
        width = 0.24 if len(CONTROLLER_ORDER) == 3 else 0.38
        for index, controller in enumerate(CONTROLLER_ORDER):
            controller_rows = {row["scenario"]: row for row in selected if row["controller"] == controller}
            scenarios = [scenario for scenario in x_values if scenario in controller_rows]
            if not scenarios:
                continue
            positions = [SCENARIO_ORDER.index(scenario) + (index - (len(CONTROLLER_ORDER) - 1) / 2) * width for scenario in scenarios]
            values = [float(controller_rows[scenario]["mean"]) for scenario in scenarios]
            deviations = [float(controller_rows[scenario]["std"] or 0.0) for scenario in scenarios]
            if percent:
                values = [value * 100 for value in values]
                deviations = [value * 100 for value in deviations]
            axis.bar(positions, values, width=width, yerr=deviations, capsize=3, label=controller)
        axis.set_xticks(range(len(SCENARIO_ORDER)), SCENARIO_ORDER, rotation=25, ha="right")
        axis.set_ylabel(ylabel)
        axis.set_title(f"{scope.title()} scope")
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle(f"{title} (simulated)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=len(handles))
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, dpi=150, metadata={"Title": f"{title} (simulated)"})
    plt.close(fig)


def write_figures(rows: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    """Write seven scenario-comparison figures with simulated labels and error bars."""
    plt = _pyplot()
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = (
        ("travel_time", ("all", "junction"), "common", "Completed common-trip travel time", "seconds", "travel_time_common.png"),
        ("travel_time", ("all", "junction"), "all", "Censored travel time", "seconds", "travel_time_censored.png"),
        ("completion_rate", ("all", "junction"), "all", "Trip completion rate", "percent", "completion_rate.png"),
        ("waiting_time", ("all", "junction"), "all", "Waiting time", "seconds", "waiting_time.png"),
        ("queue", ("junction",), "all", "Mean queue", "halting vehicles", "queue.png"),
        ("throughput", ("junction",), "all", "Controlled-movement throughput", "vehicles / simulated minute", "throughput.png"),
    )
    paths: list[Path] = []
    for metric, scopes, basis, title, ylabel, filename in specs:
        path = output_dir / filename
        _plot_metric(
            rows, metric=metric, scopes=scopes, trip_basis=basis, title=title,
            ylabel=ylabel, path=path, percent=metric == "completion_rate",
        )
        paths.append(path)

    improvement_metric = "travel_time_improvement_vs_fixed_pct"
    selected = _rows(rows, improvement_metric, "junction", "common")
    selected = [row for row in selected if row["controller"] == "rl"]
    fig, axis = plt.subplots(figsize=(8.5, 4.8))
    ordered = [scenario for scenario in SCENARIO_ORDER if any(row["scenario"] == scenario for row in selected)]
    by_scenario = {row["scenario"]: row for row in selected}
    values = [float(by_scenario[scenario]["mean"]) for scenario in ordered]
    lower = [max(0.0, value - float(by_scenario[scenario]["ci95_low"])) for scenario, value in zip(ordered, values, strict=True)]
    upper = [max(0.0, float(by_scenario[scenario]["ci95_high"]) - value) for scenario, value in zip(ordered, values, strict=True)]
    axis.errorbar(ordered, values, yerr=[lower, upper], fmt="o", capsize=4, label="RL vs fixed")
    axis.axhline(10.0, color="gray", linestyle="--", label="10% target")
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set_ylabel("Travel-time improvement (%)")
    axis.set_title("Per-scenario paired common-trip improvement (simulated)")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    fig.tight_layout()
    improvement_path = output_dir / "improvement_by_scenario.png"
    fig.savefig(improvement_path, dpi=150, metadata={"Title": "Per-scenario paired improvement (simulated)"})
    plt.close(fig)
    paths.append(improvement_path)
    return paths


def write_network_junction_figure(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    """Write a simulated heatmap of per-TLS high-congestion share by scenario."""
    plt = _pyplot()
    selected = [row for row in rows if row.get("controller") == "rl"]
    scenarios = ("net_balanced", "net_low", "net_medium", "net_heavy", "net_rush_hour")
    tls_ids = sorted({str(row["tls_id"]) for row in selected})
    values = []
    for scenario in scenarios:
        by_tls = {str(row["tls_id"]): float(row["frac_time_high_congestion_mean"]) for row in selected
                  if row["scenario"] == scenario}
        values.append([by_tls.get(tls, float("nan")) for tls in tls_ids])
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(max(12, len(tls_ids) * 0.8), 5.5))
    image = axis.imshow(values, aspect="auto", interpolation="nearest", cmap="magma", vmin=0, vmax=1)
    axis.set_yticks(range(len(scenarios)), scenarios)
    axis.set_xticks(range(len(tls_ids)), tls_ids, rotation=60, ha="right", fontsize=8)
    axis.set_title("PPO per-junction high-congestion time share (simulated)")
    axis.set_xlabel("Frozen intended traffic-light junction")
    axis.set_ylabel("Network demand scenario")
    fig.colorbar(image, ax=axis, label="Share of simulated ticks")
    fig.tight_layout()
    path = output_dir / "network_junction_congestion.png"
    fig.savefig(path, dpi=150, metadata={"Title": "Per-junction high congestion share (simulated)"})
    plt.close(fig)
    return path
