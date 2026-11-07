"""SUMO-backed safety inventory checks for the frozen intended TLS set."""

from pathlib import Path

import pytest
import yaml

from Ai.common.junction import controlled_movements
from Ai.common.sumo_client import SumoClient
from Ai.controllers.safety import SignalSafetyLayer
from scripts.inspect_network_tls import _network_path
from scripts.inspect_tls import _conflicts

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.sumo
def test_every_intended_tls_has_conflict_free_greens_and_verified_yellows() -> None:
    config = yaml.safe_load((ROOT / "config" / "stms.yaml").read_text(encoding="utf-8"))
    sumo_config = Path(config["sumo"]["config"])
    if not sumo_config.is_absolute():
        sumo_config = ROOT / sumo_config
    net_path = _network_path(sumo_config.resolve())

    with SumoClient(seed=1000) as client:
        runtime_ids = set(client.connection.trafficlight.getIDList())
        assert set(config["network"]["controlled_tls"]).issubset(runtime_ids)
        for tls_config in config["network"]["tls_configs"]:
            tls_id = tls_config["tls_id"]
            program_id = client.connection.trafficlight.getProgram(tls_id)
            logic = next(
                item for item in client.connection.trafficlight.getAllProgramLogics(tls_id)
                if item.programID == program_id
            )
            phases = list(logic.phases)
            assert len(tls_config["green_phases"]) >= 2
            conflicts, _ = _conflicts(
                client.net, net_path, tls_id, controlled_movements(client.net, tls_id), phases
            )
            assert not conflicts, f"{tls_id}: {conflicts}"
            SignalSafetyLayer(client, {**tls_config, "min_green_s": 10, "max_green_s": 60})
