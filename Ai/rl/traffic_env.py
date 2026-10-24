
import logging
import math
from pathlib import Path
from typing import ClassVar

import gymnasium as gym
import numpy as np
import sumolib
import traci
from gymnasium import spaces

logger = logging.getLogger(__name__)

TLS_ID = (
    "cluster618250255_7478115627_"
    "cluster_11927462278_11927462280_"
    "7478115626_7479633881"
)


class TrafficEnv(gym.Env):
    """Gymnasium environment for controlling one SUMO traffic light."""

    metadata: ClassVar[dict[str, list[str]]] = {"render_modes": []}

    GREEN_PHASES = (0, 2, 4)
    YELLOW_PHASES: ClassVar[dict[int, int]] = {0: 1, 2: 3, 4: 5}
    NEXT_GREEN: ClassVar[dict[int, int]] = {0: 2, 2: 4, 4: 0}

    def __init__(
        self,
        sumo_cfg=None,
        episode_seconds=600,
        green_seconds=10,
        min_green_seconds=5,
    ):
        super().__init__()

        root = Path(__file__).resolve().parents[2]
        self.sumo_cfg = Path(
            sumo_cfg or root / "SUMO" / "No_Polygon_Map" / "osm.sumocfg"
        ).resolve()

        if not self.sumo_cfg.is_file():
            raise FileNotFoundError(
                f"SUMO configuration not found: {self.sumo_cfg}"
            )

        self.episode_seconds = episode_seconds
        self.green_seconds = green_seconds
        self.min_green_seconds = min_green_seconds
        self.label = f"traffic_rl_{id(self)}"

        # Action 0 -> green phase 0
        # Action 1 -> green phase 2
        # Action 2 -> green phase 4
        self.action_space = spaces.Discrete(3)

        self.conn = None
        self.elapsed = 0.0
        self.lanes = []
        self.phase_durations = {}

        # Four measurements per lane, plus three phase indicators.
        self.observation_space = spaces.Box(
            low=0.0,
            high=np.inf,
            shape=(35,),
            dtype=np.float32,
        )

    def _start_sumo(self):
        binary = sumolib.checkBinary("sumo")
        command = [
            binary,
            "-c", str(self.sumo_cfg),
            "--no-step-log", "true",
        ]

        traci.start(command, label=self.label)
        self.conn = traci.getConnection(self.label)

        traffic_lights = self.conn.trafficlight.getIDList()
        if TLS_ID not in traffic_lights:
            raise RuntimeError(
                f"Traffic light {TLS_ID} not found. "
                f"Available IDs: {traffic_lights}"
            )

        self.lanes = sorted(
            set(self.conn.trafficlight.getControlledLanes(TLS_ID))
        )

        if not self.lanes:
            raise RuntimeError("No controlled lanes found.")

        program_id = self.conn.trafficlight.getProgram(TLS_ID)
        programs = self.conn.trafficlight.getAllProgramLogics(TLS_ID)

        matching = [
            program for program in programs
            if program.programID == program_id
        ]

        if not matching:
            raise RuntimeError("Could not inspect the active signal program.")

        phases = matching[0].phases

        if len(phases) < 6:
            raise RuntimeError(
                f"Expected at least 6 phases; found {len(phases)}."
            )

        self.phase_durations = {
            index: float(phase.duration)
            for index, phase in enumerate(phases)
        }

        for phase in self.GREEN_PHASES:
            if not phases[phase].state or "G" not in phases[phase].state:
                raise RuntimeError(
                    f"Phase {phase} does not appear to be a green phase: "
                    f"{phases[phase].state}"
                )

        self.observation_space = spaces.Box(
            low=0.0,
            high=np.inf,
            shape=(len(self.lanes) * 4 + 3,),
            dtype=np.float32,
        )

    def _run_seconds(self, seconds):
        delta_t = float(self.conn.simulation.getDeltaT())
        steps = max(1, math.ceil(seconds / delta_t))

        for _ in range(steps):
            self.conn.simulationStep()
            self.elapsed += delta_t

            if self.conn.simulation.getMinExpectedNumber() == 0:
                break

    def _green_observation(self):
        current_phase = self.conn.trafficlight.getPhase(TLS_ID)
        values = []

        for lane in self.lanes:
            vehicle_ids = self.conn.lane.getLastStepVehicleIDs(lane)

            vehicle_count = len(vehicle_ids)
            queue_length = self.conn.lane.getLastStepHaltingNumber(lane)
            waiting_time = sum(
                self.conn.vehicle.getWaitingTime(vehicle_id)
                for vehicle_id in vehicle_ids
            )
            mean_speed = max(
                0.0,
                self.conn.lane.getLastStepMeanSpeed(lane),
            )

            values.extend([
                float(vehicle_count),
                float(queue_length),
                float(waiting_time),
                float(mean_speed),
            ])

        # One-hot encoding of the currently active green phase.
        values.extend([
            float(current_phase == phase)
            for phase in self.GREEN_PHASES
        ])

        return np.asarray(values, dtype=np.float32)

    def _transition_to_green(self, target_phase):
        """Reach the selected green using the configured yellow phases."""
        for _ in range(6):
            current = self.conn.trafficlight.getPhase(TLS_ID)

            if current not in self.GREEN_PHASES:
                if current not in (1, 3, 5):
                    raise RuntimeError(
                        f"Unexpected traffic-light phase: {current}"
                    )

                yellow_duration = self.phase_durations[current]
                self._run_seconds(yellow_duration)

                next_green = {1: 2, 3: 4, 5: 0}[current]
                self.conn.trafficlight.setPhase(TLS_ID, next_green)
                current = next_green

            if current == target_phase:
                self.conn.trafficlight.setPhaseDuration(
                    TLS_ID, self.green_seconds
                )
                self._run_seconds(self.green_seconds)
                return

            # Never jump directly from one conflicting green to another.
            yellow_phase = self.YELLOW_PHASES[current]
            yellow_duration = self.phase_durations[yellow_phase]

            self.conn.trafficlight.setPhase(TLS_ID, yellow_phase)
            self.conn.trafficlight.setPhaseDuration(
                TLS_ID, yellow_duration
            )
            self._run_seconds(yellow_duration)

            next_green = self.NEXT_GREEN[current]
            self.conn.trafficlight.setPhase(TLS_ID, next_green)

            if next_green != target_phase:
                self.conn.trafficlight.setPhaseDuration(
                    TLS_ID, self.min_green_seconds
                )
                self._run_seconds(self.min_green_seconds)

        raise RuntimeError(
            f"Could not reach requested green phase {target_phase}."
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.close()
        self.elapsed = 0.0

        try:
            self._start_sumo()
            return self._green_observation(), {
                "phase": self.conn.trafficlight.getPhase(TLS_ID),
                "lanes": len(self.lanes),
            }
        except Exception:
            self.close()
            raise

    def step(self, action):
        if self.conn is None:
            raise RuntimeError("Call reset() before step().")

        target_phase = self.GREEN_PHASES[int(action)]

        try:
            self._transition_to_green(target_phase)

            observation = self._green_observation()

            total_queue = float(
                sum(
                    self.conn.lane.getLastStepHaltingNumber(lane)
                    for lane in self.lanes
                )
            )

            total_waiting = sum(
                self.conn.vehicle.getWaitingTime(vehicle_id)
                for lane in self.lanes
                for vehicle_id in
                self.conn.lane.getLastStepVehicleIDs(lane)
            )

            reward = -float(total_queue)

            terminated = (
                self.conn.simulation.getMinExpectedNumber() == 0
            )
            truncated = self.elapsed >= self.episode_seconds

            info = {
                "phase": self.conn.trafficlight.getPhase(TLS_ID),
                "queue_length": total_queue,
                "waiting_time": float(total_waiting),
                "elapsed_seconds": self.elapsed,
            }

            return (
                observation,
                float(reward),
                terminated,
                truncated,
                info,
            )

        except Exception:
            self.close()
            raise

    def close(self) -> None:
        connection, self.conn = self.conn, None
        if connection is None:
            return

        try:
            connection.close()
        except (OSError, traci.exceptions.TraCIException) as error:
            logger.warning("TraCI connection close failed: %s", error)
