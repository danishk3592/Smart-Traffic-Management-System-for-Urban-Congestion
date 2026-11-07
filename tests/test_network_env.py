"""SUMO integration acceptance suite for the shared-clock network PPO environment."""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import gymnasium as gym
import numpy as np
import pytest
from stable_baselines3.common.vec_env import VecCheckNan

from Ai.common.config import load_config
from Ai.common.traffic_state import to_vector
from Ai.controllers.safety import Accepted, Rejected
from Ai.rl.network_vec_env import NetworkVecEnv

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "net_heavy"
SEED = 1000


def _make_env(
    *, episode_s: int = 300, scenario: str = SCENARIO, rejection_penalty: float = 0.0
) -> NetworkVecEnv:
    config = copy.deepcopy(load_config())
    config["rl_net"]["episode_s"] = episode_s
    config["rl_net"]["rejected_action_penalty"] = rejection_penalty
    return NetworkVecEnv([scenario], [SEED], config)


def _safety_trace(env: NetworkVecEnv) -> None:
    assert env.client is not None and env.safety is not None
    assert tuple(env.safety.layers) == env.tls_ids
    assert set(env.safety.layers).isdisjoint(env.config["network"]["excluded_tls"])
    for tls_id, layer in env.safety.layers.items():
        phase = int(env.client.connection.trafficlight.getPhase(tls_id))
        assert phase in layer._allowed_phases
        if phase in layer.green_phases:
            assert float(env.client.connection.trafficlight.getSpentDuration(tls_id)) <= layer.max_green + 1e-6


def _install_full_safety_trace(env: NetworkVecEnv) -> None:
    """Assert min-green/clearance invariants after every one-second safety tick."""
    assert env.client is not None and env.safety is not None
    for tls_id, layer in env.safety.layers.items():
        light = env.client.connection.trafficlight
        previous = int(light.getPhase(tls_id))
        green_started = env.client.sim_time - float(light.getSpentDuration(tls_id))
        clearance_seen = previous in layer.yellow_after.values() or previous in layer.all_red_phases
        original_tick = layer.tick
        track = {"previous": previous, "green_started": green_started, "clearance_seen": clearance_seen}

        def checked_tick(*, _tls=tls_id, _layer=layer, _track=track, _original=original_tick, _light=light, _env=env):
            result = _original()
            assert isinstance(result, Accepted)
            phase = int(_light.getPhase(_tls))
            now = _env.client.sim_time
            assert phase in _layer._allowed_phases
            if phase in _layer.yellow_after.values() or phase in _layer.all_red_phases:
                _track["clearance_seen"] = True
            if phase != _track["previous"]:
                if _track["previous"] in _layer.green_phases:
                    assert now - _track["green_started"] >= _layer.min_green - 1e-6
                    if phase in _layer.green_phases:
                        assert _track["clearance_seen"], f"{_tls} skipped yellow/all-red clearance"
                if phase in _layer.green_phases:
                    _track["green_started"] = now - float(_light.getSpentDuration(_tls))
                    _track["clearance_seen"] = False
                _track["previous"] = phase
            if phase in _layer.green_phases:
                assert float(_light.getSpentDuration(_tls)) <= _layer.max_green + 1e-6
            return result

        layer.tick = checked_tick


def _episode_return(env: NetworkVecEnv, switching: bool) -> float:
    env.seed(SEED)
    env.reset()
    total = 0.0
    while True:
        actions = np.zeros(env.num_envs, dtype=np.int64)
        if switching:
            assert env.state is not None
            for index, tls_id in enumerate(env.tls_ids):
                state = env.state.junctions[tls_id]
                queue = sum(int(a.halting or 0) for a in state.approaches)
                layer = env.safety.layers[tls_id]
                if queue >= 5 and layer.elapsed_green >= layer.min_green:
                    actions[index] = 1
        _obs, rewards, dones, _ = env.step(actions)
        total += float(rewards.mean())
        _safety_trace(env)
        if bool(dones.all()):
            return total


