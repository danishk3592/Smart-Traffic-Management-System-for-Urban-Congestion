"""Run resumable rule-threshold trials on the three validation seeds."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from Ai.common.config import load_config
from Ai.common.run_episode import run_episode
from Ai.controllers.registry import get_controller

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ((6, 30.0), (8, 45.0), (10, 60.0))
SEEDS = (3000, 3001, 3002)


def _state_path() -> Path:
    path = ROOT / "results" / "raw" / "t13_rule_tuning_progress.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_completed() -> dict[str, dict[str, Any]]:
    path = _state_path()
    try:
        records = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    except (OSError, json.JSONDecodeError):
        records = []
    return {item["key"]: item for item in records if item.get("complete")}


def _save(records: dict[str, dict[str, Any]]) -> None:
    _state_path().write_text(
        json.dumps(list(records.values()), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_report(records: dict[str, dict[str, Any]], *, running: str = "") -> None:
    lines = [
        "# Rule controller validation tuning (T1.3)",
        "",
        "Unchanged `medium` demand; validation seeds 3000-3002. Three queue/wait threshold pairs were tested. ",
        "Selection uses the lowest mean approach queue over all nine runs; waiting time and teleports are shown as context.",
        "",
        "| Queue threshold | Wait threshold (s) | Seed | Avg queue | Avg wait (s) | Completed / trips | Teleports | Fallback activations | Wall time (s) | Run |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in sorted(records.values(), key=lambda row: (row["queue_threshold"], row["wait_threshold_s"], row["seed"])):
        result = item["result"]
        lines.append(
            f"| {item['queue_threshold']} | {item['wait_threshold_s']:g} | {item['seed']} | "
            f"{result['avg_queue']:.3f} | {result['avg_wait']:.3f} | "
            f"{result['n_completed']} / {result['n_trips']} | {result['teleports']} | "
            f"{result.get('fallback_activations', 0)} | {result['wall_clock_s']:.1f} | `{result['run_id']}` |"
        )
    lines += ["", f"Completed trials: {len(records)}/9."]
    if running:
        lines.append(f"Current trial: {running}.")
    if len(records) == 9:
        grouped: dict[tuple[int, float], list[dict[str, Any]]] = {}
        for item in records.values():
            grouped.setdefault((item["queue_threshold"], item["wait_threshold_s"]), []).append(item["result"])
        scores = {
            key: (
                sum(result["avg_queue"] for result in values) / len(values),
                sum(result["avg_wait"] for result in values) / len(values),
            )
            for key, values in grouped.items()
        }
        best = min(scores, key=lambda key: scores[key])
        lines += ["", f"Selected thresholds: queue `{best[0]}`, wait `{best[1]:g}s`; mean queue/wait = `{scores[best][0]:.3f}` / `{scores[best][1]:.3f}`."]
    (ROOT / "docs" / "rule_tuning.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_tuning() -> None:
    """Run missing threshold/seed pairs and persist after each completed run."""
    completed = _load_completed()
    total = len(SETTINGS) * len(SEEDS)
    average_seconds = sum(
        item["result"].get("wall_clock_s", 0.0) for item in completed.values()
    ) / max(1, len(completed))
    if not completed:
        timings = []
        for result_path in (ROOT / "results" / "raw").glob("*/run.json"):
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
                if result.get("scenario") == "medium" and float(result.get("wall_clock_s", 0)) > 0:
                    timings.append(float(result["wall_clock_s"]))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        average_seconds = sum(timings) / len(timings) if timings else 0.0
    index = len(completed)
    for queue_threshold, wait_threshold_s in SETTINGS:
        for seed in SEEDS:
            key = f"q{queue_threshold}-w{wait_threshold_s:g}-s{seed}"
            if key in completed:
                continue
            index += 1
            eta = max(0.0, total - index) * average_seconds
            print(f"[{index}/{total}] {key}; estimated remaining {eta / 60:.1f} min", flush=True)
            _write_report(completed, running=key)
            config = load_config(ROOT / "config" / "stms.yaml")
            config["rule"]["queue_threshold"] = queue_threshold
            config["rule"]["wait_threshold_s"] = wait_threshold_s
            controller = get_controller("rule", config)
            result = run_episode(controller, "medium", seed)
            record = {
                "key": key,
                "queue_threshold": queue_threshold,
                "wait_threshold_s": wait_threshold_s,
                "seed": seed,
                "complete": True,
                "result": result,
            }
            completed[key] = record
            _save(completed)
            average_seconds = sum(
                item["result"].get("wall_clock_s", 0.0) for item in completed.values()
            ) / len(completed)
            _write_report(completed)
            print(f"[{index}/{total}] completed {key}: {result}", flush=True)
    _write_report(completed)


def main() -> None:
    """CLI for resumable validation tuning."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_tuning()


if __name__ == "__main__":
    main()
