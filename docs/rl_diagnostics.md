# T2.5 RL diagnostics

| Field | Value |
|---|---|
| Evaluation date | 2026-10-27 UTC |
| Checkpoint | `Ai/rl/models/ppo_v2_variant_waithalf/evaluations/20261026-182752/best_model.zip` |
| Checkpoint SHA-256 | `9d0e3e82d8aab4e1d38c1e79ad29ec9e637ecd7001500a5b5aad3852c01bc467` |
| Seeds/scenarios | Validation seeds 3000–3002; medium and heavy; same cached route per controller/scenario/seed |

## Episode results

| Scenario | Seed | Controller | Run artifacts | Trips completed / scheduled (rate) | Junction trips completed / scheduled | Teleports | Junction travel time completed (s) | Junction travel time censored (s) | Queue | Wait (s) | Time loss (s) |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| medium | 3000 | fixed | `results\raw\20261027-133344_fixed_medium_s3000` | 1534/2600 (59.00%) | 396/1346 | 1082 | 3369.0304797979798 | 4657.724420505201 | 59.47847222222222 | 2505.193076923077 | 2606.351803846154 |
| medium | 3000 | rule | `results\raw\20261027-134325_rule_medium_s3000` | 1544/2600 (59.38%) | 421/1346 | 1145 | 3321.700047505938 | 4626.7043610698365 | 61.104166666666664 | 2526.413846153846 | 2627.035661538461 |
| medium | 3000 | rl | `results\raw\20261027-135309_rl_medium_s3000` | 1621/2600 (62.35%) | 478/1346 | 1094 | 3218.4272175732217 | 4438.862607726597 | 61.61666666666667 | 2373.7373076923077 | 2480.356969230769 |
| medium | 3001 | fixed | `results\raw\20261027-140427_fixed_medium_s3001` | 1570/2600 (60.38%) | 436/1340 | 1066 | 3024.181399082569 | 4439.029947761194 | 51.84097222222222 | 2381.960769230769 | 2481.859503846154 |
| medium | 3001 | rule | `results\raw\20261027-162514_rule_medium_s3001` | 1495/2600 (57.50%) | 393/1340 | 1099 | 3136.2325954198473 | 4586.370992537313 | 54.821527777777774 | 2531.3211538461537 | 2636.0219500000003 |
| medium | 3001 | rl | `results\raw\20261027-163912_rl_medium_s3001` | 1569/2600 (60.35%) | 444/1340 | 1055 | 2973.574099099099 | 4405.250843283582 | 58.75833333333333 | 2403.7176923076922 | 2508.5905769230767 |
| medium | 3002 | fixed | `results\raw\20261027-171359_fixed_medium_s3002` | 1549/2600 (59.58%) | 423/1343 | 1078 | 3189.624326241135 | 4507.363194341027 | 53.108333333333334 | 2421.8096153846154 | 2520.639853846154 |
| medium | 3002 | rule | `results\raw\20261027-172651_rule_medium_s3002` | 1540/2600 (59.23%) | 417/1343 | 1041 | 3205.4937170263793 | 4523.489776619508 | 52.91180555555555 | 2429.4934615384614 | 2526.888007692308 |
| medium | 3002 | rl | `results\raw\20261027-174008_rl_medium_s3002` | 1554/2600 (59.77%) | 427/1343 | 1057 | 3202.07943793911 | 4477.377341772151 | 55.706944444444446 | 2418.1015384615384 | 2521.0254653846155 |
| heavy | 3000 | fixed | `results\raw\20261027-175219_fixed_heavy_s3000` | 2019/3600 (56.08%) | 552/1898 | 1600 | 3420.7948550724636 | 4671.913530031613 | 58.052083333333336 | 2671.4416666666666 | 2775.170266666667 |
| heavy | 3000 | rule | `results\raw\20261027-181033_rule_heavy_s3000` | 1964/3600 (54.56%) | 516/1898 | 1577 | 3240.128817829457 | 4670.090031612224 | 60.045138888888886 | 2680.1111111111113 | 2782.944875 |
| heavy | 3000 | rl | `results\raw\20261027-182835_rl_heavy_s3000` | 2069/3600 (57.47%) | 597/1898 | 1582 | 3335.849179229481 | 4596.027860906218 | 62.234722222222224 | 2612.325 | 2716.2914638888888 |
| heavy | 3001 | fixed | `results\raw\20261027-184619_fixed_heavy_s3001` | 2071/3600 (57.53%) | 597/1905 | 1646 | 3454.3467336683416 | 4619.0531706036745 | 55.77569444444445 | 2636.3283333333334 | 2739.355261111111 |
| heavy | 3001 | rule | `results\raw\20261027-190343_rule_heavy_s3001` | 2127/3600 (59.08%) | 633/1905 | 1598 | 3540.0809952606637 | 4615.600152230971 | 59.64513888888889 | 2607.0980555555557 | 2709.473458333333 |
| heavy | 3001 | rl | `results\raw\20261027-192108_rl_heavy_s3001` | 2040/3600 (56.67%) | 566/1905 | 1651 | 3385.7096113074203 | 4638.372330708661 | 58.43541666666667 | 2631.5819444444446 | 2734.7855416666666 |
| heavy | 3002 | fixed | `results\raw\20261027-193743_fixed_heavy_s3002` | 2082/3600 (57.83%) | 596/1895 | 1550 | 3591.72639261745 | 4688.689546174142 | 58.17777777777778 | 2647.0822222222223 | 2751.130977777778 |
| heavy | 3002 | rule | `results\raw\20261027-195414_rule_heavy_s3002` | 2060/3600 (57.22%) | 578/1895 | 1568 | 3488.5091003460207 | 4658.735984168865 | 58.704166666666666 | 2655.6330555555555 | 2758.533288888889 |
| heavy | 3002 | rl | `results\raw\20261027-201154_rl_heavy_s3002` | 2040/3600 (56.67%) | 580/1895 | 1571 | 3520.7581896551724 | 4647.080575197889 | 59.30972222222222 | 2655.6202777777776 | 2762.055933333333 |

