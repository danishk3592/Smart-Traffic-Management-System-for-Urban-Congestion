from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from Ai.rl.network_validation import NetworkValidationCallback
from Ai.rl.network_vec_env import _censored_trip_metrics


class _EvalEnv:
    num_envs = 2

    def __init__(self) -> None:
        self.options = None
        self.closed = False
        self.evaluation = 0

    def set_options(self, options):
        self.options = options
        if options[0]["seed"] == 3000:
            self.evaluation += 1

    def reset(self):
        return np.zeros((2, 1), dtype=np.float32)

    def step(self, actions):
        seed = self.options[0]["seed"]
        travel_time = (
            {3000: 40.0, 3001: 50.0, 3002: 45.0}
            if self.evaluation == 1
            else {3000: 30.0, 3001: 20.0, 3002: 25.0}
        )[seed]
        infos = [
            {"network_avg_travel_time_censored": travel_time, "network_completion_rate": 0.9},
            {},
        ]
        return np.zeros((2, 1), dtype=np.float32), np.asarray([100.0, 0.0]), np.asarray([True, True]), infos

    def close(self):
        self.closed = True


class _Model:
    def __init__(self) -> None:
        self.saved: list[str] = []

    def predict(self, observations, deterministic=False):
        assert deterministic is True
        return np.zeros(2, dtype=np.int64), None

    def save(self, path: str) -> None:
        self.saved.append(path)
        Path(path).write_text("checkpoint", encoding="utf-8")


def test_network_validation_keeps_lowest_censored_time_not_highest_return(tmp_path: Path) -> None:
    env = _EvalEnv()
    model = _Model()
    best_updates: list[tuple[float, int]] = []
    callback = NetworkValidationCallback(
        env,
        [("net_medium", 3000), ("net_heavy", 3001), ("net_rush_hour", 3002)],
        20_000,
        tmp_path,
        on_best=lambda score, timestep: best_updates.append((score, timestep)),
    )

    callback.evaluate(model, 20_004)
    result = callback.evaluate(model, 40_008)

    assert result["avg_travel_time_censored"] == 25.0
    assert result["completion_rate"] == 0.9
    assert result["mean_junction_return"] == 50.0
    assert callback.best_censored_time == 25.0
    assert callback.best_timestep == 40_008
    assert best_updates == [(45.0, 20_004), (25.0, 40_008)]
    assert model.saved == [str(tmp_path / "best_model.zip"), str(tmp_path / "best_model.zip")]
    with (tmp_path / "validation_log.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6


def test_network_validation_skips_episode_after_budget_stop(tmp_path: Path) -> None:
    env = _EvalEnv()
    callback = NetworkValidationCallback(
        env,
        [("net_medium", 3000), ("net_heavy", 3001), ("net_rush_hour", 3002)],
        20_000,
        tmp_path,
    )
    callback.model = SimpleNamespace(stop_training=True)

    assert not callback._on_step()
    assert env.evaluation == 0
    assert not (tmp_path / "best_model.zip").exists()


def test_network_validation_accepts_new_model_before_stop_flag_is_created(tmp_path: Path) -> None:
    env = _EvalEnv()
    callback = NetworkValidationCallback(
        env,
        [("net_medium", 3000), ("net_heavy", 3001), ("net_rush_hour", 3002)],
        20_000,
        tmp_path,
    )
    callback.model = SimpleNamespace(num_timesteps=0)

    assert callback._on_step()
    assert env.evaluation == 0


def test_censored_network_metric_excludes_unfinished_tripinfo_arrivals() -> None:
    metrics = _censored_trip_metrics(
        {"finished": 0.0, "unfinished": 10.0},
        '<tripinfos><tripinfo id="finished" depart="10" departDelay="10" duration="20" arrival="30" />'
        '<tripinfo id="unfinished" depart="20" departDelay="10" duration="80" arrival="-1" /></tripinfos>',
        100.0,
    )

    assert metrics["network_avg_travel_time_censored"] == 60.0
    assert metrics["network_completion_rate"] == 0.5
