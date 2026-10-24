"""SUMO-backed safety fuzzer for the configured pilot signal program."""

import random

import pytest

from Ai.common.config import load_config
from Ai.common.sumo_client import SumoClient
from Ai.controllers.safety import Accepted, SignalSafetyLayer


@pytest.mark.sumo
def test_signal_safety_random_commands_for_1200_seconds() -> None:
    config = load_config()
    intersection = config["intersection"]
    tls_config = {
        **intersection,
        "tls_id": config["sumo"]["tls_id"],
        "min_green_s": config["signal"]["min_green_s"],
        "max_green_s": config["signal"]["max_green_s"],
    }
    green = set(tls_config["green_phases"])
    clearances = set(tls_config["yellow_after"].values())
    allowed = green | clearances | set(tls_config.get("all_red_phases", ()))
    rng = random.Random(731)

    with SumoClient(seed=1000, label="safety_fuzzer_731") as client:
        light = client.connection.trafficlight
        layer = SignalSafetyLayer(client, tls_config)
        previous_phase = int(light.getPhase(layer.tls_id))
        clearance_since_green = previous_phase in clearances
        green_started = client.sim_time - float(light.getSpentDuration(layer.tls_id))
        checked_green_durations: list[float] = []

        while client.sim_time < 1200:
            if rng.random() < 0.12:
                result = layer.request_switch()
                assert isinstance(result, (Accepted,)) or result.reason
            elif rng.random() < 0.16:
                result = layer.request_extend(rng.uniform(1, 25))
                assert isinstance(result, (Accepted,)) or result.reason
            if rng.random() < 0.02:
                result = layer.request_green_for_approach(f"unknown-{rng.randrange(10)}")
                assert result.reason

            client.step()
            phase = int(light.getPhase(layer.tls_id))
            result = layer.tick()
            assert isinstance(result, Accepted), getattr(result, "reason", "")
            assert phase in allowed, f"SUMO entered unverified phase {phase}"

            if previous_phase in green and phase != previous_phase:
                green_duration = client.sim_time - green_started
                checked_green_durations.append(green_duration)
                assert green_duration >= config["signal"]["min_green_s"] - 1e-6
                assert phase in clearances or phase in green
                if phase in green:
                    assert clearance_since_green, "green-to-green transition skipped clearance"
                clearance_since_green = phase in clearances
            elif phase in clearances:
                clearance_since_green = True

            if phase in green:
                spent = float(light.getSpentDuration(layer.tls_id))
                assert spent <= config["signal"]["max_green_s"] + 1e-6
                if previous_phase not in green:
                    green_started = client.sim_time - spent
            previous_phase = phase

        assert checked_green_durations, "fuzzer did not observe any completed green phase"
        assert client.sim_time >= 1200, "SUMO ended before the full fuzzer horizon"