Trips completed is the scheduled vehicle count and completed count. Junction trip counts and completed/censored travel times use the Section 11 route-through-junction definitions.

## RL policy diagnostics

| Scenario | Seed | Requested PPO action histogram | PPO-controlled phase usage | Mean green by phase (s, full episode) | Forced max-green switches | Accepted switches | Forced share | Safety rejections / decisions | Fallback activations |
|---|---:|---|---|---|---:|---:|---:|---:|---:|
| medium | 3000 | `{"approach": 0, "extend": 1318, "hold": 0, "switch": 122}` | `{"0": 222, "2": 215, "4": 192, "6": 195}` | `{"0": 32.53846153846154, "2": 31.557692307692307, "4": 29.627450980392158, "6": 30.11764705882353}` | 0 | 205 | 0.00% | 572 / 1440 (39.72%) | 572 |
| medium | 3001 | `{"approach": 0, "extend": 1288, "hold": 0, "switch": 152}` | `{"0": 225, "2": 206, "4": 193, "6": 178}` | `{"0": 31.833333333333332, "2": 29.87037037037037, "4": 29.11320754716981, "6": 27.79245283018868}` | 0 | 213 | 0.00% | 582 / 1440 (40.42%) | 582 |
| medium | 3002 | `{"approach": 0, "extend": 1273, "hold": 0, "switch": 167}` | `{"0": 220, "2": 210, "4": 185, "6": 175}` | `{"0": 31.254545454545454, "2": 30.35185185185185, "4": 27.75925925925926, "6": 27.38888888888889}` | 0 | 216 | 0.00% | 590 / 1440 (40.97%) | 590 |
| heavy | 3000 | `{"approach": 0, "extend": 1297, "hold": 0, "switch": 143}` | `{"0": 225, "2": 202, "4": 190, "6": 193}` | `{"0": 32.22641509433962, "2": 30.132075471698112, "4": 29.173076923076923, "6": 29.653846153846153}` | 0 | 209 | 0.00% | 581 / 1440 (40.35%) | 581 |
| heavy | 3001 | `{"approach": 0, "extend": 1320, "hold": 0, "switch": 120}` | `{"0": 220, "2": 210, "4": 200, "6": 192}` | `{"0": 32.15384615384615, "2": 31.192307692307693, "4": 30.21153846153846, "6": 29.627450980392158}` | 0 | 206 | 0.00% | 575 / 1440 (39.93%) | 575 |
| heavy | 3002 | `{"approach": 0, "extend": 1339, "hold": 0, "switch": 101}` | `{"0": 225, "2": 217, "4": 200, "6": 195}` | `{"0": 33.05882352941177, "2": 32.07843137254902, "4": 30.294117647058822, "6": 30.5}` | 0 | 202 | 0.00% | 566 / 1440 (39.31%) | 566 |

## Gate comparison

