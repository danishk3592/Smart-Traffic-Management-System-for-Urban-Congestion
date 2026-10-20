
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from traffic_env import TrafficEnv

RL_DIR = Path(__file__).resolve().parent
MODEL_DIR = RL_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

env = Monitor(TrafficEnv(episode_seconds=600))

try:
    model = PPO(
        policy="MlpPolicy",
        env=env,
        learning_rate=3e-4,
        n_steps=128,
        batch_size=64,
        gamma=0.99,
        seed=42,
        verbose=1,
        device="cpu",
    )

    print("Starting PPO training...")

    model.learn(total_timesteps=5000)

    model_path = MODEL_DIR / "ppo_traffic"
    model.save(str(model_path))

    print(f"Training complete. Model saved to: {model_path}.zip")

finally:
    env.close()
