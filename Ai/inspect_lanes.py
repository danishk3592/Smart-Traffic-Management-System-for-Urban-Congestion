
import os

import traci

sumo_cfg = os.path.abspath(
    "../SUMO/No_Polygon_Map/osm.sumocfg"
)

target_lanes = [
    "312063814#0_0",
    "312063814#0_1",
    "312063814#0_2",
    "1196514117#0_0",
    "1196514117#0_1",
    "229965236#0_0",
    "229965236#0_1",
    "1105763532#3_0",
]

traci.start(["sumo", "-c", sumo_cfg])

all_lanes = traci.lane.getIDList()

print("Total network lanes:", len(all_lanes))

for step in range(300):
    traci.simulationStep()

    if (step + 1) % 100 != 0:
        continue

    occupied = []

    for lane in all_lanes:
        count = traci.lane.getLastStepVehicleNumber(lane)

        if count > 0:
            occupied.append((lane, count))

    occupied.sort(key=lambda item: item[1], reverse=True)

    print(f"\n========== TIME {step + 1}s ==========")
    print("Vehicles in simulation:", len(traci.vehicle.getIDList()))
    print("Lanes containing vehicles:", len(occupied))

    print("\nTop 15 occupied lanes:")

    for lane, count in occupied[:15]:
        print(f"{lane}: {count} vehicles")

    print("\nOur selected lanes:")

    for lane in target_lanes:
        count = traci.lane.getLastStepVehicleNumber(lane)
        print(f"{lane}: {count} vehicles")

traci.close()
print("\nDiagnostic complete.")
