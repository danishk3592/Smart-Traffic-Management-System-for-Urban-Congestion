"""Run resumable single-junction M1 and network-wide M2 comparisons."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import logging
import math
import os
import shutil
import statistics
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

import psutil

from Ai.common.config import load_config
from Ai.common.run_episode import run_episode
from Ai.controllers.network import get_network_controller
from Ai.controllers.registry import get_controller
from Ai.evaluation.charts import write_figures, write_network_junction_figure
from Ai.evaluation.metrics import RunData, _bootstrap_ci, build_comparison_rows, per_episode_values
from scripts.make_scenarios import ScenarioBuilder

LOGGER = logging.getLogger("Ai.evaluation")
ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ("balanced", "directional_ns", "directional_ew", "low", "medium", "heavy", "rush_hour")
DEV_SEEDS = (5000, 5001, 5002, 5003, 5004)
FINAL_SEEDS = (6000, 6001, 6002, 6003, 6004)
NETWORK_SCENARIOS = ("net_balanced", "net_low", "net_medium", "net_heavy", "net_rush_hour")
CONTROLLERS = ("fixed", "rule", "rl")
NETWORK_POLICY_CONTROLLERS = ("rl", "hybrid")
NETWORK_CONTROLLERS = (*CONTROLLERS, "hybrid")
PINNED_MODEL = Path("Ai/rl/models/ppo_v2_variant_waithalf/evaluations/20261026-182752/best_model.zip")
NETWORK_PINNED_MODEL = Path("Ai/rl/models/ppo_net_v2_rejection_penalty_005/evaluations/best_model.zip")
NETWORK_PINNED_MODEL_SHA256 = "758711e7f28e29e69b59af6eade30ba679c3160daadf39e09ed89287f5037757"
COMPARISON_FIELDS = (
    "milestone", "scenario", "aggregation", "controller", "metric", "scope", "trip_basis",
    "mean", "std", "ci95_low", "ci95_high", "n_seeds", "n_trips_basis",
    "completion_rate_mean", "seed_set", "improvement_vs_fixed_pct", "improvement_vs_rule_pct",
    "target_met",
)
RUN_FILES = ("run.json", "summary.csv", "trips.csv", "steps.csv")
NETWORK_RUN_FILES = (*RUN_FILES, "junctions.csv", "evaluation.json")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _seed_block(seed_set: str) -> tuple[int, ...]:
    if seed_set == "dev":
        return DEV_SEEDS
    if seed_set == "final":
        return FINAL_SEEDS
    raise ValueError(f"Unknown seed set {seed_set!r}")


def _resolve_jobs(configured: str | int, requested: str | None) -> tuple[int, bool]:
    value = requested if requested is not None else configured
    if isinstance(value, str) and value.lower() == "auto":
        physical_cores = psutil.cpu_count(logical=False) or os.cpu_count() or 1
        return max(1, min(physical_cores - 1, 4)), True
    try:
        jobs = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"jobs must be 'auto' or a positive integer, got {value!r}") from exc
    if jobs < 1:
        raise ValueError("jobs must be at least 1")
    return jobs, False


def _make_run_data(run_dir: Path) -> RunData:
    run = _read_json(run_dir / "run.json")
    summary_rows = _read_csv(run_dir / "summary.csv")
    if len(summary_rows) != 1:
        raise ValueError(f"Expected one summary row in {run_dir}, found {len(summary_rows)}")
    summary = summary_rows[0]
    trips = _read_csv(run_dir / "trips.csv")
    if summary.get("family") not in {"single", "network"}:
        raise ValueError(f"Unknown evaluation family in {run_dir}")
    if summary.get("run_id") != run.get("run_id"):
        raise ValueError(f"Run and summary IDs differ in {run_dir}")
    if len(trips) != int(summary["n_trips"]):
        raise ValueError(f"Trip count does not match summary in {run_dir}")
    if summary.get("family") == "network":
        junctions = _read_csv(run_dir / "junctions.csv")
        expected_tls = len(load_config(ROOT / "config" / "stms.yaml")["network"]["controlled_tls"])
        if len(junctions) != expected_tls or len({row.get("tls_id") for row in junctions}) != expected_tls:
            raise ValueError(f"Network run does not contain one row per intended TLS: {run_dir}")
        if any(row.get("run_id") != run.get("run_id") for row in junctions):
            raise ValueError(f"Junction lineage mismatch in {run_dir}")
    return RunData(run=run, summary=summary, trips=trips)


def _evaluation_metadata(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "evaluation.json"
    if not path.is_file():
        return None
    try:
        return _read_json(path)
    except (OSError, TypeError, json.JSONDecodeError):
        return None


def _complete_for_cell(
    run_dir: Path,
    *,
    scenario: str,
    seed: int,
    controller: str,
    seed_set: str,
    route_hash: str,
    config_hash: str,
    model_hash: str | None,
    family: str = "single",
    controller_config_hash: str | None = None,
) -> bool:
    required_files = NETWORK_RUN_FILES if family == "network" else RUN_FILES
    if not all((run_dir / filename).is_file() and (run_dir / filename).stat().st_size > 0 for filename in required_files):
        return False
    metadata = _evaluation_metadata(run_dir)
    if (
        not metadata or metadata.get("seed_set") != seed_set
        or metadata.get("route_sha256") != route_hash
        or metadata.get("config_sha256") != config_hash
        or metadata.get("family", "single") != family
        or (controller_config_hash is not None
            and metadata.get("controller_config_sha256") != controller_config_hash)
    ):
        return False
    if metadata.get("model_sha256") != model_hash:
        return False
    try:
        record = _make_run_data(run_dir)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    if record.key != (scenario, seed, controller) or record.summary.get("config_hash") != config_hash:
        return False
    if family == "network":
        junctions = _read_csv(run_dir / "junctions.csv")
        tls_ids = set(load_config(ROOT / "config" / "stms.yaml")["network"]["controlled_tls"])
        return (
            record.run.get("family") == "network"
            and record.summary.get("ai_coverage") in {"full", "partial", "none"}
            and int(record.summary.get("n_trips", 0)) > 0
            and int(record.summary.get("n_completed", 0)) + int(record.summary.get("n_unfinished", 0))
            == int(record.summary.get("n_trips", -1))
            and int(record.summary.get("n_tls_controlled", 0)) == len(
                tls_ids
            )
            and {row.get("tls_id") for row in junctions} == tls_ids
            and all(math_is_finite(row.get(field)) for row in junctions for field in (
                "avg_queue", "avg_wait", "n_ticks", "ppo_tick_share", "n_illegal_actions", "n_forced_max_green"
            ))
            and all(0.0 <= float(row["ppo_tick_share"]) <= 1.0 for row in junctions)
            and all(math_is_finite(record.summary.get(field)) for field in (
                "n_trips", "n_completed", "completion_rate", "avg_travel_time_censored", "wall_clock_s"
            ))
        )
    # M1 run.json predates the family field; summary.csv and evaluation.json
    # carry the required family lineage for both legacy and current cells.
    return record.summary.get("family") == "single"


def math_is_finite(value: Any) -> bool:
    """Return whether an artifact field is a finite numeric value."""
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _find_complete(
    root: Path,
    *,
    scenario: str,
    seed: int,
    controller: str,
    seed_set: str,
    route_hash: str,
    config_hash: str,
    model_hash: str | None,
    family: str = "single",
    controller_config_hash: str | None = None,
) -> Path | None:
    raw_root = root / "results" / "raw"
    matches = [
        folder for folder in raw_root.iterdir()
        if folder.is_dir() and _complete_for_cell(
            folder, scenario=scenario, seed=seed, controller=controller,
            seed_set=seed_set, route_hash=route_hash, config_hash=config_hash,
            model_hash=model_hash, family=family,
            controller_config_hash=controller_config_hash,
        )
    ]
    if not matches:
        return None
    matches.sort(key=lambda path: path.name)
    if len(matches) > 1:
        LOGGER.warning("Multiple completed outputs for %s/%s/s%s; reusing latest %s", controller, scenario, seed, matches[-1].name)
    return matches[-1]


def _write_evaluation_metadata(
    run_dir: Path,
    *,
    seed_set: str,
    route_path: Path,
    route_hash: str,
    config_hash: str,
    model_path: Path | None,
    model_hash: str | None,
    family: str = "single",
    controller_config_hash: str | None = None,
) -> None:
    metadata = {
        "schema_version": 1,
        "seed_set": seed_set,
        "route_file": route_path.relative_to(ROOT).as_posix(),
        "route_sha256": route_hash,
        "config_sha256": config_hash,
        "model_path": model_path.relative_to(ROOT).as_posix() if model_path else None,
        "model_sha256": model_hash,
        "family": family,
        "controller_config_sha256": controller_config_hash,
    }
    target = run_dir / "evaluation.json"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite evaluation metadata: {target}")
    temporary = target.with_suffix(".json.pending")
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _run_one(
    *,
    scenario: str,
    seed: int,
    controller_name: str,
    seed_set: str,
    route_path: Path,
    route_hash: str,
    config_hash: str,
    config: dict[str, Any],
    model_path: Path,
    model_hash: str,
) -> tuple[str, float]:
    config_path = ROOT / "config" / "stms.yaml"
    current_config_hash = _sha256(config_path)
    if current_config_hash != config_hash:
        raise RuntimeError(
            "Configuration changed after evaluation preflight: "
            f"expected {config_hash}, found {current_config_hash}"
        )
    controller = get_controller(
        controller_name, config, model_path=model_path if controller_name == "rl" else None,
    )
    if controller_name == "rl":
        policy = getattr(controller, "controller", controller)
        selected_model = getattr(policy, "model_path", None)
        if selected_model is None or Path(selected_model).resolve() != model_path:
            raise RuntimeError(f"Pinned PPO model failed to load: {model_path}")
    started = time.perf_counter()
    result = run_episode(controller, scenario, seed)
    run_dir = Path(result["out_dir"]).resolve()
    current_config_hash = _sha256(config_path)
    if current_config_hash != config_hash:
        raise RuntimeError(
            "Configuration changed while the evaluation episode was running: "
            f"expected {config_hash}, found {current_config_hash}; "
            f"preserving unlineaged output at {run_dir}"
        )
    _write_evaluation_metadata(
        run_dir, seed_set=seed_set, route_path=route_path, route_hash=route_hash,
        config_hash=config_hash,
        model_path=model_path if controller_name == "rl" else None,
        model_hash=model_hash if controller_name == "rl" else None,
    )
    return run_dir.relative_to(ROOT).as_posix(), time.perf_counter() - started


def _sample_live_sumo_peak() -> int:
    current = 0
    for process in psutil.process_iter(("name", "memory_info")):
        try:
            name = (process.info.get("name") or "").lower()
            if name in {"sumo.exe", "sumo-gui.exe", "sumo", "sumo-gui"}:
                current = max(current, process.info["memory_info"].rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
            continue
    return current


def _run_and_sample_memory(task: dict[str, Any]) -> tuple[str, float, int]:
    from threading import Event, Thread

    stop = Event()
    peak = [0]

    def sample() -> None:
        while not stop.is_set():
            peak[0] = max(peak[0], _sample_live_sumo_peak())
            stop.wait(0.5)

    monitor = Thread(target=sample, name="stms-sumo-memory", daemon=True)
    monitor.start()
    try:
        run_dir, elapsed = _run_one(**task)
        return run_dir, elapsed, peak[0]
    finally:
        stop.set()
        monitor.join(timeout=2)


def _effective_workers(desired: int, free_memory: int, measured_peak: int) -> int:
    """Limit auto parallelism if one measured SUMO process would exceed the RAM budget."""
    if measured_peak <= 0:
        return 1
    memory_limited = max(1, int((free_memory * 0.70) // measured_peak))
    return max(1, min(desired, memory_limited))


def run_grid(
    *,
    root: Path,
    seed_set: str,
    controllers: tuple[str, ...],
    jobs_override: str | None,
) -> list[Path]:
    """Prepare each route once, then run only missing cells in a resumable grid."""
    config = load_config(root / "config" / "stms.yaml")
    config_hash = _sha256(root / "config" / "stms.yaml")
    model_path = (root / PINNED_MODEL).resolve()
    if "rl" in controllers and not model_path.is_file():
        raise FileNotFoundError(f"Pinned validation-best model not found: {model_path}")
    model_hash = _sha256(model_path) if "rl" in controllers else None
    seeds = _seed_block(seed_set)
    builder = ScenarioBuilder(root)
    (root / "results" / "raw").mkdir(parents=True, exist_ok=True)

    routes: dict[tuple[str, int], tuple[Path, str]] = {}
    for scenario in SCENARIOS:
        for seed in seeds:
            # Evaluation supplies the route file directly to SUMO. Avoid rewriting
            # the shared scenario .sumocfg as each final seed is prepared.
            route_path = builder.ensure_routes(scenario, seed, write_config=False)
            routes[(scenario, seed)] = (route_path.resolve(), _sha256(route_path))
            LOGGER.info("route ready: %s/s%s sha256=%s", scenario, seed, routes[(scenario, seed)][1])

    todo: list[dict[str, Any]] = []
    reused: list[Path] = []
    for scenario in SCENARIOS:
        for seed in seeds:
            route_path, route_hash = routes[(scenario, seed)]
            for controller_name in controllers:
                complete = _find_complete(
                    root, scenario=scenario, seed=seed, controller=controller_name,
                    seed_set=seed_set, route_hash=route_hash,
                    config_hash=config_hash,
                    model_hash=model_hash if controller_name == "rl" else None,
                )
                if complete:
                    reused.append(complete)
                    LOGGER.info("reusing completed output: %s", complete.relative_to(root))
                    continue
                todo.append({
                    "scenario": scenario, "seed": seed, "controller_name": controller_name,
                    "seed_set": seed_set, "route_path": route_path, "route_hash": route_hash,
                    "config_hash": config_hash, "config": config,
                    "model_path": model_path, "model_hash": model_hash or "",
                })
    LOGGER.info("grid cells: %d requested, %d already complete, %d remaining", len(SCENARIOS) * len(seeds) * len(controllers), len(reused), len(todo))

    desired_workers, auto = _resolve_jobs(config.get("jobs", {}).get("parallel_runs", "auto"), jobs_override)
    if not todo:
        LOGGER.info("No episode runs required; rebuilding evaluation outputs from existing results.")
        return reused

    completed_paths = list(reused)
    if auto:
        # Run the heaviest scenario once to measure per-process RSS before parallel scheduling.
        probe = next((task for task in todo if task["scenario"] == "heavy"), todo[0])
        todo.remove(probe)
        available_memory = psutil.virtual_memory().available
        LOGGER.info("auto jobs: target=%d; probing heavy scenario memory (70%% of currently available RAM)", desired_workers)
        run_dir, elapsed, peak = _run_and_sample_memory(probe)
        completed_paths.append(root / run_dir)
        LOGGER.info("completed %s in %.1fs; sampled peak SUMO RSS=%d bytes", run_dir, elapsed, peak)
        desired_workers = _effective_workers(desired_workers, available_memory, peak)
        LOGGER.info("auto jobs: measured memory limit selected %d worker(s)", desired_workers)
    else:
        LOGGER.info("parallel jobs explicitly set to %d", desired_workers)

    def on_complete(future: Future[tuple[str, float]], task: dict[str, Any]) -> None:
        run_dir, elapsed = future.result()
        completed_paths.append(root / run_dir)
        LOGGER.info("completed %s/%s/s%s in %.1fs", task["controller_name"], task["scenario"], task["seed"], elapsed)

    with ThreadPoolExecutor(max_workers=desired_workers, thread_name_prefix="stms-eval") as executor:
        pending: dict[Future[tuple[str, float]], dict[str, Any]] = {}
        initial = todo[:desired_workers]
        for task in initial:
            pending[executor.submit(_run_one, **task)] = task
        remaining = todo[desired_workers:]
        while pending:
            finished, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in finished:
                task = pending.pop(future)
                on_complete(future, task)
                if remaining:
                    next_task = remaining.pop(0)
                    pending[executor.submit(_run_one, **next_task)] = next_task

    return completed_paths


def _network_controller_config_hash(
    config: dict[str, Any], controller: str, *, root: Path = ROOT,
) -> str:
    keys = {
        "fixed": ("fixed", "signal", "network", "sumo"),
        "rule": ("fixed", "signal", "rule", "network", "sumo"),
        "rl": ("fixed", "signal", "rl_net", "network", "sumo"),
        "hybrid": ("fixed", "signal", "rule", "rl_net", "network", "sumo"),
    }[controller]
    values = {key: config.get(key) for key in keys}
    if controller in NETWORK_POLICY_CONTROLLERS and isinstance(values.get("rl_net"), dict):
        values["rl_net"] = {**values["rl_net"], "model_path": NETWORK_PINNED_MODEL.as_posix()}
    if controller == "hybrid":
        gate = Path(config.get("rl_net", {}).get(
            "hybrid_gate_path", "results/summary/t410_hybrid_gate.json"
        ))
        values["hybrid_gate_sha256"] = _sha256(gate if gate.is_absolute() else root / gate)
    return _stable_hash(values)


def _network_complete_cell(
    root: Path, *, scenario: str, seed: int, controller: str, route_hash: str,
    config_hash: str, controller_config_hash: str, model_hash: str | None,
    seed_set: str = "dev",
) -> Path | None:
    matches: list[Path] = []
    raw_root = root / "results" / "raw"
    for folder in raw_root.iterdir():
        if not folder.is_dir() or not all(
            (folder / filename).is_file() and (folder / filename).stat().st_size > 0
            for filename in NETWORK_RUN_FILES
        ):
            continue
        try:
            record = _make_run_data(folder)
            metadata = _evaluation_metadata(folder)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
        if not metadata or metadata.get("family") != "network":
            continue
        if record.key != (scenario, seed, controller):
            continue
        is_policy = controller in NETWORK_POLICY_CONTROLLERS
        expected_model_path = NETWORK_PINNED_MODEL.as_posix() if is_policy else None
        if (
            metadata.get("seed_set") == seed_set
            and metadata.get("route_sha256") == route_hash
            and metadata.get("config_sha256") == config_hash
            and metadata.get("controller_config_sha256") == controller_config_hash
            and metadata.get("model_path") == expected_model_path
            and metadata.get("model_sha256") == model_hash
            and metadata.get("route_file") == (root / "SUMO" / "scenarios" / scenario / f"seed_{seed}" / "routes.rou.xml").relative_to(root).as_posix()
            and record.summary.get("config_hash") == config_hash
            and record.run.get("family") == "network"
            and int(record.summary.get("n_tls_controlled", 0)) == len(
                load_config(root / "config" / "stms.yaml")["network"]["controlled_tls"]
            )
            and all(math_is_finite(record.summary.get(field)) for field in (
                "n_trips", "n_completed", "completion_rate", "avg_travel_time_censored", "wall_clock_s"
            ))
        ):
            matches.append(folder)
    if not matches:
        return None
    return max(matches, key=lambda path: path.name)


def run_network_grid(
    *, root: Path, seed_set: str, controllers: tuple[str, ...], jobs_override: str | None,
) -> list[Path]:
    """Prepare network routes once, then execute only lineage-valid missing cells."""
    seeds = _seed_block(seed_set)
    if controllers not in (CONTROLLERS, ("fixed", "rule", "hybrid")):
        raise ValueError("Network evaluation requires fixed, rule and exactly one of rl/hybrid")
    config = load_config(root / "config" / "stms.yaml")
    configured_scenarios = tuple(config["network"].get("scenarios", NETWORK_SCENARIOS))
    if configured_scenarios != NETWORK_SCENARIOS:
        raise ValueError(f"network scenario list differs from the frozen T4.8 list: {configured_scenarios}")
    config_hash = _sha256(root / "config" / "stms.yaml")
    model_path = (root / NETWORK_PINNED_MODEL).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"accepted T4.7 network checkpoint is missing: {model_path}")
    model_hash = _sha256(model_path)
    if model_hash != NETWORK_PINNED_MODEL_SHA256:
        raise ValueError(f"accepted T4.7 checkpoint hash changed: {model_hash}")
    network_config = copy.deepcopy(config)
    # Pin the accepted T4.7 candidate explicitly; the shared config still names the older model.
    network_config["rl_net"]["model_path"] = NETWORK_PINNED_MODEL.as_posix()
    network_config["rl_net"]["hybrid_gate_path"] = "results/summary/t410_hybrid_gate.json"
    tls_configs = list(network_config["network"]["tls_configs"])
    if [str(item["tls_id"]) for item in tls_configs] != list(network_config["network"]["controlled_tls"]):
        raise ValueError("network TLS configuration order differs from the frozen intended list")
    if "hybrid" in controllers and not (root / network_config["rl_net"]["hybrid_gate_path"]).is_file():
        raise FileNotFoundError("T4.10 frozen hybrid gate is missing")
    policy = get_network_controller("hybrid" if "hybrid" in controllers else "rl", tls_configs, network_config)
    policy_diag = policy.diagnostics()
    has_ppo_slots = "hybrid" not in controllers or bool(getattr(policy, "ppo_tls_ids", ()))
    if has_ppo_slots and (not policy_diag.get("model_loaded") or policy_diag.get("model_load_error")):
        raise RuntimeError(f"accepted T4.7 PPO model failed preflight: {policy_diag.get('model_load_error')}")
    if Path(policy_diag["model_path"]).resolve() != model_path or policy_diag["model_sha256"] != model_hash:
        raise RuntimeError("loaded PPO model identity differs from the pinned T4.7 checkpoint")
    builder = ScenarioBuilder(root, family="network")
    (root / "results" / "raw").mkdir(parents=True, exist_ok=True)
    routes: dict[tuple[str, int], tuple[Path, str]] = {}
    for scenario in NETWORK_SCENARIOS:
        for seed in seeds:
            path = builder.ensure_routes(scenario, seed, write_config=False).resolve()
            routes[(scenario, seed)] = (path, _sha256(path))
            LOGGER.info("network route ready: %s/s%s sha256=%s", scenario, seed, routes[(scenario, seed)][1])

    todo: list[dict[str, Any]] = []
    reused: list[Path] = []
    for scenario in NETWORK_SCENARIOS:
        for seed in seeds:
            route_path, route_hash = routes[(scenario, seed)]
            for controller_name in controllers:
                controller_hash = _network_controller_config_hash(network_config, controller_name, root=root)
                found = _network_complete_cell(
                    root, scenario=scenario, seed=seed, controller=controller_name,
                    route_hash=route_hash, config_hash=config_hash,
                    controller_config_hash=controller_hash,
                    model_hash=model_hash if controller_name in NETWORK_POLICY_CONTROLLERS else None,
                    seed_set=seed_set,
                )
                if found:
                    reused.append(found)
                    LOGGER.info("reusing validated network cell: %s", found.relative_to(root))
                    continue
                todo.append({
                    "scenario": scenario, "seed": seed, "controller_name": controller_name,
                    "route_path": route_path, "route_hash": route_hash, "config_hash": config_hash,
                    "controller_config_hash": controller_hash, "config": network_config,
                    "tls_configs": tls_configs, "model_path": model_path,
                    "model_hash": model_hash if controller_name in NETWORK_POLICY_CONTROLLERS else "",
                    "seed_set": seed_set,
                })
    requested = len(NETWORK_SCENARIOS) * len(seeds) * len(controllers)
    LOGGER.info("network grid cells: %d requested, %d verified complete, %d remaining", requested, len(reused), len(todo))
    if not todo:
        return reused
    desired_workers, auto = _resolve_jobs(config.get("jobs", {}).get("parallel_runs", "auto"), jobs_override)
    completed = list(reused)
    if auto:
        probe = next((task for task in todo if task["scenario"] == "net_heavy"), todo[0])
        todo.remove(probe)
        available_memory = psutil.virtual_memory().available
        LOGGER.info("auto jobs: target=%d; measuring one network SUMO cell before parallel scheduling", desired_workers)
        run_dir, elapsed, peak = _run_network_and_sample_memory(root, probe)
        completed.append(root / run_dir)
        LOGGER.info("completed memory probe cell in %.1fs; peak SUMO RSS=%d bytes", elapsed, peak)
        desired_workers = _effective_workers(desired_workers, available_memory, peak)
        LOGGER.info("auto jobs: measured memory limit selected %d worker(s)", desired_workers)
    else:
        LOGGER.info("parallel jobs explicitly set to %d", desired_workers)

    def finish(future: Future[tuple[str, float]], task: dict[str, Any]) -> None:
        run_dir, elapsed = future.result()
        completed.append(root / run_dir)
        LOGGER.info("completed %s/%s/s%s in %.1fs", task["controller_name"], task["scenario"], task["seed"], elapsed)

    with ThreadPoolExecutor(max_workers=desired_workers, thread_name_prefix="stms-network-eval") as executor:
        pending: dict[Future[tuple[str, float]], dict[str, Any]] = {}
        remaining = iter(todo)
        for _ in range(min(desired_workers, len(todo))):
            task = next(remaining, None)
            if task is not None:
                pending[executor.submit(_run_network_one, root=root, **task)] = task
        while pending:
            finished, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in finished:
                task = pending.pop(future)
                finish(future, task)
                next_task = next(remaining, None)
                if next_task is not None:
                    pending[executor.submit(_run_network_one, root=root, **next_task)] = next_task
    return completed


def _run_network_and_sample_memory(root: Path, task: dict[str, Any]) -> tuple[str, float, int]:
    from threading import Event, Thread

    stop = Event()
    peak = [0]

    def sample() -> None:
        while not stop.is_set():
            peak[0] = max(peak[0], _sample_live_sumo_peak())
            stop.wait(0.5)

    monitor = Thread(target=sample, name="stms-sumo-memory", daemon=True)
    monitor.start()
    try:
        run_dir, elapsed = _run_network_one(root=root, **task)
        return run_dir, elapsed, peak[0]
    finally:
        stop.set()
        monitor.join(timeout=2)


def _run_network_one(
    *, root: Path, scenario: str, seed: int, controller_name: str, route_path: Path,
    route_hash: str, config_hash: str, controller_config_hash: str,
    config: dict[str, Any], tls_configs: list[dict[str, Any]], model_path: Path, model_hash: str,
    seed_set: str,
) -> tuple[str, float]:
    current_config_hash = _sha256(root / "config" / "stms.yaml")
    if current_config_hash != config_hash:
        raise RuntimeError(
            "Configuration changed after network evaluation preflight: "
            f"expected {config_hash}, found {current_config_hash}"
        )
    controller = get_network_controller(controller_name, tls_configs, config)
    if controller_name in NETWORK_POLICY_CONTROLLERS:
        diagnostics = controller.diagnostics()
        has_ppo_slots = controller_name == "rl" or bool(getattr(controller, "ppo_tls_ids", ()))
        if has_ppo_slots and (not diagnostics.get("model_loaded") or diagnostics.get("model_load_error")):
            raise RuntimeError(f"Pinned network PPO failed to load: {diagnostics.get('model_load_error')}")
        if Path(diagnostics["model_path"]).resolve() != model_path or diagnostics["model_sha256"] != model_hash:
            raise RuntimeError("Network PPO model identity changed before a cell")
    started = time.perf_counter()
    result = run_episode(controller, scenario, seed, family="network")
    run_dir = Path(result["out_dir"]).resolve()
    current_config_hash = _sha256(root / "config" / "stms.yaml")
    if current_config_hash != config_hash:
        raise RuntimeError(
            "Configuration changed while the network evaluation episode was running: "
            f"expected {config_hash}, found {current_config_hash}; "
            f"preserving unlineaged output at {run_dir}"
        )
    _write_evaluation_metadata(
        run_dir, seed_set=seed_set, route_path=route_path, route_hash=route_hash,
        config_hash=config_hash,
        model_path=model_path if controller_name in NETWORK_POLICY_CONTROLLERS else None,
        model_hash=model_hash if controller_name in NETWORK_POLICY_CONTROLLERS else None,
        family="network", controller_config_hash=controller_config_hash,
    )
    return run_dir.relative_to(root).as_posix(), time.perf_counter() - started


def load_evaluation_runs(root: Path) -> dict[str, list[RunData]]:
    """Load complete, lineage-checked M1 evaluation runs from all seed sets."""
    result: dict[str, list[RunData]] = defaultdict(list)
    route_hashes: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    config_hash = _sha256(root / "config" / "stms.yaml")
    raw_root = root / "results" / "raw"
    for run_dir in sorted(raw_root.iterdir(), key=lambda path: path.name):
        if not run_dir.is_dir() or not all((run_dir / filename).is_file() for filename in RUN_FILES):
            continue
        metadata = _evaluation_metadata(run_dir)
        if not metadata or metadata.get("seed_set") not in {"dev", "final"}:
            continue
        try:
            record = _make_run_data(run_dir)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            LOGGER.warning("ignoring invalid evaluation output %s: %s", run_dir.name, exc)
            continue
        if record.run.get("scenario") not in SCENARIOS:
            continue
        seed_set = str(metadata["seed_set"])
        if metadata.get("config_sha256") != config_hash or record.summary.get("config_hash") != config_hash:
            LOGGER.warning("ignoring evaluation output from a different config hash: %s", run_dir.name)
            continue
        if int(record.run.get("seed", -1)) not in _seed_block(seed_set):
            LOGGER.warning("ignoring run with seed outside %s block: %s", seed_set, run_dir.name)
            continue
        route_path = (root / str(metadata.get("route_file", ""))).resolve()
        if not route_path.is_relative_to(root.resolve()):
            LOGGER.warning("ignoring evaluation output with an invalid route path: %s", run_dir.name)
            continue
        if not route_path.is_file() or _sha256(route_path) != metadata.get("route_sha256"):
            LOGGER.warning("ignoring evaluation output with a missing or changed route file: %s", run_dir.name)
            continue
        if record.run.get("controller") == "rl":
            selected_model = metadata.get("model_path")
            model_file = root / PINNED_MODEL
            if selected_model != PINNED_MODEL.as_posix() or not model_file.is_file() or _sha256(model_file) != metadata.get("model_sha256"):
                LOGGER.warning("ignoring RL output that does not use the pinned model: %s", run_dir.name)
                continue
        result[seed_set].append(record)
        route_hashes[(seed_set, str(record.run["scenario"]), int(record.run["seed"]))].add(
            str(metadata["route_sha256"])
        )
    mismatched = [key for key, hashes in route_hashes.items() if len(hashes) > 1]
    if mismatched:
        raise ValueError(f"Controllers did not use the same cached route for {mismatched[:3]}")
    return result


def write_comparison(root: Path, requested_seed_set: str, requested_controllers: tuple[str, ...], target_pct: float) -> list[dict[str, Any]]:
    """Rebuild comparison.csv from every complete M1 dev/final run in results/raw."""
    all_by_seed_set = load_evaluation_runs(root)
    # Validate this invocation's requested grid before publishing aggregates.
    expected = {(s, seed, c) for s in SCENARIOS for seed in _seed_block(requested_seed_set) for c in requested_controllers}
    found = {(str(r.run["scenario"]), int(r.run["seed"]), str(r.run["controller"])) for r in all_by_seed_set.get(requested_seed_set, [])}
    missing = sorted(expected - found)
    if missing:
        raise ValueError(f"Evaluation grid incomplete; {len(missing)} cells missing, first: {missing[:3]}")

    all_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    for seed_set in ("dev", "final"):
        records = all_by_seed_set.get(seed_set, [])
        if not records:
            continue
        present_controllers = tuple(
            name for name in CONTROLLERS if any(r.run.get("controller") == name for r in records)
        )
        rows = build_comparison_rows(
            records, seed_set=seed_set, controllers=present_controllers,
            target_reduction_pct=target_pct,
        )
        all_rows.extend(rows)
        if seed_set == requested_seed_set:
            target_rows = rows

    if not target_rows:
        raise ValueError(f"No complete evaluation outputs found for seed set {requested_seed_set}")

    summary_dir = root / "results" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = summary_dir / "comparison.csv"
    temporary = comparison_path.with_suffix(".csv.pending")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COMPARISON_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in all_rows:
            writer.writerow({
                key: (
                    "" if row.get(key) is None else
                    str(row[key]).lower() if key == "target_met" and isinstance(row.get(key), bool) else
                    row.get(key)
                )
                for key in COMPARISON_FIELDS
            })
    temporary.replace(comparison_path)
    write_figures(all_rows, root / "results" / "figures")
    return target_rows


NETWORK_RUN_FIELDS = (
    "milestone", "run_id", "scenario", "seed", "controller", "ai_coverage", "n_tls_ai",
    "n_tls_controlled", "model_path", "model_sha256", "n_trips", "n_completed",
    "completion_rate", "common_trip_count", "avg_travel_time_common", "avg_travel_time_censored",
    "fallback_tick_share", "rejected_actions", "forced_max_green_switches",
    "median_batch_inference_latency_ms", "max_batch_inference_latency_ms", "wall_clock_s",
    "route_sha256", "controller_config_sha256",
)
NETWORK_JUNCTION_FIELDS = (
    "scenario", "tls_id", "controller", "avg_queue_mean", "avg_wait_mean", "ci95_low",
    "ci95_high", "frac_time_high_congestion_mean", "n_seeds", "seed_set", "controlled_by", "ppo_tick_share",
    "fallback_tick_share", "fallback_ticks", "n_ticks", "n_illegal_actions",
    "n_forced_max_green", "model_sha256",
)
NETWORK_SUMMARY_FIELDS = (
    "milestone", "seed_set", "n_rl_cells", "n_tls_ai", "n_tls_controlled",
    "ai_coverage", "model_sha256",
)


def _load_network_evaluation_runs(
    root: Path, *, seed_set: str = "dev", controllers: tuple[str, ...] = CONTROLLERS,
) -> list[tuple[RunData, dict[str, Any]]]:
    """Return valid network cells for one seed block after lineage checks."""
    seeds = _seed_block(seed_set)
    config = load_config(root / "config" / "stms.yaml")
    config_hash = _sha256(root / "config" / "stms.yaml")
    model_path = (root / NETWORK_PINNED_MODEL).resolve()
    model_hash = _sha256(model_path)
    builder = ScenarioBuilder(root, family="network")
    current_routes = {
        (scenario, seed): builder.get_cached_routes(scenario, seed).resolve()
        for scenario in NETWORK_SCENARIOS for seed in seeds
    }
    found: dict[tuple[str, int, str], tuple[RunData, dict[str, Any]]] = {}
    route_hashes: dict[tuple[str, int], set[str]] = defaultdict(set)
    for folder in sorted((root / "results" / "raw").iterdir(), key=lambda path: path.name):
        if not folder.is_dir() or not (folder / "junctions.csv").is_file():
            continue
        metadata = _evaluation_metadata(folder)
        if not metadata or metadata.get("family") != "network" or metadata.get("seed_set") != seed_set:
            continue
        try:
            record = _make_run_data(folder)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            LOGGER.warning("ignoring invalid network evaluation output %s: %s", folder.name, exc)
            continue
        scenario, seed, controller = record.key
        if scenario not in NETWORK_SCENARIOS or seed not in seeds or controller not in controllers:
            continue
        expected_route = current_routes[(scenario, seed)]
        route_path = (root / str(metadata.get("route_file", ""))).resolve()
        if not route_path.is_relative_to(root.resolve()) or route_path != expected_route.resolve():
            continue
        if (
            not route_path.is_file() or _sha256(route_path) != metadata.get("route_sha256")
            or metadata.get("config_sha256") != config_hash
            or record.summary.get("config_hash") != config_hash
            or record.run.get("family") != "network"
            or int(record.summary.get("n_tls_controlled", 0)) != len(config["network"]["controlled_tls"])
        ):
            continue
        hash_config = copy.deepcopy(config)
        if controller == "hybrid":
            hash_config["rl_net"]["hybrid_gate_path"] = "results/summary/t410_hybrid_gate.json"
        controller_hash = _network_controller_config_hash(hash_config, controller, root=root)
        if metadata.get("controller_config_sha256") != controller_hash:
            continue
        if controller in NETWORK_POLICY_CONTROLLERS:
            if (
                metadata.get("model_path") != NETWORK_PINNED_MODEL.as_posix()
                or metadata.get("model_sha256") != model_hash
                or model_hash != NETWORK_PINNED_MODEL_SHA256
                or record.run.get("controller_diagnostics", {}).get("model_sha256") != model_hash
            ):
                continue
        elif metadata.get("model_path") is not None or metadata.get("model_sha256") is not None:
            continue
        if not _complete_for_cell(
            folder, scenario=scenario, seed=seed, controller=controller, seed_set=seed_set,
            route_hash=_sha256(route_path), config_hash=config_hash,
            model_hash=model_hash if controller in NETWORK_POLICY_CONTROLLERS else None,
            family="network", controller_config_hash=controller_hash,
        ):
            continue
        route_hashes[(scenario, seed)].add(str(metadata["route_sha256"]))
        found[(scenario, seed, controller)] = (record, metadata)
    mismatched = [key for key, hashes in route_hashes.items() if len(hashes) > 1]
    if mismatched:
        raise ValueError(f"Network controllers used different route files: {mismatched[:3]}")
    return [found[key] for key in sorted(found)]


def _network_run_rows(
    records: list[RunData], metadata_by_run: dict[str, dict[str, Any]], seed_set: str,
    controllers: tuple[str, ...],
) -> list[dict[str, Any]]:
    cells = per_episode_values(records, controllers)
    output: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: (item.key[0], item.key[1], item.key[2])):
        run = record.run
        summary = record.summary
        meta = metadata_by_run[str(run["run_id"])]
        common = cells.get((str(run["scenario"]), int(run["seed"]), str(run["controller"]),
                            "all", "travel_time", "common"))
        diagnostics = run.get("controller_diagnostics", {})
        latencies = diagnostics.get("batch_inference_latency_ms", [])
        junctions = _read_csv(Path(run["out_dir"]) / "junctions.csv")
        ppo_tls_ids = set(diagnostics.get("ppo_tls_ids", ()))
        if run["controller"] == "rl":
            ppo_tls_ids = {str(row["tls_id"]) for row in junctions}
        ppo_rows = [row for row in junctions if str(row["tls_id"]) in ppo_tls_ids]
        ppo_ticks = sum(float(row.get("ppo_tick_share", 0.0)) * int(row.get("n_ticks", 0)) for row in ppo_rows)
        policy_ticks = sum(int(row.get("n_ticks", 0)) for row in ppo_rows)
        rejected = sum(int(row.get("n_illegal_actions", 0)) for row in junctions)
        forced = sum(int(row.get("n_forced_max_green", 0)) for row in junctions)
        output.append({
            "milestone": "M2", "run_id": run["run_id"], "scenario": run["scenario"],
            "seed": run["seed"], "controller": run["controller"],
            "ai_coverage": summary.get("ai_coverage", "none"),
            "n_tls_ai": summary.get("n_tls_ai", 0), "n_tls_controlled": summary.get("n_tls_controlled", 0),
            "model_path": meta.get("model_path"), "model_sha256": meta.get("model_sha256"),
            "n_trips": summary.get("n_trips"), "n_completed": summary.get("n_completed"),
            "completion_rate": summary.get("completion_rate"),
            "common_trip_count": common.n_trips if common else 0,
            "avg_travel_time_common": common.value if common else None,
            "avg_travel_time_censored": summary.get("avg_travel_time_censored"),
            "fallback_tick_share": (1.0 - ppo_ticks / policy_ticks) if policy_ticks else "",
            "rejected_actions": rejected if run["controller"] in NETWORK_POLICY_CONTROLLERS else "",
            "forced_max_green_switches": forced,
            "median_batch_inference_latency_ms": diagnostics.get("median_batch_inference_latency_ms", ""),
            "max_batch_inference_latency_ms": max(latencies, default=""),
            "wall_clock_s": summary.get("wall_clock_s"),
            "route_sha256": meta.get("route_sha256"),
            "controller_config_sha256": meta.get("controller_config_sha256"),
        })
    return output


def _network_junction_rows(
    root: Path, records: list[RunData], seed_set: str,
) -> list[dict[str, Any]]:
    config = load_config(root / "config" / "stms.yaml")
    minimum_share = float(config["eval"]["ai_coverage_min_share"])
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        rows = _read_csv(Path(record.run["out_dir"]) / "junctions.csv")
        if len(rows) != len(config["network"]["controlled_tls"]):
            raise ValueError(f"Expected one row per TLS in {record.run['run_id']}")
        for row in rows:
            grouped[(str(record.run["scenario"]), row["tls_id"], str(record.run["controller"]))].append(row)
    results: list[dict[str, Any]] = []
    for index, ((scenario, tls_id, controller), rows) in enumerate(sorted(grouped.items())):
        queues = [float(row["avg_queue"]) for row in rows]
        waits = [float(row["avg_wait"]) for row in rows]
        congestion = [float(row["frac_time_high_congestion"]) for row in rows]
        queue_low, queue_high = _bootstrap_ci(queues, 2291 + index)
        ticks = sum(int(row.get("n_ticks", 0)) for row in rows)
        ppo_ticks = sum(float(row.get("ppo_tick_share", 0.0)) * int(row.get("n_ticks", 0)) for row in rows)
        ppo_share = ppo_ticks / ticks if ticks else 0.0
        is_rule_slot = controller == "hybrid" and all(
            row.get("controlled_by") == "rule" for row in rows
        )
        if controller in NETWORK_POLICY_CONTROLLERS:
            controlled_by = (
                "rule" if is_rule_slot else
                "rl" if ppo_share >= minimum_share else "rl_fallback"
            )
            fallback_share: float | str = "" if is_rule_slot else 1 - ppo_share
            fallback_ticks: int | str = "" if is_rule_slot else ticks - round(ppo_ticks)
        else:
            controlled_by = controller
            fallback_share = ""
            fallback_ticks = ""
        run = next(item.run for item in records if item.run["scenario"] == scenario
                   and item.run["controller"] == controller)
        model_hash = run.get("controller_diagnostics", {}).get("model_sha256", "") if controller in NETWORK_POLICY_CONTROLLERS else ""
        is_policy = controller in NETWORK_POLICY_CONTROLLERS
        results.append({
            "scenario": scenario, "tls_id": tls_id, "controller": controller,
            "avg_queue_mean": statistics.fmean(queues), "avg_wait_mean": statistics.fmean(waits),
            "ci95_low": queue_low, "ci95_high": queue_high,
            "frac_time_high_congestion_mean": statistics.fmean(congestion), "n_seeds": len(rows),
            "seed_set": seed_set, "controlled_by": controlled_by,
            "ppo_tick_share": ppo_share if is_policy else "",
            "fallback_tick_share": fallback_share, "fallback_ticks": fallback_ticks,
            "n_ticks": ticks, "n_illegal_actions": sum(int(row.get("n_illegal_actions", 0)) for row in rows),
            "n_forced_max_green": sum(int(row.get("n_forced_max_green", 0)) for row in rows),
            "model_sha256": model_hash,
        })
    return results


def _network_coverage_summary(
    root: Path, records: list[RunData], seed_set: str, policy_controller: str,
) -> dict[str, Any]:
    """Summarize TLS coverage conservatively across every RL cell in one seed block."""
    config = load_config(root / "config" / "stms.yaml")
    intended = tuple(str(value) for value in config["network"]["controlled_tls"])
    minimum_share = float(config["eval"]["ai_coverage_min_share"])
    policy_records = [record for record in records if record.run.get("controller") == policy_controller]
    if not policy_records:
        raise ValueError(f"No RL records available for network {seed_set} coverage summary")
    shares: dict[str, list[float]] = defaultdict(list)
    model_hashes: set[str] = set()
    for record in policy_records:
        model_hash = str(record.run.get("controller_diagnostics", {}).get("model_sha256", ""))
        if model_hash:
            model_hashes.add(model_hash)
        rows = _read_csv(Path(record.run["out_dir"]) / "junctions.csv")
        if {row.get("tls_id") for row in rows} != set(intended):
            raise ValueError(f"Coverage output is missing an intended TLS in {record.run['run_id']}")
        for row in rows:
            share = float(row["ppo_tick_share"])
            if not math.isfinite(share) or not 0 <= share <= 1:
                raise ValueError(f"Invalid PPO tick share for {row['tls_id']} in {record.run['run_id']}")
            shares[str(row["tls_id"])].append(share)
    if len(model_hashes) != 1:
        raise ValueError(f"Network {seed_set} RL cells do not share one model identity: {sorted(model_hashes)}")
    covered = sum(
        1 for tls_id in intended
        if len(shares[tls_id]) == len(policy_records)
        and all(share >= minimum_share for share in shares[tls_id])
    )
    coverage = "full" if covered == len(intended) else "none" if covered == 0 else "partial"
    return {
        "milestone": "M2", "seed_set": seed_set, "n_rl_cells": len(policy_records),
        "n_tls_ai": covered, "n_tls_controlled": len(intended),
        "ai_coverage": coverage, "model_sha256": next(iter(model_hashes)),
    }


def _write_csv_rows(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in fields})
    temporary.replace(path)


def merge_comparison_milestones(
    existing_rows: list[dict[str, Any]], network_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace M2 rows while retaining every pre-existing non-M2 row unchanged."""
    return [row for row in existing_rows if row.get("milestone") != "M2"] + network_rows