@pytest.mark.sumo
def test_vecenv_contract_shapes_nan_and_slot_order() -> None:
    env = VecCheckNan(_make_env(episode_s=100), raise_exception=True)
    try:
        observations = env.reset()
        assert observations.shape == (12, env.observation_space.shape[0])
        assert observations.dtype == np.float32
        assert env.observation_space.contains(observations[0])
        assert env.action_space.n == 4
        base = env.venv
        assert base.tls_ids == tuple(base.config["network"]["controlled_tls"])
        assert base.get_attr("tls_id") == list(base.tls_ids)
        assert base.seed(1234) == list(range(1234, 1234 + base.num_envs))
        base.set_attr("n_illegal_actions", 7, indices=0)
        assert base.get_attr("n_illegal_actions", indices=0) == [7]
        assert base.env_is_wrapped(gym.Wrapper) == [False] * base.num_envs
        assert len(base.get_images()) == base.num_envs
        assert len(base.env_method("get_attr", "tls_id", indices=0)) == 1
        for index, tls_id in enumerate(base.tls_ids):
            local = to_vector(base.state.junctions[tls_id], base.norms[tls_id])
            approach_end = len(base.norms[tls_id].approach_names) * 8
            phase_end = approach_end + len(base.norms[tls_id].green_phases)
            expected = np.zeros(base.n_obs, dtype=np.float32)
            expected[:approach_end] = local[:approach_end]
            phase_start = base.max_approaches * 8
            expected[phase_start : phase_start + len(base.norms[tls_id].green_phases)] = local[approach_end:phase_end]
            expected[phase_start + base.max_phases :] = local[phase_end:]
            assert np.array_equal(observations[index], expected), tls_id
        for _ in range(100):
            observations, rewards, dones, infos = env.step(np.zeros(env.num_envs, dtype=np.int64))
            assert observations.shape == (12, base.n_obs)
            assert observations.dtype == np.float32
            assert rewards.shape == dones.shape == (12,)
            assert rewards.dtype == np.float32
            assert dones.dtype == np.bool_
            assert len(infos) == 12
            assert all(info["tls_id"] == base.tls_ids[i] for i, info in enumerate(infos))
            assert np.isfinite(observations).all() and np.isfinite(rewards).all()
            _safety_trace(base)
    finally:
        env.close()
        env.close()


@pytest.mark.sumo
def test_two_random_episodes_keep_every_intended_tls_safe() -> None:
    env = _make_env(episode_s=300)
    rng = np.random.default_rng(731)
    try:
        env.seed(SEED)
        obs = env.reset()
        _install_full_safety_trace(env)
        excluded = env.config["network"]["excluded_tls"]
        for tls_id in excluded:
            assert isinstance(env.safety.request(tls_id, "switch"), Rejected)
        episodes = 0
        while episodes < 2:
            obs, rewards, dones, infos = env.step(rng.integers(0, 4, size=env.num_envs))
            assert obs.shape == (env.num_envs, env.n_obs)
            assert np.isfinite(rewards).all()
            _safety_trace(env)
            assert {info["tls_id"] for info in infos} == set(env.tls_ids)
            if bool(dones.all()):
                episodes += 1
                assert env.client is not None and env.client.sim_time == 0.0
                if episodes < 2:
                    _install_full_safety_trace(env)
                    for tls_id in env.config["network"]["excluded_tls"]:
                        assert isinstance(env.safety.request(tls_id, "switch"), Rejected)
    finally:
        env.close()


@pytest.mark.sumo
def test_switch_when_queue_high_beats_always_keep_on_heavy_seed() -> None:
    always = _make_env(episode_s=600)
    adaptive = _make_env(episode_s=600)
    try:
        keep_return = _episode_return(always, switching=False)
        switch_return = _episode_return(adaptive, switching=True)
        assert switch_return > keep_return, (switch_return, keep_return)
    finally:
        always.close()
        adaptive.close()


@pytest.mark.sumo
def test_same_seed_reproduces_first_fifty_observations_and_rewards() -> None:
    traces = []
    for _ in range(2):
        env = _make_env(episode_s=600)
        try:
            env.seed(SEED)
            obs = env.reset()
            trace = [(obs.copy(), None)]
            for _ in range(50):
                obs, reward, _, _ = env.step(np.zeros(env.num_envs, dtype=np.int64))
                trace.append((obs.copy(), reward.copy()))
            traces.append(trace)
        finally:
            env.close()
    for (obs_a, reward_a), (obs_b, reward_b) in zip(traces[0], traces[1], strict=True):
        assert np.array_equal(obs_a, obs_b)
        if reward_a is not None:
            assert np.array_equal(reward_a, reward_b)


