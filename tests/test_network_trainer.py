from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import gymnasium as gym
import pytest
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

import Ai.rl.train_ppo_network as trainer
from Ai.rl.train_ppo_network import (
    _BudgetCallback,
    _ExactTargetPPO,
    _load_resume_model,
    _resolve_cumulative_training_cap,
    _resume_pool_compatible,
    _rollout_steps_for_remaining,
    _stage3_training_config,
)


@pytest.fixture
def training_config() -> dict:
    return {
        "demand": {
            "net_train_pool": {
                "scenarios": [
                    "net_balanced",
                    "net_low",
                    "net_medium",
                    "net_heavy",
                    "net_rush_hour",
                ]
            }
        },
        "rl_net": {"episode_s": 3600, "decision_interval_s": 5},
    }


def test_stage3_uses_three_primary_scenarios_and_shorter_schedule(training_config: dict) -> None:
    original = deepcopy(training_config)

    stage_config, scenarios = _stage3_training_config(training_config, None)

    assert scenarios == ("net_medium", "net_heavy", "net_rush_hour")
    assert stage_config["rl_net"]["episode_s"] == 1800
    assert stage_config["rl_net"]["decision_interval_s"] == 10
    assert training_config == original


def test_stage3_rejects_a_non_reduced_scenario_pool(training_config: dict) -> None:
    with pytest.raises(ValueError, match="strict subset"):
        _stage3_training_config(
            training_config,
            training_config["demand"]["net_train_pool"]["scenarios"],
        )


def test_resume_only_allows_explicit_strict_stage3_pool_reduction() -> None:
    previous = ("net_balanced", "net_low", "net_medium", "net_heavy", "net_rush_hour")
    reduced = ("net_medium", "net_heavy", "net_rush_hour")

    assert _resume_pool_compatible(previous, reduced, stage3=True)
    assert not _resume_pool_compatible(previous, reduced, stage3=False)
    assert not _resume_pool_compatible(reduced, previous, stage3=True)


def test_budget_callback_stops_before_finalization_reserve(monkeypatch: pytest.MonkeyPatch) -> None:
    elapsed = 699.0
    monkeypatch.setattr(trainer, "_active_monotonic", lambda: elapsed)
    callback = _BudgetCallback(started=0.0, budget=1000.0, reserve_s=300.0)
    callback.model = SimpleNamespace(stop_training=False)

    assert callback._on_step()
    elapsed = 700.0
    assert not callback._on_step()
    assert callback.stopped
    assert callback.model.stop_training
    assert callback.stop_after_s == 700.0


def test_resume_clears_stop_flag_persisted_in_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    model = SimpleNamespace(stop_training=True)
    monkeypatch.setattr(trainer.PPO, "load", lambda *_args, **_kwargs: model)

    resumed = _load_resume_model(Path("checkpoint.zip"), object(), "cpu")

    assert resumed is model
    assert resumed.stop_training is False


def test_run_specific_cap_override_does_not_change_configured_cap() -> None:
    configured_cap = 40_000.0

    resolved = _resolve_cumulative_training_cap(configured_cap, 43_000.0, 36_841.7217)

    assert resolved == 43_000.0
    assert configured_cap == 40_000.0


def test_run_specific_cap_rejects_exhausted_or_invalid_limits() -> None:
    with pytest.raises(ValueError, match="already exhausted"):
        _resolve_cumulative_training_cap(40_000.0, 43_000.0, 43_000.0)
    with pytest.raises(ValueError, match="finite and valid"):
        _resolve_cumulative_training_cap(40_000.0, float("inf"), 10.0)


def test_exact_rollout_budget_uses_short_final_rollout_without_overshoot() -> None:
    assert _rollout_steps_for_remaining(99_996, n_envs=12, max_rollout_steps=512) == 512
    assert _rollout_steps_for_remaining(1_692, n_envs=12, max_rollout_steps=512) == 141
    with pytest.raises(ValueError, match="divisible"):
        _rollout_steps_for_remaining(100_000, n_envs=12, max_rollout_steps=512)


def test_exact_timestep_target_completes_short_final_ppo_update(tmp_path: Path) -> None:
    env = DummyVecEnv([lambda: gym.make("CartPole-v1") for _ in range(12)])
    try:
        model = _ExactTargetPPO(
            "MlpPolicy", env, n_steps=512, batch_size=128, n_epochs=1,
            seed=17, verbose=0, device="cpu",
        )
        model.exact_target_timesteps = 852

        model.learn(total_timesteps=852, progress_bar=False)

        assert model.num_timesteps == 852
        assert model.n_steps == 512
        assert model.rollout_buffer.buffer_size == 71
        assert model._n_updates == 1
        archive = tmp_path / "exact_target.zip"
        model.save(archive)
        reloaded = PPO.load(archive, env=env, device="cpu")
        assert reloaded.num_timesteps == 852
    finally:
        env.close()
