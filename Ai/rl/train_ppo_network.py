"""Train a resumable shared-policy PPO model across the frozen network TLS set."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sys
import time
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CallbackList, CheckpointCallback
from stable_baselines3.common.vec_env import VecMonitor

from Ai.common.config import load_config
from Ai.rl.network_validation import NetworkValidationCallback
from Ai.rl.network_vec_env import NetworkVecEnv
from Ai.rl.train_ppo import _active_monotonic, _git_commit, _library_versions
from scripts.make_scenarios import ScenarioBuilder

ROOT = Path(__file__).resolve().parents[2]
STAGE3_DEFAULT_SCENARIOS = ("net_medium", "net_heavy", "net_rush_hour")


def _stage3_training_config(
    config: dict[str, Any], requested_scenarios: Sequence[str] | None
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Apply the roadmap's lower-cost training schedule without changing validation."""
    stage_config = deepcopy(config)
    allowed = stage_config["demand"]["net_train_pool"]["scenarios"]
    scenarios = _scenarios(requested_scenarios or STAGE3_DEFAULT_SCENARIOS, allowed)
    if not set(scenarios) < set(allowed):
        raise ValueError("Stage 3 must use a strict subset of the configured training scenarios")
    stage_config["rl_net"]["episode_s"] = 1800
    stage_config["rl_net"]["decision_interval_s"] = 10
    return stage_config, scenarios


def _load_resume_model(checkpoint: Path, env: VecMonitor, device: str) -> PPO:
    """Load the durable checkpoint and clear any prior callback stop flag."""
    model = _ExactTargetPPO.load(checkpoint, env=env, device=device)
    model.stop_training = False
    return model


def _resume_pool_compatible(
    previous: Sequence[str], requested: Sequence[str], *, stage3: bool
) -> bool:
    """Allow only an explicit Stage 3 reduction when resuming a trained policy."""
    if list(previous) == list(requested):
        return True
    return stage3 and set(requested) < set(previous) and set(requested).issubset(previous)