def write_network_outputs(
    root: Path, *, seed_set: str = "dev", controllers: tuple[str, ...] = CONTROLLERS,
) -> list[dict[str, Any]]:
    """Validate a complete network seed grid and deterministically rebuild M2 summaries."""
    seeds = _seed_block(seed_set)
    if controllers not in (CONTROLLERS, ("fixed", "rule", "hybrid")):
        raise ValueError("Network aggregation requires fixed, rule and exactly one of rl/hybrid")
    validated = _load_network_evaluation_runs(root, seed_set=seed_set, controllers=controllers)
    cells = {(record.key[0], record.key[1], record.key[2]) for record, _ in validated}
    expected = {(scenario, seed, controller) for scenario in NETWORK_SCENARIOS
                for seed in seeds for controller in controllers}
    missing = sorted(expected - cells)
    if missing:
        raise ValueError(f"Network {seed_set} grid incomplete: {len(missing)} missing cells; first: {missing[:3]}")
    expected_count = len(NETWORK_SCENARIOS) * len(seeds) * len(controllers)
    if len(cells) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} unique network {seed_set} cells, found {len(cells)}")
    records = [record for record, _ in validated]
    metadata_by_run = {str(record.run["run_id"]): metadata for record, metadata in validated}
    config = load_config(root / "config" / "stms.yaml")
    rows = build_comparison_rows(
        records, seed_set=seed_set, controllers=controllers,
        target_reduction_pct=float(config["eval"]["target_reduction_pct"]), family="network",
        target_controllers=("rl", "hybrid"),
    )
    summary_dir = root / "results" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = summary_dir / "comparison.csv"
    # Keep existing M1 rows exactly as stored; replace only network M2 rows.
    existing_rows: list[dict[str, str]] = []
    if comparison_path.is_file():
        existing_rows = _read_csv(comparison_path)
    comparison_rows = merge_comparison_milestones(existing_rows, rows)
    _write_csv_rows(comparison_path, COMPARISON_FIELDS, comparison_rows)
    run_rows = _network_run_rows(records, metadata_by_run, seed_set, controllers)
    junction_rows = _network_junction_rows(root, records, seed_set)
    _write_csv_rows(summary_dir / "network_runs.csv", NETWORK_RUN_FIELDS, run_rows)
    _write_csv_rows(summary_dir / "network_junctions.csv", NETWORK_JUNCTION_FIELDS, junction_rows)
    policy_controller = "hybrid" if "hybrid" in controllers else "rl"
    _write_csv_rows(summary_dir / "summary.csv", NETWORK_SUMMARY_FIELDS,
                    [_network_coverage_summary(root, records, seed_set, policy_controller)])
    write_network_junction_figure(junction_rows, root / "results" / "figures")
    return rows


