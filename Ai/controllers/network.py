"""Multi-junction controllers that keep each policy and fallback independent."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from Ai.common.network_state import NetworkState
from Ai.controllers.base import Action
from Ai.controllers.fallback import FallbackController
from Ai.controllers.fixed_time import FixedTimeController
from Ai.controllers.registry import get_controller
from Ai.controllers.rl_network_controller import RLNetworkController


def classify_hybrid_coverage(
    tls_ids: tuple[str, ...], ppo_tls_ids: tuple[str, ...],
    per_junction: Mapping[str, Mapping[str, Any]], minimum_share: float,
) -> tuple[str, list[str]]:
    """Classify actual PPO ownership while keeping configured rule slots distinct."""
    if not 0 <= minimum_share <= 1:
        raise ValueError("minimum PPO tick share must be between zero and one")
    ppo = set(ppo_tls_ids)
    statuses = [
        ("rl" if float(per_junction.get(tls, {}).get("ppo_tick_share", 0.0)) >= minimum_share
         else "rl_fallback") if tls in ppo else "rule"
        for tls in tls_ids
    ]
    covered = sum(status == "rl" for status in statuses)
    label = "full" if covered == len(tls_ids) else "partial" if covered else "none"
    return label, statuses


class NetworkController(Protocol):
    """Policy interface for a synchronized network snapshot."""

    name: str
    decision_interval_s: float

    def decide(self, state: NetworkState) -> dict[str, Action]: ...

    def reset(self) -> None: ...


class PerJunctionController:
    """Apply one single-junction controller per TLS with independent fallback latches."""

    def __init__(
        self,
        name: str,
        tls_configs: list[Mapping[str, Any]],
        project_config: Mapping[str, Any],
    ) -> None:
        if name not in {"fixed", "rule"}:
            raise ValueError("network fixed/rule controllers accept only 'fixed' or 'rule'")
        if not tls_configs:
            raise ValueError("network controller requires at least one TLS")
        self.name = name
        self.controllers: dict[str, FallbackController] = {}
        for tls_config in tls_configs:
            tls_id = str(tls_config["tls_id"])
            policy = get_controller(name, project_config, tls_config=dict(tls_config))
            if isinstance(policy, FallbackController):
                wrapped = policy
            else:
                fallback = FixedTimeController(dict(tls_config), float(project_config["fixed"]["green_s"]))
                wrapped = FallbackController(policy, fallback)
            self.controllers[tls_id] = wrapped
        self.decision_interval_s = max(
            1.0, max(controller.decision_interval_s for controller in self.controllers.values())
        )

    def decide(self, state: NetworkState) -> dict[str, Action]:
        """Return an action for each configured junction, using a safe hold if absent."""
        return {
            tls_id: controller.decide(state.junctions[tls_id])
            if tls_id in state.junctions else Action("hold")
            for tls_id, controller in self.controllers.items()
        }

    def on_rejection(self, tls_id: str, state: NetworkState, reason: str) -> Action:
        """Fail over only the junction whose requested action was rejected."""
        controller = self.controllers[tls_id]
        return controller.on_rejection(state.junctions[tls_id], reason)

    def reset(self) -> None:
        for controller in self.controllers.values():
            controller.reset()


class HybridNetworkController:
    """Use the frozen PPO gate at eligible TLS and independent rule fallback elsewhere."""

    name = "hybrid"

    def __init__(
        self,
        tls_configs: list[Mapping[str, Any]],
        project_config: Mapping[str, Any],
        ppo_tls_ids: tuple[str, ...],
        *,
        ppo_controller: RLNetworkController | None = None,
    ) -> None:
        self.tls_ids = tuple(str(item["tls_id"]) for item in tls_configs)
        selected = tuple(str(value) for value in ppo_tls_ids)
        if len(set(selected)) != len(selected) or not set(selected).issubset(self.tls_ids):
            raise ValueError("hybrid PPO TLS IDs must be unique members of the frozen intended list")
        self.ppo_tls_ids = tuple(tls for tls in self.tls_ids if tls in selected)
        self.rule_tls_ids = tuple(tls for tls in self.tls_ids if tls not in selected)
        self.ppo_controller = ppo_controller
        if self.ppo_tls_ids and self.ppo_controller is None:
            self.ppo_controller = RLNetworkController(
                tls_configs, project_config, active_tls_ids=self.ppo_tls_ids,
            )
        self.rule_controller = (
            PerJunctionController(
                "rule",
                [item for item in tls_configs if str(item["tls_id"]) in self.rule_tls_ids],
                project_config,
            )
            if self.rule_tls_ids else None
        )
        self.controllers = {
            **(self.ppo_controller.controllers if self.ppo_controller else {}),
            **(self.rule_controller.controllers if self.rule_controller else {}),
        }
        if self.ppo_controller is not None:
            self.model_path = self.ppo_controller.model_path
            self.model_sha256 = self.ppo_controller.model_sha256
        else:
            model_path = Path(str(project_config["rl_net"].get("model_path", "")))
            if not model_path.is_absolute():
                model_path = Path(__file__).resolve().parents[2] / model_path
            self.model_path = model_path.resolve()
            self.model_sha256 = (
                hashlib.sha256(self.model_path.read_bytes()).hexdigest()
                if self.model_path.is_file() else None
            )
        intervals = [
            controller.decision_interval_s
            for controller in (self.ppo_controller, self.rule_controller)
            if controller is not None
        ]
        self.decision_interval_s = max(intervals, default=1.0)

    def decide(self, state: NetworkState) -> dict[str, Action]:
        actions: dict[str, Action] = {}
        if self.ppo_controller is not None:
            actions.update(self.ppo_controller.decide(state))
        if self.rule_controller is not None:
            actions.update(self.rule_controller.decide(state))
        return actions

    def on_rejection(self, tls_id: str, state: NetworkState, reason: str) -> Action:
        if tls_id in self.ppo_tls_ids:
            assert self.ppo_controller is not None
            return self.ppo_controller.on_rejection(tls_id, state, reason)
        if self.rule_controller is None:
            raise KeyError(f"no controller configured for TLS {tls_id!r}")
        return self.rule_controller.on_rejection(tls_id, state, reason)

    def reset(self) -> None:
        if self.ppo_controller is not None:
            self.ppo_controller.reset()
        if self.rule_controller is not None:
            self.rule_controller.reset()

    def record_tick(self, tls_id: str) -> None:
        if tls_id in self.ppo_tls_ids and self.ppo_controller is not None:
            self.ppo_controller.record_tick(tls_id)

    def diagnostics(self) -> dict[str, Any]:
        ppo = self.ppo_controller.diagnostics() if self.ppo_controller else {
            "model_path": str(self.model_path), "model_sha256": self.model_sha256,
            "model_loaded": False,
            "model_load_error": None, "batch_inference_count": 0,
            "median_batch_inference_latency_ms": 0.0, "batch_inference_latency_ms": [],
            "per_junction": {},
        }
        per_junction = dict(ppo["per_junction"])
        for tls_id in self.rule_tls_ids:
            per_junction[tls_id] = {
                "action_histogram": {}, "applied_action_histogram": {}, "phase_usage": {},
                "ppo_decisions": 0, "fallback_decisions": 0, "hold_overridden": 0,
                "fallback_active": False, "ppo_tick_share": 0.0,
            }
        return {
            **ppo, "controller_level": "stage4_hybrid",
            "ppo_tls_ids": list(self.ppo_tls_ids), "rule_tls_ids": list(self.rule_tls_ids),
            "per_junction": per_junction,
        }


def get_network_controller(
    name: str,
    tls_configs: list[Mapping[str, Any]],
    project_config: Mapping[str, Any],
) -> PerJunctionController | RLNetworkController | HybridNetworkController:
    """Build a network policy while preserving the fixed/rule controller path."""
    key = name.lower()
    if key == "rl":
        return RLNetworkController(tls_configs, project_config)
    if key == "hybrid":
        import json
        from pathlib import Path

        gate_path = Path(
            project_config.get("rl_net", {}).get(
                "hybrid_gate_path", "results/summary/t410_hybrid_gate.json"
            )
        )
        if not gate_path.is_absolute():
            gate_path = Path(__file__).resolve().parents[2] / gate_path
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("tls_list_hash") != project_config["network"].get("tls_list_hash"):
            raise ValueError("T4.10 hybrid gate TLS hash differs from the frozen network")
        pinned_model = str(gate.get("model_path", ""))
        rl_config = dict(project_config["rl_net"])
        rl_config["model_path"] = pinned_model
        hybrid_config = {**project_config, "rl_net": rl_config}
        return HybridNetworkController(
            tls_configs, hybrid_config, tuple(gate.get("ppo_tls_ids", ())),
        )
    if key not in {"fixed", "rule"}:
        raise ValueError(f"Unknown network controller {name!r}; choose fixed, rule, or rl")
    return PerJunctionController(key, tls_configs, project_config)
