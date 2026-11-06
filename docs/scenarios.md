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

## Network scenarios (M2 demand design)

Measured with the native SUMO traffic programs, using the unchanged network and seed 1000.
Frozen intended TLS count: 12; list SHA-256: `4fc1323e1885d0763d8ac0598a1ec5e7446c6a835a63b62136f657c735979bcd`.
Target controlled-route share: 0.500; route design minimum: 0.300; teleport design target: <0.010.

| Scenario | Trips | Planned controlled trips | Planned share | Mean planned TLS/trip | Actual crossing trips | Actual share of departed | Arrived | Completion | Unique teleports | Teleport share | Pending max | Pending at horizon | Sim seconds | Warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_balanced | 350 | 263 | 0.751 | 3.037 | 263 | 0.751 | 350 | 1.000 | 2 | 0.006 | 1 | 0 | 4270 | 4 |
| net_low | 250 | 165 | 0.660 | 2.364 | 165 | 0.660 | 250 | 1.000 | 0 | 0.000 | 1 | 0 | 4223 | 0 |
| net_medium | 650 | 410 | 0.631 | 2.206 | 410 | 0.631 | 650 | 1.000 | 0 | 0.000 | 1 | 0 | 4147 | 0 |
| net_heavy | 800 | 516 | 0.645 | 2.174 | 514 | 0.642 | 800 | 1.000 | 7 | 0.009 | 1 | 0 | 4445 | 14 |
| net_rush_hour | 500 | 323 | 0.646 | 2.192 | 323 | 0.646 | 500 | 1.000 | 0 | 0.000 | 1 | 0 | 4196 | 0 |

### Per-TLS network measurements

Congestion bands use `config/stms.yaml`: low ≤4, medium 5–12, high ≥13 halting vehicles. The design gate requires at least one controlled TLS to reach the medium band in each primary scenario; the native teleport target remains <1%.