| Scenario | Seed | Common completed junction trips | Fixed mean (s) | RL mean (s) | RL change vs fixed |
|---|---:|---:|---:|---:|---:|
| medium | 3000 | 294 | 3181.17 | 2773.51 | -12.81% |
| medium | 3001 | 314 | 2729.60 | 2712.51 | -0.63% |
| medium | 3002 | 269 | 2882.71 | 2753.06 | -4.50% |
| heavy | 3000 | 353 | 3119.28 | 2858.31 | -8.37% |
| heavy | 3001 | 372 | 3013.80 | 3016.53 | 0.09% |
| heavy | 3002 | 354 | 3203.54 | 3113.92 | -2.80% |

Across the pooled paired common trips: fixed mean 3028.68 s; RL mean 2884.04 s; RL change -4.78%. This is the matched-trip T2.5 comparison; censored travel time and completion counts remain alongside it above.

Requested policy actions across RL episodes: `{"approach": 0, "extend": 7835, "hold": 0, "switch": 805}` (2 distinct). Phases used: `[0, 2, 4, 6]`. Forced max-green share: 0/1251 (0.00%).

| Criterion | Result | Evidence |
|---|---|---|
| At least 2 distinct RL actions | PASS | 2 requested actions across six episodes |
| All green phases served | PASS | phases [0, 2, 4, 6]; expected [0, 2, 4, 6] |
| Forced max-green switches < 30% | PASS | 0/1251 = 0.00% |
| Junction travel time no more than 5% worse than fixed | PASS | paired common-trip change -4.78% |

**Overall gate:** PASS.

Safety-rejected actions and teleports are preserved as measurements. This gate passed, so no T2.5 tuning iteration was needed and the pinned checkpoint remains selected.
Mean green durations and forced-switch counts cover the full safety-controlled episode, including intervals after a fallback. PPO phase coverage excludes rows whose action is prefixed `fallback:` in `steps.csv`; this prevents fixed-time fallback from satisfying the PPO phase-use criterion.

## Artifact paths

Each `Run artifacts` entry contains immutable `run.json`, `summary.csv`, `steps.csv`, and `trips.csv`. RL `run.json` records the pinned model path, policy action histogram, phase usage, green-duration diagnostics, safety rejections, fallback actions, and forced max-green share.

## Part 2 — T4.7 network PPO gate audit (2026-11-01)

Selected model: `Ai/rl/models/ppo_net_v2/evaluations/best_model.zip`, SHA-256 `a536084b147bca9b5e9e56651a836455f4b4e9ad90777fb5cea6dbab09110566`. It was selected at 940,008 steps, before Stage 3 began at 2,076,672; the selected checkpoint's Stage 2 decision interval and the gate config are both 5 s. The frozen slot order/hash is unchanged. Six RL artifacts were produced by job `20261101-101549_51ad5875` (return code 0); the first attempt `20261101-101030_1be0de33` exited 1 after `net_medium/3000` when a post-close diagnostic queried TraCI. Its partial directory `results/raw/20261101-154039_rl_net_medium_s3000` is preserved and excluded. No model or further cell was run for this audit.

The six RL cells each contain `run.json`, `summary.csv`, `steps.csv`, `trips.csv`, and 12 TLS rows in `junctions.csv`; all scheduled trips completed. Fixed/rule rows below are the T4.4 paired run IDs in `results/summary/t44_network_common_trips.csv`. Those selected baseline artifacts were checked for 12 TLS rows and 100% completion; the matching trip counts are 650 (medium) and 800 (heavy) in every controller/seed cell.

| Scenario | Seed | RL run | Censored mean RL (s) | Fixed (s) | Rule (s) | Completion RL/fixed/rule |
|---|---:|---|---:|---:|---:|---:|
| net_medium | 3000 | `20261101-154554_rl_net_medium_s3000` | 268.923 | 364.737 | 271.618 | 100% / 100% / 100% |
| net_medium | 3001 | `20261101-154941_rl_net_medium_s3001` | 267.259 | 336.296 | 267.179 | 100% / 100% / 100% |
| net_medium | 3002 | `20261101-155310_rl_net_medium_s3002` | 268.520 | 329.438 | 268.629 | 100% / 100% / 100% |
| net_heavy | 3000 | `20261101-155645_rl_net_heavy_s3000` | 277.025 | 540.032 | 273.090 | 100% / 100% / 100% |
| net_heavy | 3001 | `20261101-160029_rl_net_heavy_s3001` | 267.464 | 416.816 | 267.980 | 100% / 100% / 100% |
| net_heavy | 3002 | `20261101-160411_rl_net_heavy_s3002` | 270.538 | 479.393 | 273.232 | 100% / 100% / 100% |

