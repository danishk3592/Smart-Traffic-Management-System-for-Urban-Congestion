"""Train a resumable CPU PPO policy on validated, cached SUMO scenarios."""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CallbackList,
    CheckpointCallback,
    EvalCallback,
)
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from Ai.common.config import load_config
from Ai.rl.traffic_env import TrafficEnvironment
from scripts.make_scenarios import get_cached_routes

ROOT = Path(__file__).resolve().parents[2]
METRIC_FIELDS = (
    "episode",
    "reward",
    "mean_wait",
    "mean_queue",
    "illegal_action_rate",
    "action_histogram",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _active_monotonic() -> float:
    """Measure active system time, excluding Windows sleep and hibernation."""
    if os.name != "nt":
        return time.monotonic()
    ticks = ctypes.c_ulonglong()
    query = ctypes.WinDLL("kernel32", use_last_error=True).QueryUnbiasedInterruptTime
    query.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]
    query.restype = ctypes.c_bool
    if not query(ctypes.byref(ticks)):
        raise ctypes.WinError(ctypes.get_last_error())
    return ticks.value / 10_000_000


def _parse_scenarios(values: Sequence[str] | None, allowed: Sequence[str]) -> tuple[str, ...]:
    """Parse a scenario list while preserving the requested order."""
    requested = [
        item.strip()
        for value in (values or allowed)
        for item in value.split(",")
        if item.strip()
    ]
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("scenarios must be a non-empty list without duplicates")
    invalid = sorted(set(requested) - set(allowed))
    if invalid:
        raise ValueError(f"unknown training scenarios: {invalid}")
    return tuple(requested)


