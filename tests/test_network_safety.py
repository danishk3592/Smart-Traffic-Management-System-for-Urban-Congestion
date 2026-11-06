"""Fuzz all frozen intended TLS simultaneously through their safety layers."""

import random
from pathlib import Path

import pytest

from Ai.common.config import load_config
from Ai.common.junction import controlled_movements
from Ai.common.sumo_client import SumoClient
from Ai.controllers.safety import Accepted, NetworkSafetyManager
from scripts.inspect_network_tls import _network_path
from scripts.inspect_tls import _conflicts

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.sumo
def test_network_safety_random_commands_for_1200_seconds() -> None:
    config = load_config()
    tls_configs = list(config["network"]["tls_configs"])
    excluded = set(config["network"]["excluded_tls"])
    static_ids = {
        item["tls_id"]: item["static_program_id"]
        for item in tls_configs if item.get("static_program_id")
    }
    static_file = ROOT / "SUMO" / "derived" / "network_static_tls.add.xml"
    net_path = _network_path((ROOT / config["sumo"]["config"]).resolve())
    rng = random.Random(731)

    with SumoClient(
        seed=1000, label="network_safety_fuzzer_731",
        extra_additional_files=(static_file,),
    ) as client:
        manager = NetworkSafetyManager(
            client, tls_configs, excluded_tls=tuple(excluded), static_program_ids=static_ids
        )
        assert set(manager.layers) == set(config["network"]["controlled_tls"])
        assert set(manager.layers).isdisjoint(excluded)
        lights = client.connection.trafficlight
        phases = {}
        green = {}
        yellow = {}
        for item in tls_configs:
            tls_id = item["tls_id"]
            program_id = lights.getProgram(tls_id)
            logic = next(
                value for value in lights.getAllProgramLogics(tls_id)
                if value.programID == program_id
            )
            phases[tls_id] = {index: phase.state for index, phase in enumerate(logic.phases)}
            green[tls_id] = set(item["green_phases"])
            yellow[tls_id] = set(item["yellow_after"].values())
            conflicts, _ = _conflicts(
                client.net, net_path, tls_id, controlled_movements(client.net, tls_id), list(logic.phases)
            )
            assert not conflicts, f"{tls_id}: {conflicts}"

        old_phase = {tls_id: lights.getPhase(tls_id) for tls_id in manager.layers}
        clearance_seen = {tls_id: old_phase[tls_id] in yellow[tls_id] for tls_id in manager.layers}
        green_started = {
            tls_id: client.sim_time - lights.getSpentDuration(tls_id)
            for tls_id in manager.layers
        }
        green_durations = {tls_id: [] for tls_id in manager.layers}
        while client.sim_time < 1200:
            for tls_id in manager.layers:
                choice = rng.randrange(3)
                if choice == 1:
                    manager.request(tls_id, "switch")
                elif choice == 2:
                    manager.request(tls_id, "extend", rng.uniform(1, 25))
            client.step()
            results = manager.tick_all()
            assert all(isinstance(result, Accepted) for result in results.values())
            for tls_id in manager.layers:
                phase = int(lights.getPhase(tls_id))
                assert phase in phases[tls_id]
                state = phases[tls_id][phase]
                assert (
                    not any(char in "Gg" for char in state)
                    or phase in green[tls_id]
                    or phase in yellow[tls_id]
                )
                if old_phase[tls_id] in green[tls_id] and phase != old_phase[tls_id]:
                    duration = client.sim_time - green_started[tls_id]
                    green_durations[tls_id].append(duration)
                    assert duration >= config["signal"]["min_green_s"] - 1e-6
                    assert phase in yellow[tls_id], f"{tls_id} skipped yellow"
                    clearance_seen[tls_id] = True
                elif phase in yellow[tls_id]:
                    clearance_seen[tls_id] = True
                if phase in green[tls_id]:
                    spent = float(lights.getSpentDuration(tls_id))
                    assert spent <= config["signal"]["max_green_s"] + 1e-6
                    if old_phase[tls_id] not in green[tls_id]:
                        assert clearance_seen[tls_id], f"{tls_id} changed green without clearance"
                        green_started[tls_id] = client.sim_time - spent
                        clearance_seen[tls_id] = False
                old_phase[tls_id] = phase
        assert all(green_durations[tls_id] for tls_id in manager.layers)
        assert client.sim_time >= 1200
