
import numpy as np
from traffic_env import TrafficEnv

env = TrafficEnv(episode_seconds=120)

try:
    observation, info = env.reset(seed=42)

    print("Reset successful")
    print("Observation shape:", observation.shape)
    print("Observation space:", env.observation_space)
    print("Initial info:", info)

    assert env.observation_space.contains(observation)

    for i in range(10):
        action = env.action_space.sample()

        observation, reward, terminated, truncated, info = env.step(action)

        print(
            f"Step {i + 1}: action={action}, "
            f"reward={reward:.2f}, "
            f"phase={info['phase']}, "
            f"queue={info['queue_length']}"
        )

        assert env.observation_space.contains(observation)
        assert np.isfinite(reward)

        if terminated or truncated:
            print("Episode finished.")
            break

    print("Environment test passed.")

finally:
    env.close()
