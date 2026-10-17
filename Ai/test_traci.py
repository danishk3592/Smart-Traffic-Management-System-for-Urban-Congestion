import os
import traci

# Path to our SUMO configuration
sumo_cfg = os.path.abspath(
    "../SUMO/No_Polygon_Map/osm.sumocfg"
)

# Start SUMO with GUI
sumo_binary = "sumo-gui"

print("Starting SUMO...")
traci.start([sumo_binary, "-c", sumo_cfg])

print("TraCI connected successfully!")

# Get all traffic light IDs
tls_ids = traci.trafficlight.getIDList()

print("\n========== TRAFFIC LIGHTS ==========")
print(f"Total traffic lights: {len(tls_ids)}")

for tls_id in tls_ids:
    print(f"Traffic Light ID : {tls_id}")

# Run simulation 
for step in range(20):
    traci.simulationStep()

    #Vehicle Information
    vehicles = traci.vehicle.getIDList()

    print(
        f"\n--- Step {step + 1}: "
        f"Vehicles : {len(vehicles)}"
    )

     # Traffic light information
    for tls_id in tls_ids:
        phase = traci.trafficlight.getPhase(tls_id)
        program = traci.trafficlight.getProgram(tls_id)

        print(
            f"TLS: {tls_id} | "
            f"Phase: {phase} | "
            f"Program: {program}"
        )

traci.close()

print("\nTraCI connection closed.")