Pooling the 4,350 completed trips per controller gives censored mean travel times of **270.133 s RL**, **418.115 s fixed**, and **270.407 s rule**. RL is 35.39% lower than fixed and 0.10% lower than rule on this gate grid. This is the T4.7 sanity grid, not the T4.8/4.9 final result.

### Per-junction diversity and diagnostics

Action indices match the training environment: 0 = keep/one-interval safe extension, 1 = switch, 2 = 5 s hold lockout, 3 = 10 s hold lockout. The saved action histogram is binned after the controller applies hold lockout, so its `keep` count can include overridden outputs. For diversity, lockout overrides were removed from `keep`: at TLS `2387385680`, 2,138 overrides leave 557 raw keeps; at TLS `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293`, 2,208 overrides leave 10 raw keeps. All other TLS had zero overrides. This correction does not change the diversity result. The four switch-only TLS had zero overrides and therefore emitted only action 1 in all six cells. Safety rejections and fallback actions are measured separately and do not enter the policy-action set.

| TLS | Distinct PPO actions observed (count) | PPO phase use across six cells | Mean green by phase (s; mean of episode means) | Forced / recorded `n_switches` | Safety rejected (%) | Hold overridden (%) | Mean PPO tick share | Fallback activations | Queue change vs fixed |
|---|---|---|---|---:|---:|---:|---:|---:|
| `2387385680` | keep, switch, hold_10s (3) | 0:2156, 2:1889 | 0:16.97, 2:14.99 | 0/1261 | 23.77 | 40.29 | 0.7625 | 1261 | -58.47% |
| `GS_2407671508` | keep, switch (2) | 0:2000, 2:1984 | 0:14.98, 2:14.98 | 0/5193 | 74.78 | 0.00 | 0.2520 | 3968 | -7.86% |
| `GS_cluster_11178931802_11178931803_2414626606_6887565739` | keep, switch (2) | 0:1998, 2:1985 | 0:14.94, 2:14.99 | 0/5296 | 74.95 | 0.00 | 0.2503 | 3977 | +8.85% |
| `GS_cluster_12067305554_6017833806_6017833807_6131076159` | keep, switch (2) | 0:2001, 2:1983 | 0:15.04, 2:15.00 | 0/5215 | 74.24 | 0.00 | 0.2579 | 3939 | -31.02% |
| `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | switch (1) | 0:894, 2:886, 4:884, 6:878 | 0:11.00, 2:11.00, 4:11.00, 6:10.96 | 0/5306 | 66.70 | 0.00 | 0.3328 | 3539 | -57.17% |
| `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | keep, switch, hold_10s (3) | 0:2014, 3:891, 5:891, 8:916 | 0:30.45, 3:15.00, 5:13.00, 8:15.47 | 0/1979 | 25.63 | 41.61 | 0.7437 | 1360 | -51.66% |
| `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | keep, switch (2) | 0:894, 2:886, 4:884, 6:878 | 0:11.00, 2:11.00, 4:11.00, 6:10.96 | 0/5270 | 66.70 | 0.00 | 0.3328 | 3539 | -52.35% |
| `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | switch (1) | 0:1778, 2:1764, 4:1764 | 0:11.96, 2:12.00, 4:12.00 | 0/5306 | 66.70 | 0.00 | 0.3328 | 3539 | -55.41% |
| `cluster_2447849296_306618051` | keep, switch (2) | 0:1778, 2:1764 | 0:11.00, 2:10.98 | 0/5305 | 66.70 | 0.00 | 0.3328 | 3539 | -49.42% |
| `cluster_266273090_4377707444` | switch (1) | 0:1998, 2:1985 | 0:14.94, 2:14.99 | 0/5306 | 75.01 | 0.00 | 0.2497 | 3980 | -14.60% |
| `cluster_306608060_6131903446` | switch (1) | 0:1190, 2:1176, 4:1176 | 0:10.97, 2:11.00, 4:11.00 | 0/5306 | 66.70 | 0.00 | 0.3328 | 3539 | -42.86% |
| `cluster_6633301856_7432359269_7432359283_7432359284` | keep, switch (2) | 0:1998, 2:1985 | 0:14.94, 2:14.99 | 0/5299 | 74.99 | 0.00 | 0.2499 | 3979 | -4.28% |

Recorded action histogram counts, ordered `keep/switch/hold_5s/hold_10s` (post-lockout binning; see correction above):