def _parse_reward_weights(value: str | None, defaults: dict[str, float]) -> dict[str, float]:
    """Parse comma-separated ``name=value`` reward-weight overrides."""
    if value is None:
        return dict(defaults)
    result: dict[str, float] = {}
    for assignment in value.split(","):
        if "=" not in assignment:
            raise ValueError("reward weights must use queue=value,wait=value,throughput=value")
        key, raw = assignment.split("=", maxsplit=1)
        key = key.strip()
        if key not in defaults or key in result:
            raise ValueError(f"unknown or repeated reward weight: {key!r}")
        number = float(raw)
        if not math.isfinite(number):
            raise ValueError(f"reward weight {key!r} must be finite")
        result[key] = number
    if set(result) != set(defaults):
        raise ValueError(f"reward weights must define exactly {sorted(defaults)}")
    return result


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _git_commit() -> str:
    """Return the checked-out commit for model provenance."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def _library_versions() -> dict[str, str]:
    """Collect installed library versions for the training record."""
    packages = ("stable-baselines3", "gymnasium", "numpy", "torch", "tensorboard")
    found: dict[str, str] = {"python": sys.version.split()[0]}
    for package in packages:
        try:
            found[package] = version(package)
        except PackageNotFoundError:
            found[package] = "not-installed"
    return found


def _validate_caches(scenarios: Sequence[str], train_seeds: Sequence[int], eval_seeds: Sequence[int]) -> None:
    """Fail before model creation unless every training and validation cache is valid."""
    total = len(scenarios) * (len(train_seeds) + len(eval_seeds))
    checked = 0
    for seed in (*train_seeds, *eval_seeds):
        for scenario in scenarios:
            get_cached_routes(scenario, seed)
            checked += 1
            if checked % 20 == 0 or checked == total:
                print(f"validated route caches {checked}/{total}", flush=True)


def _latest_checkpoint(out_dir: Path) -> Path:
    """Return the newest numbered checkpoint without changing prior files."""
    paths = list((out_dir / "checkpoints").glob("ppo_*_steps.zip"))
    if not paths:
        raise FileNotFoundError(f"no resumable PPO checkpoints under {out_dir / 'checkpoints'}")
    return max(paths, key=lambda path: int(re.search(r"ppo_(\d+)_steps\.zip$", path.name).group(1)))


class ValidationSeedEnvironment(TrafficEnvironment):
    """Cycle EvalCallback episodes through the reserved 3000–3009 seeds."""

    def __init__(self, scenarios: Sequence[str], seeds: Sequence[int], config: dict[str, Any]) -> None:
        self.validation_seeds = tuple(seeds)
        self._validation_index = 0
        super().__init__(scenario_pool=scenarios, seeds=seeds, config=config)

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        if seed is None:
            seed = self.validation_seeds[self._validation_index % len(self.validation_seeds)]
            self._validation_index += 1
        return super().reset(seed=seed, options=options)


class EpisodeMetricsCallback(BaseCallback):
    """Append per-episode environment metrics and periodic ETA to CSV/stdout."""

    def __init__(
        self,
        csv_path: Path,
        target_steps: int,
        started_at: float,
        initial_steps: int = 0,
    ) -> None:
        super().__init__(verbose=0)
        self.csv_path = csv_path
        self.target_steps = target_steps
        self.started_at = started_at
        self.initial_steps = initial_steps
        self.episode_count = 0
        self._totals: dict[int, dict[str, Any]] = {}
        self._last_progress_step = 0
        self._last_sim_time: dict[int, float] = {}
        self.simulated_seconds = 0.0

    def _on_training_start(self) -> None:
        if self.csv_path.is_file():
            with self.csv_path.open(encoding="utf-8", newline="") as stream:
                self.episode_count = sum(1 for _ in csv.DictReader(stream))
        else:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
                csv.DictWriter(stream, fieldnames=METRIC_FIELDS).writeheader()

    def _on_step(self) -> bool:
        rewards = self.locals["rewards"]
        dones = self.locals["dones"]
        infos = self.locals["infos"]
        for index, info in enumerate(infos):
            sim_time = float(info.get("sim_time", 0.0))
            previous_sim_time = self._last_sim_time.get(index, 0.0)
            if sim_time >= previous_sim_time:
                self.simulated_seconds += sim_time - previous_sim_time
            self._last_sim_time[index] = 0.0 if dones[index] else sim_time
            bucket = self._totals.setdefault(
                index,
                {"reward": 0.0, "wait": 0.0, "queue": 0.0, "illegal": 0, "steps": 0, "actions": Counter()},
            )
            bucket["reward"] += float(rewards[index])
            bucket["wait"] += float(info.get("wait_total", 0.0))
            bucket["queue"] += float(info.get("queue_total", 0.0))
            bucket["illegal"] += int(bool(info.get("illegal_action", False)))
            bucket["steps"] += 1
            bucket["actions"][int(info.get("action_taken", 0))] += 1
            if dones[index]:
                self.episode_count += 1
                count = max(1, bucket["steps"])
                row = {
                    "episode": self.episode_count,
                    "reward": float(info.get("episode", {}).get("r", bucket["reward"])),
                    "mean_wait": bucket["wait"] / count,
                    "mean_queue": bucket["queue"] / count,
                    "illegal_action_rate": bucket["illegal"] / count,
                    "action_histogram": json.dumps(
                        {str(action): bucket["actions"].get(action, 0) for action in range(4)},
                        sort_keys=True,
                    ),
                }
                with self.csv_path.open("a", encoding="utf-8", newline="") as stream:
                    csv.DictWriter(stream, fieldnames=METRIC_FIELDS).writerow(row)
                self._totals[index] = {
                    "reward": 0.0,
                    "wait": 0.0,
                    "queue": 0.0,
                    "illegal": 0,
                    "steps": 0,
                    "actions": Counter(),
                }

        if self.num_timesteps - self._last_progress_step >= 1000:
            elapsed = max(1e-6, _active_monotonic() - self.started_at)
            rate = (self.num_timesteps - self.initial_steps) / elapsed
            remaining = max(0, self.target_steps - self.num_timesteps)
            eta_s = remaining / rate if rate else math.inf
            print(
                f"[ppo] steps={self.num_timesteps}/{self.target_steps} "
                f"steps_per_hour={rate * 3600:.0f} "
                f"sim_s_per_real_s={self.simulated_seconds / elapsed:.2f} eta_s={eta_s:.0f}",
                flush=True,
            )
            self._last_progress_step = self.num_timesteps
        return True


class WallClockBudgetCallback(BaseCallback):
    """Stop cleanly at the configured maximum training wall-clock budget."""

    def __init__(
        self,
        started_at: float,
        max_hours: float,
        previously_spent_s: float = 0.0,
    ) -> None:
        super().__init__(verbose=0)
        self.started_at = started_at
        self.max_seconds = max_hours * 3600 - previously_spent_s

    def _on_step(self) -> bool:
        if _active_monotonic() - self.started_at >= self.max_seconds:
            print("[ppo] configured wall-clock budget reached; stopping at this step", flush=True)
            self.model.stop_training = True
            return False
        return True


def _best_validation_model(validation_root: Path) -> tuple[Path, float, int, str]:
    """Select the checkpoint with the highest measured validation mean reward."""
    candidates: list[tuple[float, int, Path, str]] = []
    for run_dir in validation_root.iterdir() if validation_root.exists() else ():
        result_path = run_dir / "evaluations.npz"
        best_path = run_dir / "best_model.zip"
        if not result_path.is_file() or not best_path.is_file():
            continue
        with np.load(result_path) as results:
            means = results["results"].mean(axis=1)
            steps = results["timesteps"]
        if len(means):
            index = int(np.argmax(means))
            candidates.append((float(means[index]), int(steps[index]), best_path, run_dir.name))
    if not candidates:
        raise RuntimeError("EvalCallback produced no complete validation checkpoint")
    mean_reward, step, path, run_name = max(candidates, key=lambda item: item[0])
    return path, mean_reward, step, run_name


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timesteps", type=int, required=True)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--scenarios", nargs="+", help="scenario names or comma-separated names")
    parser.add_argument("--reward-weights", help="queue=value,wait=value,throughput=value")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="resume the newest checkpoint in --out")
    return parser.parse_args(argv)


def train(args: argparse.Namespace) -> int:
    """Validate inputs, train with callbacks, and save the best validation model."""
    if args.timesteps <= 0 or args.timesteps > 300_000:
        raise ValueError("timesteps must be in 1..300000")
    if not 1000 <= args.seed <= 1999:
        raise ValueError("PPO training seed must be in 1000–1999")

    config = deepcopy(load_config())
    train_pool = config["demand"]["train_pool"]
    scenarios = _parse_scenarios(args.scenarios, train_pool["scenarios"])
    weights = _parse_reward_weights(args.reward_weights, config["rl"]["reward_weights"])
    config["rl"]["reward_weights"] = weights
    max_train_hours = float(config["rl"]["max_train_hours"])
    train_seeds = tuple(
        range(int(train_pool["seed_min"]), int(train_pool["seed_min"]) + int(train_pool["seeds_per_scenario"]))
    )
    validation_seeds = tuple(int(seed) for seed in config["eval"]["validation_seeds"])
    if validation_seeds != tuple(range(3000, 3010)):
        raise ValueError("T2.3 validation seeds must be exactly 3000–3009")

    out_dir = args.out if args.out.is_absolute() else ROOT / args.out
    out_dir = out_dir.resolve()
    if args.resume:
        if not out_dir.is_dir() or not (out_dir / "config.json").is_file():
            raise FileNotFoundError(f"cannot resume without an existing training output: {out_dir}")
        existing_config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
        if existing_config.get("scenarios") != list(scenarios) or existing_config.get("reward_weights") != weights:
            raise ValueError("resume settings differ from the existing run's scenarios or reward weights")
        checkpoint = _latest_checkpoint(out_dir)
        previous_training_seconds = float(existing_config.get("training_wall_clock_s", 0.0))
        if previous_training_seconds >= max_train_hours * 3600:
            raise ValueError("the configured cumulative PPO wall-clock budget is already exhausted")
    else:
        if out_dir.exists():
            raise FileExistsError(f"training output already exists; use --resume or choose a new path: {out_dir}")
        checkpoint = None
        previous_training_seconds = 0.0

    print(f"preflighting {len(scenarios) * (len(train_seeds) + len(validation_seeds))} cached routes", flush=True)
    _validate_caches(scenarios, train_seeds, validation_seeds)
    if not args.resume:
        out_dir.mkdir(parents=True, exist_ok=False)
    checkpoint_dir = out_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    validation_root = out_dir / "evaluations"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    validation_run_dir = validation_root / run_id
    validation_run_dir.mkdir(parents=True, exist_ok=False)
    monitor_dir = out_dir / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)

    hyperparameters = {
        "learning_rate": float(config["rl"]["ppo"]["learning_rate"]),
        "n_steps": int(config["rl"]["ppo"]["n_steps"]),
        "batch_size": int(config["rl"]["ppo"]["batch_size"]),
        "gamma": float(config["rl"]["ppo"]["gamma"]),
        "ent_coef": float(config["rl"]["ppo"]["ent_coef"]),
        "device": "auto",
    }
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "created_utc": _utc_now(),
        "run_id": run_id,
        "command": sys.argv,
        "scenarios": list(scenarios),
        "seed": args.seed,
        "training_seed_block": [1000, 1999],
        "training_seeds": list(train_seeds),
        "validation_seeds": list(validation_seeds),
        "reward_weights": weights,
        "reward_scales": dict(config["rl"]["reward_scales"]),
        "hyperparameters": hyperparameters,
        "git_commit": _git_commit(),
        "library_versions": _library_versions(),
        "training_wall_clock_s": float(existing_config.get("training_wall_clock_s", 0.0)) if args.resume else 0.0,
        "target_timesteps": args.timesteps,
        "starting_timesteps": 0,
        "num_timesteps": 0,
        "selected_validation_mean_reward": None,
        "selected_validation_timestep": None,
        "selected_validation_run": None,
        "out_dir": str(out_dir),
    }
    _atomic_json(out_dir / "config.json", metadata)

    def make_training_env() -> Monitor:
        environment = TrafficEnvironment(scenario_pool=scenarios, seeds=train_seeds, config=config)
        return Monitor(environment, filename=str(monitor_dir / f"train_{run_id}.csv"))

    def make_validation_env() -> Monitor:
        environment = ValidationSeedEnvironment(scenarios, validation_seeds, config)
        return Monitor(environment, filename=str(monitor_dir / f"validation_{run_id}.csv"))

    training_env = DummyVecEnv([make_training_env])
    evaluation_env = DummyVecEnv([make_validation_env])
    run_started = _active_monotonic()
    try:
        if args.resume:
            model = PPO.load(checkpoint, env=training_env, device="auto")
            starting_steps = int(model.num_timesteps)
        else:
            model = PPO(
                policy="MlpPolicy",
                env=training_env,
                learning_rate=hyperparameters["learning_rate"],
                n_steps=hyperparameters["n_steps"],
                batch_size=hyperparameters["batch_size"],
                gamma=hyperparameters["gamma"],
                ent_coef=hyperparameters["ent_coef"],
                seed=args.seed,
                verbose=1,
                device="auto",
                tensorboard_log=str(out_dir / "tensorboard"),
            )
            starting_steps = 0
        remaining = args.timesteps - starting_steps
        if remaining <= 0:
            raise ValueError(
                f"model already has {starting_steps} steps; requested target is {args.timesteps}"
            )
        metadata["starting_timesteps"] = starting_steps
        _atomic_json(out_dir / "config.json", metadata)

        checkpoint_callback = CheckpointCallback(
            save_freq=int(config["rl"]["ppo"]["checkpoint_every_timesteps"]),
            save_path=str(checkpoint_dir),
            name_prefix="ppo",
            save_replay_buffer=False,
            save_vecnormalize=False,
        )
        metrics_callback = EpisodeMetricsCallback(
            out_dir / "training_log.csv",
            target_steps=args.timesteps,
            started_at=run_started,
            initial_steps=starting_steps,
        )
        evaluation_callback = EvalCallback(
            evaluation_env,
            best_model_save_path=str(validation_run_dir),
            log_path=str(validation_run_dir),
            eval_freq=int(config["rl"]["ppo"]["eval_every_timesteps"]),
            n_eval_episodes=len(validation_seeds),
            deterministic=True,
            render=False,
            verbose=1,
            warn=False,
        )
        budget_callback = WallClockBudgetCallback(
            started_at=run_started,
            max_hours=max_train_hours,
            previously_spent_s=previous_training_seconds,
        )
        model.learn(
            total_timesteps=remaining,
            callback=CallbackList(
                [checkpoint_callback, metrics_callback, evaluation_callback, budget_callback]
            ),
            tb_log_name="ppo",
            reset_num_timesteps=not args.resume,
            progress_bar=False,
        )

        best_path, best_reward, best_step, best_run = _best_validation_model(validation_root)
        final_model = out_dir / "model.zip"
        temporary_model = out_dir / ".model.tmp.zip"
        shutil.copy2(best_path, temporary_model)
        temporary_model.replace(final_model)
        elapsed = _active_monotonic() - run_started
        metadata.update(
            completed_utc=_utc_now(),
            training_wall_clock_s=float(metadata["training_wall_clock_s"]) + elapsed,
            num_timesteps=int(model.num_timesteps),
            selected_validation_mean_reward=best_reward,
            selected_validation_timestep=best_step,
            selected_validation_run=best_run,
            final_model=str(final_model),
        )
        _atomic_json(out_dir / "config.json", metadata)
        with np.load(validation_root / best_run / "evaluations.npz") as validation:
            latest_mean = float(validation["results"][-1].mean())
        rate = (model.num_timesteps - starting_steps) / max(elapsed, 1e-6)
        print(
            f"training complete: steps={model.num_timesteps} elapsed_s={elapsed:.1f} "
            f"steps_per_hour={rate * 3600:.0f} "
            f"sim_s_per_real_s={metrics_callback.simulated_seconds / max(elapsed, 1e-6):.2f} "
            f"validation_best_mean_reward={best_reward:.6f} "
            f"validation_latest_mean_reward={latest_mean:.6f} model={final_model}",
            flush=True,
        )
        return 0
    finally:
        evaluation_env.close()
        training_env.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the staged PPO training command."""
    return train(_parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