def _print_headline(rows: list[dict[str, Any]], config: dict[str, Any], controllers: tuple[str, ...]) -> None:
    target = float(config["eval"]["target_reduction_pct"])
    policy_controller = "hybrid" if "hybrid" in controllers else "rl"
    rl_rows = [
        row for row in rows
        if row["controller"] == policy_controller
        and row["metric"] == "travel_time" and row["scope"] in {"all", "junction"}
    ]
    decisions: dict[tuple[str, str, str, str], bool] = {}
    for row in sorted(rl_rows, key=lambda item: (item["aggregation"], item["scenario"], item["scope"], item["trip_basis"])):
        improvement = row["improvement_vs_fixed_pct"]
        met = None if improvement is None else float(improvement) >= target
        key = (str(row["aggregation"]), str(row["scenario"]), str(row["scope"]), str(row["trip_basis"]))
        decisions[key] = met
        basis_label = "common-trip" if row["trip_basis"] == "common" else "censored/all trips"
        milestone = str(row.get("milestone", "M1"))
        print(
            f"{milestone} {row['aggregation']} ({row['scenario']}) {row['scope']} {basis_label}: "
            f"{policy_controller} improvement vs fixed {'n/a' if improvement is None else f'{float(improvement):.2f}%'} "
            f"(target {target:.1f}%: {'not computable' if met is None else 'met' if met else 'not met'}); "
            f"mean={float(row['mean']):.2f}, std={float(row['std']):.2f}, "
            f"paired-bootstrap 95% CI is in comparison.csv improvement rows."
        )
    comparison_keys = {(row["aggregation"], row["scenario"], row["scope"]) for row in rl_rows}
    for aggregation, scenario, scope in sorted(comparison_keys):
        common = decisions.get((str(aggregation), str(scenario), str(scope), "common"))
        censored = decisions.get((str(aggregation), str(scenario), str(scope), "all"))
        if common is not None and censored is not None and common != censored:
            print(f"TARGET BASIS DISAGREEMENT ({aggregation}/{scenario}/{scope}): common-trip and censored results differ.")

    if "fixed" in controllers and policy_controller in controllers:
        gap = float(config["eval"]["completion_gap_flag_pp"])
        for aggregation, scenario, scope in sorted(comparison_keys):
            rl = next((r for r in rl_rows if r["aggregation"] == aggregation and r["scenario"] == scenario
                       and r["scope"] == scope and r["trip_basis"] == "common"), None)
            if not rl:
                continue
            fixed = next((r for r in rows if r["aggregation"] == aggregation and r["scenario"] == scenario
                          and r["controller"] == "fixed" and r["metric"] == "travel_time"
                          and r["scope"] == scope and r["trip_basis"] == "common"), None)
            if fixed and rl["completion_rate_mean"] is not None and fixed["completion_rate_mean"] is not None:
                gap_pp = abs(float(rl["completion_rate_mean"]) - float(fixed["completion_rate_mean"])) * 100
                if gap_pp > gap:
                    print(f"POSSIBLE SURVIVORSHIP BIAS ({aggregation}/{scenario}/{scope}): RL/fixed completion gap "
                          f"{gap_pp:.2f} pp exceeds {gap:.2f} pp.")