| TLS | K/S/H5/H10 counts |
|---|---:|
| `2387385680` | 2695/1261/0/1350 |
| `GS_2407671508` | 113/5193/0/0 |
| `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 10/5296/0/0 |
| `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 91/5215/0/0 |
| `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 0/5306/0/0 |
| `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 2218/1979/0/1109 |
| `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 36/5270/0/0 |
| `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 0/5306/0/0 |
| `cluster_2447849296_306618051` | 1/5305/0/0 |
| `cluster_266273090_4377707444` | 0/5306/0/0 |
| `cluster_306608060_6131903446` | 0/5306/0/0 |
| `cluster_6633301856_7432359269_7432359283_7432359284` | 7/5299/0/0 |

The diversity gate is **8/12 = 66.67%**, below the required 80% (at least 10 TLS). The exact single-action TLS are the pilot `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963`, `cluster618250255_7478115627_cluster_11927462278_11927462280_7479633881`, `cluster_266273090_4377707444`, and `cluster_306608060_6131903446`; each requested `switch` in all 5,306 policy decisions and had zero hold overrides. The index-to-action mapping and the 5 s decision interval are consistent with the selected Stage 2 checkpoint. Safety rejected 40,159/63,672 requested actions (63.07%) and triggered the same number of per-TLS fallback activations; this explains reduced mean PPO tick share (36.92%, range 24.96–77.07%) but cannot explain the four single-action histograms because those have no lockout overrides and rejected/fallback actions are not counted as policy actions.

| T4.7 criterion | Status | Verified evidence |
|---|---|---|
| (a) PPO coverage at all 12 frozen TLS | PASS, with fallback caveat | All six `run.json` files report `ai_coverage=full`, 12/12 AI/controlled TLS; all 72 junction rows say `controlled_by=rl`. Every TLS received PPO decisions and accepted PPO switches. `ppo_tick_share` is nonzero at all TLS but is reduced by safety-triggered fallback as reported above. |
| (b) ≥80% of TLS use ≥2 distinct PPO actions | **FAIL** | 8/12 (66.67%); the four switch-only TLS are enumerated above. |
| (c) Forced max-green <30% of switches | PASS | Zero forced max-green switches in all 72 TLS episodes. Actual switch count is positive (the four switch-only TLS each had accepted switch requests); thus forced share is 0%. The stored `n_switches` total is 56,042 but can include fallback-accepted replacements after a rejected PPO request, so it is not an exact accepted-PPO denominator. |
| (d) Censored travel time no more than 5% worse than fixed | PASS | Pooled 4,350-trip RL mean 270.133 s vs fixed 418.115 s (-35.39%); all comparison cells have 100% completion. |
| (e) Worst TLS queue regression reported; investigate if >50% | PASS | Worst is `GS_cluster_11178931802_11178931803_2414626606_6887565739` at +8.85%; none exceeded +50%. |
| (f) Median batched-inference latency <100 ms | PASS | Median 1.2693 ms across 5,306 batches; maximum 2.9032 ms. |
| Required controller test | PASS | `Ai/.venv/Scripts/pytest.exe -q tests/test_rl_network_controller.py` → **5 passed**, one pytest cache-path warning. |

**Status at the initial-model audit (before remediation): T4.7 In progress.** The initial policy's diversity failure was genuine model action collapse, not an action-index/slot-order mapping error or fallback contamination. At that point no change or rerun had yet been authorized. The subsequent authorized rejection-penalty candidate and completed gate are recorded below; this historical disposition is superseded by the final acceptance verdict.

### Targeted action-diversity investigation — 2026-11-01

The four switch-only TLS above each requested policy index 1 (`switch`) for all 5,306 decisions across the six saved cells. They had zero hold-lockout overrides. Their rejection rates were 3,539/5,306 (66.70%) at `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963`, 3,539/5,306 (66.70%) at `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881`, 3,980/5,306 (75.01%) at `cluster_266273090_4377707444`, and 3,539/5,306 (66.70%) at `cluster_306608060_6131903446`. The saved six-cell aggregate rejection reasons were 13,530 clearance-phase, 24,615 minimum-green, and 2,014 other rejections. The logs do not attach rejection reasons to TLS, so the reason split for these four specifically is unavailable; safety code permits switch rejection only during clearance or before the 10 s minimum green.

The action index/slot order and decision cadence match between training and deployment (5 s). The policy output collapse is therefore measured correctly and not explained by lockout or fallback histogram contamination. There is, however, a training/deployment response mismatch after rejection: training increments `illegal_action` and safely attempts one-interval extension, but the reward has no rejection penalty; deployment calls the TLS-local fallback controller and changes control ownership. The reward contains queue, wait, and throughput terms only. This supports testing a small configurable negative reward term for rejected actions, but does not prove that omission caused the collapse or guarantee improved diversity. Keep the safety constraints unchanged and count raw PPO requests separately from applied actions.

