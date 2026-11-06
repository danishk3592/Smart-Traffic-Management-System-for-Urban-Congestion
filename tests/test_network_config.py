"""Validate the frozen network TLS configuration and its documentation."""

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_tls_configuration_matches_inventory_and_hash() -> None:
    config = yaml.safe_load((ROOT / "config" / "stms.yaml").read_text(encoding="utf-8"))
    network = config["network"]
    intended = network["controlled_tls"]
    excluded = network["excluded_tls"]
    inventory = (ROOT / "docs" / "network_tls.md").read_text(encoding="utf-8")

    assert intended
    assert config["sumo"]["tls_id"] in intended
    assert set(intended).isdisjoint(excluded)
    assert len(intended) == len(set(intended))
    assert len(excluded) == len(set(excluded))
    assert all(f"`{tls_id}`" in inventory for tls_id in (*intended, *excluded))
    payload = json.dumps(sorted(intended), separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(payload).hexdigest() == network["tls_list_hash"]
    assert network["frozen_utc"]
    assert network["max_approaches"] == max(len(item["approaches"]) for item in network["tls_configs"])
    assert network["max_phases"] == max(len(item["green_phases"]) for item in network["tls_configs"])
    assert {item["tls_id"] for item in network["tls_configs"]} == set(intended)
    assert all(item["green_phases"] and item["yellow_after"] for item in network["tls_configs"])