def _network_wall_time_estimate(root: Path) -> tuple[float, int, int]:
    """Estimate serial network-cell time from unique T4.4 baselines and T4.7 candidate runs."""
    baseline_times: dict[tuple[str, int, str], float] = {}
    candidate_times: list[float] = []
    for folder in (root / "results" / "raw").iterdir():
        run_path = folder / "run.json"
        summary_path = folder / "summary.csv"
        if not folder.is_dir() or not run_path.is_file() or not summary_path.is_file():
            continue
        try:
            run = _read_json(run_path)
            summary = _read_csv(summary_path)[0]
            wall = float(summary["wall_clock_s"])
        except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError):
            continue
        if not math.isfinite(wall) or wall <= 0:
            continue
        key = (str(run.get("scenario")), int(run.get("seed", -1)), str(run.get("controller")))
        if key[0] in NETWORK_SCENARIOS and 3000 <= key[1] <= 3002 and key[2] in {"fixed", "rule"}:
            baseline_times[key] = wall
        if (
            key[0] in NETWORK_SCENARIOS and 3000 <= key[1] <= 3002 and key[2] == "rl"
            and run.get("controller_diagnostics", {}).get("model_sha256") == NETWORK_PINNED_MODEL_SHA256
        ):
            candidate_times.append(wall)
    baseline_default = statistics.fmean(baseline_times.values()) if baseline_times else 816.5936188
    rl_default = statistics.fmean(candidate_times) if candidate_times else baseline_default
    serial_seconds = 50 * baseline_default + 25 * rl_default
    return serial_seconds, len(baseline_times), len(candidate_times)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("single", "network"), default="single")
    parser.add_argument("--controllers", nargs="+", choices=NETWORK_CONTROLLERS, default=list(CONTROLLERS))
    parser.add_argument("--seed-set", choices=("dev", "final"), default="dev")
    parser.add_argument("--jobs", help="parallel runs: a positive worker count or 'auto' (config default)")
    arguments = parser.parse_args(argv)
    controllers = tuple(dict.fromkeys(arguments.controllers))
    if not controllers:
        parser.error("at least one controller is required")
    try:
        config = load_config(ROOT / "config" / "stms.yaml")
        if arguments.family == "network":
            if controllers not in (CONTROLLERS, ("fixed", "rule", "hybrid")):
                raise ValueError("Network evaluation requires fixed, rule and exactly one of rl/hybrid")
            serial_seconds, baseline_count, rl_count = _network_wall_time_estimate(ROOT)
            desired, auto = _resolve_jobs(config.get("jobs", {}).get("parallel_runs", "auto"), arguments.jobs)
            print(
                f"Estimated network {arguments.seed_set} grid: {serial_seconds / 3600:.2f} h serial "
                f"from {baseline_count}/30 T4.4 baseline timings and {rl_count} T4.7 candidate runs; "
                f"auto worker target={desired} (effective workers selected after memory probe); "
                "route generation and startup excluded.", flush=True,
            )
            run_network_grid(root=ROOT, seed_set=arguments.seed_set, controllers=controllers, jobs_override=arguments.jobs)
            if arguments.seed_set == "final":
                summary_dir = ROOT / "results" / "summary"
                for source, backup in (
                    ("comparison.csv", "comparison_dev_snapshot.csv"),
                    ("network_runs.csv", "network_runs_dev_snapshot.csv"),
                    ("network_junctions.csv", "network_junctions_dev_snapshot.csv"),
                ):
                    source_path = summary_dir / source
                    backup_path = summary_dir / backup
                    if source_path.is_file() and not backup_path.exists():
                        shutil.copy2(source_path, backup_path)
            rows = write_network_outputs(ROOT, seed_set=arguments.seed_set, controllers=controllers)
            _print_headline(rows, config, controllers)
            headline = next(row for row in rows if row["aggregation"] == "headline"
                            and row["scenario"] == "headline" and row["controller"] in NETWORK_POLICY_CONTROLLERS
                            and row["controller"] == ("hybrid" if "hybrid" in controllers else "rl")
                            and row["metric"] == "travel_time" and row["scope"] == "all"
                            and row["trip_basis"] == "common")
            print(
                f"M2 {arguments.seed_set} Metric N: common-trip headline improvement vs fixed="
                f"{headline['improvement_vs_fixed_pct']:.2f}% (10% target "
                f"{'MET' if headline['target_met'] else 'NOT MET'}).", flush=True,
            )
            print(f"comparison={ROOT / 'results' / 'summary' / 'comparison.csv'}", flush=True)
            print(f"network_runs={ROOT / 'results' / 'summary' / 'network_runs.csv'}", flush=True)
            print(f"network_junctions={ROOT / 'results' / 'summary' / 'network_junctions.csv'}", flush=True)
            return 0
        if "hybrid" in controllers:
            raise ValueError("The hybrid network controller is available only with --family network")
        estimate_s = 917.126  # measured T1.4 fixed medium seed-3000 episode wall time
        desired, auto = _resolve_jobs(config.get("jobs", {}).get("parallel_runs", "auto"), arguments.jobs)
        estimated = len(SCENARIOS) * len(_seed_block(arguments.seed_set)) * len(controllers) * estimate_s / desired
        print(
            f"Estimated episode grid wall time: {estimated / 3600:.2f} h "
            f"({len(SCENARIOS)} scenarios × 5 seeds × {len(controllers)} controllers × "
            f"{estimate_s:.1f}s measured T1.4 mean / {desired} planned workers; "
            f"{'auto' if auto else 'explicit'} scheduling; route generation not included).",
            flush=True,
        )
        run_grid(
            root=ROOT, seed_set=arguments.seed_set, controllers=controllers,
            jobs_override=arguments.jobs,
        )
        rows = write_comparison(
            ROOT, arguments.seed_set, controllers, float(config["eval"]["target_reduction_pct"]),
        )
        _print_headline(rows, config, controllers)
        print(f"comparison={ROOT / 'results' / 'summary' / 'comparison.csv'}", flush=True)
        print(f"figures={ROOT / 'results' / 'figures'}", flush=True)
    except Exception:
        LOGGER.exception("Evaluation failed; completed run folders are preserved for resume")
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    raise SystemExit(main())
