"""SUMO integration gate for the single-junction PPO environment."""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from stable_baselines3.common.env_checker import check_env

from Ai.common.config import load_config
from Ai.controllers.safety import Accepted
from Ai.rl.traffic_env import TrafficEnvironment

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SEED = 1000


def _make_env(scenario: str = "medium", *, episode_s: int = 900) -> TrafficEnvironment:
    """Build an environment using the prepared seed-1000 cache only."""
    config = copy.deepcopy(load_config())
    config["rl"]["episode_s"] = episode_s
    return TrafficEnvironment([scenario], [TRAIN_SEED], config)


def _assert_observation(env: TrafficEnvironment, observation: np.ndarray) -> None:
    assert observation.shape == env.observation_space.shape
    assert observation.dtype == np.float32
    assert env.observation_space.contains(observation)
    assert np.isfinite(observation).all()


def _record_safety(env: TrafficEnvironment) -> list[int]:
    """Assert verified phases, minimum/maximum green and yellow between greens."""
    assert env.client is not None and env.safety is not None
    layer = env.safety
    light = env.client.connection.trafficlight
    green = set(layer.green_phases)
    yellow = set(layer.yellow_after.values())
    allowed = set(layer._allowed_phases)
    tls_id = layer.tls_id
    previous = int(light.getPhase(tls_id))
    green_started = env.client.sim_time - float(light.getSpentDuration(tls_id))
    clearance_seen = previous in yellow or previous in layer.all_red_phases
    history = [previous]
    original_tick = layer.tick

    def checked_tick() -> Accepted:
        nonlocal previous, green_started, clearance_seen
        result = original_tick()
        phase = int(light.getPhase(tls_id))
        assert phase in allowed
        assert isinstance(result, Accepted)
        if phase in yellow or phase in layer.all_red_phases:
            clearance_seen = True
        if phase != previous:
            if previous in green:
                duration = env.client.sim_time - green_started
                assert duration >= layer.min_green - 1e-6
                if phase in green:
                    assert clearance_seen, "green-to-green transition skipped yellow/all-red"
            if phase in green:
                green_started = env.client.sim_time - float(light.getSpentDuration(tls_id))
                clearance_seen = False
            previous = phase
        if phase in green:
            spent = float(light.getSpentDuration(tls_id))
            assert spent <= layer.max_green + 1e-6
        history.append(phase)
        return result

    layer.tick = checked_tick
    return history


@pytest.mark.sumo
def test_gymnasium_check_env_passes() -> None:
    env = _make_env(episode_s=120)
    env.action_space.seed(731)
    try:
        check_env(env, skip_render_check=True)
    finally:
        env.close()


@pytest.mark.sumo
def test_three_random_policy_episodes_preserve_signal_safety() -> None:
    for episode in range(3):
        env = _make_env(episode_s=300)
        try:
            observation, _ = env.reset(seed=TRAIN_SEED)
            _assert_observation(env, observation)
            history = _record_safety(env)
            rng = np.random.default_rng(731 + episode)
            done = False
            while not done:
                action = int(rng.integers(0, 4))
                observation, reward, terminated, truncated, info = env.step(action)
                _assert_observation(env, observation)
                assert np.isfinite(reward)
                assert info["action_taken"] in range(4)
                done = terminated or truncated
            assert truncated or terminated
            assert env.elapsed >= 300
            assert len(history) > 1
        finally:
            env.close()


def _policy_return(*, switch_when_queue_high: bool) -> float:
    env = _make_env("heavy", episode_s=900)
    try:
        observation, _ = env.reset(seed=TRAIN_SEED)
        _assert_observation(env, observation)
        total_reward = 0.0
        done = False
        while not done:
            if switch_when_queue_high:
                assert env.state is not None and env.safety is not None
                queue_total = sum(approach.halting or 0 for approach in env.state.approaches)
                action = int(
                    queue_total >= 6
                    and env.safety._current_phase() in env.safety.green_phases
                    and env.safety.elapsed_green >= env.safety.min_green
                )
            else:
                action = 0
            observation, reward, terminated, truncated, _ = env.step(action)
            _assert_observation(env, observation)
            total_reward += reward
            done = terminated or truncated
        return total_reward
    finally:
        env.close()


@pytest.mark.sumo
def test_switch_when_queue_high_beats_always_keep_on_same_heavy_seed() -> None:
    keep_reward = _policy_return(switch_when_queue_high=False)
    switch_reward = _policy_return(switch_when_queue_high=True)
    assert keep_reward < switch_reward, (
        f"always-keep reward {keep_reward:.6f} was not below "
        f"queue-triggered switch reward {switch_reward:.6f}"
    )


@pytest.mark.sumo
def test_same_seed_reproduces_first_50_observations_and_rewards() -> None:
    actions = np.random.default_rng(90210).integers(0, 4, size=50)
    episodes: list[tuple[list[np.ndarray], list[float]]] = []
    for _ in range(2):
        env = _make_env("medium", episode_s=900)
        observations: list[np.ndarray] = []
        rewards: list[float] = []
        try:
            observation, _ = env.reset(seed=TRAIN_SEED)
            observations.append(observation.copy())
            for action in actions:
                observation, reward, terminated, truncated, _ = env.step(int(action))
                observations.append(observation.copy())
                rewards.append(reward)
                if terminated or truncated:
                    break
            assert len(rewards) == 50
        finally:
            env.close()
        episodes.append((observations, rewards))

    assert len(episodes[0][0]) == len(episodes[1][0]) == 51
    for first, second in zip(episodes[0][0], episodes[1][0], strict=True):
        np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(episodes[0][1], episodes[1][1])


@pytest.mark.sumo
def test_five_reset_close_cycles_leave_no_zombie_sumo() -> None:
    env = _make_env("low", episode_s=60)
    try:
        for _ in range(5):
            observation, _ = env.reset(seed=TRAIN_SEED)
            _assert_observation(env, observation)
            env.close()
            env.close()
            assert env.client is None
    finally:
        env.close()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_zombies.py")],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=30,
    )
    assert "No running sumo or sumo-gui processes detected." in result.stdout


@pytest.mark.sumo
def test_missing_training_route_cache_fails_fast(tmp_path: Path) -> None:
    env = _make_env("low", episode_s=60)
    missing = tmp_path / "missing.routes.xml"
    try:
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr("Ai.rl.traffic_env.get_cached_routes", lambda *_: missing)
            with pytest.raises(FileNotFoundError, match="cached routes missing"):
                env.reset(seed=TRAIN_SEED)
        assert env.client is None
    finally:
        env.close()


def test_default_environment_seeds_match_prepared_training_pool() -> None:
    env = TrafficEnvironment()
    try:
        assert env.seeds == tuple(range(1000, 1020))
    finally:
        env.close()
