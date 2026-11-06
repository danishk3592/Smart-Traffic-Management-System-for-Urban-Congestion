"""Shared-clock, parameter-sharing vector environment for the frozen TLS set."""

from __future__ import annotations

import math
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3.common.vec_env import VecEnv
from stable_baselines3.common.vec_env.base_vec_env import VecEnvIndices

from Ai.common.config import load_config
from Ai.common.network_state import NetworkSensorReader, NetworkState
from Ai.common.sumo_client import SumoClient
from Ai.common.traffic_state import to_vector, vector_norm_from_config
from Ai.controllers.safety import NetworkSafetyManager, Rejected
from scripts.make_scenarios import ScenarioBuilder


def _rejection_category(reason: str) -> str:
    """Map detailed safety reasons to stable, reviewable per-junction buckets."""
    if reason == "signal is already in a clearance phase":
        return "clearance_phase"
    if reason.startswith("minimum green not met"):
        return "minimum_green"
    if reason.startswith("no verified yellow clearance") or "clearance" in reason:
        return "clearance_or_phase"
    if "maximum green" in reason or "exceed maximum green" in reason:
        return "maximum_green"
    if reason == "hold_lockout_override":
        return "hold_lockout_override"
    if reason == "invalid_action":
        return "invalid_action"
    return "other_safety_rejection"


def _apply_rejection_penalty(
    rewards: np.ndarray, illegal: np.ndarray, penalty: float
) -> np.ndarray:
    """Apply the same small local penalty only to rejected/overridden actions."""
    return rewards - np.float32(penalty) * np.asarray(illegal, dtype=np.float32)


def _censored_trip_metrics(
    scheduled_departures: Mapping[str, float], tripinfo_xml: str, sim_end_s: float
) -> dict[str, float]:
    """Summarize all scheduled trips, treating SUMO arrival=-1 entries as unfinished."""
    if not scheduled_departures:
        raise ValueError("network validation requires at least one scheduled trip")
    trip_root = ET.fromstring(tripinfo_xml)
    completed: dict[str, float] = {}
    for trip in trip_root.findall("tripinfo"):
        vehicle_id = trip.get("id")
        if vehicle_id in scheduled_departures and float(trip.get("arrival", "-1")) >= 0:
            completed[vehicle_id] = float(trip.get("departDelay", "0")) + float(trip.get("duration", "0"))
    censored = [
        completed.get(vehicle_id, max(0.0, sim_end_s - departure))
        for vehicle_id, departure in scheduled_departures.items()
    ]
    return {
        "network_avg_travel_time_censored": float(np.mean(censored)),
        "network_completion_rate": len(completed) / len(scheduled_departures),
    }


