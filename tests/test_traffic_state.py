"""Unit tests for traffic state normalization and sensor aggregation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import ClassVar

import numpy as np
import pytest

from Ai.common.config import load_config
from Ai.common.traffic_state import (
    ApproachState,
    IntersectionState,
    SumoSensorReader,
    VectorNorm,
    congestion_level,
    to_vector,
    vector_norm_from_config,
)


def test_congestion_threshold_boundaries() -> None:
    thresholds = load_config()["congestion"]["thresholds"]
    assert congestion_level(0, thresholds) == "Low"
    assert congestion_level(4, thresholds) == "Low"
    assert congestion_level(5, thresholds) == "Medium"
    assert congestion_level(12, thresholds) == "Medium"
    assert congestion_level(13, thresholds) == "High"


def test_vector_uses_configured_shape_order_and_clips() -> None:
    config = load_config()
    norm = vector_norm_from_config(config)
    state = IntersectionState(
        timestamp_utc=datetime.now(timezone.utc),
        sim_time=30,
        intersection_id=config["sumo"]["tls_id"],
        approaches=[
            ApproachState(
                name="approach_1",
                vehicle_count=100,
                halting=65,
                mean_speed=20.0,
                waiting_time=400.0,
                queue_length=30.0,
                congestion="High",
                available_fields=["vehicle_count", "halting", "mean_speed", "waiting_time"],
            )
        ],
        phase=0,
        phase_elapsed_s=90.0,
        mode="green",
        totals={"waiting_vehicles": 65, "avg_wait": 10.0, "throughput_veh_min": 2.0},
        source="sumo",
    )

    vector = to_vector(state, norm)
    assert vector.dtype == np.float32
    assert vector.shape == (norm.vector_length,)
    assert np.isfinite(vector).all()
    assert vector.min() >= 0.0
    assert vector.max() <= 1.0
    assert vector[:4].tolist() == [1.0, 1.0, 1.0, 1.0]
    assert vector[4:8].tolist() == [1.0, 1.0, 1.0, 1.0]
    phase_offset = len(norm.approach_names) * 8
    assert vector[phase_offset : phase_offset + len(norm.green_phases)].sum() == 1.0


def test_vector_encodes_unavailable_fields_and_missing_approaches() -> None:
    norm = VectorNorm(
        approach_names=("north", "south"),
        green_phases=(0, 2),
        max_vehicle_count=10,
        max_halting=10,
        max_mean_speed_mps=10,
        max_waiting_time_s=100,
        max_phase_elapsed_s=60,
    )
    state = IntersectionState(
        timestamp_utc=datetime.now(timezone.utc),
        sim_time=1,
        intersection_id="tls",
        approaches=[
            ApproachState("north", 3, 1, 4.0, None, 5.0, "Low", ["vehicle_count", "halting", "mean_speed"])
        ],
        phase=1,
        phase_elapsed_s=None,
        mode="yellow",
        totals={"waiting_vehicles": 1, "avg_wait": 0.0, "throughput_veh_min": 0.0},
        source="camera",
    )

    vector = to_vector(state, norm)
    assert vector.shape == (2 * 8 + 2 + 2,)
    assert vector[0:4].tolist() == pytest.approx([0.3, 0.1, 0.4, 0.0])
    assert vector[4:8].tolist() == [1.0, 1.0, 1.0, 0.0]
    assert vector[8:16].tolist() == [0.0] * 8
    assert vector[-3:].tolist() == [0.0, 0.0, 0.0]


def test_state_to_dict_is_json_serializable_utc() -> None:
    state = IntersectionState(
        timestamp_utc=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        sim_time=12.5,
        intersection_id="tls",
        approaches=[ApproachState("north", None, 0, None, None, None, None, ["halting"])],
        phase=2,
        phase_elapsed_s=4.0,
        mode="green",
        totals={"waiting_vehicles": 0, "avg_wait": 0.0, "throughput_veh_min": 0.0},
        source="camera",
    )
    encoded = json.dumps(state.to_dict())
    decoded = json.loads(encoded)
    assert decoded["timestamp_utc"] == "2026-01-02T03:04:05.000Z"
    assert decoded["approaches"][0]["waiting_time"] is None
    assert decoded["approaches"][0]["available_fields"] == ["halting"]


class FakeLaneDomain:
    def __init__(self) -> None:
        self.vehicles = {"lane_a": ["v1", "v2"], "lane_b": ["v3"]}
        self.speeds = {"lane_a": 2.0, "lane_b": 4.0}

    def getLastStepVehicleNumber(self, lane_id: str) -> int:
        return len(self.vehicles[lane_id])

    def getLastStepHaltingNumber(self, lane_id: str) -> int:
        return sum(1 for vehicle_id in self.vehicles[lane_id] if vehicle_id in {"v1", "v3"})

    def getLastStepMeanSpeed(self, lane_id: str) -> float:
        return self.speeds[lane_id]

    def getLastStepVehicleIDs(self, lane_id: str) -> tuple[str, ...]:
        return tuple(self.vehicles[lane_id])


class FakeVehicleDomain:
    speeds: ClassVar[dict[str, float]] = {"v1": 0.0, "v2": 2.0, "v3": 0.0}
    waits: ClassVar[dict[str, float]] = {"v1": 20.0, "v2": 0.0, "v3": 40.0}

    def getSpeed(self, vehicle_id: str) -> float:
        return self.speeds[vehicle_id]

    def getWaitingTime(self, vehicle_id: str) -> float:
        return self.waits[vehicle_id]

    def getLength(self, vehicle_id: str) -> float:
        return 5.0

    def getMinGap(self, vehicle_id: str) -> float:
        return 2.5


class FakeTrafficLightDomain:
    def getPhase(self, tls_id: str) -> int:
        assert tls_id == "tls"
        return 2

    def getSpentDuration(self, tls_id: str) -> float:
        assert tls_id == "tls"
        return 7.0

    def getRedYellowGreenState(self, tls_id: str) -> str:
        assert tls_id == "tls"
        return "GGrr"


class FakeSimulationDomain:
    def getStartingTeleportIDList(self) -> list[str]:
        return []


class FakeConnection:
    def __init__(self) -> None:
        self.lane = FakeLaneDomain()
        self.vehicle = FakeVehicleDomain()
        self.trafficlight = FakeTrafficLightDomain()
        self.simulation = FakeSimulationDomain()


class FakeClient:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.sim_time = 0.0


def test_sumo_sensor_reader_aggregates_and_tracks_approach_exits() -> None:
    tls_config = {
        "tls_id": "tls",
        "approaches": [
            {"name": "north", "lanes": ["lane_a", "lane_b"]},
        ],
    }
    client = FakeClient()
    reader = SumoSensorReader(tls_config)
    first = reader.read(client)

    assert first.approaches[0].vehicle_count == 3
    assert first.approaches[0].halting == 2
    assert first.approaches[0].mean_speed == pytest.approx(8.0 / 3.0)
    assert first.approaches[0].waiting_time == pytest.approx(30.0)
    assert first.approaches[0].queue_length == pytest.approx(15.0)
    assert first.totals["throughput_veh_min"] == 0.0
    assert first.phase == 2
    assert first.phase_elapsed_s == 7.0

    client.connection.lane.vehicles = {"lane_a": ["v2"], "lane_b": []}
    client.sim_time = 2.0
    second = reader.read(client)
    assert second.totals["throughput_veh_min"] == pytest.approx(60.0)
