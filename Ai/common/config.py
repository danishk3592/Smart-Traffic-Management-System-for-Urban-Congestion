"""Load and validate the project YAML configuration."""

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the STMS configuration, defaulting to config/stms.yaml in the repository."""
    if config_path is None:
        path = Path(__file__).resolve().parents[2] / "config" / "stms.yaml"
    else:
        path = Path(config_path).expanduser()

    with path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise TypeError(f"Configuration must contain a YAML mapping: {path}")

    sumo = config.get("sumo")
    if not isinstance(sumo, dict) or not isinstance(sumo.get("tls_id"), str):
        raise TypeError(f"Configuration is missing sumo.tls_id: {path}")

    return config