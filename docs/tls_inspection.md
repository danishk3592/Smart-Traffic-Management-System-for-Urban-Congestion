# SUMO traffic-light inspection

Measured 2026-10-24 using the existing network and demand, native programs, seed 1000. The same uninterrupted run included the first 600 s and continued to 1800 s. SUMO reports and edgeData outputs were redirected to a temporary directory; the protected source map was not written.
Unique vehicles are counted from subscribed road-ID transitions matching a controlled from-edge to to-edge pair.

## Suitability ranking

| Rank | TLS ID | Program type | Program ID | Approaches | Green phases | Unique vehicles crossing |
|---:|---|---|---|---:|---:|---:|
| 1 | cluster_6633301856_7432359269_7432359283_7432359284 | static | 0 | 4 | 2 | 526 |
| 2 | GS_2407671508 | actuated | 0 | 4 | 2 | 431 |
| 3 | cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963 | static | 0 | 5 | 4 | 349 |
| 4 | cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293 | static | 0 | 6 | 4 | 335 |
| 5 | GS_cluster_11178931802_11178931803_2414626606_6887565739 | actuated | 0 | 4 | 2 | 316 |
| 6 | cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881 | static | 0 | 4 | 3 | 298 |
| 7 | GS_cluster_12067305554_6017833806_6017833807_6131076159 | actuated | 0 | 3 | 2 | 243 |
| 8 | cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011 | static | 0 | 4 | 4 | 243 |
| 9 | cluster_266273090_4377707444 | static | 0 | 4 | 2 | 198 |
| 10 | cluster_2447849296_306618051 | static | 0 | 4 | 2 | 189 |
| 11 | cluster_306608060_6131903446 | static | 0 | 4 | 3 | 186 |
| 12 | 2387385680 | actuated | 0 | 2 | 2 | 52 |
| 13 | cluster_263386438_7432382412 | static | 0 | 4 | 2 | 16 |

Median count: 243; configured pilot rank: 3; count: 349.

## Configured pilot: cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963

- Runtime program: 0 (static).
- Joined cluster: yes; net node(s): cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963; numeric IDs in generated cluster name: 6.
- Approaches: 5.
- Center (SUMO x,y): (1730.06, 7233.24); junction bounding box: (1719.52, 7218.6, 1741.7, 7253.75).
- Distance to nearest map bounding-box edge: 1730.06 m.

### Running native program phases

| Phase | Duration (s) | State | Classification |
|---:|---:|---|---|
| 0 | 20 | GGGrrrrrGGGrrrrrrrrrrrr | green |
| 1 | 5 | yyyrrrrryyyrrrrrrrrrrrr | yellow |
| 2 | 6 | rrrGrrrrrrrGGrrrrrrrrrr | green |
| 3 | 5 | rrryrrrrrrryyrrrrrrrrrr | yellow |
| 4 | 22 | rrrrGGGgrrrrrGGgggrrrrr | green |
| 5 | 5 | rrrryyyyrrrrryyyyyrrrrr | yellow |
| 6 | 22 | GrrrrrrrrrrrrrrrrrGGGGg | green |
| 7 | 5 | Grrrrrrrrrrrrrrrrryyyyy | mixed |

### Approaches

| Name | Incoming edge | Lanes | Bearing (degrees clockwise from north) |
|---|---|---|---:|
| approach_1 | 27935136#2 | 27935136#2_0 | 73.3 |
| approach_2 | -27936940#1 | -27936940#1_0 | 79.65 |
| approach_3 | 735135993#2 | 735135993#2_0, 735135993#2_1 | 177.98 |
| approach_4 | 1215278281#0 | 1215278281#0_0, 1215278281#0_1 | 268.94 |
| approach_5 | 1215278272#0 | 1215278272#0_0 | 358.36 |

### Distinct controlled movements

| From edge | To edge | TLS link indices |
|---|---|---|
| -27936940#1 | -27935136#2 | 18 |
| -27936940#1 | 1215278273#0 | 21 |
| -27936940#1 | 1215278280#1 | 20 |
| -27936940#1 | 1215278284#2 | 19 |
| -27936940#1 | 27936940#0 | 22 |
| 1215278272#0 | -27935136#2 | 1 |
| 1215278272#0 | 1215278280#1 | 3 |
| 1215278272#0 | 1215278284#2 | 2 |
| 1215278272#0 | 27936940#0 | 0 |
| 1215278281#0 | -27935136#2 | 6 |
| 1215278281#0 | 1215278273#0 | 4 |
| 1215278281#0 | 1215278284#2 | 7 |
| 1215278281#0 | 27936940#0 | 5 |
| 27935136#2 | -27935136#2 | 17 |
| 27935136#2 | 1215278273#0 | 15 |
| 27935136#2 | 1215278280#1 | 14 |
| 27935136#2 | 1215278284#2 | 13 |
| 27935136#2 | 27936940#0 | 16 |
| 735135993#2 | -27935136#2 | 12 |
| 735135993#2 | 1215278273#0 | 9, 10 |
| 735135993#2 | 1215278280#1 | 8 |
| 735135993#2 | 27936940#0 | 11 |