| Scenario | TLS ID | Planned route trips | Actual crossing trips | Mean halting queue | Max halting queue | Medium-congestion time share | High-congestion time share |
|---|---|---:|---:|---:|---:|---:|---:|
| net_balanced | `2387385680` | 14 | 14 | 0.025 | 1 | 0.000 | 0.000 |
| net_balanced | `GS_2407671508` | 104 | 104 | 0.132 | 2 | 0.000 | 0.000 |
| net_balanced | `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 124 | 108 | 0.105 | 3 | 0.000 | 0.000 |
| net_balanced | `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 40 | 40 | 0.054 | 2 | 0.000 | 0.000 |
| net_balanced | `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 144 | 144 | 2.135 | 7 | 0.030 | 0.000 |
| net_balanced | `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 90 | 89 | 0.662 | 5 | 0.003 | 0.000 |
| net_balanced | `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 64 | 64 | 0.319 | 3 | 0.000 | 0.000 |
| net_balanced | `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 65 | 65 | 0.406 | 4 | 0.000 | 0.000 |
| net_balanced | `cluster_2447849296_306618051` | 106 | 106 | 0.537 | 5 | 0.006 | 0.000 |
| net_balanced | `cluster_266273090_4377707444` | 66 | 66 | 0.236 | 3 | 0.000 | 0.000 |
| net_balanced | `cluster_306608060_6131903446` | 92 | 92 | 0.518 | 5 | 0.007 | 0.000 |
| net_balanced | `cluster_6633301856_7432359269_7432359283_7432359284` | 154 | 152 | 0.499 | 5 | 0.005 | 0.000 |
| net_low | `2387385680` | 4 | 4 | 0.000 | 0 | 0.000 | 0.000 |
| net_low | `GS_2407671508` | 64 | 64 | 0.071 | 2 | 0.000 | 0.000 |
| net_low | `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 70 | 59 | 0.068 | 2 | 0.000 | 0.000 |
| net_low | `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 17 | 17 | 0.019 | 1 | 0.000 | 0.000 |
| net_low | `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 95 | 94 | 1.310 | 6 | 0.016 | 0.000 |
| net_low | `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 41 | 41 | 0.257 | 2 | 0.000 | 0.000 |
| net_low | `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 39 | 39 | 0.294 | 2 | 0.000 | 0.000 |
| net_low | `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 26 | 26 | 0.191 | 2 | 0.000 | 0.000 |
| net_low | `cluster_2447849296_306618051` | 75 | 75 | 0.354 | 3 | 0.000 | 0.000 |
| net_low | `cluster_266273090_4377707444` | 32 | 32 | 0.139 | 2 | 0.000 | 0.000 |
| net_low | `cluster_306608060_6131903446` | 42 | 42 | 0.168 | 3 | 0.000 | 0.000 |
| net_low | `cluster_6633301856_7432359269_7432359283_7432359284` | 86 | 84 | 0.215 | 3 | 0.000 | 0.000 |
| net_medium | `2387385680` | 11 | 11 | 0.007 | 1 | 0.000 | 0.000 |
| net_medium | `GS_2407671508` | 167 | 167 | 0.226 | 4 | 0.000 | 0.000 |
| net_medium | `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 193 | 178 | 0.156 | 3 | 0.000 | 0.000 |
| net_medium | `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 42 | 42 | 0.048 | 2 | 0.000 | 0.000 |
| net_medium | `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 196 | 196 | 2.483 | 9 | 0.122 | 0.000 |
| net_medium | `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 120 | 116 | 0.835 | 5 | 0.007 | 0.000 |
| net_medium | `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 104 | 104 | 0.342 | 3 | 0.000 | 0.000 |
| net_medium | `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 63 | 63 | 0.362 | 3 | 0.000 | 0.000 |
| net_medium | `cluster_2447849296_306618051` | 123 | 123 | 0.624 | 5 | 0.012 | 0.000 |
| net_medium | `cluster_266273090_4377707444` | 76 | 76 | 0.299 | 2 | 0.000 | 0.000 |
| net_medium | `cluster_306608060_6131903446` | 99 | 99 | 0.563 | 7 | 0.007 | 0.000 |
| net_medium | `cluster_6633301856_7432359269_7432359283_7432359284` | 240 | 238 | 0.759 | 5 | 0.002 | 0.000 |
| net_heavy | `2387385680` | 14 | 14 | 0.009 | 1 | 0.000 | 0.000 |
| net_heavy | `GS_2407671508` | 188 | 188 | 0.239 | 3 | 0.000 | 0.000 |
| net_heavy | `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 222 | 193 | 0.160 | 4 | 0.000 | 0.000 |
| net_heavy | `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 71 | 71 | 0.087 | 2 | 0.000 | 0.000 |
| net_heavy | `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 244 | 241 | 3.481 | 10 | 0.293 | 0.000 |
| net_heavy | `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 121 | 119 | 0.898 | 5 | 0.003 | 0.000 |
| net_heavy | `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 96 | 96 | 0.443 | 3 | 0.000 | 0.000 |
| net_heavy | `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 94 | 94 | 0.586 | 5 | 0.000 | 0.000 |
| net_heavy | `cluster_2447849296_306618051` | 167 | 167 | 0.696 | 7 | 0.020 | 0.000 |
| net_heavy | `cluster_266273090_4377707444` | 111 | 111 | 0.497 | 4 | 0.000 | 0.000 |
| net_heavy | `cluster_306608060_6131903446` | 141 | 141 | 0.791 | 9 | 0.015 | 0.000 |
| net_heavy | `cluster_6633301856_7432359269_7432359283_7432359284` | 270 | 263 | 0.875 | 5 | 0.003 | 0.000 |
| net_rush_hour | `2387385680` | 11 | 11 | 0.007 | 1 | 0.000 | 0.000 |
| net_rush_hour | `GS_2407671508` | 140 | 140 | 0.162 | 5 | 0.000 | 0.000 |
| net_rush_hour | `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 167 | 145 | 0.141 | 3 | 0.000 | 0.000 |
| net_rush_hour | `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 43 | 43 | 0.059 | 2 | 0.000 | 0.000 |
| net_rush_hour | `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 143 | 143 | 2.383 | 8 | 0.098 | 0.000 |
| net_rush_hour | `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 78 | 78 | 0.586 | 6 | 0.003 | 0.000 |
| net_rush_hour | `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 72 | 71 | 0.295 | 3 | 0.000 | 0.000 |
| net_rush_hour | `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 49 | 49 | 0.363 | 3 | 0.000 | 0.000 |
| net_rush_hour | `cluster_2447849296_306618051` | 86 | 86 | 0.372 | 4 | 0.000 | 0.000 |
| net_rush_hour | `cluster_266273090_4377707444` | 53 | 53 | 0.222 | 3 | 0.000 | 0.000 |
| net_rush_hour | `cluster_306608060_6131903446` | 71 | 71 | 0.482 | 4 | 0.000 | 0.000 |
| net_rush_hour | `cluster_6633301856_7432359269_7432359283_7432359284` | 183 | 182 | 0.488 | 5 | 0.002 | 0.000 |

These are demand-design measurements under native programs, not fixed/rule/PPO comparisons.

## T4.4 fixed/rule teleport re-check (validation seeds 3000–3002)

These controller-baseline measurements use the frozen routes and are separate from the seed-1000 native demand-design table above. Fixed/rule teleports by scenario were:

| Scenario | Fixed teleports / trips | Fixed share | Rule teleports / trips | Rule share |
|---|---:|---:|---:|---:|
| net_balanced | 3 / 1,050 | 0.286% | 0 / 1,050 | 0.000% |
| net_low | 2 / 750 | 0.267% | 0 / 750 | 0.000% |
| net_medium | 16 / 1,950 | 0.821% | 0 / 1,950 | 0.000% |
| net_heavy | 52 / 2,400 | 2.167% | 0 / 2,400 | 0.000% |
| net_rush_hour | 0 / 1,500 | 0.000% | 0 / 1,500 | 0.000% |

The fixed heavy baseline exceeds the 1% target; fixed `net_medium` seed 3000 individually also measured 8/650 (1.23%), although the three-seed medium aggregate is below 1%. Preserve these results without lowering demand. Per-seed outputs and full metrics are in `results/raw/*/summary.csv` and `docs/experiment_log.md`.
