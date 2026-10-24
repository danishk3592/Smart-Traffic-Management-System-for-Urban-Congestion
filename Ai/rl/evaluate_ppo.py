
import csv
from pathlib import Path

from stable_baselines3 import PPO
from traffic_env import TrafficEnv

RL_DIR = Path(__file__).resolve().parent
MODEL_PATH = RL_DIR / "models" / "ppo_traffic.zip"
RESULTS_PATH = RL_DIR / "ppo_evaluation.csv"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_PATH}. "
        "Run train_ppo.py first."
    )

model = PPO.load(str(MODEL_PATH), device="cpu")
env = TrafficEnv(episode_seconds=3600)

rows = []

try:
    observation, info = env.reset(seed=42)
    terminated = False
    truncated = False
    step_number = 0
    total_reward = 0.0

    while not (terminated or truncated):
        action, _ = model.predict(observation, deterministic=True)

        observation, reward, terminated, truncated, info = env.step(
            int(action)
        )

        step_number += 1
        total_reward += reward

        rows.append({
            "step": step_number,
            "action": int(action),
            "phase": info["phase"],
            "reward": reward,
            "queue_length": info["queue_length"],
            "waiting_time": info["waiting_time"],
            "elapsed_seconds": info["elapsed_seconds"],
        })

        if step_number % 10 == 0:
            print(
                f"Step {step_number}: "
                f"phase={info['phase']}, "
                f"queue={info['queue_length']}"
            )

    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("\nEvaluation complete.")
    print("Actions taken:", step_number)
    print("Total reward:", round(total_reward, 2))
    print("Results saved to:", RESULTS_PATH)

finally:
    env.close()