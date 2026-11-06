"""Unit checks for JSON-safe network state and sensor configuration."""

import json

import pytest

from Ai.common.network_state import NetworkSensorReader, NetworkState


def test_network_state_serializes_nested_intersections() -> None:
    state = NetworkState(sim_time=1, junctions={}, totals={"halting": 0})
    assert json.loads(json.dumps(state.to_dict())) == {
        "sim_time": 1.0,
        "junctions": {},
        "totals": {"halting": 0.0},
    }


def test_network_sensor_rejects_empty_or_duplicate_tls_configs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        NetworkSensorReader([])
    config = {"tls_id": "tls-a", "approaches": [{"name": "a", "lanes": ["lane-a"]}]}
    with pytest.raises(ValueError, match="unique"):
        NetworkSensorReader([config, config])
