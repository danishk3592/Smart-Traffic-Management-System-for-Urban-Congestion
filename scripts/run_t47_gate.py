"""Run or resume the six network PPO T4.7 validation episodes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from Ai.common.config import load_config
from Ai.common.run_episode import run_episode
from Ai.controllers.network import get_network_controller

ROOT = Path(__file__).resolve().parents[1]
CELLS = tuple(
    (scenario, seed)
    for scenario in ("net_medium", "net_heavy")
    for seed in (3000, 3001, 3002)
)


def _valid_existing(
    directory: Path, scenario: str, seed: int, model_path: str, model_sha256: str,
    tls_ids: set[str],
) -> dict[str, Any] | None:
    required = ("run.json", "summary.csv", "steps.csv", "trips.csv", "junctions.csv")
    if any(not (directory / name).is_file() for name in required):
        return None
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    if (
        run.get("family") != "network" or run.get("controller") != "rl"
        or run.get("scenario") != scenario or int(run.get("seed", -1)) != seed
    ):
        return None
    diag = run.get("controller_diagnostics", {})
    if diag.get("model_path") != model_path or diag.get("model_sha256") != model_sha256:
        return None
    junctions = list(csv.DictReader((directory / "junctions.csv").open(encoding="utf-8-sig", newline="")))
    summary_rows = list(csv.DictReader((directory / "summary.csv").open(encoding="utf-8-sig", newline="")))
    if len(junctions) != len(tls_ids) or {row["tls_id"] for row in junctions} != tls_ids:
        return None
    if len(summary_rows) != 1 or int(summary_rows[0]["n_tls_controlled"]) != len(tls_ids):
        return None
    if int(run.get("n_tls_controlled", -1)) != len(tls_ids):
        return None
    return run


def run_gate(model_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Execute only missing cells; completed matching artifacts are reused."""
    config = load_config(ROOT / "config" / "stms.yaml")
    if model_path is not None:
        config["rl_net"]["model_path"] = str(Path(model_path).resolve())
    controller_probe = get_network_controller("rl", config["network"]["tls_configs"], config)
    diag = controller_probe.diagnostics()
    if not diag["model_loaded"]:
        raise RuntimeError(f"selected network PPO failed preflight: {diag['model_load_error']}")
    model_path = diag["model_path"]
    model_sha256 = diag["model_sha256"]
    tls_ids = set(config["network"]["controlled_tls"])
    records: list[dict[str, Any]] = []

    for scenario, seed in CELLS:
        matching: list[tuple[Path, dict[str, Any]]] = []
        for directory in (ROOT / "results" / "raw").iterdir():
            if not directory.is_dir() or not (directory / "run.json").is_file():
                continue
            valid = _valid_existing(directory, scenario, seed, model_path, model_sha256, tls_ids)
            if valid is not None:
                matching.append((directory, valid))
        if len(matching) > 1:
            raise RuntimeError(f"multiple completed matching T4.7 cells exist: {scenario}/{seed}")
        if matching:
            directory, run = matching[0]
            print(f"reused valid cell {scenario}/{seed}: {directory.relative_to(ROOT)}", flush=True)
        else:
            controller = get_network_controller("rl", config["network"]["tls_configs"], config)
            run = run_episode(controller, scenario, seed, family="network")
            directory = Path(run["out_dir"])
            print(
                f"completed {scenario}/{seed}: run_id={run['run_id']} "
                f"coverage={run['ai_coverage']} wall_s={run['wall_clock_s']:.3f} "
                f"out={directory.relative_to(ROOT)}",
                flush=True,
            )
        records.append({"scenario": scenario, "seed": seed, "run_dir": str(directory.relative_to(ROOT)), "run": run})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, help="candidate network PPO checkpoint to gate")
    args = parser.parse_args()
    for record in run_gate(args.model):
        print(json.dumps(record, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
