"""Tests for the project configuration loader."""

import pytest

from Ai.common.config import load_config


def test_loads_default_project_config() -> None:
    config = load_config()

    assert config["sumo"]["tls_id"] == (
        "cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881"
    )
    assert config["sumo"]["max_sim_s"] == 7200


def test_rejects_a_non_mapping_configuration(tmp_path) -> None:
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("- not a mapping\n", encoding="utf-8")

    with pytest.raises(TypeError, match="YAML mapping"):
        load_config(config_path)
