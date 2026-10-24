"""Focused tests for controller actions, policies, registry and fallback."""

import time
from datetime import datetime, timezone

from Ai.common.config import load_config
from Ai.common.sumo_client import SumoClient
from Ai.common.traffic_state import ApproachState, IntersectionState
from Ai.controllers.base import Action, valid_action
from Ai.controllers.fallback import FallbackController
from Ai.controllers.fixed_time import FixedTimeController
from Ai.controllers.registry import get_controller, phase_approaches_from_network
from Ai.controllers.rule_based import RuleBasedController


def _state(
    phase: int = 0,
    elapsed: float = 1.0,
    *,
    active_halting: int = 1,
    other_halting: int = 12,
) -> IntersectionState:
    return IntersectionState(
        timestamp_utc=datetime.now(timezone.utc),
        sim_time=elapsed,
        intersection_id="tls",
        approaches=[
            ApproachState("active", 5, active_halting, 1.0, 2.0, 10.0, "Low", ["halting", "waiting_time"]),
            ApproachState("other", 15, other_halting, 1.0, 55.0, 50.0, "High", ["halting", "waiting_time"]),
        ],
        phase=phase,
        phase_elapsed_s=elapsed,
        mode="green",
        totals={"waiting_vehicles": active_halting + other_halting},
        source="sumo",
    )


def _tls() -> dict[str, object]:
    return {"green_phases": [0, 2], "yellow_after": {0: 1, 2: 3}}


def test_action_validation_rejects_malformed_values() -> None:
    assert valid_action(Action("hold"))
    assert valid_action(Action("switch"))
    assert valid_action(Action("extend", seconds=5))
    assert valid_action(Action("approach", approach="north"))
    assert not valid_action(Action("extend", seconds=float("nan")))
    assert not valid_action(Action("extend", seconds="five"))
    assert not valid_action(object())


def test_fixed_time_holds_green_then_requests_switch() -> None:
    controller = FixedTimeController(_tls(), green_seconds=30)
    assert controller.decide(_state(elapsed=0)) == Action("extend", seconds=30)
    assert controller.decide(_state(elapsed=29)) == Action("hold")
    assert controller.decide(_state(elapsed=30)) == Action("switch")
    assert controller.decide(_state(phase=1, elapsed=0)) == Action("hold")
    assert controller.decide(_state(phase=2, elapsed=0)) == Action("extend", seconds=30)


def test_rule_controller_extends_busy_green_and_switches_to_busy_approach() -> None:
    controller = RuleBasedController(
        _tls(), {0: ["active"], 2: ["other"]}, queue_threshold=8,
        wait_threshold_s=45, min_green_s=10, max_green_s=60,
    )
    assert controller.decide(_state(active_halting=10, elapsed=15)) == Action("extend", seconds=5)
    assert controller.decide(_state(active_halting=1, elapsed=15)) == Action("switch")
    assert controller.decide(_state(active_halting=1, elapsed=5)) == Action("hold")
    assert controller.decide(_state(active_halting=10, elapsed=55)) == Action("switch")


def test_fallback_wraps_exceptions_and_invalid_actions() -> None:
    fixed = FixedTimeController(_tls())

    class BrokenController:
        name = "broken"
        decision_interval_s = 1.0

        def decide(self, _state: IntersectionState) -> object:
            return object()

        def reset(self) -> None:
            pass

    wrapped = FallbackController(BrokenController(), fixed)
    assert wrapped.decide(_state(elapsed=0)) == Action("extend", seconds=30)
    assert wrapped.fallback_active
    wrapped.reset()
    assert not wrapped.fallback_active


def test_fallback_times_out_and_latches_to_fixed_controller() -> None:
    fixed = FixedTimeController(_tls())

    class SlowController:
        name = "slow"
        decision_interval_s = 1.0

        def decide(self, _state: IntersectionState) -> Action:
            time.sleep(0.2)
            return Action("hold")

        def reset(self) -> None:
            pass

    wrapped = FallbackController(SlowController(), fixed, timeout_s=0.01)
    started = time.monotonic()
    assert wrapped.decide(_state(elapsed=0)) == Action("extend", seconds=30)
    assert time.monotonic() - started < 0.1
    assert wrapped.fallback_active
    wrapped.reset()
    assert wrapped.decide(_state(elapsed=0)) == Action("extend", seconds=30)


def test_registry_maps_phase_approaches_from_actual_tls_program() -> None:
    config = load_config()
    tls = dict(config["intersection"])
    tls["tls_id"] = config["sumo"]["tls_id"]
    net = SumoClient()._resolve_config()["net"]
    mapping = phase_approaches_from_network(net, tls)
    assert set(mapping) == set(tls["green_phases"])
    assert all(mapping.values())
    assert get_controller("fixed", config).name == "fixed"
    assert get_controller("rule", config).name == "rule"
