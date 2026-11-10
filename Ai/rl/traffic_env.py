"""Gymnasium environment for safe PPO control of the configured pilot junction."""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from Ai.common.config import load_config
from Ai.common.sumo_client import SumoClient
from Ai.common.traffic_state import SumoSensorReader, to_vector, vector_norm_from_config
from Ai.controllers.safety import Accepted, Rejected, SignalSafetyLayer
from scripts.make_scenarios import get_cached_routes


class TrafficEnvironment(gym.Env[np.ndarray, int]):
    """Single-junction PPO env. Observation uses configured to_vector layout:
    eight normalized measurement/mask values per approach, green phase one-hot,
    normalized elapsed green and mask. Actions: keep this green for one decision
    interval, request the next green, extend by 5s, and extend by 10s. Keeping
    and switching are subject to SignalSafetyLayer's maximum/minimum green rules.
    Signal commands are delegated to SignalSafetyLayer, never applied directly.
    """
    metadata: ClassVar[dict[str, list[str]]] = {"render_modes": []}
    def __init__(self, scenario_pool: Iterable[str] | None = None,
                 seeds: Sequence[int] | None = None,
                 config: Mapping[str, Any] | str | Path | None = None) -> None:
        super().__init__()
        self.config = load_config(config) if not isinstance(config, Mapping) else dict(config)
        self.root = Path(__file__).resolve().parents[2]
        pool = self.config["demand"]["train_pool"]
        self.scenario_pool = tuple(
            pool["scenarios"] if scenario_pool is None else scenario_pool
        )
        cached_seeds = range(
            int(pool["seed_min"]),
            int(pool["seed_min"]) + int(pool["seeds_per_scenario"]),
        )
        self.seeds = tuple(int(s) for s in (cached_seeds if seeds is None else seeds))
        if not self.scenario_pool or not self.seeds:
            raise ValueError("scenario_pool and seeds must be non-empty")
        if any(
            not (1000 <= seed <= 1999 or 3000 <= seed <= 3009)
            for seed in self.seeds
        ):
            raise ValueError("seeds must be in the training block 1000–1999 or validation block 3000–3009")
        self.tls = dict(self.config["intersection"])
        self.tls.update({"tls_id": self.config["sumo"]["tls_id"],
                         "min_green_s": self.config["signal"]["min_green_s"],
                         "max_green_s": self.config["signal"]["max_green_s"]})
        self.norm = vector_norm_from_config(self.config, self.tls)
        self.reward_weights = {key: float(value) for key, value in self.config["rl"]["reward_weights"].items()}
        self.reward_scales = {key: float(value) for key, value in self.config["rl"]["reward_scales"].items()}
        required_scales = {"queue_change", "mean_wait_s", "throughput_vehicles"}
        if set(self.reward_scales) != required_scales:
            raise ValueError(f"rl.reward_scales must define exactly {sorted(required_scales)}")
        if any(not math.isfinite(value) or value <= 0 for value in self.reward_scales.values()):
            raise ValueError("rl.reward_scales values must be finite and strictly positive")
        if any(not math.isfinite(value) for value in self.reward_weights.values()):
            raise ValueError("rl.reward_weights values must be finite")
        self.observation_space = spaces.Box(0.0, 1.0, (self.norm.vector_length,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)
        self.client: SumoClient | None = None
        self.safety: SignalSafetyLayer | None = None
        self.sensor: SumoSensorReader | None = None
        self.state = None
        self.elapsed = 0.0
        self._queue_previous = 0.0
        self._sensor_time_previous = 0.0

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        self.close()
        options = options or {}
        scenario = (
            str(options["scenario"])
            if "scenario" in options
            else self.scenario_pool[int(self.np_random.integers(len(self.scenario_pool)))]
        )
        if scenario not in self.scenario_pool:
            raise ValueError(f"scenario is outside training pool: {scenario}")
        default_seed = seed if seed in self.seeds else self.seeds[int(self.np_random.integers(len(self.seeds)))]
        sim_seed = int(options.get("seed", default_seed))
        if sim_seed not in self.seeds:
            raise ValueError(f"seed is outside training pool: {sim_seed}")
        route = get_cached_routes(scenario, sim_seed)
        if not route.is_file():
            raise FileNotFoundError(f"cached routes missing: {route}")
        self.client = SumoClient(config_path=self.root / "config" / "stms.yaml",
                                 seed=sim_seed, route_file=route)
        try:
            self.client.start()
            self.safety = SignalSafetyLayer(self.client, self.tls)
            self.sensor = SumoSensorReader(self.tls, self.config["congestion"]["thresholds"])
            self.elapsed = 0.0
            self.state = self.sensor.read(self.client)
            self._queue_previous = float(self.state.totals["waiting_vehicles"] or 0)
            self._sensor_time_previous = self.client.sim_time
            return to_vector(self.state, self.norm), {
                "scenario": scenario, "seed": sim_seed, "sim_time": self.client.sim_time,
                "phase": self.state.phase, "phase_elapsed": self.state.phase_elapsed_s}
        except Exception:
            self.close()
            raise

    def step(self, action: int):
        if self.client is None or self.safety is None or self.sensor is None:
            raise RuntimeError("reset() must be called before step()")
        illegal = not self.action_space.contains(action)
        action = int(action) if not illegal else 0
        decision_interval = float(self.config["rl"]["decision_interval_s"])
        result = None
        if action == 0:
            result = self.safety.request_extend(decision_interval)
        elif action == 1:
            result = self.safety.request_switch()
        elif action in (2, 3):
            result = self.safety.request_extend(5.0 if action == 2 else 10.0)
        if action != 0 and result is not None and not isinstance(result, Accepted):
            illegal = True
        actual = 0 if illegal else action
        if illegal:
            self.safety.request_extend(decision_interval)
        duration = decision_interval + (5.0 if actual == 2 else 10.0 if actual == 3 else 0.0)
        start = self.client.sim_time
        while self.client.sim_time - start < duration:
            self.client.step()
            self.elapsed += float(self.config["sumo"]["step_length"])
            tick = self.safety.tick()
            match tick:
                case Rejected(reason=reason):
                    raise RuntimeError(f"safety tick rejected: {reason}")
                case Accepted():
                    pass
            if self.client.connection.simulation.getMinExpectedNumber() == 0 or self.elapsed >= self.config["rl"]["episode_s"]:
                break
        self.state = self.sensor.read(self.client)
        queue = float(self.state.totals["waiting_vehicles"] or 0)
        queue_change = queue - self._queue_previous
        vehicle_domain = self.client.connection.vehicle
        vehicle_ids = vehicle_domain.getIDList()
        mean_wait = (
            sum(float(vehicle_domain.getWaitingTime(vehicle_id)) for vehicle_id in vehicle_ids)
            / len(vehicle_ids)
            if vehicle_ids else 0.0
        )
        interval_s = self.client.sim_time - self._sensor_time_previous
        throughput_rate = float(self.state.totals["throughput_veh_min"] or 0)
        passed = throughput_rate * interval_s / 60.0
        self._sensor_time_previous = self.client.sim_time
        scales = self.reward_scales
        weights = self.reward_weights
        queue_term = float(np.clip(queue_change / scales["queue_change"], -1.0, 1.0))
        wait_term = float(np.clip(mean_wait / scales["mean_wait_s"], 0.0, 1.0))
        throughput_term = float(np.clip(passed / scales["throughput_vehicles"], 0.0, 1.0))
        reward = (
            -weights["queue"] * queue_term
            -weights["wait"] * wait_term
            +weights["throughput"] * throughput_term
        )
        self._queue_previous = queue
        terminated = self.client.connection.simulation.getMinExpectedNumber() == 0
        truncated = self.elapsed >= self.config["rl"]["episode_s"]
        return to_vector(self.state, self.norm), float(reward), bool(terminated), bool(truncated), {
            "sim_time": self.client.sim_time, "phase": self.state.phase,
            "phase_elapsed": self.state.phase_elapsed_s, "action_taken": actual,
            "illegal_action": bool(illegal), "queue_total": queue, "wait_total": mean_wait,
            "forced_max_green_switches": self.safety.forced_max_green_switches,
            "green_durations_by_phase": {
                phase: list(durations)
                for phase, durations in self.safety.green_durations_by_phase.items()
            }}

    def close(self) -> None:
        """Stop SUMO; safe to call repeatedly."""
        client, self.client = self.client, None
        self.safety = self.sensor = self.state = None
        if client is not None:
            client.close()
