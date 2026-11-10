"""Run one deterministic PPO episode and persist controller diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from Ai.common.config import load_config
from Ai.controllers.base import Action
from Ai.controllers.registry import get_controller
from Ai.rl.traffic_env import TrafficEnvironment

ROOT = Path(__file__).resolve().parents[2]
ACTION_INDEX = {"hold": 0, "switch": 1}


def _action_index(action: Action) -> int:
    if action.kind in ACTION_INDEX:
        return ACTION_INDEX[action.kind]
    if action.kind == "extend":
        if action.seconds is None:
            raise ValueError("extend action requires a duration")
        return 2 if action.seconds <= 5 else 3
    raise ValueError(f"PPO adapter returned unsupported action: {action!r}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="PPO model zip or model directory")
    parser.add_argument("--seed", type=int, default=3000, help="validation seed in 3000–3009")
    parser.add_argument("--scenario", default="medium", help="cached scenario (default: medium)")
    parser.add_argument("--output-dir", type=Path, default=Path("results/rl"))
    return parser.parse_args(argv)


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    if not 3000 <= args.seed <= 3009:
        raise ValueError("evaluation seed must be in validation block 3000–3009")
    config = load_config()
    selected_model = args.model
    if not selected_model.is_absolute():
        selected_model = ROOT / selected_model
    controller = get_controller("rl", config, model_path=selected_model)
    env = TrafficEnvironment(
        scenario_pool=(args.scenario,), seeds=(args.seed,), config=config
    )
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"ppo_{args.scenario}_seed{args.seed}_{run_id}"
    step_path = output_dir / f"{stem}_steps.csv"
    diagnostics_path = output_dir / f"{stem}_diagnostics.json"
    actions: Counter[int] = Counter()
    executed_actions: Counter[int] = Counter()
    phases: Counter[int] = Counter()
    rows: list[dict[str, object]] = []
    reward_sum = 0.0
    illegal_count = 0
    fallback_count = 0
    try:
        _, reset_info = env.reset(
            seed=args.seed,
            options={"scenario": args.scenario, "seed": args.seed},
        )
        terminated = truncated = False
        while not (terminated or truncated):
            assert env.state is not None
            request = controller.decide(env.state)
            requested_action = _action_index(request)
            _, reward, terminated, truncated, info = env.step(requested_action)
            actions[requested_action] += 1
            executed_actions[int(info["action_taken"])] += 1
            phase = int(info["phase"])
            if phase in env.tls["green_phases"]:
                phases[phase] += 1
            illegal_count += int(bool(info["illegal_action"]))
            fallback_count += int(bool(getattr(controller, "fallback_active", False)))
            reward_sum += float(reward)
            rows.append(
                {
                    "step": len(rows) + 1,
                    "sim_time": float(info["sim_time"]),
                    "phase": phase,
                    "phase_elapsed_s": info["phase_elapsed"],
                    "requested_action": request.kind,
                    "requested_action_index": requested_action,
                    "action_index": int(info["action_taken"]),
                    "reward": float(reward),
                    "queue_total": float(info["queue_total"]),
                    "wait_total": float(info["wait_total"]),
                    "illegal_action": bool(info["illegal_action"]),
                }
            )
        safety = env.safety
        if safety is None:
            raise RuntimeError("environment closed before diagnostics were collected")
        durations_by_phase = {
            phase: list(durations)
            for phase, durations in safety.green_durations_by_phase.items()
        }
        if env.state is not None and env.state.phase in durations_by_phase:
            final_duration = env.state.phase_elapsed_s
            if final_duration is not None and final_duration > 0:
                durations_by_phase[env.state.phase].append(float(final_duration))
        training_duration = {
            str(phase): {
                "count": len(durations),
                "mean_green_s": (
                    sum(durations) / len(durations) if durations else None
                ),
                "durations_s": durations,
            }
            for phase, durations in durations_by_phase.items()
        }
        diagnostics: dict[str, object] = {
            "run_id": run_id,
            "scenario": args.scenario,
            "seed": args.seed,
            "model": str(selected_model.resolve()),
            "steps": len(rows),
            "total_reward": reward_sum,
            "action_histogram": {str(index): actions[index] for index in range(4)},
            "executed_action_histogram": {
                str(index): executed_actions[index] for index in range(4)
            },
            "phase_usage_histogram": {
                str(phase): phases[phase] for phase in sorted(env.tls["green_phases"])
            },
            "mean_green_per_phase": training_duration,
            "forced_max_green_switches": safety.forced_max_green_switches,
            "illegal_action_count": illegal_count,
            "illegal_action_rate": illegal_count / len(rows) if rows else 0.0,
            "fallback_decision_count": fallback_count,
            "initial_state": reset_info,
            "step_log": str(step_path),
        }
        with step_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["step"])
            writer.writeheader()
            writer.writerows(rows)
        diagnostics_path.write_text(
            json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(diagnostics, indent=2, sort_keys=True))
        print(f"diagnostics={diagnostics_path}")
        return diagnostics
    finally:
        env.close()


def main(argv: Sequence[str] | None = None) -> int:
    evaluate(_parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