@pytest.mark.sumo
def test_five_reset_close_cycles_leave_no_sumo_processes() -> None:
    for _ in range(5):
        env = _make_env(episode_s=300)
        env.reset()
        env.close()
        env.close()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_zombies.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert "no running sumo or sumo-gui processes detected" in completed.stdout.lower()


@pytest.mark.sumo
def test_missing_cached_pool_file_fails_before_starting_sumo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env = _make_env()
    missing = tmp_path / "missing.rou.xml"
    monkeypatch.setattr(env.builder, "get_cached_routes", lambda scenario, seed: missing)
    try:
        with pytest.raises(FileNotFoundError, match="cached network route file missing"):
            env.reset()
        assert env.client is None
    finally:
        env.close()


@pytest.mark.sumo
def test_padding_zeroes_unused_approaches_and_phase_slots() -> None:
    env = _make_env(episode_s=30)
    try:
        observations = env.reset()
        assert env.max_approaches == 6
        for index, tls_id in enumerate(env.tls_ids):
            approach_count = len(env.tls_configs[tls_id]["approaches"])
            assert np.all(observations[index, approach_count * 8 : env.max_approaches * 8] == 0)
            phase_count = len(env.tls_configs[tls_id]["green_phases"])
            phase_start = env.max_approaches * 8
            assert np.all(observations[index, phase_start + phase_count : phase_start + env.max_phases] == 0)
    finally:
        env.close()


@pytest.mark.sumo
def test_episode_truncation_has_terminal_observation_and_auto_resets_at_zero() -> None:
    env = _make_env(episode_s=10)
    try:
        env.reset()
        _, _, dones, infos = env.step(np.zeros(env.num_envs, dtype=np.int64))
        assert not dones.any()
        _, _, dones, infos = env.step(np.zeros(env.num_envs, dtype=np.int64))
        assert dones.all()
        assert all(info["TimeLimit.truncated"] for info in infos)
        assert all(info["terminal_observation"].shape == (env.n_obs,) for info in infos)
        assert np.isfinite(infos[0]["network_avg_travel_time_censored"])
        assert 0.0 <= infos[0]["network_completion_rate"] <= 1.0
        assert env.client is not None and env.client.sim_time == 0.0
        assert env.scenario in env.scenario_pool and env.sim_seed in env.seeds
    finally:
        env.close()


@pytest.mark.sumo
def test_action_three_holds_switches_for_two_following_ticks() -> None:
    env = _make_env(episode_s=60)
    try:
        env.reset()
        actions = np.zeros(env.num_envs, dtype=np.int64)
        actions[0] = 3
        _, _, _, _ = env.step(actions)
        for _ in range(2):
            actions.fill(0)
            actions[0] = 1
            _, _, _, infos = env.step(actions)
            assert infos[0]["illegal_action"] and infos[0]["hold_overridden"]
        assert infos[0]["last_rejection_reason"] == "hold_lockout_override"
        assert infos[0]["rejection_reason_counts"]["hold_lockout_override"] == 2
        assert infos[0]["n_illegal_actions_episode"] == 2
        assert env.n_hold_overridden[0] == 2
        assert env.n_illegal_actions[0] >= 2
    finally:
        env.close()


@pytest.mark.sumo
def test_rejection_penalty_changes_only_the_rejected_junction_reward() -> None:
    def one_step(penalty: float) -> np.ndarray:
        env = _make_env(episode_s=30, rejection_penalty=penalty)
        try:
            env.seed(SEED)
            env.reset()
            actions = np.zeros(env.num_envs, dtype=np.int64)
            actions[0] = 99
            _, rewards, _, _ = env.step(actions)
            return rewards
        finally:
            env.close()

    baseline = one_step(0.0)
    penalized = one_step(0.05)

    np.testing.assert_allclose(penalized[0], baseline[0] - 0.05, atol=1e-6)
    np.testing.assert_allclose(penalized[1:], baseline[1:], atol=1e-6)
