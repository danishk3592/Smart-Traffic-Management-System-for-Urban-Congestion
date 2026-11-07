"""T4.10 hybrid gate routing and PPO ownership reporting tests."""

from datetime import datetime, timezone

from Ai.common.network_state import NetworkState
from Ai.common.traffic_state import IntersectionState
from Ai.controllers.base import Action
from Ai.controllers.network import HybridNetworkController, classify_hybrid_coverage
from Ai.evaluation.hybrid_gate import evaluate_tls_gate


class _Policy:
    name = "rule"
    decision_interval_s = 5.0

    def decide(self, state: IntersectionState) -> Action:
        del state
        return Action("hold")

    def reset(self) -> None:
        pass


class _Wrapped:
    fallback_active = False

    def decide(self, state: IntersectionState) -> Action:
        return Action("hold")

    def reset(self) -> None:
        pass

    def on_rejection(self, state: IntersectionState, reason: str) -> Action:
        del state, reason
        return Action("switch")


class _PPO:
    decision_interval_s = 10.0
    model_path = "candidate.zip"
    model_sha256 = "candidate-hash"

    def __init__(self) -> None:
        self.controllers = {"tls-a": _Wrapped(), "tls-c": _Wrapped()}
        self.rejected: list[str] = []

    def decide(self, state: NetworkState) -> dict[str, Action]:
        del state
        return {tls: Action("switch") for tls in self.controllers}

    def on_rejection(self, tls_id: str, state: NetworkState, reason: str) -> Action:
        del state, reason
        self.rejected.append(tls_id)
        return Action("hold")

    def reset(self) -> None:
        pass

    def record_tick(self, tls_id: str) -> None:
        del tls_id

    def diagnostics(self) -> dict:
        return {"per_junction": {}, "model_path": self.model_path, "model_sha256": self.model_sha256}


def _state(tls_ids: tuple[str, ...]) -> NetworkState:
    return NetworkState(
        sim_time=1,
        junctions={
            tls: IntersectionState(
                timestamp_utc=datetime.now(timezone.utc), sim_time=1, intersection_id=tls,
                approaches=[], phase=0, phase_elapsed_s=20, mode="green", totals={}, source="sumo",
            )
            for tls in tls_ids
        },
        totals={},
    )


def test_hybrid_routes_only_frozen_gate_passing_tls_to_ppo(monkeypatch) -> None:
    monkeypatch.setattr("Ai.controllers.network.get_controller", lambda *args, **kwargs: _Policy())
    tls_ids = ("tls-a", "tls-b", "tls-c")
    configs = [{"tls_id": tls, "green_phases": [0, 2], "approaches": []} for tls in tls_ids]
    ppo = _PPO()
    controller = HybridNetworkController(
        configs, {"fixed": {"green_s": 30}}, ("tls-c", "tls-a"), ppo_controller=ppo,
    )

    actions = controller.decide(_state(tls_ids))

    assert controller.ppo_tls_ids == ("tls-a", "tls-c")
    assert controller.rule_tls_ids == ("tls-b",)
    assert {tls: action.kind for tls, action in actions.items()} == {
        "tls-a": "switch", "tls-b": "hold", "tls-c": "switch",
    }


def test_hybrid_rejection_and_ticks_are_isolated_by_controller_type(monkeypatch) -> None:
    monkeypatch.setattr("Ai.controllers.network.get_controller", lambda *args, **kwargs: _Policy())
    tls_ids = ("tls-a", "tls-b")
    configs = [{"tls_id": tls, "green_phases": [0, 2], "approaches": []} for tls in tls_ids]
    ppo = _PPO()
    controller = HybridNetworkController(
        configs, {"fixed": {"green_s": 30}}, ("tls-a",), ppo_controller=ppo,
    )
    state = _state(tls_ids)
    controller.on_rejection("tls-a", state, "injected")
    controller.on_rejection("tls-b", state, "injected")
    controller.record_tick("tls-a")
    controller.record_tick("tls-b")

    assert ppo.rejected == ["tls-a"]


def test_hybrid_coverage_distinguishes_rule_and_safety_fallback() -> None:
    label, statuses = classify_hybrid_coverage(
        ("tls-a", "tls-b", "tls-c"), ("tls-a", "tls-b"),
        {"tls-a": {"ppo_tick_share": 0.98}, "tls-b": {"ppo_tick_share": 0.70}},
        0.95,
    )
    assert (label, statuses) == ("partial", ["rl", "rl_fallback", "rule"])
    assert classify_hybrid_coverage(("tls-a",), (), {}, 0.95) == ("none", ["rule"])


def test_t410_gate_applies_queue_wait_and_action_criteria_without_relaxation() -> None:
    passing = evaluate_tls_gate(
        ppo_mean_queue=10.5, fixed_mean_queue=10.0,
        ppo_mean_wait=2.0, fixed_mean_wait=2.0, actions={"keep", "switch"},
    )
    failing_queue = evaluate_tls_gate(
        ppo_mean_queue=10.5001, fixed_mean_queue=10.0,
        ppo_mean_wait=1.0, fixed_mean_wait=2.0, actions={"keep", "switch"},
    )
    failing_diversity = evaluate_tls_gate(
        ppo_mean_queue=9.0, fixed_mean_queue=10.0,
        ppo_mean_wait=1.0, fixed_mean_wait=2.0, actions={"switch"},
    )
    assert passing["ppo_eligible"]
    assert not failing_queue["ppo_eligible"]
    assert not failing_diversity["ppo_eligible"]
