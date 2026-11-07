# Network traffic-light inventory and frozen intended set

Measured using the existing SUMO network and unchanged native demand, seed 1000, for 1800 s.
Native-program teleports observed: 38. The source map under `SUMO/No_Polygon_Map/` was not written.
Intended TLS count: 12; excluded: 1; list SHA-256: `4fc1323e1885d0763d8ac0598a1ec5e7446c6a835a63b62136f657c735979bcd`.
Frozen UTC: `2026-10-31T07:20:08Z`. Maximum approaches: 6; maximum green phases: 4.

| TLS ID | Program | Approaches | Green phases | Crossings/1800 s | Protected foes | Suitability | Reason |
|---|---|---:|---:|---:|---:|---|---|
| `2387385680` | actuated | 2 | 2 | 52 | 0 | intended | meets all suitability criteria |
| `GS_2407671508` | actuated | 4 | 2 | 431 | 0 | intended | meets all suitability criteria |
| `GS_cluster_11178931802_11178931803_2414626606_6887565739` | actuated | 4 | 2 | 316 | 0 | intended | meets all suitability criteria |
| `GS_cluster_12067305554_6017833806_6017833807_6131076159` | actuated | 3 | 2 | 243 | 0 | intended | meets all suitability criteria |
| `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | static | 5 | 4 | 349 | 0 | intended | meets all suitability criteria |
| `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | static | 6 | 4 | 335 | 0 | intended | meets all suitability criteria |
| `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | static | 4 | 4 | 243 | 0 | intended | meets all suitability criteria |
| `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | static | 4 | 3 | 298 | 0 | intended | meets all suitability criteria |
| `cluster_2447849296_306618051` | static | 4 | 2 | 189 | 0 | intended | meets all suitability criteria |
| `cluster_263386438_7432382412` | static | 4 | 2 | 16 | 0 | excluded | 16 native crossings in 1800s, below 20 |
| `cluster_266273090_4377707444` | static | 4 | 2 | 198 | 0 | intended | meets all suitability criteria |
| `cluster_306608060_6131903446` | static | 4 | 3 | 186 | 0 | intended | meets all suitability criteria |
| `cluster_6633301856_7432359269_7432359283_7432359284` | static | 4 | 2 | 526 | 0 | intended | meets all suitability criteria |

## Per-TLS detail


### `2387385680`

- Joined cluster: False; SUMO node IDs: 2387385680; center: [3614.53, 8600.44].
- Movements: 4; permissive/yielding foe overlaps: 0.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'GGGrr'}, {'index': 1, 'duration_s': 6.0, 'state': 'Gyyrr'}, {'index': 2, 'duration_s': 39.0, 'state': 'GrrGG'}, {'index': 3, 'duration_s': 6.0, 'state': 'Grryy'}].

### `GS_2407671508`

- Joined cluster: False; SUMO node IDs: 2407671508; center: [3535.42, 7189.61].
- Movements: 16; permissive/yielding foe overlaps: 14.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'rrrrGGGggrrrrGGGgg'}, {'index': 1, 'duration_s': 6.0, 'state': 'rrrryyyyyrrrryyyyy'}, {'index': 2, 'duration_s': 39.0, 'state': 'GGggrrrrrGGggrrrrr'}, {'index': 3, 'duration_s': 6.0, 'state': 'yyyyrrrrryyyyrrrrr'}].

### `GS_cluster_11178931802_11178931803_2414626606_6887565739`

- Joined cluster: True; SUMO node IDs: cluster_11178931802_11178931803_2414626606_6887565739; center: [3055.54, 7207.25].
- Movements: 16; permissive/yielding foe overlaps: 16.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'rrrrrGGGggrrrrrGGGgg'}, {'index': 1, 'duration_s': 6.0, 'state': 'rrrrryyyyyrrrrryyyyy'}, {'index': 2, 'duration_s': 39.0, 'state': 'GGGggrrrrrGGGggrrrrr'}, {'index': 3, 'duration_s': 6.0, 'state': 'yyyyyrrrrryyyyyrrrrr'}].

### `GS_cluster_12067305554_6017833806_6017833807_6131076159`

- Joined cluster: True; SUMO node IDs: cluster_12067305554_6017833806_6017833807_6131076159; center: [2537.31, 8502.73].
- Movements: 9; permissive/yielding foe overlaps: 8.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'GGGGgGGggrrr'}, {'index': 1, 'duration_s': 6.0, 'state': 'Gyyyyyyyyrrr'}, {'index': 2, 'duration_s': 39.0, 'state': 'GrrrrrrrrGGg'}, {'index': 3, 'duration_s': 6.0, 'state': 'Grrrrrrrryyy'}].