The historical `steps.csv` `action_accepted` field records the final result after fallback, obscuring whether the PPO request itself was accepted. Instrumentation now records `requested_action_accepted`, `fallback_action_accepted`, `fallback_used`, and `safety_rejection_reason`; junction diagnostics separately record raw `action_histogram` and lockout-adjusted `applied_action_histogram`. Existing six-cell artifacts are immutable and were not regenerated. Focused tests: `Ai/.venv/Scripts/pytest.exe -q tests/test_rl_network_controller.py tests/test_run_episode.py` → **8 passed** (pytest cache-path warning); focused Ruff check → **All checks passed**.

**Disposition at the investigation checkpoint (before separate authorization):** No PPO policy, model, training run, or gate episode had yet been changed or run. The proposed remediation was a small configurable rejection penalty, per-TLS rejection-reason diagnostics, a versioned model candidate, then the same six cells. The estimate was based on measured Stage 3 throughput; this plan was subsequently authorized and executed as recorded below. This is historical, not the current T4.7 status.

### Authorized rejection-penalty candidate — pre-run record (2026-11-01)

The owner authorized one isolated candidate using `Ai/rl/models/ppo_net_v2/checkpoints/ppo_2196480_steps.zip` (2,196,480 steps; SHA-256 `7b17b0df973d56a611c9700a7026def41b771e800332912ed5283e5b2bfb0675`) and target **2,296,476** (99,996 additional steps). Candidate path is `Ai/rl/models/ppo_net_v2_rejection_penalty_005/`; original checkpoint, selected model, and six prior gate cells remain unchanged. Configured penalty is **0.05 per locally rejected/overridden action**, about 3.33% of the base local reward's maximum absolute bound (1.5). It is applied after the existing network-wide term so it affects only the TLS whose request was rejected. Safety constraints and gate thresholds remain unchanged.

Verified pre-run cumulative training time is **36,841.7217013 s**; the authorized hard cap is **43,000 s** (6,158.2782987 s remaining). The shared `config/stms.yaml` setting stays at 40,000 s; trainer support for a run-specific CLI cap is tested and records the effective cap in candidate metadata. The cap callback keeps a 300 s finalization reserve. Existing Stage 3 scenario/episode/interval settings, seed 1001, reward weights, network term 0.25, and PPO hyperparameters are retained; validation runs every 20,000 steps without plateau early-stop for this fixed-budget candidate. Exact-target PPO shortens its final rollout to 141 vector steps and completes that PPO update.

Before training: trainer/penalty tests 11 passed; full SUMO environment suite 9 passed; updated lockout-reason and reward-locality tests each 1 passed; Ruff clean. T4.4 selected baseline artifacts for all six cells were revalidated (complete files, 12 TLS rows, 100% completion). For `rule/net_medium/3001`, duplicate summary run IDs were disambiguated by confirming the frozen T4.4 q8/w45 controller parameters. No training or candidate gate cell has run yet. After training, candidate validation must produce a loadable best model and finite rows before running exactly `net_medium/net_heavy` × seeds 3000–3002; no T4.8 work.

### Candidate training progress — job `20261101-113217_b592e349`

Authorized training job `20261101-113217_b592e349` exited **0** at exactly **2,296,476** timesteps. Cumulative training time is **38,893.1046384 s**, within the **43,000 s** run cap by **4,106.8953616 s**. Latest durable checkpoint `ppo_2296320_steps.zip` and selected candidate `evaluations/best_model.zip` reload successfully, have valid ZIP integrity, observation space `(54,)`, and four discrete actions. `model.zip` and the selected best model SHA-256 match: `758711e7f28e29e69b59af6eade30ba679c3160daadf39e09ed89287f5037757`. Six validation rounds (18 scenario/seed rows) are finite; best is **253.432630 s censored travel time** at **2,240,004** steps. Six-cell candidate gate job `20261101-120825_14a91b7b` exited **0**; final validity and acceptance results follow. Previous model and gate results remain intact. The resumed SB3 TensorBoard writer added one new event file under the old run's folder while preserving existing files.

#### Rejection-penalty candidate gate — completed cell results

