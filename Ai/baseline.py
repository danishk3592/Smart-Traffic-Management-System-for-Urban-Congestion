
import os
import xml.etree.ElementTree as ET

import traci

sumo_cfg = os.path.abspath(
    "../SUMO/No_Polygon_Map/osm.sumocfg"
)

sumo_binary = "sumo"
simulation_steps = 3600
tripinfo_file = "baseline_tripinfo.xml"

# Start SUMO
traci.start([
    sumo_binary,
    "-c", sumo_cfg,
    "--tripinfo-output", tripinfo_file,
    "--tripinfo-output.write-unfinished", "true",
    "--no-step-log", "true"
])

print("Running baseline simulation...")

try:
    for step in range(simulation_steps):
        if traci.simulation.getMinExpectedNumber() == 0:
            break

        traci.simulationStep()

    print("Simulation time:", traci.simulation.getTime())

finally:
    traci.close()

print("\nSimulation finished.")

# Read trip information
tree = ET.parse(tripinfo_file)
root = tree.getroot()
trips = root.findall("tripinfo")

completed = []
unfinished = []

for trip in trips:
    arrival = trip.get("arrival")
    vaporized = trip.get("vaporized", "")

    if arrival not in (None, "", "-1", "-1.00") and not vaporized:
        completed.append(trip)
    else:
        unfinished.append(trip)
        
print("\n========== BASELINE RESULTS ==========")
print("Recorded trips:", len(trips))
print("Completed trips:", len(completed))
print("Unfinished trips:", len(unfinished))

# Check XML arrival values
missing_arrival = sum(
    1 for trip in trips if trip.get("arrival") is None
)
invalid_arrival = sum(
    1 for trip in trips if trip.get("arrival") in ("", "-1")
)

print("Missing arrival values:", missing_arrival)
print("Invalid arrival values:", invalid_arrival)

# Calculate metrics for completed trips only
if completed:
    avg_duration = sum(
        float(t.get("duration", 0))
        for t in completed
    ) / len(completed)

    avg_waiting = sum(
        float(t.get("waitingTime", 0))
        for t in completed
    ) / len(completed)

    avg_time_loss = sum(
        float(t.get("timeLoss", 0))
        for t in completed
    ) / len(completed)

    print(f"Average travel time: {avg_duration:.2f} s")
    print(f"Average waiting time: {avg_waiting:.2f} s")
    print(f"Average time loss: {avg_time_loss:.2f} s")
else:
    print("No completed trips available for evaluation.")

# Show a few XML records for verification
print("\n========== SAMPLE TRIP RECORDS ==========")

for trip in trips[:3]:
    print(trip.attrib)
