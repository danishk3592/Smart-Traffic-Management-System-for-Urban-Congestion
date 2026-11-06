"""Shared-policy PPO controller with independent per-junction fail-safe latches."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from stable_baselines3 import PPO

from Ai.common.network_state import NetworkState
from Ai.common.traffic_state import IntersectionState, to_vector, vector_norm_from_config
from Ai.controllers.base import Action
from Ai.controllers.fallback import FallbackController
from Ai.controllers.fixed_time import FixedTimeController

logger = logging.getLogger(__name__)

_ACTION_NAMES = ("keep", "switch", "hold_5s", "hold_10s")
_ACTIONS = (Action("hold"), Action("switch"), Action("hold"), Action("hold"))


class _BatchedSlotPolicy:
    """Expose one already-computed batch row through the single-TLS fallback API."""

    name = "rl"

    def __init__(self, decision_interval_s: float) -> None:
        self.decision_interval_s = decision_interval_s
        self.action: Action | None = None
        self.error: Exception | None = None

    def decide(self, state: IntersectionState) -> Action:
        del state
        if self.error is not None:
            raise RuntimeError("batched PPO inference unavailable") from self.error
        if self.action is None:
            raise RuntimeError("batched PPO action was not prepared")
        return self.action

    def reset(self) -> None:
        self.action = None
        self.error = None


class RLNetworkController:
    """Run one ordered PPO batch and isolate fallback state for each intended TLS."""

    name = "rl"

    def __init__(
        self,
        tls_configs: list[Mapping[str, Any]],
        project_config: Mapping[str, Any],
        *,
        model_path: str | Path | None = None,
        model: Any | None = None,
        active_tls_ids: tuple[str, ...] | None = None,
    ) -> None:
        self.config = dict(project_config)
        self.tls_ids = tuple(str(value) for value in self.config["network"]["controlled_tls"])
        if not self.tls_ids or len(self.tls_ids) != len(set(self.tls_ids)):
            raise ValueError("network.controlled_tls must contain unique TLS IDs")
        if tuple(str(item["tls_id"]) for item in tls_configs) != self.tls_ids:
            raise ValueError("TLS configs must exactly match the frozen network slot order")
        self.active_tls_ids = tuple(self.tls_ids if active_tls_ids is None else active_tls_ids)
        if not self.active_tls_ids or len(self.active_tls_ids) != len(set(self.active_tls_ids)):
            raise ValueError("active PPO TLS IDs must be a non-empty unique subset of the frozen list")
        if not set(self.active_tls_ids).issubset(self.tls_ids):
            raise ValueError("active PPO TLS IDs must belong to the frozen intended list")
        self.tls_configs = {str(item["tls_id"]): dict(item) for item in tls_configs}
        rl_config = self.config["rl_net"]
        self.decision_interval_s = float(rl_config["decision_interval_s"])
        if not math.isfinite(self.decision_interval_s) or self.decision_interval_s <= 0:
            raise ValueError("rl_net.decision_interval_s must be positive and finite")
        self.max_approaches = int(self.config["network"]["max_approaches"])
        self.max_phases = int(self.config["network"]["max_phases"])
        self.n_obs = self.max_approaches * 8 + self.max_phases + 2
        self.norms = {
            tls_id: vector_norm_from_config(self.config, self.tls_configs[tls_id])
            for tls_id in self.tls_ids
        }
        configured_path = model_path or rl_config.get(
            "model_path", "Ai/rl/models/ppo_net_v2/evaluations/best_model.zip"
        )
        self.model_path = self._resolve_path(configured_path)
        self.model_sha256 = (
            hashlib.sha256(self.model_path.read_bytes()).hexdigest()
            if self.model_path.is_file() else None
        )
        self.model = model
        self.load_error: Exception | None = None
        if self.model is None:
            try:
                self._validate_model_metadata()
                self.model = PPO.load(str(self.model_path), device=str(rl_config.get("device", "cpu")))
                self._validate_model_spaces(self.model)
            except Exception as exc:  # fail closed to independent fixed-time fallbacks
                self.load_error = exc
                logger.exception("Network PPO unavailable; per-junction fixed-time fallback is active")
        else:
            self._validate_model_spaces(self.model)

        green_s = float(self.config["fixed"]["green_s"])
        self.slot_policies: dict[str, _BatchedSlotPolicy] = {}
        self.controllers: dict[str, FallbackController] = {}
        for tls_id in self.active_tls_ids:
            slot_policy = _BatchedSlotPolicy(self.decision_interval_s)
            fixed = FixedTimeController(self.tls_configs[tls_id], green_s)
            self.slot_policies[tls_id] = slot_policy
            self.controllers[tls_id] = FallbackController(slot_policy, fixed)
        self._reset_diagnostics()

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        resolved = Path(path).expanduser()
        if not resolved.is_absolute():
            resolved = Path(__file__).resolve().parents[2] / resolved
        return resolved.resolve()

    def _validate_model_metadata(self) -> None:
        if not self.model_path.is_file():
            raise FileNotFoundError(f"network PPO model file not found: {self.model_path}")
        candidates = (self.model_path.parent / "config.json", self.model_path.parent.parent / "config.json")
        metadata_path = next((path for path in candidates if path.is_file()), None)
        if metadata_path is None:
            raise FileNotFoundError(f"network PPO provenance config not found beside {self.model_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        network = self.config["network"]
        if metadata.get("intended_tls_hash") != network.get("tls_list_hash"):
            raise ValueError("network PPO intended-TLS hash does not match the frozen network")
        if metadata.get("slot_order") != list(self.tls_ids):
            raise ValueError("network PPO slot order does not match the frozen network")

    def _validate_model_spaces(self, model: Any) -> None:
        if tuple(model.observation_space.shape or ()) != (self.n_obs,):
            raise ValueError(f"network PPO observation shape must be ({self.n_obs},)")
        if int(model.action_space.n) != len(_ACTIONS):
            raise ValueError(f"network PPO must expose {len(_ACTIONS)} actions")

    def _reset_diagnostics(self) -> None:
        self._action_histograms = {tls: Counter() for tls in self.tls_ids}
        self._applied_action_histograms = {tls: Counter() for tls in self.tls_ids}
        self._phase_usage = {tls: Counter() for tls in self.tls_ids}
        self._ppo_decisions = Counter()
        self._fallback_decisions = Counter()
        self._hold_overridden = Counter()
        self._ppo_ticks = Counter()
        self._total_ticks = Counter()
        self._hold_remaining = {tls: 0 for tls in self.tls_ids}
        self.inference_latencies_ms: list[float] = []

    def _observations(self, state: NetworkState) -> np.ndarray:
        if tuple(state.junctions) != self.tls_ids and set(state.junctions) != set(self.tls_ids):
            raise ValueError("network state does not contain exactly the frozen intended TLS set")
        rows = np.zeros((len(self.tls_ids), self.n_obs), dtype=np.float32)
        for index, tls_id in enumerate(self.tls_ids):
            local = to_vector(state.junctions[tls_id], self.norms[tls_id])
            approach_end = len(self.norms[tls_id].approach_names) * 8
            phase_end = approach_end + len(self.norms[tls_id].green_phases)
            rows[index, :approach_end] = local[:approach_end]
            phase_start = self.max_approaches * 8
            rows[index, phase_start : phase_start + len(self.norms[tls_id].green_phases)] = local[
                approach_end:phase_end
            ]
            rows[index, self.max_approaches * 8 + self.max_phases :] = local[phase_end:]
        if not np.isfinite(rows).all():
            raise ValueError("network PPO observation batch contains non-finite values")
        return rows

    def decide(self, state: NetworkState) -> dict[str, Action]:
        """Predict all TLS actions in one deterministic forward pass."""
        predictions: np.ndarray | None = None
        inference_error = self.load_error
        started = time.perf_counter()
        try:
            if self.model is None:
                raise RuntimeError("network PPO model did not load") from inference_error
            rows = self._observations(state)
            values, _ = self.model.predict(rows, deterministic=True)
            predictions = np.asarray(values).reshape(-1)
            if predictions.shape != (len(self.tls_ids),):
                raise ValueError(
                    f"network PPO returned {predictions.size} actions for {len(self.tls_ids)} TLS slots"
                )
        except Exception as exc:  # noqa: BLE001 - batch failures route to each TLS-local fallback
            inference_error = exc
        finally:
            self.inference_latencies_ms.append((time.perf_counter() - started) * 1000.0)

        actions: dict[str, Action] = {}
        for index, tls_id in enumerate(self.tls_ids):
            if tls_id not in self.active_tls_ids:
                continue
            slot = self.slot_policies[tls_id]
            slot.action = None
            slot.error = inference_error
            if inference_error is None and predictions is not None:
                raw_value = predictions[index]
                try:
                    numeric_action = float(raw_value)
                    action_index = int(numeric_action)
                    if not math.isfinite(numeric_action) or action_index != numeric_action or not 0 <= action_index < len(_ACTIONS):
                        raise ValueError
                except (TypeError, ValueError, OverflowError):
                    slot.error = ValueError(f"invalid PPO action for TLS {tls_id}: {raw_value!r}")
                else:
                    raw_action_index = action_index
                    if self._hold_remaining[tls_id] > 0:
                        if action_index != 0:
                            self._hold_overridden[tls_id] += 1
                            action_index = 0
                        self._hold_remaining[tls_id] -= 1
                    elif action_index in (2, 3):
                        lock_s = 5.0 if action_index == 2 else 10.0
                        self._hold_remaining[tls_id] = math.ceil(lock_s / self.decision_interval_s)
                    slot.action = _ACTIONS[action_index]

            wrapped = self.controllers[tls_id]
            action = wrapped.decide(state.junctions[tls_id])
            actions[tls_id] = action
            if wrapped.fallback_active:
                self._fallback_decisions[tls_id] += 1
            else:
                self._ppo_decisions[tls_id] += 1
                self._action_histograms[tls_id][_ACTION_NAMES[raw_action_index]] += 1
                self._applied_action_histograms[tls_id][_ACTION_NAMES[action_index]] += 1
                phase = int(state.junctions[tls_id].phase)
                if phase in self.tls_configs[tls_id]["green_phases"]:
                    self._phase_usage[tls_id][str(phase)] += 1
        return actions

    def on_rejection(self, tls_id: str, state: NetworkState, reason: str) -> Action:
        """Latch fallback only for the TLS whose safety request was rejected."""
        return self.controllers[tls_id].on_rejection(state.junctions[tls_id], reason)

    def reset(self) -> None:
        """Reset episode counters while preserving safety-latched corrupt/failed slots."""
        self._reset_diagnostics()
        for policy in self.slot_policies.values():
            policy.reset()
        for wrapped in self.controllers.values():
            wrapped.reset()

    def record_tick(self, tls_id: str) -> None:
        """Count whether PPO or the TLS-local fallback owns one safety tick."""
        if tls_id not in self.controllers:
            raise KeyError(f"unknown intended TLS {tls_id!r}")
        self._total_ticks[tls_id] += 1
        if not self.controllers[tls_id].fallback_active:
            self._ppo_ticks[tls_id] += 1

    @property
    def median_inference_latency_ms(self) -> float:
        return float(np.median(self.inference_latencies_ms)) if self.inference_latencies_ms else 0.0

    def diagnostics(self) -> dict[str, Any]:
        """Return JSON-safe inference and per-junction action diagnostics."""
        return {
            "model_path": str(self.model_path),
            "model_sha256": self.model_sha256,
            "model_loaded": self.model is not None,
            "model_load_error": str(self.load_error) if self.load_error else None,
            "batch_inference_count": len(self.inference_latencies_ms),
            "median_batch_inference_latency_ms": self.median_inference_latency_ms,
            "batch_inference_latency_ms": list(self.inference_latencies_ms),
            "per_junction": {
                tls: {
                    "action_histogram": {
                        name: self._action_histograms[tls][name] for name in _ACTION_NAMES
                    },
                    "applied_action_histogram": {
                        name: self._applied_action_histograms[tls][name] for name in _ACTION_NAMES
                    },
                    "phase_usage": dict(sorted(self._phase_usage[tls].items())),
                    "ppo_decisions": self._ppo_decisions[tls],
                    "fallback_decisions": self._fallback_decisions[tls],
                    "hold_overridden": self._hold_overridden[tls],
                    "fallback_active": self.controllers[tls].fallback_active,
                    "ppo_tick_share": (
                        self._ppo_ticks[tls] / self._total_ticks[tls]
                        if self._total_ticks[tls] else 0.0
                    ),
                }
                for tls in self.active_tls_ids
            },
        }
