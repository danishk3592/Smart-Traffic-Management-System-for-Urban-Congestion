"""Traffic state models and SUMO sensor aggregation for one junction."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
import traci

Source = Literal["sumo"]
DEFAULT_THRESHOLDS = {
    "low_max_halting": 4,
    "medium_max_halting": 12,
    "high_min_halting": 13,
}
APPROACH_VECTOR_FIELDS = ("vehicle_count", "halting", "mean_speed", "waiting_time")


@dataclass
class ApproachState:
    """Measurements aggregated over the incoming lanes of one approach.

    ``waiting_time`` is the mean accumulated waiting time, in seconds, of
    halting vehicles. ``queue_length`` is the sum of stopped vehicle lengths
    and minimum gaps, in metres.
    """

    name: str
    vehicle_count: int | None
    halting: int | None
    mean_speed: float | None
    waiting_time: float | None
    queue_length: float | None
    congestion: str | None
    available_fields: list[str]


@dataclass
class IntersectionState:
    """Serializable snapshot of one signalized intersection."""

    timestamp_utc: datetime
    sim_time: float
    intersection_id: str
    approaches: list[ApproachState]
    phase: int | None
    phase_elapsed_s: float | None
    mode: str
    totals: dict[str, int | float | None]
    source: Source

    def __post_init__(self) -> None:
        if self.source != "sumo":
            raise ValueError("source must be 'sumo'")
        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if self.timestamp_utc.utcoffset().total_seconds() != 0:
            raise ValueError("timestamp_utc must use UTC")

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready values with an ISO-8601 UTC timestamp."""
        timestamp = self.timestamp_utc.isoformat(timespec="milliseconds")
        if timestamp.endswith("+00:00"):
            timestamp = timestamp[:-6] + "Z"
        return {
            "timestamp_utc": timestamp,
            "sim_time": float(self.sim_time),
            "intersection_id": self.intersection_id,
            "approaches": [
                {
                    "name": approach.name,
                    "vehicle_count": approach.vehicle_count,
                    "halting": approach.halting,
                    "mean_speed": approach.mean_speed,
                    "waiting_time": approach.waiting_time,
                    "queue_length": approach.queue_length,
                    "congestion": approach.congestion,
                    "available_fields": list(approach.available_fields),
                }
                for approach in self.approaches
            ],
            "phase": self.phase,
            "phase_elapsed_s": self.phase_elapsed_s,
            "mode": self.mode,
            "totals": dict(self.totals),
            "source": self.source,
        }


