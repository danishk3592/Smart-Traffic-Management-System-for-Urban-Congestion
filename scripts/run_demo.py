"""Run one reproducible, seed-8000-or-higher STMS demo episode."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from Ai.common.config import load_config
from Ai.common.run_episode import run_episode
from Ai.controllers.network import HybridNetworkController, get_network_controller
from Ai.controllers.registry import get_controller
from scripts.make_scenarios import ScenarioBuilder

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _build_controller(family: str, name: str, config: dict[str, Any]) -> Any:
    """Build the selected controller, mapping delivered network RL to Stage 4."""
    if family == "single":
        return get_controller(name, config)
    network = config["network"]
    if name == "rl":
        return get_network_controller("hybrid", list(network["tls_configs"]), config)
    return get_network_controller(name, list(network["tls_configs"]), config)


def _read_status(path: Path) -> dict[str, Any] | None:
    """Read the atomically replaced status record, tolerating a replace race."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _run(options: argparse.Namespace) -> int:
    config = load_config(ROOT / "config" / "stms.yaml")
    ScenarioBuilder(ROOT, family=options.family).ensure_routes(
        options.scenario, options.seed
    )
    controller = _build_controller(options.family, options.controller, config)
    controller_name = str(getattr(controller, "name", options.controller)).lower()
    started_at = datetime.now()
    run_id = (
        f"{started_at:%Y%m%d-%H%M%S}_{controller_name}_"
        f"{options.scenario}_s{options.seed}"
    )
    output_dir = ROOT / "results" / "raw" / run_id
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse demo output directory {output_dir}")

    result_holder: dict[str, Any] = {}
    error_holder: dict[str, BaseException] = {}

    def execute() -> None:
        try:
            result_holder["result"] = run_episode(
                controller,
                options.scenario,
                options.seed,
                output_dir,
                options.gui,
                family=options.family,
            )
        except Exception as exc:  # noqa: BLE001 - propagate episode failures to the CLI exit status
            error_holder["error"] = exc

    worker = threading.Thread(target=execute, name="stms-demo-episode", daemon=True)
    worker.start()
    status_path = output_dir / "status.json"
    last_update = None
    while worker.is_alive():
        status = _read_status(status_path)
        if status and status.get("updated_utc") != last_update:
            last_update = status.get("updated_utc")
            sim_time = status.get("sim_time", 0)
            max_time = status.get("max_sim_s", 0)
            LOGGER.info(
                "%s %s %s seed=%d sim=%.0f/%.0f s",
                str(status.get("state", "running")).upper(),
                options.family,
                status.get("controller", controller_name),
                options.seed,
                float(sim_time or 0),
                float(max_time or 0),
            )
        time.sleep(1)
    worker.join()
    if "error" in error_holder:
        error = error_holder["error"]
        LOGGER.error(
            "Demo episode failed: %s",
            error,
            exc_info=(type(error), error, error.__traceback__),
        )
        return 1

    result = result_holder["result"]
    LOGGER.info("Demo completed: %s", json.dumps(result, sort_keys=True))
    if isinstance(controller, HybridNetworkController):
        coverage = result.get("ai_coverage", "none")
        count = result.get("n_tls_ai", 0)
        total = result.get("n_tls_controlled", len(controller.tls_ids))
        print(f"Controller level: DEC-14 Stage 4 hybrid; AI coverage: {count}/{total} ({coverage})")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse and run one demo from the disjoint demo seed block."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("single", "network"), required=True)
    parser.add_argument("--controller", choices=("fixed", "rule", "rl"), required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--seed", type=int, default=8000)
    parser.add_argument("--gui", action="store_true")
    options = parser.parse_args(argv)
    if options.seed < 8000:
        parser.error("demo seeds must be 8000 or higher")
    valid_scenario = (
        options.scenario == "net_medium"
        if options.family == "network"
        else options.scenario == "medium"
    )
    if not valid_scenario:
        parser.error("use medium for single-family demos or net_medium for network demos")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        return _run(options)
    except Exception:
        LOGGER.exception("Could not start demo")
        return 1


if __name__ == "__main__":
    sys.exit(main())
