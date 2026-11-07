"""PPO adapter checks, including the required on-machine latency gate."""

from __future__ import annotations

import statistics
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from Ai.common.config import load_config
from Ai.common.traffic_state import ApproachState, IntersectionState
from Ai.controllers.base import Action
from Ai.controllers.fallback import FallbackController
from Ai.controllers.registry import get_controller
from Ai.controllers.rl_controller import RLController


class _FixedActionModel:
    def __init__(self, action: int) -> None:
        self.action = action
        self.observations: list[np.ndarray] = []

    def predict(self, observation: np.ndarray, *, deterministic: bool):
        assert deterministic
        self.observations.append(observation.copy())
        return np.asarray(self.action), None


def _state(config: dict) -> IntersectionState:
    approaches = [
        ApproachState(
            name=item["name"],
            vehicle_count=0,
            halting=0,
            mean_speed=0.0,
            waiting_time=0.0,
            queue_length=0.0,
            congestion="Low",
            available_fields=["vehicle_count", "halting", "mean_speed", "waiting_time"],
        )
        for item in config["intersection"]["approaches"]
    ]
    return IntersectionState(
        timestamp_utc=datetime.now(timezone.utc),
        sim_time=0.0,
        intersection_id=str(config["sumo"]["tls_id"]),
        approaches=approaches,
        phase=int(config["intersection"]["green_phases"][0]),
        phase_elapsed_s=0.0,
        mode="green",
        totals={"waiting_vehicles": 0},
        source="sumo",
    )


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, Action("hold")),
        (1, Action("switch")),
        (2, Action("extend", seconds=5.0)),
        (3, Action("extend", seconds=10.0)),
    ],
)
def test_policy_action_mapping_and_state_vector(index: int, expected: Action) -> None:
    config = load_config()
    model = _FixedActionModel(index)
    controller = RLController(
        config["rl"]["model_path"], config, model=model
    )

    assert controller.decide(_state(config)) == expected
    assert model.observations[0].shape == (controller.norm.vector_length,)
    assert model.observations[0].dtype == np.float32


@pytest.mark.parametrize("corrupt", [False, True], ids=["missing", "corrupt"])
def test_missing_or_corrupt_model_activates_fixed_time_fallback(
    corrupt: bool
) -> None:
    config = load_config()
    if corrupt:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary_dir:
            model_path = Path(temporary_dir) / "bad_model.zip"
            model_path.write_bytes(b"not a valid PPO model archive")
            controller = get_controller("rl", config, model_path=model_path)
    else:
        controller = get_controller(
            "rl", config, model_path=Path("results/rl/definitely_missing_model.zip")
        )
    assert isinstance(controller, FallbackController)
    action = controller.decide(_state(config))
    assert controller.fallback_active
    assert isinstance(action, Action)


def test_median_inference_latency_under_100_ms_for_1000_calls() -> None:
    config = load_config()
    controller = get_controller("rl", config)
    state = _state(config)
    for _ in range(20):
        controller.decide(state)
    latencies = []
    for _ in range(1000):
        started = time.perf_counter()
        action = controller.decide(state)
        latencies.append(time.perf_counter() - started)
        assert isinstance(action, Action)
    median_latency_s = statistics.median(latencies)
    print(f"median inference latency over 1000 calls: {median_latency_s * 1000:.3f} ms")
    assert median_latency_s < 0.1