| Scenario | Seed | Run | TLS coverage | Completed / total trips | Censored network travel time (s) | Mean junction queue | Worst-junction mean queue | Teleports | Wall (s) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| net_medium | 3000 | `20261101-173830_rl_net_medium_s3000` | 12/12, full | 650/650 | 271.543 | 0.3533 | 1.3503 | 0 | 233.132 |
| net_medium | 3001 | `20261101-174224_rl_net_medium_s3001` | 12/12, full | 650/650 | 267.250 | 0.3657 | 1.2106 | 0 | 227.598 |
| net_medium | 3002 | `20261101-174614_rl_net_medium_s3002` | 12/12, full | 650/650 | 267.417 | 0.3585 | 1.3544 | 0 | 258.011 |
| net_heavy | 3000 | `20261101-175034_rl_net_heavy_s3000` | 12/12, full | 800/800 | 272.249 | 0.4914 | 1.9767 | 0 | 234.028 |
| net_heavy | 3001 | `20261101-175430_rl_net_heavy_s3001` | 12/12, full | 800/800 | 268.802 | 0.5007 | 1.9810 | 0 | 210.934 |
| net_heavy | 3002 | `20261101-175802_rl_net_heavy_s3002` | 12/12, full | 800/800 | 272.772 | 0.4772 | 1.9852 | 0 | 255.469 |

All six candidate cells completed; gate job `20261101-120825_14a91b7b` exited 0. The aggregate audit below uses only the candidate-hash-matched six RL runs and the already validated T4.4 fixed/rule baselines. Each candidate run has five nonempty artifacts, 12 unique RL-controlled TLS rows, and matching trip/run records. All 4,350 scheduled candidate trips completed; all six report full AI coverage and zero teleports. The 12 selected fixed/rule baseline artifacts (six each) were rechecked for matching scenario/seed/controller, 12 TLS rows, and 100% completion.

##### Candidate compared with the previous T4.7 policy

| Measure | Previous candidate | Rejection-penalty candidate | Result |
|---|---:|---:|---|
| TLS with ≥2 distinct raw PPO actions | 8/12 (66.67%) | 12/12 (100%) | Pass threshold (≥80%) |
| Rejected PPO requests | 40,159/63,672 (63.07%) | 36,604/63,384 (57.75%) | Reduced by 5.32 percentage points |
| Aggregate rejection reasons: clearance / minimum green / other | 13,530 / 24,615 / 2,014 | 11,285 / 21,703 / 3,616 | New detailed per-TLS reasons available; old candidate stored only aggregate categories |
| Fallback-owned safety ticks | 63.08% | 57.74% | Reduced by 5.34 percentage points; PPO tick share 36.92% → 42.26% |
| Hold-lockout overrides | 4,346 | 1,677 | Reduced |
| Forced max-green switches / recorded switches | 0/56,042 | 0/17,323 | Both below 30% |
| Pooled censored network travel time | 270.132910 s | 270.136818 s | +0.00145% vs previous; 35.39% below fixed and 0.10% below rule |
| Worst per-TLS queue regression vs fixed | +8.85% | +15.48% | Below the +50% investigation trigger |
| Batched inference latency, median / maximum | 1.2693 / 2.9032 ms | 1.3799 / 19.4866 ms | Median below 100 ms |

The new rejection counts are grouped into clearance-phase (11,285), minimum-green (21,703), and other (3,616: 3,573 verified-green extension rejections and 43 maximum-duration rejections). Prior per-TLS reason counts were not saved, so only its documented aggregate split is comparable. Candidate safety rejections total 36,604/63,384 policy/fallback decisions; fallback-owned tick share is independently calculated from weighted `1 - ppo_tick_share`. A high fallback share remains a visible operational limitation, although every TLS also has a positive PPO-owned tick share and passes the documented coverage criterion.

##### Candidate per-junction diagnostics

Action counts below are raw policy outputs in order `keep/switch/hold_5s/hold_10s`; hold-lockout-applied outputs are stored separately. Reason counts use `clearance/minimum-green/other`. Queue delta is the mean of six episode-average queue values per TLS against the corresponding fixed-time cells.

