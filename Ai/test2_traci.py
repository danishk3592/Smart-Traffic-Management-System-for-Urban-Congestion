import os

import traci

# SUMO configuration
sumo_cfg = os.path.abspath(
    "../SUMO/No_Polygon_Map/osm.sumocfg"
)

sumo_binary = "sumo-gui"

# Traffic light we want to control
tls_id = "cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881"

print("Starting SUMO...")

traci.start([sumo_binary, "-c", sumo_cfg])

print("TraCI connected successfully!")

# -------------------------------------------------
# Get traffic light program information
# -------------------------------------------------

logics = traci.trafficlight.getAllProgramLogics(tls_id)
logic = logics[0]

print("\n========== TRAFFIC LIGHT ==========")
print("ID:", tls_id)
print("Program:", logic.programID)
print("Number of phases:", len(logic.phases))

for i, phase in enumerate(logic.phases):
    print(
        f"Phase {i}: "
        f"Duration={phase.duration}s | "
        f"State={phase.state}"
    )

# -------------------------------------------------
# Run a few steps
# -------------------------------------------------

for step in range(5):
    traci.simulationStep()

current_phase = traci.trafficlight.getPhase(tls_id)

print("\n===================================")
print("Current phase:", current_phase)

# -------------------------------------------------
# Change to the next phase
# -------------------------------------------------

new_phase = (current_phase + 1) % len(logic.phases)

print("Changing phase...")
print("Old phase:", current_phase)
print("New phase:", new_phase)

traci.trafficlight.setPhase(tls_id, new_phase)

# Confirm
print(
    "Phase after command:",
    traci.trafficlight.getPhase(tls_id)
)

# -------------------------------------------------
# Let SUMO run for a few seconds
# -------------------------------------------------

print("\nRunning after phase change...")

for step in range(10):

    traci.simulationStep()

    phase = traci.trafficlight.getPhase(tls_id)
    vehicles = traci.vehicle.getIDList()

    print(
        f"Step {step + 1}: "
        f"Phase={phase} | "
        f"Vehicles={len(vehicles)}"
    )

traci.close()

print("\nTraCI connection closed.")