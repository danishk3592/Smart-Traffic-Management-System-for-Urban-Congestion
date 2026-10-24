"""Focused unit coverage for signal request validation."""

from types import SimpleNamespace

import pytest

from Ai.controllers.safety import Accepted, Rejected, SignalSafetyLayer


class FakeTrafficLight:
    def __init__(self) -> None:
        self.phase = 0
        self.spent = 12.0
        self.next_switch = 20.0
        self.applied: list[int] = []
        self.duration: float | None = None
        self.states = ["Grr", "yrr", "rGr", "ryr"]

    def getAllProgramLogics(self, _tls_id: str) -> list[object]:
        return [SimpleNamespace(programID="0", phases=[SimpleNamespace(state=s) for s in self.states])]

    def getProgram(self, _tls_id: str) -> str:
        return "0"

    def getPhase(self, _tls_id: str) -> int:
        return self.phase

    def getSpentDuration(self, _tls_id: str) -> float:
        return self.spent

    def getNextSwitch(self, _tls_id: str) -> float:
        return self.next_switch

    def setPhase(self, _tls_id: str, phase: int) -> None:
        self.phase = phase
        self.spent = 0.0
        self.applied.append(phase)

    def setPhaseDuration(self, _tls_id: str, duration: float) -> None:
        self.duration = duration


class FakeClient:
    sim_time = 12.0

    def __init__(self) -> None:
        self.connection = SimpleNamespace(trafficlight=FakeTrafficLight())


@pytest.fixture
def setup_layer() -> tuple[FakeClient, SignalSafetyLayer]:
    client = FakeClient()
    config = {
        "tls_id": "tls",
        "green_phases": [0, 2],
        "yellow_after": {0: 1, 2: 3},
        "min_green_s": 10,
        "max_green_s": 30,
    }
    return client, SignalSafetyLayer(client, config)


def test_valid_switch_enters_verified_yellow(setup_layer: tuple[FakeClient, SignalSafetyLayer]) -> None:
    client, layer = setup_layer
    result = layer.request_switch()
    assert isinstance(result, Accepted)
    assert client.connection.trafficlight.applied == [1]


def test_early_switch_and_invalid_extension_are_rejected(
    setup_layer: tuple[FakeClient, SignalSafetyLayer],
) -> None:
    client, layer = setup_layer
    client.connection.trafficlight.spent = 2
    client.sim_time = 2
    assert isinstance(layer.request_switch(), Rejected)
    assert isinstance(layer.request_extend(0), Rejected)
    assert isinstance(layer.request_extend(float("nan")), Rejected)
    assert client.connection.trafficlight.applied == []


def test_phase_transition_requires_and_tracks_clearance(
    setup_layer: tuple[FakeClient, SignalSafetyLayer],
) -> None:
    client, layer = setup_layer
    light = client.connection.trafficlight
    assert isinstance(layer.request_switch(), Accepted)
    light.phase = 1
    client.sim_time = 13
    assert isinstance(layer.tick(), Accepted)
    light.phase = 2
    client.sim_time = 18
    assert isinstance(layer.tick(), Accepted)
    assert layer.elapsed_green == pytest.approx(0)


def test_extension_is_capped_at_maximum_green(
    setup_layer: tuple[FakeClient, SignalSafetyLayer],
) -> None:
    client, layer = setup_layer
    light = client.connection.trafficlight
    light.spent = 20
    client.sim_time = 20
    light.next_switch = 25
    assert isinstance(layer.request_extend(100), Accepted)
    assert light.duration == pytest.approx(10)


def test_unknown_tls_phase_configuration_is_rejected() -> None:
    client = FakeClient()
    config = {
        "tls_id": "tls",
        "green_phases": [4],
        "yellow_after": {4: 1},
        "min_green_s": 10,
        "max_green_s": 30,
    }
    with pytest.raises(ValueError, match="absent from active program"):
        SignalSafetyLayer(client, config)