| TLS | Raw policy actions K/S/H5/H10 | Distinct | Rejections / decisions | Rejection reasons C/M/O | Hold overrides | Fallback ticks | Forced / switches | Queue delta vs fixed | PPO phase-use counts | Mean green per phase (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `2387385680` | 3904/1068/0/310 | 3 | 1085/5282 (20.54%) | 0/0/1085 | 212 | 20.53% | 0/1038 | -68.28% | 0:1842, 2:2393 | 0:17.47, 2:22.79 |
| `GS_2407671508` | 203/4429/642/8 | 4 | 3193/5282 (60.45%) | 1076/1952/165 | 392 | 60.43% | 0/1237 | -20.65% | 0:2027, 2:2017 | 0:16.24, 2:16.28 |
| `GS_cluster_11178931802_11178931803_2414626606_6887565739` | 63/5038/180/1 | 4 | 3679/5282 (69.65%) | 1217/2386/76 | 161 | 69.65% | 0/1294 | +15.48% | 0:2001, 2:1988 | 0:15.34, 2:15.35 |
| `GS_cluster_12067305554_6017833806_6017833807_6131076159` | 3726/1491/65/0 | 3 | 1454/5282 (27.53%) | 0/411/1043 | 39 | 27.52% | 0/1043 | -38.01% | 0:2450, 2:1789 | 0:23.29, 2:17.13 |
| `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | 48/5234/0/0 | 2 | 3518/5282 (66.60%) | 1715/1762/41 | 0 | 66.59% | 0/1757 | -56.62% | 0:891, 2:880, 4:879, 6:876 | 0:10.99, 2:11.00, 4:10.99, 6:11.00 |
| `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | 1378/3826/78/0 | 3 | 3020/5282 (57.18%) | 53/2287/680 | 40 | 57.17% | 0/1460 | -44.05% | 0:1249, 3:1112, 5:1100, 8:1090 | 0:13.96, 3:15.12, 5:13.01, 8:15.01 |
| `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | 83/4991/208/0 | 3 | 3320/5282 (62.85%) | 1565/1595/160 | 150 | 62.84% | 0/1726 | -40.79% | 0:927, 2:911, 4:861, 6:858 | 0:11.60, 2:11.51, 4:10.98, 6:10.98 |
| `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | 128/5124/30/0 | 3 | 3372/5282 (63.84%) | 1/3370/1 | 22 | 63.82% | 0/1737 | -57.08% | 0:1798, 2:1747, 4:1735 | 0:12.38, 2:12.04, 4:12.00 |
| `cluster_2447849296_306618051` | 42/5164/74/2 | 4 | 3423/5282 (64.80%) | 1662/1683/78 | 78 | 64.79% | 0/1741 | -50.31% | 0:1754, 2:1788 | 0:10.99, 2:11.27 |
| `cluster_266273090_4377707444` | 8/5083/189/2 | 4 | 3729/5282 (70.60%) | 1216/2424/89 | 165 | 70.59% | 0/1306 | -19.78% | 0:1976, 2:2001 | 0:15.01, 2:15.33 |
| `cluster_306608060_6131903446` | 30/4972/272/8 | 4 | 3244/5282 (61.42%) | 1589/1549/106 | 210 | 61.42% | 0/1698 | -49.90% | 0:1149, 2:1312, 4:1126 | 0:11.05, 2:12.58, 4:10.98 |
| `cluster_6633301856_7432359269_7432359283_7432359284` | 104/4960/216/2 | 4 | 3567/5282 (67.53%) | 1191/2284/92 | 208 | 67.53% | 0/1286 | -4.36% | 0:2000, 2:1999 | 0:15.45, 2:15.56 |

##### T4.7 acceptance verdict

| Criterion | Status | Evidence |
|---|---|---|
| (a) All 12 frozen intended TLS receive PPO control | PASS | All six candidate runs report `ai_coverage=full`; all 72 junction rows are `controlled_by=rl`; each TLS has positive PPO tick share. |
| (b) At least 80% of TLS use ≥2 distinct policy actions | PASS | 12/12 (100%) have at least two nonzero raw PPO action counts across the six cells; counts are independent of fallback outputs and shown above. |
| (c) Forced max-green switches <30% of switches | PASS | 0/17,323; no forced max-green events in any candidate cell. |
| (d) Censored travel time ≤5% worse than fixed | PASS | Trip-weighted 270.136818 s vs fixed 418.114749 s (35.39% lower); all baseline cells validated. |
| (e) Worst-junction queue regression reported; >50% investigated | PASS | Maximum +15.48% at `GS_cluster_11178931802_11178931803_2414626606_6887565739`; none exceed +50%. |
| (f) Median batched-inference latency <100 ms | PASS | 1.37985 ms over 5,282 batches; maximum 19.48660 ms. |
| Required controller test | PASS | `Ai/.venv/Scripts/pytest.exe -q tests/test_rl_network_controller.py` → 5 passed (nonfatal pytest cache warning). |

The complete T4.7 gate passes; mark T4.7 Done. The rejection-aware iteration improves diversity from 8/12 to 12/12, reduces rejected requests from 63.07% to 57.75%, and keeps network censored travel essentially unchanged versus the previous candidate. The fallback-owned tick share remains high and is disclosed above. T4.10 is not triggered; T4.8 is the next roadmap task but was not started in this checkpoint.