### `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963`

- Joined cluster: True; SUMO node IDs: cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963; center: [1730.06, 7233.24].
- Movements: 22; permissive/yielding foe overlaps: 8.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 20.0, 'state': 'GGGrrrrrGGGrrrrrrrrrrrr'}, {'index': 1, 'duration_s': 5.0, 'state': 'yyyrrrrryyyrrrrrrrrrrrr'}, {'index': 2, 'duration_s': 6.0, 'state': 'rrrGrrrrrrrGGrrrrrrrrrr'}, {'index': 3, 'duration_s': 5.0, 'state': 'rrryrrrrrrryyrrrrrrrrrr'}, {'index': 4, 'duration_s': 22.0, 'state': 'rrrrGGGgrrrrrGGgggrrrrr'}, {'index': 5, 'duration_s': 5.0, 'state': 'rrrryyyyrrrrryyyyyrrrrr'}, {'index': 6, 'duration_s': 22.0, 'state': 'GrrrrrrrrrrrrrrrrrGGGGg'}, {'index': 7, 'duration_s': 5.0, 'state': 'Grrrrrrrrrrrrrrrrryyyyy'}].

### `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293`

- Joined cluster: True; SUMO node IDs: cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293; center: [2353.67, 7618.17].
- Movements: 21; permissive/yielding foe overlaps: 14.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 21.0, 'state': 'rrrrGGGgrrrrrrrrGGGgrrrr'}, {'index': 1, 'duration_s': 3.0, 'state': 'rrrryyyyrrrrrrrryyyyrrrr'}, {'index': 2, 'duration_s': 3.0, 'state': 'rrrrrrrrrrrrrrrrrrrrrrrr'}, {'index': 3, 'duration_s': 22.0, 'state': 'rrrrrrrrGGggrrrrrrrrGGGg'}, {'index': 4, 'duration_s': 3.0, 'state': 'rrrrrrrryyggrrrrrrrryyyg'}, {'index': 5, 'duration_s': 6.0, 'state': 'rrrrrrrrrrGGrrrrrrrrrrrG'}, {'index': 6, 'duration_s': 3.0, 'state': 'rrrrrrrrrryyrrrrrrrrrrry'}, {'index': 7, 'duration_s': 3.0, 'state': 'rrrrrrrrrrrrrrrrrrrrrrrr'}, {'index': 8, 'duration_s': 22.0, 'state': 'GGggrrrrrrrrGGggrrrrrrrr'}, {'index': 9, 'duration_s': 3.0, 'state': 'yyyyrrrrrrrryyyyrrrrrrrr'}, {'index': 10, 'duration_s': 1.0, 'state': 'rrrrrrrrrrrrrrrrrrrrrrrr'}].

### `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011`

- Joined cluster: True; SUMO node IDs: cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011; center: [1715.48, 7672.04].
- Movements: 14; permissive/yielding foe overlaps: 15.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 20.0, 'state': 'rrrrrrrrGGGGGgGGGggg'}, {'index': 1, 'duration_s': 5.0, 'state': 'rrrrrrrryyyyygyyyggg'}, {'index': 2, 'duration_s': 6.0, 'state': 'rrrrrrrrrrrrrGrrrGGG'}, {'index': 3, 'duration_s': 5.0, 'state': 'rrrrrrrrrrrrryrrryyy'}, {'index': 4, 'duration_s': 22.0, 'state': 'GGGGGrrrrrrrrrrrrrrr'}, {'index': 5, 'duration_s': 5.0, 'state': 'yyyyGrrrrrrrrrrrrrrr'}, {'index': 6, 'duration_s': 22.0, 'state': 'rrrrGGGGrrrrrGrrrrrr'}, {'index': 7, 'duration_s': 5.0, 'state': 'rrrryyyyrrrrryrrrrrr'}].

### `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881`

- Joined cluster: True; SUMO node IDs: cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881; center: [1340.25, 6632.6].
- Movements: 19; permissive/yielding foe overlaps: 21.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 26.0, 'state': 'ggGGGGgGGGggggrrrrrrrrr'}, {'index': 1, 'duration_s': 4.0, 'state': 'yyyyyyyyyyyyyyrrrrrrrrr'}, {'index': 2, 'duration_s': 26.0, 'state': 'rrrrrrrrrrrrrrGGggGrrrr'}, {'index': 3, 'duration_s': 4.0, 'state': 'rrrrrrrrrrrrrryyyyGrrrr'}, {'index': 4, 'duration_s': 26.0, 'state': 'GrrrrrrrrrrrrrrrrrGGGGg'}, {'index': 5, 'duration_s': 4.0, 'state': 'yrrrrrrrrrrrrrrrrryyyyy'}].