@dataclass(frozen=True)
class VectorNorm:
    """Configured feature order and clipping scales for ``to_vector``."""

    approach_names: tuple[str, ...]
    green_phases: tuple[int, ...]
    max_vehicle_count: float
    max_halting: float
    max_mean_speed_mps: float
    max_waiting_time_s: float
    max_phase_elapsed_s: float

    def __post_init__(self) -> None:
        if not self.approach_names or len(set(self.approach_names)) != len(self.approach_names):
            raise ValueError("approach_names must be non-empty and unique")
        if len(set(self.green_phases)) != len(self.green_phases):
            raise ValueError("green_phases must be unique")
        for name in (
            "max_vehicle_count",
            "max_halting",
            "max_mean_speed_mps",
            "max_waiting_time_s",
            "max_phase_elapsed_s",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")

    @property
    def vector_length(self) -> int:
        """Four measurements and four availability masks per approach, plus phase."""
        return len(self.approach_names) * 8 + len(self.green_phases) + 2


def congestion_level(halting: int, thresholds: Mapping[str, int]) -> str:
    """Classify halting vehicles using configured inclusive boundaries."""
    low_max = int(thresholds["low_max_halting"])
    medium_max = int(thresholds["medium_max_halting"])
    high_min = int(thresholds["high_min_halting"])
    if low_max < 0 or medium_max < low_max or high_min <= medium_max:
        raise ValueError("congestion thresholds must be ordered and non-negative")
    if halting <= low_max:
        return "Low"
    if halting <= medium_max:
        return "Medium"
    return "High"


def vector_norm_from_config(
    project_config: Mapping[str, Any], tls_config: Mapping[str, Any] | None = None
) -> VectorNorm:
    """Build the stable vector layout from project and per-TLS configuration."""
    target = tls_config or project_config.get("intersection")
    if not isinstance(target, Mapping):
        raise TypeError("TLS config must be a mapping with approaches and green_phases")
    approaches = target.get("approaches")
    green_phases = target.get("green_phases")
    if not isinstance(approaches, Sequence) or isinstance(approaches, (str, bytes)):
        raise TypeError("TLS config approaches must be a sequence")
    if not isinstance(green_phases, Sequence) or isinstance(green_phases, (str, bytes)):
        raise TypeError("TLS config green_phases must be a sequence")
    names = tuple(str(item["name"]) for item in approaches)
    scales = project_config.get("state", {}).get("vector_normalization", {})
    signal = project_config.get("signal", {})
    return VectorNorm(
        approach_names=names,
        green_phases=tuple(int(phase) for phase in green_phases),
        max_vehicle_count=float(scales.get("max_vehicle_count", 60)),
        max_halting=float(scales.get("max_halting", 60)),
        max_mean_speed_mps=float(scales.get("max_mean_speed_mps", 15)),
        max_waiting_time_s=float(scales.get("max_waiting_time_s", 300)),
        max_phase_elapsed_s=float(signal.get("max_green_s", 60)),
    )


def to_vector(state: IntersectionState, norm: VectorNorm) -> np.ndarray:
    """Encode per-approach count/halting/speed/wait, validity, phase and elapsed time.

    The fixed layout is eight values per configured approach (four normalized
    values followed by four availability masks), one-hot green phase, normalized
    phase elapsed time, and an elapsed-time availability mask. Missing approaches
    and unavailable values are zero-filled with a zero mask. All output is float32
    and clipped to [0, 1].
    """
    by_name = {approach.name: approach for approach in state.approaches}
    values: list[float] = []
    maxima = {
        "vehicle_count": norm.max_vehicle_count,
        "halting": norm.max_halting,
        "mean_speed": norm.max_mean_speed_mps,
        "waiting_time": norm.max_waiting_time_s,
    }
    for name in norm.approach_names:
        approach = by_name.get(name)
        available = set(approach.available_fields) if approach is not None else set()
        fields = [getattr(approach, field) if approach is not None else None for field in APPROACH_VECTOR_FIELDS]
        values.extend(
            0.0
            if value is None or field not in available
            else _clip_unit(float(value) / maxima[field])
            for field, value in zip(APPROACH_VECTOR_FIELDS, fields, strict=True)
        )
        values.extend(
            1.0 if value is not None and field in available else 0.0
            for field, value in zip(APPROACH_VECTOR_FIELDS, fields, strict=True)
        )

    values.extend(1.0 if state.phase == phase else 0.0 for phase in norm.green_phases)
    has_elapsed = state.phase_elapsed_s is not None
    values.append(
        _clip_unit(float(state.phase_elapsed_s) / norm.max_phase_elapsed_s)
        if has_elapsed
        else 0.0
    )
    values.append(1.0 if has_elapsed else 0.0)
    vector = np.asarray(values, dtype=np.float32)
    if vector.size != norm.vector_length:
        raise ValueError(f"vector length {vector.size} does not match configured {norm.vector_length}")
    return vector


def _clip_unit(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return min(1.0, max(0.0, value))


class SumoSensorReader:
    """Aggregate lane-level TraCI measurements for configured approaches."""

    def __init__(
        self,
        tls_config: Mapping[str, Any],
        thresholds: Mapping[str, int] | None = None,
    ) -> None:
        self.tls_config = tls_config
        self.thresholds = dict(thresholds or DEFAULT_THRESHOLDS)
        self._previous_vehicle_ids: set[str] | None = None
        self._previous_sim_time: float | None = None
        approaches = tls_config.get("approaches")
        if not isinstance(approaches, Sequence) or isinstance(approaches, (str, bytes)):
            raise TypeError("TLS config approaches must be a sequence")
        if not approaches:
            raise ValueError("TLS config must define at least one approach")
        names = [str(item["name"]) for item in approaches]
        if len(names) != len(set(names)):
            raise ValueError("approach names must be unique")
        lanes = [str(lane) for item in approaches for lane in item.get("lanes", [])]
        if not lanes or len(lanes) != len(set(lanes)):
            raise ValueError("approach lanes must be non-empty and unique")

    def read(self, client: Any) -> IntersectionState:
        """Read one simulation snapshot; a first sample reports zero throughput."""
        connection = getattr(client, "connection", client)
        sim_time = float(client.sim_time if hasattr(client, "sim_time") else connection.simulation.getTime())
        tls_id = self._tls_id(client)
        lane_domain = connection.lane
        vehicle_domain = connection.vehicle
        current_ids: set[str] = set()
        approach_states: list[ApproachState] = []
        all_waiting: list[float] = []
        for approach in self.tls_config["approaches"]:
            lane_ids = [str(lane_id) for lane_id in approach["lanes"]]
            lane_counts = [int(lane_domain.getLastStepVehicleNumber(lane_id)) for lane_id in lane_ids]
            lane_halting = [int(lane_domain.getLastStepHaltingNumber(lane_id)) for lane_id in lane_ids]
            lane_speeds = [float(lane_domain.getLastStepMeanSpeed(lane_id)) for lane_id in lane_ids]
            ids_by_lane = [tuple(lane_domain.getLastStepVehicleIDs(lane_id)) for lane_id in lane_ids]
            vehicle_ids = list(dict.fromkeys(vehicle_id for ids in ids_by_lane for vehicle_id in ids))
            current_ids.update(vehicle_ids)
            halting_ids = [vehicle_id for vehicle_id in vehicle_ids if float(vehicle_domain.getSpeed(vehicle_id)) < 0.1]
            waits = [float(vehicle_domain.getWaitingTime(vehicle_id)) for vehicle_id in halting_ids]
            all_waiting.extend(waits)
            queue_length = sum(
                float(vehicle_domain.getLength(vehicle_id)) + float(vehicle_domain.getMinGap(vehicle_id))
                for vehicle_id in halting_ids
            )
            vehicle_count = sum(lane_counts)
            speed_weight = sum(max(0.0, speed) * count for speed, count in zip(lane_speeds, lane_counts, strict=True))
            mean_speed = speed_weight / vehicle_count if vehicle_count else 0.0
            halting_count = sum(lane_halting)
            average_wait = sum(waits) / len(waits) if waits else 0.0
            fields = ["vehicle_count", "halting", "mean_speed", "waiting_time", "queue_length", "congestion"]
            approach_states.append(
                ApproachState(
                    name=str(approach["name"]),
                    vehicle_count=vehicle_count,
                    halting=halting_count,
                    mean_speed=mean_speed,
                    waiting_time=average_wait,
                    queue_length=queue_length,
                    congestion=congestion_level(halting_count, self.thresholds),
                    available_fields=fields,
                )
            )

        departed_from_approaches = 0
        if self._previous_vehicle_ids is not None and self._previous_sim_time is not None:
            elapsed = sim_time - self._previous_sim_time
            if elapsed > 0:
                departed = self._previous_vehicle_ids - current_ids
                try:
                    teleported = set(connection.simulation.getStartingTeleportIDList())
                except (AttributeError, traci.exceptions.TraCIException):
                    teleported = set()
                departed_from_approaches = len(departed - teleported)
        elapsed = (
            sim_time - self._previous_sim_time
            if self._previous_sim_time is not None and sim_time > self._previous_sim_time
            else 0.0
        )
        throughput = departed_from_approaches * 60.0 / elapsed if elapsed else 0.0
        self._previous_vehicle_ids = current_ids
        self._previous_sim_time = sim_time

        traffic_light = connection.trafficlight
        phase = int(traffic_light.getPhase(tls_id))
        try:
            phase_elapsed = float(traffic_light.getSpentDuration(tls_id))
        except (AttributeError, traci.exceptions.TraCIException):
            phase_elapsed = None
        signal_state = str(traffic_light.getRedYellowGreenState(tls_id))
        if any(char in "Gg" for char in signal_state):
            mode = "green"
        elif any(char in "Yy" for char in signal_state):
            mode = "yellow"
        else:
            mode = "red"
        waiting_count = sum(state.halting or 0 for state in approach_states)
        totals = {
            "waiting_vehicles": waiting_count,
            "avg_wait": sum(all_waiting) / len(all_waiting) if all_waiting else 0.0,
            "throughput_veh_min": throughput,
        }
        return IntersectionState(
            timestamp_utc=datetime.now(timezone.utc),
            sim_time=sim_time,
            intersection_id=tls_id,
            approaches=approach_states,
            phase=phase,
            phase_elapsed_s=phase_elapsed,
            mode=mode,
            totals=totals,
            source="sumo",
        )

    def _tls_id(self, client: Any) -> str:
        configured_id = self.tls_config.get("tls_id") or self.tls_config.get("id")
        if configured_id:
            return str(configured_id)
        net = getattr(client, "net", None)
        if net is None:
            raise ValueError("TLS config needs tls_id, or client must expose the SUMO net")
        input_lanes = {
            str(lane)
            for approach in self.tls_config["approaches"]
            for lane in approach["lanes"]
        }
        matches = []
        for tls in net.getTrafficLights():
            controlled_lanes = {
                group[0].getID()
                for groups in tls.getLinks().values()
                for group in groups
            }
            if input_lanes.issubset(controlled_lanes):
                matches.append(str(tls.getID()))
        if len(matches) != 1:
            raise ValueError(f"Could not uniquely resolve TLS from configured lanes: {matches}")
        return matches[0]
