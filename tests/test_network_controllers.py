"""Per-junction fallback isolation checks for network controllers."""

from datetime import datetime, timezone

from Ai.common.network_state import NetworkState
from Ai.common.traffic_state import IntersectionState
from Ai.controllers.base import Action
from Ai.controllers.network import PerJunctionController


class _Policy:
    name = "rule"
    decision_interval_s = 5.0

    def __init__(self, *, fails: bool) -> None:
        self.fails = fails

    def decide(self, state: IntersectionState) -> Action:
        if self.fails:
            raise RuntimeError("injected policy failure")
        return Action("hold")

    def reset(self) -> None:
        pass


def _tls_config(tls_id: str) -> dict[str, object]:
    return {"tls_id": tls_id, "green_phases": [0, 2], "approaches": []}


def _state(tls_id: str) -> IntersectionState:
    return IntersectionState(
        timestamp_utc=datetime.now(timezone.utc), sim_time=1, intersection_id=tls_id,
        approaches=[], phase=0, phase_elapsed_s=20, mode="green", totals={}, source="sumo",
    )


def test_one_policy_failure_falls_back_without_affecting_other_tls(monkeypatch) -> None:
    policies = iter((_Policy(fails=True), _Policy(fails=False)))
    monkeypatch.setattr("Ai.controllers.network.get_controller", lambda *args, **kwargs: next(policies))
    tls_configs = [_tls_config("tls-a"), _tls_config("tls-b")]
    project_config = {"fixed": {"green_s": 30}}
    controller = PerJunctionController("rule", tls_configs, project_config)
    state = NetworkState(
        sim_time=1, junctions={"tls-a": _state("tls-a"), "tls-b": _state("tls-b")}, totals={}
    )

    actions = controller.decide(state)

    assert set(actions) == {"tls-a", "tls-b"}
    assert all(isinstance(action, Action) for action in actions.values())
    assert controller.controllers["tls-a"].fallback_active
    assert not controller.controllers["tls-b"].fallback_active
