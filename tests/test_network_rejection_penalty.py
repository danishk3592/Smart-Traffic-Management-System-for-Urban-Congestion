from __future__ import annotations

import numpy as np

from Ai.rl.network_vec_env import _apply_rejection_penalty, _rejection_category


def test_rejection_penalty_is_local_to_rejected_junction_samples() -> None:
    rewards = np.asarray([-0.25, 0.10, 0.40], dtype=np.float32)
    rejected = np.asarray([True, False, True])

    adjusted = _apply_rejection_penalty(rewards, rejected, 0.05)

    np.testing.assert_allclose(adjusted, [-0.30, 0.10, 0.35], atol=1e-7)


def test_rejection_reasons_use_stable_per_junction_categories() -> None:
    assert _rejection_category("signal is already in a clearance phase") == "clearance_phase"
    assert _rejection_category("minimum green not met (5.00s < 10s)") == "minimum_green"
    assert _rejection_category("hold_lockout_override") == "hold_lockout_override"
    assert _rejection_category("invalid_action") == "invalid_action"
    assert _rejection_category("extension must be a finite positive number") == "other_safety_rejection"
