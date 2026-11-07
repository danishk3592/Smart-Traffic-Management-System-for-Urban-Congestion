"""Unit checks for controller action dispatch in the single-junction runner."""

from Ai.common.run_episode import _dispatch, _dispatch_network_action
from Ai.controllers.base import Action
from Ai.controllers.safety import Accepted, Rejected


class _SafetyStub:
    def __init__(self) -> None:
        self.extensions: list[float] = []

    def request_extend(self, seconds: float) -> Accepted:
        self.extensions.append(seconds)
        return Accepted("extended")


def test_rl_hold_dispatch_extends_for_one_decision_interval() -> None:
    safety = _SafetyStub()

    result = _dispatch(safety, Action("hold"), hold_seconds=5.0)

    assert result == Accepted("extended")
    assert safety.extensions == [5.0]


def test_fixed_and_rule_hold_dispatch_remains_a_no_op() -> None:
    safety = _SafetyStub()

    result = _dispatch(safety, Action("hold"))

    assert result == Accepted("hold")
    assert safety.extensions == []


def test_network_dispatch_preserves_ppo_rejection_separately_from_fallback() -> None:
    class SafetyStub:
        def __init__(self) -> None:
            self.actions: list[tuple[str, str, float | None]] = []

        def request(self, tls_id: str, kind: str, seconds: float | None) -> Accepted | Rejected:
            self.actions.append((tls_id, kind, seconds))
            if len(self.actions) == 1:
                return Rejected("minimum green time not reached")
            return Accepted("fallback accepted")

    class ControllerStub:
        def __init__(self) -> None:
            self.rejections: list[tuple[str, str]] = []

        def on_rejection(self, tls_id: str, state: object, reason: str) -> Action:
            self.rejections.append((tls_id, reason))
            return Action("hold")

    safety = SafetyStub()
    controller = ControllerStub()
    state = object()

    requested, fallback, reason = _dispatch_network_action(
        controller, safety, "tls-a", state, Action("switch")
    )

    assert requested == Rejected("minimum green time not reached")
    assert fallback == Accepted("fallback accepted")
    assert reason == "minimum green time not reached"
    assert controller.rejections == [("tls-a", "minimum green time not reached")]
    assert safety.actions == [("tls-a", "switch", None), ("tls-a", "hold", None)]
