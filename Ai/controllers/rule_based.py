"""Queue and waiting-time rule controller using intersection observations only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from Ai.common.traffic_state import IntersectionState
from Ai.controllers.base import Action


class RuleBasedController:
    """Extend busy approaches and switch toward an approach with high demand."""

    name = "rule"

    def __init__(
        self,
        tls_config: Mapping[str, Any],
        phase_approaches: Mapping[int, Sequence[str]],
        *,
        queue_threshold: int = 8,
        wait_threshold_s: float = 45.0,
        min_green_s: float = 10.0,
        max_green_s: float = 60.0,
        extension_s: float = 5.0,
        decision_interval_s: float = 5.0,
    ) -> None:
        self.green_phases = {int(phase) for phase in tls_config["green_phases"]}
        self.phase_approaches = {int(k): tuple(v) for k, v in phase_approaches.items()}
        self.queue_threshold = int(queue_threshold)
        self.wait_threshold_s = float(wait_threshold_s)
        self.min_green_s = float(min_green_s)
        self.max_green_s = float(max_green_s)
        self.extension_s = float(extension_s)
        self.decision_interval_s = float(decision_interval_s)

    def decide(self, state: IntersectionState) -> Action:
        """Choose only from the current observation and configured phase mapping."""
        if state.phase not in self.green_phases:
            return Action("hold")
        approaches = {item.name: item for item in state.approaches}
        active = [approaches[name] for name in self.phase_approaches.get(state.phase, ()) if name in approaches]
        active_queue = sum(item.halting or 0 for item in active)
        active_wait = max((item.waiting_time or 0.0 for item in active), default=0.0)
        elapsed = state.phase_elapsed_s or 0.0
        active_busy = active_queue >= self.queue_threshold or active_wait >= self.wait_threshold_s
        if active_busy and elapsed >= self.max_green_s - self.extension_s:
            return Action("switch")
        if active_busy and elapsed < self.max_green_s:
            return Action("extend", seconds=self.extension_s)

        other_busy = any(
            name not in self.phase_approaches.get(state.phase, ())
            and ((item.halting or 0) >= self.queue_threshold
                 or (item.waiting_time or 0.0) >= self.wait_threshold_s)
            for name, item in approaches.items()
        )
        if elapsed >= self.min_green_s and active_queue < self.queue_threshold and active_wait < self.wait_threshold_s and other_busy:
            return Action("switch")
        return Action("hold")

    def reset(self) -> None:
        """This policy has no episode-local state."""
