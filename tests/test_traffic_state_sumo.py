"""Live SUMO acceptance test for the T1.1 sensor reader."""

from __future__ import annotations

import math

import pytest

from Ai.common.config import load_config
from Ai.common.sumo_client import SumoClient
from Ai.common.traffic_state import SumoSensorReader, to_vector, vector_norm_from_config


@pytest.mark.sumo
def test_live_sensor_reader_runs_for_60_seconds_with_configured_vector() -> None:
    config = load_config()
    tls_config = config["intersection"]
    reader = SumoSensorReader(tls_config, config["congestion"]["thresholds"])
    norm = vector_norm_from_config(config, tls_config)

    with SumoClient(seed=1000) as client:
        state = reader.read(client)
        for _ in range(60):
            client.step()
            state = reader.read(client)
            vector = to_vector(state, norm)
            assert vector.shape == (norm.vector_length,)
            assert all(math.isfinite(float(value)) for value in vector)
            assert (vector >= 0).all() and (vector <= 1).all()
            assert len(state.approaches) == len(tls_config["approaches"])
            assert state.source == "sumo"
            assert all(math.isfinite(float(value)) for value in state.totals.values())
