"""Contract tests for demo-only seed and controller routing."""

from __future__ import annotations

from typing import Any

import pytest

from scripts import run_demo


def test_demo_rejects_evaluation_seeds() -> None:
    """Seed blocks reserved for evaluation cannot be used for demos."""
    with pytest.raises(SystemExit) as error:
        run_demo.main(
            ["--family", "single", "--controller", "fixed", "--scenario", "medium", "--seed", "6000"]
        )
    assert error.value.code == 2


def test_demo_restricts_scenarios_to_documented_pairings() -> None:
    """The CLI accepts only the two configured, resource-safe demo scenarios."""
    with pytest.raises(SystemExit) as error:
        run_demo.main(
            ["--family", "network", "--controller", "rule", "--scenario", "medium", "--seed", "8000"]
        )
    assert error.value.code == 2


def test_network_rl_demo_uses_frozen_stage4_hybrid(monkeypatch: Any) -> None:
    """The network RL demo must use the delivered hybrid gate."""
    calls: list[str] = []
    expected = object()

    def fake_get(name: str, tls: list[dict[str, str]], config: dict[str, Any]) -> object:
        del tls, config
        calls.append(name)
        return expected

    monkeypatch.setattr(run_demo, "get_network_controller", fake_get)
    actual = run_demo._build_controller(
        "network", "rl", {"network": {"tls_configs": [{"tls_id": "tls-a"}]}}
    )
    assert actual is expected
    assert calls == ["hybrid"]
