"""Contract, batching, fallback-isolation and latency checks for network PPO."""

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from Ai.common.config import load_config
from Ai.common.network_state import NetworkState
from Ai.common.traffic_state import IntersectionState
from Ai.controllers.base import Action
from Ai.controllers.network import get_network_controller
from Ai.controllers.rl_network_controller import RLNetworkController


class _Model:
    observation_space = SimpleNamespace(shape=(54,))
    action_space = SimpleNamespace(n=4)

    def __init__(self, outputs: list[int]) -> None:
        self.outputs = outputs
        self.calls: list[np.ndarray] = []

    def predict(self, observations: np.ndarray, *, deterministic: bool):
        assert deterministic
        self.calls.append(observations.copy())
        return np.asarray(self.outputs, dtype=np.int64), None


def _state(config: dict) -> NetworkState:
    junctions = {}
    for tls in config["network"]["tls_configs"]:
        tls_id = tls["tls_id"]
        junctions[tls_id] = IntersectionState(
            timestamp_utc=datetime.now(timezone.utc), sim_time=10.0,
            intersection_id=tls_id, approaches=[], phase=int(tls["green_phases"][0]),
            phase_elapsed_s=10.0, mode="green", totals={}, source="sumo",
        )
    return NetworkState(sim_time=10.0, junctions=junctions, totals={})


def _controller(config: dict, model: _Model) -> RLNetworkController:
    return RLNetworkController(config["network"]["tls_configs"], config, model=model)


def test_network_rl_predicts_one_ordered_batch_for_all_frozen_tls(monkeypatch) -> None:
    config = load_config()
    monkeypatch.setattr(
        "Ai.controllers.rl_network_controller.to_vector",
        lambda state, norm: np.zeros(norm.vector_length, dtype=np.float32),
    )
    model = _Model([1] * len(config["network"]["controlled_tls"]))
    controller = _controller(config, model)

    actions = controller.decide(_state(config))

    assert len(model.calls) == 1
    assert model.calls[0].shape == (12, 54)
    assert model.calls[0].dtype == np.float32
    assert list(actions) == config["network"]["controlled_tls"]
    assert all(action == Action("switch") for action in actions.values())
    assert controller.diagnostics()["batch_inference_count"] == 1
    assert np.isfinite(controller.median_inference_latency_ms)


def test_hybrid_rl_subset_keeps_frozen_batch_order_but_returns_only_enabled_tls(monkeypatch) -> None:
    config = load_config()
    monkeypatch.setattr(
        "Ai.controllers.rl_network_controller.to_vector",
        lambda state, norm: np.zeros(norm.vector_length, dtype=np.float32),
    )
    model = _Model([1] * len(config["network"]["controlled_tls"]))
    tls_ids = tuple(config["network"]["controlled_tls"])
    controller = RLNetworkController(
        config["network"]["tls_configs"], config, model=model,
        active_tls_ids=(tls_ids[1], tls_ids[4]),
    )

    actions = controller.decide(_state(config))

    assert list(actions) == [tls_ids[1], tls_ids[4]]
    assert model.calls[0].shape == (12, 54)
    assert set(controller.diagnostics()["per_junction"]) == {tls_ids[1], tls_ids[4]}


def test_hold_action_lockout_is_local_and_recorded(monkeypatch) -> None:
    config = load_config()
    monkeypatch.setattr(
        "Ai.controllers.rl_network_controller.to_vector",
        lambda state, norm: np.zeros(norm.vector_length, dtype=np.float32),
    )
    model = _Model([2] + [0] * 11)
    controller = _controller(config, model)
    state = _state(config)

    first = controller.decide(state)
    model.outputs = [1] * 12
    second = controller.decide(state)
    third = controller.decide(state)

    tls0, tls1 = controller.tls_ids[:2]
    assert first[tls0] == Action("hold")
    assert second[tls0] == Action("hold")  # its five-second lockout overrides one later switch
    assert third[tls0] == Action("switch")
    assert second[tls1] == Action("switch")  # another TLS is not locked out
    diagnostics = controller.diagnostics()["per_junction"]
    assert diagnostics[tls0]["hold_overridden"] == 1
    assert diagnostics[tls0]["action_histogram"]["hold_5s"] == 1
    assert diagnostics[tls0]["action_histogram"]["switch"] == 2
    assert diagnostics[tls0]["applied_action_histogram"]["keep"] == 1
    assert diagnostics[tls0]["applied_action_histogram"]["switch"] == 1
    assert diagnostics[tls1]["hold_overridden"] == 0


def test_invalid_action_latches_only_one_tls_and_reduces_its_tick_share(monkeypatch) -> None:
    config = load_config()
    monkeypatch.setattr(
        "Ai.controllers.rl_network_controller.to_vector",
        lambda state, norm: np.zeros(norm.vector_length, dtype=np.float32),
    )
    model = _Model([99] + [1] * 11)
    controller = _controller(config, model)
    actions = controller.decide(_state(config))

    bad_tls = controller.tls_ids[0]
    assert controller.controllers[bad_tls].fallback_active
    assert not controller.controllers[controller.tls_ids[1]].fallback_active
    assert actions[bad_tls].kind in {"hold", "extend", "switch"}  # fixed-time fallback action
    for _ in range(4):
        for tls_id in controller.tls_ids:
            controller.record_tick(tls_id)
    shares = {
        tls: values["ppo_tick_share"]
        for tls, values in controller.diagnostics()["per_junction"].items()
    }
    assert shares[bad_tls] == 0.0
    assert all(shares[tls] == 1.0 for tls in controller.tls_ids[1:])
    assert len(model.calls) == 1


def test_corrupt_model_load_falls_back_per_junction(monkeypatch, tmp_path: Path) -> None:
    config = load_config()
    model_path = tmp_path / "corrupt.zip"
    model_path.write_bytes(b"not a PPO archive")
    (tmp_path / "config.json").write_text(
        json.dumps({
            "intended_tls_hash": config["network"]["tls_list_hash"],
            "slot_order": config["network"]["controlled_tls"],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "Ai.controllers.rl_network_controller.PPO.load",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("injected corrupt archive")),
    )
    monkeypatch.setattr(
        "Ai.controllers.rl_network_controller.to_vector",
        lambda state, norm: np.zeros(norm.vector_length, dtype=np.float32),
    )

    controller = get_network_controller(
        "rl", config["network"]["tls_configs"], config
    )
    actions = controller.decide(_state(config))

    assert len(actions) == 12
    assert all(controller.controllers[tls].fallback_active for tls in controller.tls_ids)
    for tls_id in controller.tls_ids:
        controller.record_tick(tls_id)
    diag = controller.diagnostics()
    assert diag["model_loaded"] is False
    assert all(row["ppo_tick_share"] == 0.0 for row in diag["per_junction"].values())


def test_network_controller_factory_keeps_fixed_and_rule_paths(monkeypatch) -> None:
    config = load_config()
    monkeypatch.setattr(
        "Ai.controllers.network.get_controller",
        lambda name, project_config, tls_config: SimpleNamespace(
            name=name, decision_interval_s=5.0, reset=lambda: None,
            decide=lambda state: Action("hold"),
        ),
    )
    fixed = get_network_controller("fixed", config["network"]["tls_configs"], config)
    rule = get_network_controller("rule", config["network"]["tls_configs"], config)
    assert fixed.name == "fixed"
    assert rule.name == "rule"