def _rollout_steps_for_remaining(
    remaining_timesteps: int, n_envs: int, max_rollout_steps: int
) -> int:
    """Choose a full (possibly short final) vector rollout for an exact target."""
    if remaining_timesteps <= 0 or n_envs <= 0 or max_rollout_steps <= 0:
        raise ValueError("remaining timesteps, environment count, and rollout size must be positive")
    if remaining_timesteps % n_envs:
        raise ValueError(
            f"remaining timesteps ({remaining_timesteps}) must be divisible by n_envs ({n_envs})"
        )
    return min(max_rollout_steps, remaining_timesteps // n_envs)


def _resolve_cumulative_training_cap(
    configured_seconds: float, override_seconds: float | None, already_spent: float
) -> float:
    """Resolve a per-run cap without mutating shared configuration."""
    cap = configured_seconds if override_seconds is None else override_seconds
    if not math.isfinite(cap) or cap <= 0 or not math.isfinite(already_spent) or already_spent < 0:
        raise ValueError("cumulative training cap and recorded spend must be finite and valid")
    if already_spent >= cap:
        raise ValueError("cumulative network PPO wall-clock budget already exhausted")
    return cap


class _ExactTargetPPO(PPO):
    """PPO variant that trains on a shortened final rollout at an exact target."""

    exact_target_timesteps: int | None = None

    def collect_rollouts(self, env, callback, rollout_buffer, n_rollout_steps: int):
        if self.exact_target_timesteps is not None:
            remaining = self.exact_target_timesteps - int(self.num_timesteps)
            n_rollout_steps = _rollout_steps_for_remaining(
                remaining, int(env.num_envs), n_rollout_steps
            )
            # Arrays are allocated at the original size; the active length controls
            # buffer completion and minibatch iteration for the final update.
            rollout_buffer.buffer_size = n_rollout_steps
        return super().collect_rollouts(env, callback, rollout_buffer, n_rollout_steps)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _scenarios(values: Sequence[str] | None, allowed: Sequence[str]) -> tuple[str, ...]:
    requested = [part.strip() for value in (values or allowed) for part in value.split(",") if part.strip()]
    if not requested or len(requested) != len(set(requested)):
        raise ValueError("scenarios must be non-empty and unique")
    unknown = sorted(set(requested) - set(allowed))
    if unknown:
        raise ValueError(f"unknown network training scenarios: {unknown}")
    return tuple(requested)


def _weights(value: str | None, defaults: dict[str, float]) -> dict[str, float]:
    if value is None:
        return dict(defaults)
    result: dict[str, float] = {}
    for assignment in value.split(","):
        if "=" not in assignment:
            raise ValueError("reward weights must use queue=value,wait=value,throughput=value")
        key, raw = assignment.split("=", 1)
        key = key.strip()
        number = float(raw)
        if key not in defaults or key in result or not math.isfinite(number):
            raise ValueError(f"unknown, repeated, or non-finite reward weight: {key!r}")
        result[key] = number
    if set(result) != set(defaults):
        raise ValueError(f"reward weights must define exactly {sorted(defaults)}")
    return result


def _preflight(scenarios: Sequence[str], config: dict[str, Any]) -> None:
    builder = ScenarioBuilder(ROOT, family="network")
    pool = config["demand"]["net_train_pool"]
    seeds = range(int(pool["seed_min"]), int(pool["seed_min"]) + int(pool["seeds_per_scenario"]))
    for seed in seeds:
        for scenario in scenarios:
            route = builder.get_cached_routes(scenario, seed)
            if not route.is_file():
                raise FileNotFoundError(f"training route cache missing: {scenario}/{seed}: {route}")
    for scenario, seed in config["rl_net"]["validation_pairs"]:
        route = builder.get_cached_routes(scenario, int(seed))
        if not route.is_file():
            raise FileNotFoundError(f"validation route cache missing: {scenario}/{seed}: {route}")


class TrainingMetricsCallback(BaseCallback):
    """Persist completed episode rewards, throughput and wall-clock progress."""

    def __init__(self, path: Path, target: int, started: float, interval_s: float, meta_path: Path, metadata: dict[str, Any], initial: int = 0) -> None:
        super().__init__(verbose=0)
        self.path = path
        self.target = target
        self.started = started
        self.previously_spent = float(metadata.get("training_wall_clock_s", 0.0))
        self.initial = initial
        self.interval_s = interval_s
        self.meta_path = meta_path
        self.metadata = metadata
        self.fields = (
            "episode", "timesteps", "simulated_seconds", "mean_junction_return",
            "scenario", "seed", "censored_travel_time", "completion_rate",
            "rejected_action_rate_by_tls", "rejection_reasons_by_tls",
        )
        self.episode = 0
        self.totals = np.zeros(12, dtype=np.float64)
        self.calls = 0
        self.episode_decisions = 0

    def _on_training_start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            with self.path.open(encoding="utf-8", newline="") as stream:
                self.episode = sum(1 for _ in csv.DictReader(stream))
        else:
            with self.path.open("w", encoding="utf-8", newline="") as stream:
                csv.DictWriter(stream, fieldnames=self.fields).writeheader()

    def _on_step(self) -> bool:
        self.calls += 1
        rewards = np.asarray(self.locals["rewards"], dtype=np.float64)
        dones = self.locals["dones"]
        infos = self.locals["infos"]
        self.totals += rewards
        self.episode_decisions += 1
        if any(dones):
            self.episode += 1
            info = infos[0]
            tls_rejections = {
                str(item.get("tls_id", index)): int(item.get("n_illegal_actions_episode", 0))
                for index, item in enumerate(infos)
            }
            reason_counts: dict[str, dict[str, int]] = {
                str(item.get("tls_id", index)): {
                    str(reason): int(count)
                    for reason, count in item.get("rejection_reason_counts", {}).items()
                }
                for index, item in enumerate(infos)
            }
            row = {
                "episode": self.episode,
                "timesteps": self.num_timesteps,
                "simulated_seconds": info.get("sim_time", 0.0),
                "mean_junction_return": float(np.mean(self.totals)),
                "scenario": info.get("scenario", ""),
                "seed": info.get("seed", ""),
                "censored_travel_time": info.get("network_avg_travel_time_censored", ""),
                "completion_rate": info.get("network_completion_rate", ""),
                "rejected_action_rate_by_tls": json.dumps(
                    {
                        tls_id: count / max(1, self.episode_decisions)
                        for tls_id, count in tls_rejections.items()
                    }, sort_keys=True,
                ),
                "rejection_reasons_by_tls": json.dumps(reason_counts, sort_keys=True),
            }
            with self.path.open("a", encoding="utf-8", newline="") as stream:
                csv.DictWriter(stream, fieldnames=self.fields).writerow(row)
            self.totals.fill(0.0)
            self.episode_decisions = 0
        if self.num_timesteps % 12000 < 12:
            elapsed = max(1e-6, _active_monotonic() - self.started)
            trained = max(0, self.num_timesteps - self.initial)
            rate = trained / elapsed
            self.metadata.update(
                training_wall_clock_s=self.previously_spent + elapsed,
                num_timesteps=int(self.num_timesteps),
            )
            _atomic_json(self.meta_path, self.metadata)
            print(
                f"[network-ppo] timesteps={self.num_timesteps}/{self.target} "
                f"vector_steps={self.num_timesteps // 12} steps_per_hour={rate * 3600:.0f} "
                f"sim_s_per_real_s={self.calls * self.interval_s / elapsed:.2f} "
                f"simulated_hours={self.calls * self.interval_s / 3600:.2f}",
                flush=True,
            )
        return True


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timesteps", type=int, required=True)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--scenarios", nargs="+", help="network scenario names or comma-separated names")
    parser.add_argument("--reward-weights", help="queue=value,wait=value,throughput=value")
    parser.add_argument("--network-term", type=float)
    parser.add_argument("--rejected-action-penalty", type=float)
    parser.add_argument(
        "--max-cumulative-train-seconds", type=float,
        help="run-specific hard cumulative training-time cap; does not edit config/stms.yaml",
    )
    parser.add_argument("--early-stop-patience", type=int, help="stop after this many validation checks without a new best")
    parser.add_argument(
        "--disable-validation-early-stop", action="store_true",
        help="disable Stage 3 validation patience for an explicitly bounded diagnostic run",
    )
    parser.add_argument(
        "--stage3-cost-reductions",
        action="store_true",
        help="resume with fewer scenarios, 1800 s episodes, 10 s decisions, and validation early stop",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def train(args: argparse.Namespace) -> int:
    if args.timesteps <= 0 or not 1000 <= args.seed <= 1999:
        raise ValueError("timesteps must be positive and training seed must be in 1000..1999")
    base_config = deepcopy(load_config())
    pool = base_config["demand"]["net_train_pool"]
    if args.stage3_cost_reductions:
        config, scenarios = _stage3_training_config(base_config, args.scenarios)
        if args.early_stop_patience is None and not args.disable_validation_early_stop:
            args.early_stop_patience = 2
    else:
        config = deepcopy(base_config)
        scenarios = _scenarios(args.scenarios, pool["scenarios"])
    validation_config = deepcopy(base_config)
    weights = _weights(args.reward_weights, config["rl_net"]["reward_weights"])
    network_term = config["rl_net"]["network_term_weight"] if args.network_term is None else args.network_term
    if not math.isfinite(network_term) or network_term < 0:
        raise ValueError("network-term must be finite and non-negative")
    rejected_action_penalty = (
        float(config["rl_net"].get("rejected_action_penalty", 0.0))
        if args.rejected_action_penalty is None else args.rejected_action_penalty
    )
    if not math.isfinite(rejected_action_penalty) or rejected_action_penalty < 0:
        raise ValueError("rejected-action-penalty must be finite and non-negative")
    out_dir = args.out if args.out.is_absolute() else ROOT / args.out
    out_dir = out_dir.resolve()
    if args.resume:
        if not (out_dir / "config.json").is_file():
            raise FileNotFoundError(f"cannot resume without {out_dir / 'config.json'}")
        metadata = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
        if (
            not _resume_pool_compatible(
                metadata.get("scenarios", []), scenarios, stage3=args.stage3_cost_reductions
            )
            or metadata.get("reward_weights") != weights
            or metadata.get("network_term_weight") != network_term
            or metadata.get("seed") != args.seed
            or metadata.get("intended_tls_hash") != config["network"]["tls_list_hash"]
            or metadata.get("slot_order") != config["network"]["controlled_tls"]
            or metadata.get("validation_pairs")
            != [{"scenario": str(pair[0]), "seed": int(pair[1])} for pair in config["rl_net"]["validation_pairs"]]
            or metadata.get("hyperparameters", {}).get("n_steps") != 512
            or metadata.get("hyperparameters", {}).get("batch_size") != 128
            or metadata.get("hyperparameters", {}).get("learning_rate") != float(config["rl"]["ppo"]["learning_rate"])
            or metadata.get("hyperparameters", {}).get("gamma") != float(config["rl"]["ppo"]["gamma"])
            or metadata.get("hyperparameters", {}).get("ent_coef") != float(config["rl"]["ppo"]["ent_coef"])
        ):
            raise ValueError("resume settings differ from the recorded scenarios, rewards, seed, or TLS set")
        checkpoints = list((out_dir / "checkpoints").glob("ppo_*_steps.zip"))
        if not checkpoints:
            raise FileNotFoundError(f"no resumable checkpoints under {out_dir / 'checkpoints'}")
        checkpoint = max(checkpoints, key=lambda p: int(re.search(r"ppo_(\d+)_steps\.zip$", p.name).group(1)))
        already_spent = float(metadata.get("training_wall_clock_s", 0))
    else:
        if out_dir.exists():
            raise FileExistsError(f"output already exists; use --resume or a new path: {out_dir}")
        metadata = {}
        checkpoint = None
        already_spent = 0.0
    _preflight(scenarios, config)
    config["rl_net"]["reward_weights"] = weights
    config["rl_net"]["network_term_weight"] = network_term
    config["rl_net"]["rejected_action_penalty"] = rejected_action_penalty
    validation_config["rl_net"]["reward_weights"] = weights
    validation_config["rl_net"]["network_term_weight"] = network_term
    validation_config["rl_net"]["rejected_action_penalty"] = rejected_action_penalty
    if not args.resume:
        out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "monitor").mkdir(parents=True, exist_ok=True)
    train_env = VecMonitor(NetworkVecEnv(scenarios, range(pool["seed_min"], pool["seed_min"] + pool["seeds_per_scenario"]), config), filename=str(out_dir / "monitor" / "training.csv"))
    val_pairs = [(str(pair[0]), int(pair[1])) for pair in config["rl_net"]["validation_pairs"]]
    val_env = VecMonitor(NetworkVecEnv([item[0] for item in val_pairs], [item[1] for item in val_pairs], validation_config))
    rl_config = config["rl"]["ppo"]
    n_envs = train_env.num_envs
    n_steps = 512
    batch_size = 128
    if (n_steps * n_envs) % batch_size:
        raise ValueError("n_steps × number of TLS slots must be divisible by batch_size")
    run_started = _active_monotonic()
    configured_cap_seconds = float(config["rl_net"]["max_train_hours"]) * 3600
    cumulative_cap_seconds = _resolve_cumulative_training_cap(
        configured_cap_seconds, args.max_cumulative_train_seconds, already_spent
    )
    try:
        if args.resume:
            model = _load_resume_model(
                checkpoint,
                train_env,
                device=config["rl_net"].get("device", "cpu"),
            )
            start_steps = int(model.num_timesteps)
        else:
            model = _ExactTargetPPO(
                "MlpPolicy", train_env, learning_rate=float(rl_config["learning_rate"]),
                n_steps=n_steps, batch_size=batch_size, gamma=float(rl_config["gamma"]),
                ent_coef=float(rl_config["ent_coef"]), seed=args.seed,
                device=config["rl_net"].get("device", "cpu"), verbose=1,
                tensorboard_log=str(out_dir / "tensorboard"),
            )
            start_steps = 0
        if args.timesteps <= start_steps:
            raise ValueError(
                f"model already has {start_steps} steps; requested target is {args.timesteps}"
            )
        if (args.timesteps - start_steps) % n_envs:
            raise ValueError(
                f"additional timestep target {args.timesteps - start_steps} is not divisible by {n_envs} environments"
            )
        model.exact_target_timesteps = args.timesteps
        stage_history = list(metadata.get("training_stage_history", []))
        if args.stage3_cost_reductions and args.resume and not stage_history:
            stage_history.append({
                "stage": "stage2",
                "scenarios": list(metadata["scenarios"]),
                "episode_s": int(base_config["rl_net"]["episode_s"]),
                "decision_interval_s": int(base_config["rl_net"]["decision_interval_s"]),
                "num_timesteps_before_stage3": start_steps,
                "cumulative_wall_clock_s_before_stage3": already_spent,
            })
        if args.stage3_cost_reductions:
            stage_history.append({
                "stage": "stage3",
                "started_utc": _utc_now(),
                "scenarios": list(scenarios),
                "episode_s": int(config["rl_net"]["episode_s"]),
                "decision_interval_s": int(config["rl_net"]["decision_interval_s"]),
                "early_stop_patience": args.early_stop_patience,
            })
        meta: dict[str, Any] = {
            "schema_version": 1, "created_utc": metadata.get("created_utc", _utc_now()),
            "run_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
            "command": sys.argv, "scenarios": list(scenarios), "seed": args.seed,
            "training_seeds": list(range(pool["seed_min"], pool["seed_min"] + pool["seeds_per_scenario"])),
            "validation_pairs": [{"scenario": s, "seed": seed} for s, seed in val_pairs],
            "reward_weights": weights, "network_term_weight": network_term,
            "intended_tls_hash": config["network"]["tls_list_hash"],
            "slot_order": list(config["network"]["controlled_tls"]),
            "hyperparameters": {"learning_rate": float(rl_config["learning_rate"]), "n_steps": n_steps, "batch_size": batch_size, "gamma": float(rl_config["gamma"]), "ent_coef": float(rl_config["ent_coef"]), "device": config["rl_net"].get("device", "cpu")},
            "git_commit": _git_commit(), "library_versions": _library_versions(),
            "training_wall_clock_s": already_spent, "target_timesteps": args.timesteps,
            "max_cumulative_train_seconds": cumulative_cap_seconds,
            "starting_timesteps": start_steps, "num_timesteps": start_steps, "out_dir": str(out_dir),
            "rejected_action_penalty": rejected_action_penalty,
            "training_schedule": {
                "stage": "stage3" if args.stage3_cost_reductions else "standard",
                "scenarios": list(scenarios),
                "episode_s": int(config["rl_net"]["episode_s"]),
                "decision_interval_s": int(config["rl_net"]["decision_interval_s"]),
                "early_stop_patience": args.early_stop_patience,
            },
            "training_stage_history": stage_history,
            "selected_validation_mean_censored_time": metadata.get("selected_validation_mean_censored_time"),
            "selected_validation_timestep": metadata.get("selected_validation_timestep"),
            "selected_validation_checkpoint": metadata.get("selected_validation_checkpoint"),
            "state": "running",
        }
        _atomic_json(out_dir / "config.json", meta)
        checkpoint_callback = CheckpointCallback(save_freq=max(1, 5000 // n_envs), save_path=str(out_dir / "checkpoints"), name_prefix="ppo", save_replay_buffer=False, save_vecnormalize=False)
        metrics_callback = TrainingMetricsCallback(
            out_dir / "training_log.csv", args.timesteps, run_started,
            float(config["rl_net"]["decision_interval_s"]), out_dir / "config.json", meta, start_steps,
        )
        def save_selected_validation(score: float, timestep: int) -> None:
            meta["selected_validation_mean_censored_time"] = score
            meta["selected_validation_timestep"] = timestep
            meta["selected_validation_checkpoint"] = "evaluations/best_model.zip"
            _atomic_json(out_dir / "config.json", meta)

        validation_callback = NetworkValidationCallback(
            val_env, val_pairs, int(config["rl_net"]["validation_every_timesteps"]),
            out_dir / "evaluations", early_stop_patience=args.early_stop_patience,
            on_best=save_selected_validation,
        )
        budget_callback = _BudgetCallback(
            run_started,
            cumulative_cap_seconds - already_spent,
            reserve_s=300.0,
        )
        model.learn(
            total_timesteps=args.timesteps - start_steps,
            callback=CallbackList([
                checkpoint_callback, metrics_callback, budget_callback,
                validation_callback,
            ]),
            reset_num_timesteps=not args.resume,
            tb_log_name="ppo_network", progress_bar=False,
        )
        if validation_callback.best_timestep is None:
            raise RuntimeError("training ended without a best-by-validation checkpoint")
        best_model = out_dir / "evaluations" / "best_model.zip"
        if not best_model.is_file():
            raise FileNotFoundError(f"selected validation model was not saved: {best_model}")
        shutil.copy2(best_model, out_dir / "model.zip")
        elapsed = _active_monotonic() - run_started
        reached_target = int(model.num_timesteps) == args.timesteps
        if int(model.num_timesteps) > args.timesteps:
            raise RuntimeError("network PPO exceeded its authorized exact timestep target")
        meta.update(
            training_wall_clock_s=already_spent + elapsed,
            num_timesteps=int(model.num_timesteps),
            target_reached=reached_target,
            stopped_by_budget=not reached_target and budget_callback.stopped,
            budget_stop_reserve_s=budget_callback.reserve_s,
            max_cumulative_train_seconds=cumulative_cap_seconds,
            rejected_action_penalty=rejected_action_penalty,
            selected_validation_mean_censored_time=validation_callback.best_censored_time,
            selected_validation_timestep=validation_callback.best_timestep,
            final_model=str(out_dir / "model.zip"),
        )
        if reached_target:
            meta["completed_utc"] = _utc_now()
            meta["state"] = "complete"
        else:
            meta["state"] = "stopped_before_target"
        _atomic_json(out_dir / "config.json", meta)
        status = "complete" if reached_target else "stopped before target"
        print(f"network PPO {status}: timesteps={model.num_timesteps} vector_steps={model.num_timesteps // n_envs} simulated_hours={metrics_callback.calls * metrics_callback.interval_s / 3600:.3f} wall_clock_s={elapsed:.1f} steps_per_hour={(model.num_timesteps-start_steps)/max(elapsed,1e-6)*3600:.0f} best_censored_travel_time={validation_callback.best_censored_time:.3f}", flush=True)
        return 0
    finally:
        val_env.close()
        train_env.close()


class _BudgetCallback(BaseCallback):
    def __init__(self, started: float, budget: float, reserve_s: float = 300.0) -> None:
        super().__init__(verbose=0)
        if budget < 0 or reserve_s < 0:
            raise ValueError("training budget and finalization reserve must be non-negative")
        self.started = started
        self.budget = budget
        self.reserve_s = min(reserve_s, budget)
        self.stop_after_s = budget - self.reserve_s
        self.stopped = False

    def _on_step(self) -> bool:
        if _active_monotonic() - self.started >= self.stop_after_s:
            self.stopped = True
            self.model.stop_training = True
            print(
                f"[network-ppo] stopping at budget reserve; reserve_s={self.reserve_s:.0f}",
                flush=True,
            )
            return False
        return True


def main(argv: Sequence[str] | None = None) -> int:
    return train(_parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
