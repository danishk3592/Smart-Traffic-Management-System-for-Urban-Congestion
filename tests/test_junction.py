"""Tests for controller-independent junction route membership."""

import xml.etree.ElementTree as ET
from pathlib import Path

from sumolib.net import readNet

from Ai.common.config import load_config
from Ai.common.junction import controlled_movements, route_uses_controlled_movement

MOVEMENTS = [
    {"from_edge": "north_in", "to_edge": "south_out", "link_indices": [2]},
    {"from_edge": "east_in", "to_edge": "west_out", "link_indices": [4]},
]


def test_route_uses_a_controlled_movement() -> None:
    assert route_uses_controlled_movement(
        ["origin", "north_in", "south_out", "destination"], MOVEMENTS
    )


def test_touching_incoming_edge_without_crossing_is_not_a_match() -> None:
    assert not route_uses_controlled_movement(["origin", "north_in", "side_road"], MOVEMENTS)


def test_route_ending_on_incoming_edge_is_not_a_match() -> None:
    assert not route_uses_controlled_movement(["origin", "north_in"], MOVEMENTS)


def test_configured_movements_match_the_sumo_network() -> None:
    config = load_config()
    root = Path(__file__).resolve().parents[1]
    sumo_config = root / config["sumo"]["config"]
    net_file = ET.parse(sumo_config).getroot().find("input/net-file").get("value")
    net = readNet(str(sumo_config.parent / net_file), withPrograms=True)
    assert controlled_movements(net, config["sumo"]["tls_id"]) == config["intersection"][
        "movements"
    ]
