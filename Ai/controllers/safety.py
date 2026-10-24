"""Safety checks and clearance handling for SUMO traffic-light commands."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, TypeAlias


@dataclass(frozen=True)
class Accepted:
    """A signal command accepted by the safety layer."""

    reason: str = "accepted"


@dataclass(frozen=True)
class Rejected:
    """A signal command rejected with an explanation."""

    reason: str


ActionResult: TypeAlias = Accepted | Rejected


class SignalSafetyLayer:
    """Validate signal requests against one TLS's inspected SUMO program."""

    def __init__(self, client: Any, tls_config: dict[str, Any]) -> None:
        self.client = client
        self.tls_id = str(tls_config["tls_id"])
        self.green_phases = tuple(int(i) for i in tls_config["green_phases"])
        self.yellow_after = {int(k): int(v) for k, v in tls_config["yellow_after"].items()}
        self.all_red_phases = tuple(int(i) for i in tls_config.get("all_red_phases", ()))
        self.min_green = float(tls_config["min_green_s"])
        self.max_green = float(tls_config["max_green_s"])
        self.approaches = tls_config.get("approaches", ())
        self._validate_config()
        self._phases = self._load_verified_program()
        self._allowed_phases = (
            set(self.green_phases) | set(self.yellow_after.values()) | set(self.all_red_phases)
        )
        self._approach_phases = self._map_approaches()
        self._target_green: int | None = None
        self._last_phase = int(self._trafficlight().getPhase(self.tls_id))
        self._green_started = self._now() - self._spent()
        self._clearance_seen = False
        if self._last_phase in self.green_phases:
            self._enforce_minimum_on_entry(self._last_phase)

    def request_switch(self) -> ActionResult:
        """Request the next verified green, beginning with configured yellow clearance."""
        phase = self._current_phase()
        if phase not in self.green_phases:
            return Rejected("signal is already in a clearance phase")
        if self.elapsed_green < self.min_green:
            return Rejected(f"minimum green not met ({self.elapsed_green:.2f}s < {self.min_green:g}s)")
        yellow = self.yellow_after.get(phase)
        if yellow not in self._phases or not self._is_clearance(yellow):
            return Rejected(f"no verified yellow clearance follows green phase {phase}")
        self._target_green = self._next_green(phase)
        self._clearance_seen = False
        self._apply_phase(yellow)
        return Accepted("yellow clearance started")

    def request_extend(self, seconds: float) -> ActionResult:
        """Extend the current green without allowing it to exceed max_green."""
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            return Rejected("extension must be a finite positive number")
        if not math.isfinite(seconds) or seconds <= 0:
            return Rejected("extension must be a finite positive number")
        phase = self._current_phase()
        if phase not in self.green_phases:
            return Rejected("green can only be extended during a verified green phase")
        elapsed = self.elapsed_green
        remaining = max(0.0, float(self._trafficlight().getNextSwitch(self.tls_id)) - self._now())
        allowed_remaining = self.max_green - elapsed
        if allowed_remaining <= remaining:
            return Rejected("current green is already at its maximum duration")
        new_remaining = min(remaining + seconds, allowed_remaining)
        if new_remaining <= remaining:
            return Rejected("extension would exceed maximum green")
        self._trafficlight().setPhaseDuration(self.tls_id, new_remaining)
        return Accepted(f"green extended by {new_remaining - remaining:.2f}s")

    def tick(self) -> ActionResult:
        """Update phase bookkeeping and enforce green bounds after each simulation step."""
        phase = self._current_phase()
        if phase not in self._phases:
            return Rejected(f"SUMO entered unverified phase {phase}")
        if phase != self._last_phase:
            previous = self._last_phase
            self._last_phase = phase
            if self._is_clearance(phase):
                self._clearance_seen = True
            if phase in self.green_phases:
                if previous in self.green_phases and not self._clearance_seen:
                    return Rejected("green phase changed without verified yellow/all-red clearance")
                self._green_started = self._now() - self._spent()
                self._enforce_minimum_on_entry(phase)
                self._clearance_seen = False
                if self._target_green is not None and phase != self._target_green:
                    target = self._target_green
                    self._target_green = None
                    self._apply_phase(target)
                    self._last_phase = target
                    self._green_started = self._now()
                    self._enforce_minimum_on_entry(target)
                else:
                    self._target_green = None
        if phase in self.green_phases and self.elapsed_green >= self.max_green:
            yellow = self.yellow_after[phase]
            self._target_green = self._next_green(phase)
            self._clearance_seen = False
            self._apply_phase(yellow)
            return Accepted("maximum green reached; yellow clearance started")
        return Accepted("signal state checked")

    def request_green_for_approach(self, name: str) -> ActionResult:
        """Request a verified green serving an approach, with clearance on a switch."""
        targets = self._approach_phases.get(name)
        if not targets:
            return Rejected(f"no verified green phase serves approach {name!r}")
        current = self._current_phase()
        if current in targets:
            return Accepted(f"approach {name!r} already has green")
        if current not in self.green_phases:
            return Rejected("cannot request an approach while signal is in clearance")
        if self.elapsed_green < self.min_green:
            return Rejected(f"minimum green not met ({self.elapsed_green:.2f}s < {self.min_green:g}s)")
        yellow = self.yellow_after[current]
        self._target_green = next((p for p in self.green_phases if p in targets), None)
        if self._target_green is None:
            return Rejected(f"no verified green phase serves approach {name!r}")
        self._clearance_seen = False
        self._apply_phase(yellow)
        return Accepted(f"yellow clearance started for approach {name!r}")

    @property
    def elapsed_green(self) -> float:
        """Return elapsed time in the current green phase."""
        if self._current_phase() not in self.green_phases:
            return 0.0
        return max(0.0, self._now() - self._green_started)

    def _validate_config(self) -> None:
        if not self.tls_id:
            raise ValueError("tls_config must define tls_id")
        if not self.green_phases or set(self.green_phases) != set(self.yellow_after):
            raise ValueError("every verified green phase must map to one yellow clearance phase")
        if len(set(self.green_phases)) != len(self.green_phases):
            raise ValueError("green phase indices must be unique")
        if self.min_green <= 0 or self.max_green < self.min_green:
            raise ValueError("green bounds must satisfy 0 < min_green_s <= max_green_s")

    def _load_verified_program(self) -> dict[int, str]:
        logic_list = self._trafficlight().getAllProgramLogics(self.tls_id)
        current_program = self._trafficlight().getProgram(self.tls_id)
        logic = next((item for item in logic_list if item.programID == current_program), None)
        if logic is None:
            raise ValueError(f"cannot inspect active program {current_program!r} for {self.tls_id}")
        phases = {index: str(item.state) for index, item in enumerate(logic.phases)}
        required = set(self.green_phases) | set(self.yellow_after.values()) | set(self.all_red_phases)
        if not required.issubset(phases):
            raise ValueError(f"configured phase indices are absent from active program: {sorted(required - phases.keys())}")
        for green in self.green_phases:
            if not any(char in "Gg" for char in phases[green]):
                raise ValueError(f"configured green phase {green} has no green signal")
            yellow = self.yellow_after[green]
            if not any(char in "Yy" for char in phases[yellow]):
                raise ValueError(f"configured clearance phase {yellow} has no yellow signal")
        for red in self.all_red_phases:
            if any(char in "GgYy" for char in phases[red]):
                raise ValueError(f"configured all-red phase {red} contains a non-red signal")
        for green in self.green_phases:
            yellow = self.yellow_after[green]
            if (green + 1) % len(phases) != yellow:
                raise ValueError(f"yellow phase {yellow} does not immediately follow green phase {green}")
            cursor = (yellow + 1) % len(phases)
            while cursor not in self.green_phases:
                state = phases[cursor]
                if cursor not in self.all_red_phases and not any(char in "Yy" for char in state):
                    raise ValueError(f"unverified transition phase {cursor} follows green phase {green}")
                cursor = (cursor + 1) % len(phases)
            if cursor != self._next_green(green):
                raise ValueError(f"program transition after green phase {green} skips the expected green")
        return phases

    def _map_approaches(self) -> dict[str, tuple[int, ...]]:
        result: dict[str, tuple[int, ...]] = {}
        for approach in self.approaches:
            name = approach.get("name")
            lanes = set(approach.get("lanes", ()))
            edges = {str(approach.get("incoming_edge", ""))}
            phases: set[int] = set()
            for link_index, groups in self.client.net.getTLS(self.tls_id).getLinks().items():
                for link_group in groups:
                    from_lane = link_group[0]
                    if from_lane.getID() in lanes or from_lane.getEdge().getID() in edges:
                        phases.update(
                            phase for phase in self.green_phases
                            if self._phases[phase][link_index] in "Gg"
                        )
            if name:
                result[str(name)] = tuple(sorted(phases))
        return result

    def _trafficlight(self) -> Any:
        return self.client.connection.trafficlight

    def _current_phase(self) -> int:
        return int(self._trafficlight().getPhase(self.tls_id))

    def _now(self) -> float:
        return float(self.client.sim_time)

    def _spent(self) -> float:
        return float(self._trafficlight().getSpentDuration(self.tls_id))

    def _is_clearance(self, phase: int) -> bool:
        state = self._phases[phase]
        return phase in self.all_red_phases or any(char in "Yy" for char in state)

    def _next_green(self, phase: int) -> int:
        index = self.green_phases.index(phase)
        return self.green_phases[(index + 1) % len(self.green_phases)]

    def _enforce_minimum_on_entry(self, phase: int) -> None:
        spent = self._spent()
        if spent < self.min_green:
            remaining = self.min_green - spent
            self._trafficlight().setPhaseDuration(self.tls_id, remaining)

    def _apply_phase(self, phase: int) -> None:
        if phase not in self._allowed_phases:
            raise ValueError(f"refusing to apply unverified phase {phase}")
        self._trafficlight().setPhase(self.tls_id, phase)
