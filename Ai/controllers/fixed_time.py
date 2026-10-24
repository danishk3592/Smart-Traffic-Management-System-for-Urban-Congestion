"""Fixed-time controller using verified green phases and program clearance."""

from __future__ import annotations

from typing import Any

from Ai.common.traffic_state import IntersectionState
from Ai.controllers.base import Action


class FixedTimeController:
    """Hold each native verified green for the configured fixed interval."""

    name = "fixed"

    def __init__(self, tls_config: dict[str, Any], green_seconds: float = 30.0) -> None:
        self.green_phases = {int(value) for value in tls_config["green_phases"]}
        self.green_seconds = float(green_seconds)
        self.decision_interval_s = 1.0
        self._last_phase: int | None = None
        self._armed_phase: int | None = None

    def decide(self, state: IntersectionState) -> Action:
        """Extend on green entry, then request clearance at the configured duration."""
        phase = state.phase
        if phase is None or phase not in self.green_phases:
            self._last_phase = phase
            self._armed_phase = None
            return Action("hold")
        if phase != self._last_phase or self._armed_phase != phase:
            self._last_phase = phase
            self._armed_phase = phase
            return Action("extend", seconds=self.green_seconds)
        if state.phase_elapsed_s is not None and state.phase_elapsed_s >= self.green_seconds:
            self._armed_phase = None
            return Action("switch")
        return Action("hold")

    def reset(self) -> None:
        """Clear phase bookkeeping before a new simulation episode."""
        self._last_phase = None
        self._armed_phase = None