### Foe/conflict check

Method: SUMO junction request foe bitsets and response/yield bitsets; all simultaneous G/g links are checked.
**PASS:** no protected G/G foe pairs; lowercase g overlaps have a network yield response.
Permissive/yielding foe overlaps: 8.
- phase 4: links 5(G) and 15(g) are foes and SUMO request response grants yielding
- phase 4: links 5(G) and 16(g) are foes and SUMO request response grants yielding
- phase 4: links 6(G) and 15(g) are foes and SUMO request response grants yielding
- phase 4: links 6(G) and 16(g) are foes and SUMO request response grants yielding
- phase 4: links 6(G) and 17(g) are foes and SUMO request response grants yielding
- phase 4: links 7(g) and 13(G) are foes and SUMO request response grants yielding
- phase 4: links 7(g) and 14(G) are foes and SUMO request response grants yielding
- phase 6: links 0(G) and 22(g) are foes and SUMO request response grants yielding

Green phases: [0, 2, 4, 6]; yellow phases: [1, 3, 5, 7]; yellow_after: {0: 1, 2: 3, 4: 5, 6: 7}.

## Run evidence

- Simulation duration: 1800 s.
- Unique IDs starting a teleport in first 600 s: 1; over 1800 s: 38.
- Warning lines in first 600 s: 2; over 1800 s: 71.
  - Warning: Teleporting vehicle 'veh188'; waited too long (yield), lane='60194989#8_0', time=542.00.
  - Warning: Vehicle 'veh188' ends teleporting on edge '1215278280#1', time=552.00.
  - Warning: Teleporting vehicle 'veh655'; waited too long (yield), lane='-28535807#0_0', time=856.00.
  - Warning: Vehicle 'veh655' ends teleporting on edge '-1340257807', time=856.00.
  - Warning: Teleporting vehicle 'veh663'; waited too long (yield), lane='-28535807#0_0', time=1162.00.
  - Warning: Vehicle 'veh663' ends teleporting on edge '-1340257807', time=1162.00.
  - Warning: Teleporting vehicle 'veh422'; waited too long (jam), lane='-1384917246_0', time=1324.00.
  - Warning: Vehicle 'veh422' ends teleporting on edge '-1340257807', time=1324.00.
  - Warning: Teleporting vehicle 'veh706'; waited too long (jam), lane='-1391538489_0', time=1343.00.
  - Warning: Vehicle 'veh706' ends teleporting on edge '-1391538488', time=1343.00.
  - Warning: Teleporting vehicle 'veh932'; waited too long (yield), lane='655504666_0', time=1346.00.
  - Warning: Vehicle 'veh932' ends teleporting on edge '-1391538489', time=1346.00.
  - Warning: Teleporting vehicle 'veh1259'; waited too long (yield), lane='128220108#8_0', time=1367.00.
  - Warning: Teleporting vehicle 'veh397'; waited too long (yield), lane='-413271593_0', time=1390.00.
  - Warning: Vehicle 'veh397' ends teleporting on edge '-1340257806#2', time=1390.00.
  - Warning: Teleporting vehicle 'veh522'; waited too long (jam), lane='-1340257807_0', time=1392.00.
  - Warning: Teleporting vehicle 'veh1331'; waited too long (yield), lane='-654386823#0_0', time=1392.00.
  - Warning: Vehicle 'veh522' ends teleporting on edge '-413271593', time=1392.00.
  - Warning: Teleporting vehicle 'veh1319'; waited too long (yield), lane='-237478670#3_0', time=1393.00.
  - Warning: Vehicle 'veh1259' ends teleporting on edge '60194989#6', time=1398.00.
  - Warning: Teleporting vehicle 'veh1363'; waited too long (yield), lane='-1430862729_0', time=1411.00.
  - Warning: Vehicle 'veh1363' ends teleporting on edge '60194989#6', time=1411.00.
  - Warning: Teleporting vehicle 'veh1364'; waited too long (yield), lane='27936940#4_0', time=1413.00.
  - Warning: Teleporting vehicle 'veh625'; waited too long (yield), lane='60194989#8_0', time=1420.00.
  - Warning: Teleporting vehicle 'veh319'; waited too long (jam), lane='60194989#7_0', time=1425.00.
  - Warning: Vehicle 'veh319' ends teleporting on edge '60194989#8', time=1428.00.
  - Warning: Teleporting vehicle 'veh546'; waited too long (jam), lane='60194989#5_0', time=1440.00.
  - Warning: Vehicle 'veh625' ends teleporting on edge '1215278280#1', time=1440.00.
  - Warning: Vehicle 'veh1364' ends teleporting on edge '60194989#5', time=1440.00.
  - Warning: Teleporting vehicle 'veh1394'; waited too long (yield), lane='-1101696071_0', time=1450.00.
  - Warning: Teleporting vehicle 'veh838'; waited too long (jam), lane='60194989#3_0', time=1456.00.
  - Warning: Teleporting vehicle 'veh925'; waited too long (jam), lane='60194989#2_0', time=1459.00.
  - Warning: Vehicle 'veh1331' ends teleporting on edge '-1391538489', time=1462.00.
  - Warning: Teleporting vehicle 'veh1098'; waited too long (jam), lane='60194989#1_0', time=1465.00.
  - Warning: Teleporting vehicle 'veh1378'; waited too long (yield), lane='317318168#4_0', time=1466.00.
  - Warning: Teleporting vehicle 'veh1286'; waited too long (jam), lane='60194989#0_0', time=1467.00.
  - Warning: Vehicle 'veh1394' ends teleporting on edge '-1391538489', time=1520.00.
  - Warning: Vehicle 'veh1319' ends teleporting on edge '-1391538489', time=1552.00.
  - Warning: Teleporting vehicle 'veh1393'; waited too long (jam), lane='744561216#0_0', time=1562.00.
  - Warning: Vehicle 'veh1393' ends teleporting on edge '744561215', time=1562.00.
  - Warning: Vehicle 'veh546' ends teleporting on edge '1215278280#1', time=1594.00.
  - Warning: Teleporting vehicle 'veh807'; waited too long (yield), lane='655504666_0', time=1650.00.
  - Warning: Vehicle 'veh807' ends teleporting on edge '-1391538489', time=1650.00.
  - Warning: Vehicle 'veh1378' ends teleporting on edge '60194989#6', time=1655.00.
  - Warning: Teleporting vehicle 'veh1100'; waited too long (yield), lane='237478670#2_0', time=1680.00.
  - Warning: Teleporting vehicle 'veh1167'; waited too long (jam), lane='237478670#1_0', time=1684.00.
  - Warning: Vehicle 'veh1167' ends teleporting on edge '-1217023688#1', time=1691.00.
  - Warning: Teleporting vehicle 'veh482'; waited too long (yield), lane='-413271593_0', time=1696.00.
  - Warning: Vehicle 'veh482' ends teleporting on edge '-1340257806#2', time=1696.00.
  - Warning: Teleporting vehicle 'veh1376'; waited too long (yield), lane='-654386823#0_0', time=1697.00.
  - Warning: Teleporting vehicle 'veh1540'; waited too long (yield), lane='-237478670#3_0', time=1698.00.
  - Warning: Teleporting vehicle 'veh743'; waited too long (jam), lane='-1340257807_0', time=1700.00.
  - Warning: Teleporting vehicle 'veh646'; waited too long (jam), lane='-1384917246_0', time=1706.00.
  - Warning: Vehicle 'veh743' ends teleporting on edge '-413271593', time=1712.00.
  - Warning: Teleporting vehicle 'veh927'; waited too long (jam), lane=':313460477_7_0', time=1713.00.
  - Warning: Vehicle 'veh646' ends teleporting on edge '-1340257807', time=1717.00.
  - Warning: Teleporting vehicle 'veh1418'; waited too long (yield), lane='28535816#0_0', time=1719.00.
  - Warning: Teleporting vehicle 'veh1700'; waited too long (yield), lane='27936940#4_0', time=1721.00.
  - Warning: Vehicle 'veh1418' ends teleporting on edge '-28535807#0', time=1731.00.
  - Warning: Vehicle 'veh838' ends teleporting on edge '1215278280#1', time=1733.00.
  - Warning: Vehicle 'veh927' ends teleporting on edge '-1340257807', time=1733.00.
  - Warning: Teleporting vehicle 'veh596'; waited too long (jam), lane='60194989#5_0', time=1744.00.
  - Warning: Vehicle 'veh596' ends teleporting on edge '60194989#6', time=1744.00.
  - Warning: Vehicle 'veh1700' ends teleporting on edge '60194989#5', time=1744.00.
  - Warning: Vehicle 'veh1098' ends teleporting on edge '1340257806#1', time=1751.00.
  - Warning: Vehicle 'veh925' ends teleporting on edge '1215278284#2', time=1758.00.
  - Warning: Vehicle 'veh1376' ends teleporting on edge '237478670#3', time=1758.00.
  - Warning: Teleporting vehicle 'veh1713'; waited too long (yield), lane='128220108#8_0', time=1762.00.
  - Warning: Teleporting vehicle 'veh981'; waited too long (jam), lane='60194989#2_0', time=1764.00.
  - Warning: Teleporting vehicle 'veh1693'; waited too long (yield), lane='317318168#4_0', time=1770.00.
  - Warning: Vehicle 'veh1693' ends teleporting on edge '60194989#1', time=1771.00.
