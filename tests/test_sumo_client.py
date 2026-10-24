"""SUMO-backed client lifecycle and fail-fast input tests."""

from pathlib import Path

import pytest

from Ai.common.sumo_client import SumoClient


@pytest.mark.sumo
def test_client_starts_steps_and_closes() -> None:
    with SumoClient(seed=314) as client:
        assert client.connection.simulation.getTime() == 0
        client.step()
        assert client.sim_time > 0
        assert client.connection.simulation.getMinExpectedNumber() >= 0
    assert not client._started


@pytest.mark.sumo
def test_missing_route_file_fails_before_start(tmp_path: Path) -> None:
    config = tmp_path / "bad.sumocfg"
    net_path = Path(__file__).resolve().parents[1] / "SUMO" / "No_Polygon_Map" / "osm.net.xml"
    config.write_text(
        f'<configuration><input><net-file value="{net_path.as_posix()}"/>'
        '<route-files value="missing.rou.xml"/></input></configuration>',
        encoding="utf-8",
    )
    yaml_config = tmp_path / "stms.yaml"
    yaml_config.write_text(
        f"sumo:\n  config: {config.as_posix()}\n  tls_id: missing\n",
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="route-files"):
        SumoClient(config_path=yaml_config, repo_root=tmp_path).__enter__()


@pytest.mark.sumo
def test_traci_loss_stops_the_owned_sumo_process() -> None:
    client = SumoClient(seed=2718)
    with pytest.raises(RuntimeError, match="TraCI connection was lost"), client:
        client._process.terminate()
        client._process.wait(timeout=5)
        client.step()
    assert not client._started
