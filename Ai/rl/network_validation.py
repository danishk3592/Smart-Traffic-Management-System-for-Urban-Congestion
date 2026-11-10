"""Deterministic whole-network validation for shared-policy PPO."""

from __future__ import annotations

import csv
import math
from collections.abc import Callable
from pathlib import Path
from statistics import fmean
from typing import Any

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback


class NetworkValidationCallback(BaseCallback):
    """Select and save the policy with lowest censored network travel time."""

    def __init__(
        self,
        eval_env: Any,
        validation_pairs: list[tuple[str, int]],
        every_timesteps: int,
        output_dir: Path,
        early_stop_patience: int | None = None,
        on_best: Callable[[float, int], None] | None = None,
    ) -> None:
        super().__init__(verbose=0)
        if not validation_pairs or every_timesteps <= 0:
            raise ValueError("validation pairs and a positive validation interval are required")
        if any(seed >= 5000 or seed < 3000 for _, seed in validation_pairs):
            raise ValueError("network PPO validation must use reserved 3000-series seeds")
        if early_stop_patience is not None and early_stop_patience <= 0:
            raise ValueError("early-stop patience must be positive when enabled")
        self.eval_env = eval_env
        self.validation_pairs = tuple((str(scenario), int(seed)) for scenario, seed in validation_pairs)
        self.every_timesteps = int(every_timesteps)
        self.early_stop_patience = early_stop_patience
        self.on_best = on_best
        self.evaluations_without_improvement = 0
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.best_censored_time = math.inf
        self.best_timestep: int | None = None
        self.next_timestep = self.every_timesteps
        self.csv_path = self.output_dir / "validation_log.csv"
        self.fields = ("timesteps", "scenario", "seed", "avg_travel_time_censored", "completion_rate", "mean_junction_return")
        if self.csv_path.is_file():
            with self.csv_path.open(newline="", encoding="utf-8") as stream:
                old_rows = list(csv.DictReader(stream))
            by_timestep: dict[int, list[float]] = {}
            for row in old_rows:
                by_timestep.setdefault(int(row["timesteps"]), []).append(float(row["avg_travel_time_censored"]))
            if by_timestep:
                self.best_timestep = min(by_timestep, key=lambda step: fmean(by_timestep[step]))
                self.best_censored_time = fmean(by_timestep[self.best_timestep])
                if not (self.output_dir / "best_model.zip").is_file():
                    raise FileNotFoundError("validation history exists without its selected best checkpoint")
                self.next_timestep = (max(by_timestep) // self.every_timesteps + 1) * self.every_timesteps
        else:
            with self.csv_path.open("w", newline="", encoding="utf-8") as stream:
                csv.DictWriter(stream, fieldnames=self.fields).writeheader()

    def evaluate(self, model: Any, timestep: int) -> dict[str, float]:
        """Run one fixed pair at a time and return aggregate validation measures."""
        records: list[dict[str, float]] = []
        for scenario, seed in self.validation_pairs:
            options = {"scenario": scenario, "seed": seed}
            self.eval_env.set_options([options] * self.eval_env.num_envs)
            observations = self.eval_env.reset()
            returns = np.zeros(self.eval_env.num_envs, dtype=np.float64)
            while True:
                actions, _ = model.predict(observations, deterministic=True)
                observations, rewards, dones, infos = self.eval_env.step(actions)
                returns += np.asarray(rewards, dtype=np.float64)
                if bool(np.asarray(dones).all()):
                    break
            info = infos[0]
            value = float(info["network_avg_travel_time_censored"])
            completion = float(info["network_completion_rate"])
            if not math.isfinite(value) or value < 0 or not math.isfinite(completion):
                raise ValueError(f"invalid network validation metrics for {scenario}/{seed}")
            records.append({
                "scenario": scenario,
                "seed": seed,
                "avg_travel_time_censored": value,
                "completion_rate": completion,
                "mean_junction_return": float(np.mean(returns)),
            })
        aggregate = {
            "avg_travel_time_censored": fmean(row["avg_travel_time_censored"] for row in records),
            "completion_rate": fmean(row["completion_rate"] for row in records),
            "mean_junction_return": fmean(row["mean_junction_return"] for row in records),
        }
        with self.csv_path.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields)
            for row in records:
                writer.writerow({"timesteps": timestep, **row})
        if aggregate["avg_travel_time_censored"] < self.best_censored_time:
            self.best_censored_time = aggregate["avg_travel_time_censored"]
            self.best_timestep = int(timestep)
            model.save(str(self.output_dir / "best_model.zip"))
            if self.on_best is not None:
                self.on_best(self.best_censored_time, self.best_timestep)
        return aggregate

    def _on_step(self) -> bool:
        if getattr(self.model, "stop_training", False):
            return False
        if self.num_timesteps >= self.next_timestep:
            previous_best = self.best_censored_time
            result = self.evaluate(self.model, self.num_timesteps)
            print(
                f"[network-validation] timesteps={self.num_timesteps} "
                f"censored_travel_time={result['avg_travel_time_censored']:.3f} "
                f"completion={result['completion_rate']:.4f} "
                f"mean_junction_return={result['mean_junction_return']:.4f}",
                flush=True,
            )
            if result["avg_travel_time_censored"] < previous_best:
                self.evaluations_without_improvement = 0
            else:
                self.evaluations_without_improvement += 1
            if self.early_stop_patience is not None and self.evaluations_without_improvement >= self.early_stop_patience:
                print("[network-validation] early stopping after validation plateau", flush=True)
                self.model.stop_training = True
            while self.next_timestep <= self.num_timesteps:
                self.next_timestep += self.every_timesteps
        return True

    def _on_training_end(self) -> None:
        self.eval_env.close()