### `cluster_2447849296_306618051`

- Joined cluster: True; SUMO node IDs: cluster_2447849296_306618051; center: [1738.82, 6965.27].
- Movements: 16; permissive/yielding foe overlaps: 14.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 40.0, 'state': 'GGGggrrrrGGGggrrrr'}, {'index': 1, 'duration_s': 5.0, 'state': 'yyyyyrrrryyyyyrrrr'}, {'index': 2, 'duration_s': 40.0, 'state': 'rrrrrGGggrrrrrGGgg'}, {'index': 3, 'duration_s': 5.0, 'state': 'rrrrryyyyrrrrryyyy'}].

### `cluster_263386438_7432382412`

- Joined cluster: True; SUMO node IDs: cluster_263386438_7432382412; center: [3824.82, 7628.68].
- Movements: 16; permissive/yielding foe overlaps: 22.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'GGGGGggrrrrGGGGGggrrrr'}, {'index': 1, 'duration_s': 6.0, 'state': 'yyyyyyyrrrryyyyyyyrrrr'}, {'index': 2, 'duration_s': 39.0, 'state': 'rrrrrrrGGggrrrrrrrGGgg'}, {'index': 3, 'duration_s': 6.0, 'state': 'rrrrrrryyyyrrrrrrryyyy'}].

### `cluster_266273090_4377707444`

- Joined cluster: True; SUMO node IDs: cluster_266273090_4377707444; center: [2696.97, 6470.57].
- Movements: 16; permissive/yielding foe overlaps: 12.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'GGggrrrrGGggrrrr'}, {'index': 1, 'duration_s': 6.0, 'state': 'yyyyrrrryyyyrrrr'}, {'index': 2, 'duration_s': 39.0, 'state': 'rrrrGGggrrrrGGgg'}, {'index': 3, 'duration_s': 6.0, 'state': 'rrrryyyyrrrryyyy'}].

### `cluster_306608060_6131903446`

- Joined cluster: True; SUMO node IDs: cluster_306608060_6131903446; center: [1747.24, 6593.64].
- Movements: 16; permissive/yielding foe overlaps: 8.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 35.0, 'state': 'rrrrrGGggrrrrGGgg'}, {'index': 1, 'duration_s': 5.0, 'state': 'rrrrryyyyrrrryyyy'}, {'index': 2, 'duration_s': 34.0, 'state': 'GGGggrrrrGGrrrrrr'}, {'index': 3, 'duration_s': 5.0, 'state': 'yyyggrrrryyrrrrrr'}, {'index': 4, 'duration_s': 6.0, 'state': 'rrrGGrrrrrrGGrrrr'}, {'index': 5, 'duration_s': 5.0, 'state': 'rrryyrrrrrryyrrrr'}].

### `cluster_6633301856_7432359269_7432359283_7432359284`

- Joined cluster: True; SUMO node IDs: cluster_6633301856_7432359269_7432359283_7432359284; center: [2345.84, 7220.93].
- Movements: 16; permissive/yielding foe overlaps: 16.
- Phases (index: duration s, state): [{'index': 0, 'duration_s': 39.0, 'state': 'rrrrrGGGggrrrrrGGGgg'}, {'index': 1, 'duration_s': 6.0, 'state': 'rrrrryyyyyrrrrryyyyy'}, {'index': 2, 'duration_s': 39.0, 'state': 'GGGggrrrrrGGGggrrrrr'}, {'index': 3, 'duration_s': 6.0, 'state': 'yyyyyrrrrryyyyyrrrrr'}].

Actuated intended programs were copied with unchanged phase states and nominal durations to `SUMO/derived/network_static_tls.add.xml`.

The intended list is frozen before network evaluation. The all-intended-TLS controlled speed probe is `results/raw/20261031-125924_fixed_medium_s3000`: 12/12 intended junctions controlled, simulation reached the 7200 s cap in 816.5936 s wall time (8.8171 simulated seconds per real second). This was a runtime probe, not a comparative performance evaluation. SUMO teleport warnings appeared during the probe; its current T4.2 run record does not count them, so network metrics must report teleports in T4.4.

T4.1 acceptance recheck on 2026-11-06: `Ai/.venv/Scripts/python.exe scripts/inspect_network_tls.py` inspected 13 TLS for 1800 s, found 12 intended and one excluded, and reproduced frozen hash `4fc1323e1885d0763d8ac0598a1ec5e7446c6a835a63b62136f657c735979bcd`. Native-program run recorded 38 teleports; this inventory probe is not a controller comparison. Config and inventory values matched the frozen list.
