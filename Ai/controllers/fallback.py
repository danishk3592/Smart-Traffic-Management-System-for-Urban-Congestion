"""Fail-safe wrapper that delegates invalid or failing decisions to fixed-time."""

from __future__ import annotations

import logging
import threading
import time

from Ai.common.traffic_state import IntersectionState
from Ai.controllers.base import Action, Controller, valid_action

logger = logging.getLogger(__name__)


class FallbackController:
    """Use fixed-time whenever a wrapped controller fails, times out or misbehaves."""

    def __init__(self, controller: Controller, fixed_time: Controller, timeout_s: float = 1.0) -> None:
        self.controller = controller
        self.fixed_time = fixed_time
        self.name = controller.name
        self.timeout_s = float(timeout_s)
        self.decision_interval_s = float(controller.decision_interval_s)
        self.fallback_active = False
        self._latched = False

    def decide(self, state: IntersectionState) -> Action:
        """Return a valid wrapped action or a fixed-time fallback action."""
        if self._latched:
            self.fallback_active = True
            return self.fixed_time.decide(state)
        started = time.monotonic()
        try:
            completed = threading.Event()
            outcome: list[object] = []

            def invoke() -> None:
                try:
                    outcome.append(self.controller.decide(state))
                except Exception as exc:  # noqa: BLE001 - forwarded to the caller thread
                    outcome.append(exc)
                finally:
                    completed.set()

            worker = threading.Thread(target=invoke, name="controller-decision", daemon=True)
            worker.start()
            if not completed.wait(self.timeout_s):
                self._latched = True
                raise TimeoutError(f"controller exceeded {self.timeout_s:g}s decision budget")
            if time.monotonic() - started > self.timeout_s:
                self._latched = True
                raise TimeoutError(f"controller exceeded {self.timeout_s:g}s decision budget")
            action = outcome[0]
            if isinstance(action, Exception):
                raise action
            if not valid_action(action):
                raise ValueError(f"controller returned an invalid action: {action!r}")
            self.fallback_active = False
            return action
        except Exception as exc:  # noqa: BLE001 - policy plug-ins may raise arbitrary errors
            self._activate(exc)
            return self.fixed_time.decide(state)

    def on_rejection(self, state: IntersectionState, reason: str) -> Action:
        """Replace a safety-rejected policy action with the safe fixed-time action."""
        self._activate(ValueError(f"safety layer rejected action: {reason}"))
        return self.fixed_time.decide(state)

    def reset(self) -> None:
        """Reset episode state without reviving a timed-out policy thread."""
        self.fallback_active = False
        if not self._latched:
            self.controller.reset()
        self.fixed_time.reset()

    def _activate(self, error: Exception) -> None:
        self.fallback_active = True
        logger.warning("Controller fallback activated: %s", error)