class NetworkVecEnv(VecEnv):
    """Expose each intended TLS as a slot while advancing one shared SUMO world."""

    render_mode = None

    def __init__(
        self,
        scenario_pool: Iterable[str] | None = None,
        seeds: Iterable[int] | None = None,
        config: Mapping[str, Any] | str | Path | None = None,
    ) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.builder = ScenarioBuilder(self.root, family="network")
        self.config = load_config(config) if not isinstance(config, Mapping) else dict(config)
        network = self.config["network"]
        self.tls_ids = tuple(str(value) for value in network["controlled_tls"])
        self.tls_configs = {str(item["tls_id"]): dict(item) for item in network["tls_configs"]}
        if not self.tls_ids or len(self.tls_ids) != len(set(self.tls_ids)):
            raise ValueError("network.controlled_tls must contain unique intended TLS IDs")
        if set(self.tls_ids) != set(self.tls_configs):
            raise ValueError("network TLS configs must exactly match the frozen intended TLS list")
        if tuple(sorted(self.tls_ids)) != self.tls_ids:
            raise ValueError("network.controlled_tls must be in fixed sorted slot order")
        net_pool = self.config["demand"]["net_train_pool"]
        self.scenario_pool = tuple(str(s) for s in (net_pool["scenarios"] if scenario_pool is None else scenario_pool))
        if not self.scenario_pool or len(set(self.scenario_pool)) != len(self.scenario_pool):
            raise ValueError("scenario_pool must be non-empty and contain no duplicates")
        if any(s not in network["scenarios"] for s in self.scenario_pool):
            raise ValueError("scenario_pool contains a scenario outside the configured network pool")
        default_seeds = range(
            int(net_pool["seed_min"]),
            int(net_pool["seed_min"]) + int(net_pool["seeds_per_scenario"]),
        )
        self.seeds = tuple(int(s) for s in (default_seeds if seeds is None else seeds))
        if not self.seeds or any(not (1000 <= s <= 1999 or 3000 <= s <= 3009) for s in self.seeds):
            raise ValueError("seeds must be in the training block 1000–1999 or validation block 3000–3009")
        rl_net = self.config["rl_net"]
        self.interval = float(rl_net["decision_interval_s"])
        self.episode_s = float(rl_net["episode_s"])
        self.step_length = float(self.config["sumo"]["step_length"])
        if not all(math.isfinite(x) and x > 0 for x in (self.interval, self.episode_s, self.step_length)):
            raise ValueError("rl_net decision interval, episode length, and SUMO step length must be positive")
        if not math.isclose(self.interval / self.step_length, round(self.interval / self.step_length), abs_tol=1e-9):
            raise ValueError("decision_interval_s must be an integer multiple of SUMO step_length")
        if not math.isclose(self.episode_s / self.interval, round(self.episode_s / self.interval), abs_tol=1e-9):
            raise ValueError("episode_s must be an integer multiple of decision_interval_s")
        self.interval_steps = round(self.interval / self.step_length)
        self.episode_steps = round(self.episode_s / self.step_length)
        self.hold_ticks = {2: math.ceil(5.0 / self.interval), 3: math.ceil(10.0 / self.interval)}
        self.network_term_weight = float(rl_net.get("network_term_weight", 0.0))
        if not math.isfinite(self.network_term_weight) or self.network_term_weight < 0:
            raise ValueError("network_term_weight must be finite and non-negative")
        self.rejected_action_penalty = float(rl_net.get("rejected_action_penalty", 0.0))
        if not math.isfinite(self.rejected_action_penalty) or self.rejected_action_penalty < 0:
            raise ValueError("rl_net.rejected_action_penalty must be finite and non-negative")
        self.weights = {
            k: float(v)
            for k, v in rl_net.get("reward_weights", self.config["rl"]["reward_weights"]).items()
        }
        self.scales = {k: float(v) for k, v in self.config["rl"]["reward_scales"].items()}
        if set(self.weights) != {"queue", "wait", "throughput"} or any(not math.isfinite(v) for v in self.weights.values()):
            raise ValueError("rl.reward_weights must define finite queue, wait, and throughput weights")
        required_scales = {"queue_change", "mean_wait_s", "throughput_vehicles"}
        if set(self.scales) != required_scales or any(not math.isfinite(v) or v <= 0 for v in self.scales.values()):
            raise ValueError("rl.reward_scales must define finite positive queue_change, mean_wait_s, throughput_vehicles")
        self.max_approaches = int(network["max_approaches"])
        self.max_phases = int(network["max_phases"])
        if self.max_approaches <= 0 or self.max_phases <= 0:
            raise ValueError("network.max_approaches and max_phases must be positive")
        if any(len(self.tls_configs[tls]["approaches"]) > self.max_approaches for tls in self.tls_ids):
            raise ValueError("network.max_approaches is smaller than an intended TLS approach count")
        if any(len(self.tls_configs[tls]["green_phases"]) > self.max_phases for tls in self.tls_ids):
            raise ValueError("network.max_phases is smaller than an intended TLS green phase count")
        self.n_obs = self.max_approaches * 8 + self.max_phases + 2
        self.observation_space = spaces.Box(0.0, 1.0, (self.n_obs,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)
        self.norms = {
            tls: vector_norm_from_config(self.config, self.tls_configs[tls]) for tls in self.tls_ids
        }
        self.client: SumoClient | None = None
        self.safety: NetworkSafetyManager | None = None
        self.sensors: NetworkSensorReader | None = None
        self.state: NetworkState | None = None
        self.sim_seed: int | None = None
        self.scenario: str | None = None
        self.elapsed_s = 0.0
        self._step_actions: np.ndarray | None = None
        self._rng = np.random.default_rng()
        self._next_entry: tuple[str, int] | None = None
        self.n_illegal_actions = np.zeros(len(self.tls_ids), dtype=np.int64)
        self.n_hold_overridden = np.zeros(len(self.tls_ids), dtype=np.int64)
        self._episode_rejection_reason_counts: list[dict[str, int]] = [
            {} for _ in self.tls_ids
        ]
        self._hold_remaining = np.zeros(len(self.tls_ids), dtype=np.int64)
        self._queue_previous = np.zeros(len(self.tls_ids), dtype=np.float64)
        self.last_episode_metrics: dict[str, float] = {}
        self._last_tripinfo_output = ""
        super().__init__(len(self.tls_ids), self.observation_space, self.action_space)

    def _observations(self) -> np.ndarray:
        if self.state is None:
            raise RuntimeError("network environment has not been reset")
        rows = np.zeros((len(self.tls_ids), self.n_obs), dtype=np.float32)
        for index, tls_id in enumerate(self.tls_ids):
            local = to_vector(self.state.junctions[tls_id], self.norms[tls_id])
            approach_end = len(self.norms[tls_id].approach_names) * 8
            phase_end = approach_end + len(self.norms[tls_id].green_phases)
            rows[index, :approach_end] = local[:approach_end]
            rows[index, self.max_approaches * 8 : self.max_approaches * 8 + len(self.norms[tls_id].green_phases)] = local[approach_end:phase_end]
            rows[index, self.max_approaches * 8 + self.max_phases :] = local[phase_end:]
        return rows

    def _start_episode(self) -> np.ndarray:
        self.close()
        if self._next_entry is not None:
            scenario, sim_seed = self._next_entry
            self._next_entry = None
        else:
            scenario = self.scenario_pool[int(self._rng.integers(len(self.scenario_pool)))]
            sim_seed = self.seeds[int(self._rng.integers(len(self.seeds)))]
        route = self.builder.get_cached_routes(scenario, sim_seed)
        if not route.is_file():
            raise FileNotFoundError(f"cached network route file missing: {route}")
        static_programs = {
            tls: str(self.tls_configs[tls]["static_program_id"])
            for tls in self.tls_ids if self.tls_configs[tls].get("static_program_id")
        }
        static_file = self.root / "SUMO" / "derived" / "network_static_tls.add.xml"
        extras = (static_file,) if static_programs else ()
        client = SumoClient(
            seed=sim_seed,
            label=f"network_rl_{uuid.uuid4().hex[:12]}",
            route_file=route,
            extra_additional_files=extras,
        )
        try:
            client.start()
            self.client = client
            self.safety = NetworkSafetyManager(
                client,
                [self.tls_configs[tls] for tls in self.tls_ids],
                excluded_tls=self.config["network"]["excluded_tls"],
                static_program_ids=static_programs,
            )
            self.sensors = NetworkSensorReader(
                [self.tls_configs[tls] for tls in self.tls_ids], self.config["congestion"]["thresholds"]
            )
            self.state = self.sensors.read(client)
            self.scenario, self.sim_seed = scenario, sim_seed
            self.elapsed_s = 0.0
            self._hold_remaining.fill(0)
            self._queue_previous = np.asarray([
                sum(float(a.halting or 0) for a in self.state.junctions[tls].approaches)
                for tls in self.tls_ids
            ])
            self._episode_rejection_reason_counts = [{} for _ in self.tls_ids]
            return self._observations()
        except Exception:
            client.close()
            self.client = self.safety = self.sensors = self.state = None
            raise

    def reset(self) -> np.ndarray:
        seeds = self._seeds
        self._reset_seeds()
        seed = seeds[0] if seeds and seeds[0] is not None else None
        options = self._options
        self._reset_options()
        self._step_actions = None
        if options and any(option != options[0] for option in options[1:]):
            raise ValueError("all TLS slots share one simulation and must receive identical reset options")
        selected = options[0] if options else {}
        scenario = selected.get("scenario")
        sim_seed = selected.get("seed")
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        if scenario is not None and str(scenario) not in self.scenario_pool:
            raise ValueError(f"scenario is outside the configured network pool: {scenario}")
        if sim_seed is not None and int(sim_seed) not in self.seeds:
            raise ValueError(f"seed is outside the configured network seed pool: {sim_seed}")
        self.reset_infos = [{} for _ in self.tls_ids]
        selected_scenario = str(scenario) if scenario is not None else self.scenario_pool[int(self._rng.integers(len(self.scenario_pool)))]
        selected_seed = int(sim_seed) if sim_seed is not None else self.seeds[int(self._rng.integers(len(self.seeds)))]
        self._next_entry = (selected_scenario, selected_seed)
        obs = self._start_episode()
        for index, tls_id in enumerate(self.tls_ids):
            self.reset_infos[index] = {"tls_id": tls_id, "scenario": self.scenario, "seed": self.sim_seed}
        return obs

    def step_async(self, actions: np.ndarray) -> None:
        if self.client is None or self.safety is None:
            raise RuntimeError("reset() must be called before step_async()")
        array = np.asarray(actions)
        if array.shape != (len(self.tls_ids),):
            raise ValueError(f"actions must have shape ({len(self.tls_ids)},)")
        if self._step_actions is not None:
            raise RuntimeError("step_async called while another step is pending")
        self._step_actions = array.copy()

    def step_wait(self):
        if self._step_actions is None:
            raise RuntimeError("step_wait called without step_async")
        if self.client is None or self.safety is None or self.sensors is None or self.state is None:
            raise RuntimeError("network environment is not active")
        actions = self._step_actions
        self._step_actions = None
        n = len(self.tls_ids)
        illegal = np.zeros(n, dtype=bool)
        overridden = np.zeros(n, dtype=bool)
        actual = np.zeros(n, dtype=np.int64)
        rejection_reasons: list[str | None] = [None] * n
        locked_at_start = self._hold_remaining.copy()
        for i, tls_id in enumerate(self.tls_ids):
            raw = actions[i]
            if not self.action_space.contains(raw):
                illegal[i] = True
                rejection_reasons[i] = "invalid_action"
                continue
            action = int(raw)
            if self._hold_remaining[i] > 0 and action != 0:
                illegal[i] = overridden[i] = True
                rejection_reasons[i] = "hold_lockout_override"
                continue
            if action == 1:
                result = self.safety.request(tls_id, "switch")
                if isinstance(result, Rejected):
                    illegal[i] = True
                    rejection_reasons[i] = result.reason
                    continue
            elif action in (2, 3):
                self._hold_remaining[i] = self.hold_ticks[action]
            if action != 1:
                result = self.safety.request(tls_id, "extend", self.interval)
                if isinstance(result, Rejected):
                    illegal[i] = True
                    rejection_reasons[i] = result.reason
                    if action in (2, 3):
                        self._hold_remaining[i] = 0
                    continue
            actual[i] = action

        # Rejected samples are safe holds. Hold-lockouts are counted on every blocked request.
        for i, tls_id in enumerate(self.tls_ids):
            if illegal[i]:
                self.n_illegal_actions[i] += 1
                reason = _rejection_category(rejection_reasons[i] or "unspecified_rejection")
                counts = self._episode_rejection_reason_counts[i]
                counts[reason] = counts.get(reason, 0) + 1
                self.safety.request(tls_id, "extend", self.interval)
            if overridden[i]:
                self.n_hold_overridden[i] += 1

        for _ in range(self.interval_steps):
            self.client.step()
            self.elapsed_s += self.step_length
            results = self.safety.tick_all()
            rejected = {tls: result.reason for tls, result in results.items() if isinstance(result, Rejected)}
            if rejected:
                self.close()
                raise RuntimeError(f"network safety tick rejected: {rejected}")
            if self.elapsed_s + 1e-9 >= self.episode_s:
                break
        self.state = self.sensors.read(self.client)
        rewards = np.zeros(n, dtype=np.float32)
        local_queue = np.zeros(n, dtype=np.float64)
        for i, tls_id in enumerate(self.tls_ids):
            junction = self.state.junctions[tls_id]
            queue = sum(float(a.halting or 0) for a in junction.approaches)
            local_queue[i] = queue
            queue_term = float(np.clip((queue - self._queue_previous[i]) / self.scales["queue_change"], -1.0, 1.0))
            lane_domain = self.client.connection.lane
            vehicle_domain = self.client.connection.vehicle
            vehicle_ids = {
                vehicle_id
                for approach in self.tls_configs[tls_id]["approaches"]
                for lane_id in approach["lanes"]
                for vehicle_id in lane_domain.getLastStepVehicleIDs(lane_id)
            }
            wait = (
                sum(float(vehicle_domain.getWaitingTime(vehicle_id)) for vehicle_id in vehicle_ids)
                / len(vehicle_ids)
                if vehicle_ids else 0.0
            )
            wait_term = float(np.clip(wait / self.scales["mean_wait_s"], 0.0, 1.0))
            throughput = float(junction.totals.get("throughput_veh_min", 0.0) or 0.0)
            passed = throughput * self.interval / 60.0
            throughput_term = float(np.clip(passed / self.scales["throughput_vehicles"], 0.0, 1.0))
            rewards[i] = (
                -self.weights["queue"] * queue_term
                -self.weights["wait"] * wait_term
                +self.weights["throughput"] * throughput_term
            )
        self._queue_previous = local_queue
        rewards += np.float32(self.network_term_weight * float(rewards.mean()))
        rewards = _apply_rejection_penalty(rewards, illegal, self.rejected_action_penalty)
        done = self.elapsed_s + 1e-9 >= self.episode_s
        terminal = self._observations() if done else None
        episode_scenario, episode_seed = self.scenario, self.sim_seed
        sim_time = float(self.client.sim_time)
        local_wait = [
            float(self.state.junctions[tls_id].totals.get("avg_wait", 0.0) or 0.0)
            for tls_id in self.tls_ids
        ]
        if done:
            self.last_episode_metrics = self._finish_episode_metrics()
        infos = []
        for i, tls_id in enumerate(self.tls_ids):
            info = {
                "tls_id": tls_id,
                "scenario": episode_scenario,
                "seed": episode_seed,
                "sim_time": sim_time,
                "illegal_action": bool(illegal[i]),
                "hold_overridden": bool(overridden[i]),
                "n_illegal_actions": int(self.n_illegal_actions[i]),
                "n_illegal_actions_episode": int(sum(self._episode_rejection_reason_counts[i].values())),
                "rejection_reason_counts": dict(self._episode_rejection_reason_counts[i]),
                "last_rejection_reason": rejection_reasons[i] or "",
                "n_hold_overridden": int(self.n_hold_overridden[i]),
                "fallback_active": False,
                "action_taken": int(actual[i]),
                "queue_total": float(local_queue[i]),
                "wait_total": local_wait[i],
            }
            if done:
                info["TimeLimit.truncated"] = True
                info["terminal_observation"] = terminal[i].copy()
                if i == 0:
                    info.update(self.last_episode_metrics)
            infos.append(info)
        dones = np.full(n, done, dtype=bool)
        if done:
            # Cache lookups are validated before closing/replacing the current episode.
            next_scenario = self.scenario_pool[int(self._rng.integers(len(self.scenario_pool)))]
            next_seed = self.seeds[int(self._rng.integers(len(self.seeds)))]
            try:
                route = self.builder.get_cached_routes(next_scenario, next_seed)
                if not route.is_file():
                    raise FileNotFoundError(f"cached network route file missing: {route}")
            except Exception:
                self.close()
                raise
            self._next_entry = (next_scenario, next_seed)
            try:
                obs = self._start_episode()
            except Exception:
                self.close()
                raise
            if (self.scenario, self.sim_seed) != (next_scenario, next_seed):
                raise AssertionError("next episode selection changed after cache preflight")
            self.reset_infos = [
                {"tls_id": tls_id, "scenario": self.scenario, "seed": self.sim_seed}
                for tls_id in self.tls_ids
            ]
        else:
            obs = self._observations()
            for i in range(n):
                if locked_at_start[i] > 0:
                    self._hold_remaining[i] = max(0, self._hold_remaining[i] - 1)
        return obs, rewards, dones, infos

    def seed(self, seed: int | None = None) -> list[int | None]:
        if seed is None:
            seed = int(np.random.SeedSequence().generate_state(1)[0])
        self._rng = np.random.default_rng(int(seed))
        self._seeds = [int(seed) + index for index in range(self.num_envs)]
        return list(self._seeds)

    def get_attr(self, attr_name: str, indices: VecEnvIndices = None) -> list[Any]:
        ids = self._get_indices(indices)
        if attr_name == "render_mode":
            value: Any = None
        elif attr_name == "tls_id":
            return [self.tls_ids[index] for index in ids]
        elif attr_name == "tls_config":
            return [self.tls_configs[self.tls_ids[index]] for index in ids]
        elif attr_name == "norm":
            return [self.norms[self.tls_ids[index]] for index in ids]
        elif attr_name == "n_illegal_actions":
            return [int(self.n_illegal_actions[index]) for index in ids]
        elif attr_name == "n_hold_overridden":
            return [int(self.n_hold_overridden[index]) for index in ids]
        elif attr_name == "hold_remaining":
            return [int(self._hold_remaining[index]) for index in ids]
        elif hasattr(self, attr_name):
            value = getattr(self, attr_name)
        else:
            raise AttributeError(attr_name)
        return [value for _ in ids]

    def set_attr(self, attr_name: str, value: Any, indices: VecEnvIndices = None) -> None:
        ids = self._get_indices(indices)
        if attr_name == "n_illegal_actions":
            for index in ids:
                self.n_illegal_actions[index] = int(value)
            return
        if attr_name == "n_hold_overridden":
            for index in ids:
                self.n_hold_overridden[index] = int(value)
            return
        if attr_name == "hold_remaining":
            for index in ids:
                self._hold_remaining[index] = int(value)
            return
        if attr_name in {"num_envs", "tls_ids", "tls_configs", "client", "safety", "sensors", "state"}:
            raise AttributeError(f"cannot mutate structural environment attribute {attr_name!r}")
        if not hasattr(self, attr_name):
            raise AttributeError(attr_name)
        if len(ids) != self.num_envs:
            raise ValueError("shared simulation attributes cannot be set for only selected TLS slots")
        setattr(self, attr_name, value)

    def env_method(self, method_name: str, *method_args: Any, indices: VecEnvIndices = None, **method_kwargs: Any) -> list[Any]:
        ids = self._get_indices(indices)
        method = getattr(self, method_name, None)
        if not callable(method):
            raise TypeError(f"environment method {method_name!r} is not callable")
        # One physical environment backs every slot: invoke shared methods once.
        result = method(*method_args, **method_kwargs)
        return [result for _ in ids]

    def env_is_wrapped(self, wrapper_class: type[gym.Wrapper], indices: VecEnvIndices = None) -> list[bool]:
        return [False for _ in self._get_indices(indices)]

    def get_images(self) -> list[None]:
        return [None for _ in range(self.num_envs)]

    def close(self) -> None:
        client, self.client = self.client, None
        self.safety = self.sensors = self.state = None
        if client is not None:
            client.close()
            self._last_tripinfo_output = client.tripinfo_output

    def _finish_episode_metrics(self) -> dict[str, float]:
        """Return censored all-trip time and completion for the finished episode."""
        if self.client is None or self.scenario is None or self.sim_seed is None:
            raise RuntimeError("cannot summarize a network episode without an active run")
        scenario, sim_seed, sim_end = self.scenario, self.sim_seed, self.elapsed_s
        self.close()
        route_path = self.builder.get_cached_routes(scenario, sim_seed)
        root = ET.parse(route_path).getroot()
        scheduled = {
            vehicle.get("id"): float(vehicle.get("depart", "0"))
            for vehicle in root.findall("vehicle") if vehicle.get("id")
        }
        if not scheduled:
            raise ValueError(f"network validation route has no vehicles: {route_path}")
        return _censored_trip_metrics(scheduled, self._last_tripinfo_output, sim_end)
