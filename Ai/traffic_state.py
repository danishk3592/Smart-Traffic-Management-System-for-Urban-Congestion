import os
import traci

# SUMO configuration
sumo_cfg = os.path.abspath(
    "../SUMO/No_Polygon_Map/osm.sumocfg"
)

sumo_binary = "sumo-gui"

# Our fixed intersection
tls_id = "cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881"

print("Starting SUMO...")

traci.start([sumo_binary, "-c", sumo_cfg])

print("TraCI connected successfully!")

# --------------------------------------------------
# Run simulation
# --------------------------------------------------

for step in range(30):

    traci.simulationStep()

    print(f"\n========== STEP {step + 1} ==========")

    # ----------------------------------------------
    # Traffic light
    # ----------------------------------------------

    phase = traci.trafficlight.getPhase(tls_id)

    print("Traffic Light Phase:", phase)

    # ----------------------------------------------
    # All vehicles
    # ----------------------------------------------

    vehicle_ids = traci.vehicle.getIDList()

    print("Total Vehicles:", len(vehicle_ids))

    # ----------------------------------------------
    # Vehicle information
    # ----------------------------------------------

    total_waiting_time = 0
    total_speed = 0

    for vehicle_id in vehicle_ids:

        speed = traci.vehicle.getSpeed(vehicle_id)

        waiting_time = traci.vehicle.getAccumulatedWaitingTime(
            vehicle_id
        )

        total_speed += speed
        total_waiting_time += waiting_time

    # ----------------------------------------------
    # Calculate averages
    # ----------------------------------------------

    if len(vehicle_ids) > 0:

        average_speed = total_speed / len(vehicle_ids)

        average_waiting_time = (
            total_waiting_time / len(vehicle_ids)
        )

    else:

        average_speed = 0
        average_waiting_time = 0

    print("Average Speed:", round(average_speed, 2), "m/s")
    print(
        "Average Waiting Time:",
        round(average_waiting_time, 2),
        "seconds"
    )

traci.close()

print("\nTraCI connection closed.")