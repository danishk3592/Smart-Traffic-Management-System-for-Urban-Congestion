"""Controller interface and typed actions for one signalized junction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Protocol

from Ai.common.traffic_state import IntersectionState

ActionKind = Literal["hold", "switch", "extend", "approach"]


@dataclass(frozen=True)
class Action:
    """A controller request; all signal changes are applied by SignalSafetyLayer."""

    kind: ActionKind
    seconds: float | None = None
    approach: str | None = None


def valid_action(action: object) -> bool:
    """Return whether an object is a well-formed controller action."""
    if not isinstance(action, Action) or action.kind not in {"hold", "switch", "extend", "approach"}:
        return False
    if action.kind == "extend":
        return (
            isinstance(action.seconds, (int, float))
            and math.isfinite(action.seconds)
            and action.seconds > 0
        )
    if action.kind == "approach":
        return isinstance(action.approach, str) and bool(action.approach.strip())
    return action.seconds is None and action.approach is None


class Controller(Protocol):
    """Minimal state-only interface shared by fixed, rule and learned policies."""

    name: str
    decision_interval_s: float

    def decide(self, state: IntersectionState) -> Action: ...

    def reset(self) -> None: ...
