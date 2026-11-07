"""PPO policy adapter for the shared controller and safety-layer interface."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from stable_baselines3 import PPO

from Ai.common.config import load_config
from Ai.common.traffic_state import IntersectionState, to_vector, vector_norm_from_config
from Ai.controllers.base import Action

_ACTIONS = (
    Action("hold"),
    Action("switch"),
    Action("extend", seconds=5.0),
    Action("extend", seconds=10.0),
)


class RLController:
    """Load a CPU PPO model and translate state snapshots into safe requests."""

    name = "rl"

    def __init__(
        self,
        model_path: str | Path,
        project_config: Mapping[str, Any] | None = None,
        *,
        tls_config: Mapping[str, Any] | None = None,
        model: Any | None = None,
    ) -> None:
        self.config = dict(project_config or load_config())
        self.tls = dict(tls_config or self.config["intersection"])
        self.tls.setdefault("tls_id", str(self.config["sumo"]["tls_id"]))
        self.norm = vector_norm_from_config(self.config, self.tls)
        self.decision_interval_s = float(self.config["rl"]["decision_interval_s"])
        self.model_path = self._resolve_model_path(model_path)
        self.model = model if model is not None else PPO.load(str(self.model_path), device="cpu")
        self.action_count = len(_ACTIONS)

    def decide(self, state: IntersectionState) -> Action:
        """Encode a traffic snapshot and return the PPO policy's safe request."""
        observation = to_vector(state, self.norm)
        prediction, _ = self.model.predict(observation, deterministic=True)
        action_index = int(prediction)
        if not 0 <= action_index < self.action_count:
            raise ValueError(f"PPO predicted unsupported action {action_index}")
        return _ACTIONS[action_index]

    def reset(self) -> None:
        """The feed-forward PPO policy has no per-episode controller state."""

    @staticmethod
    def _resolve_model_path(model_path: str | Path) -> Path:
        path = Path(model_path).expanduser()
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        if path.is_dir():
            path = path / "model.zip"
        if not path.is_file():
            raise FileNotFoundError(f"PPO model file not found: {path}")
        return path.resolve()
