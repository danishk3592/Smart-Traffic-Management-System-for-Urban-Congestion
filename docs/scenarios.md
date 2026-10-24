# Scenario generation and native-program measurements

Measured with SUMO's native signal programs on 2026-10-24. Planned junction share uses the shared controlled-movement definition from Ai.common.junction. Congestion indicators count pilot halting vehicles; congested-time share is the fraction of simulated seconds with at least five halting vehicles across configured approach lanes. Teleport share uses unique vehicles that started teleporting divided by planned trips.

| Scenario | Seed | Trips | Planned junction trips | Junction share | Arrived | Completion | Unique teleports | Teleport share | Pending max | Pending at 3600 s | Mean pilot halting | Max pilot halting | Congested-time share | Simulated seconds | SUMO warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced | 1000 | 1800 | 946 | 0.526 | 1201 | 0.667 | 604 | 0.336 | 3 | 2 | 61.90 | 73 | 0.972 | 7200 | 1752 |
| directional_ns | 1000 | 1800 | 978 | 0.543 | 1170 | 0.650 | 730 | 0.406 | 4 | 4 | 59.07 | 73 | 0.975 | 7200 | 2170 |
| directional_ew | 1000 | 1800 | 950 | 0.528 | 1115 | 0.619 | 616 | 0.342 | 2 | 1 | 56.75 | 73 | 0.972 | 7200 | 1886 |
| low | 1000 | 700 | 325 | 0.464 | 693 | 0.990 | 118 | 0.169 | 0 | 0 | 16.95 | 28 | 0.933 | 7200 | 284 |
| medium | 1000 | 2600 | 1304 | 0.502 | 1576 | 0.606 | 1030 | 0.396 | 19 | 18 | 56.56 | 73 | 0.973 | 7200 | 3338 |
| heavy | 1000 | 3600 | 1885 | 0.524 | 2121 | 0.589 | 1637 | 0.455 | 22 | 22 | 64.67 | 73 | 0.978 | 7200 | 5176 |
| rush_hour | 1000 | 3200 | 1702 | 0.532 | 1917 | 0.599 | 1426 | 0.446 | 38 | 38 | 61.17 | 73 | 0.975 | 7200 | 4502 |

## Stop-gate checks

- medium: junction share 0.502 (minimum 0.300); teleport share 0.396 (design target <0.010).
- heavy: junction share 0.524 (minimum 0.300); teleport share 0.455 (design target <0.010).
- rush_hour: junction share 0.532 (minimum 0.300); teleport share 0.446 (design target <0.010).

The low scenario is reported honestly even if its measured share is below 0.300. Teleport shares are recorded as failed native-baseline results where above 5%. Under the human-approved 2026-10-24 roadmap amendment, this performance criterion is evaluated after PPO is connected, using identical demand and seeds for fixed-time and PPO. This deferral does not pass or remove the baseline failures.
