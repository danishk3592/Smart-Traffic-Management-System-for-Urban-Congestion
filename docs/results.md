# Evaluation results

## Part 1 — M1 single-junction milestone

**Pending T3.2 final-seed report.** The previously recorded M1 development result is not a final-seed result and does not complete T3.2. See `docs/PROGRESS.md` and the roadmap before presenting M1 as final.

## Part 2 — M2 network development evaluation (T4.8; not final)

**Scope and provenance.** The authorized dev command was `Ai/.venv/Scripts/python.exe -m Ai.evaluation.evaluate --family network --controllers fixed rule rl --seed-set dev`, job `20261101-130401_d0dddfe6`, return code 0. It completed 75/75 scenario × seed × controller cells for `net_balanced`, `net_low`, `net_medium`, `net_heavy`, `net_rush_hour`, seeds 5000–5004, fixed/rule/RL. Full artifact and lineage validation found 75 valid, 0 invalid, 0 incomplete cells. All 25 scenario/seed route groups use the same route SHA across the three controllers. RL used only `Ai/rl/models/ppo_net_v2_rejection_penalty_005/evaluations/best_model.zip`, SHA-256 `758711e7f28e29e69b59af6eade30ba679c3160daadf39e09ed89287f5037757`.

**Metric N.** Primary values are completed common trips, computed by averaging seeds within each scenario and equally averaging the four non-low scenarios for the headline. Travel time is seconds; improvement is `(fixed − RL) / fixed × 100`. The 95% interval shown is the paired-bootstrap interval for the improvement versus fixed, from `comparison.csv`.

| Scenario / aggregation | Fixed (s) | Rule (s) | RL (s) | RL reduction vs fixed (95% CI) | Common trips | Completion, fixed/rule/RL |
|---|---:|---:|---:|---:|---:|---:|
| `net_balanced` | 374.202 | 327.962 | 319.242 | 14.61% (12.94–16.55%) | 1,750 | 100% / 100% / 100% |
| `net_medium` | 327.050 | 277.796 | 265.704 | 18.54% (15.79–22.57%) | 3,250 | 100% / 100% / 100% |
| `net_heavy` | 461.409 | 341.395 | 275.193 | 39.50% (32.98–44.85%) | 4,000 | 100% / 100% / 100% |
| `net_rush_hour` | 293.367 | 260.663 | 255.443 | 12.84% (10.68–14.91%) | 2,500 | 100% / 100% / 100% |
| **Headline** (unweighted mean of the four rows above) | **364.007** | **301.954** | **278.895** | **23.35% (22.08–24.69%)** | **11,500** | **100% / 100% / 100%** |
| `net_low` (separate; excluded from headline) | 323.936 | 294.583 | 287.662 | 11.11% (9.15–12.96%) | 1,250 | 100% / 100% / 100% |

The configured 10% target is **MET on this development headline** (`target_met=true`). The pooled-trip sensitivity, including `net_low`, is 25.04% lower travel time versus fixed (12,750 trips). Since all runs completed every scheduled trip, the completed-common and all-scheduled censored travel-time means coincide; completion is 100%, and there is no completion-gap survivorship difference in these results. The headline RL reduction versus rule is 7.48%.

**Coverage, fallback, and safety.** Each RL cell loaded and used the pinned model, but under the frozen `eval.ai_coverage_min_share=0.95` definition all 25 RL cells report `ai_coverage=none` (`n_tls_ai=0/12`). Across the 60 RL per-scenario/per-junction rows, PPO owned 26.67–79.94% of ticks (mean 41.39%); fallback owned 20.06–73.33% (mean 58.61%). No junction reached 95% PPO tick ownership. The 25 RL cells recorded 147,123 safety rejections and zero forced max-green switches. Mean per-run median batch inference latency was 2.386 ms; the maximum recorded batch latency was 1,095.353 ms and should be reviewed as a latency outlier before drawing operational conclusions. These measurements do not establish complete AI ownership across the network.

**Censored/safety/junction outputs.** `results/summary/network_runs.csv` contains one row per run with coverage, common-trip count, completion, censored and common travel time, fallback share, safety counts, inference latency, route hash, and model identity. `results/summary/network_junctions.csv` contains 180 scenario/controller/TLS rows with queue, wait, congestion, controller ownership/tick shares, fallback and safety diagnostics. `results/figures/network_junction_congestion.png` is a simulated per-junction congestion figure. `results/summary/comparison.csv` contains 1,457 M2 rows and the preserved 1,782 M1 rows.

**Reproducibility and checks.** Rebuilding aggregation twice produced byte-identical `comparison.csv`, SHA-256 `047cf3e163156d9f6db82b36de80ddc43cadd612ea9898d8389bc70ba17cef45`. The 1,782 M1 rows retain canonical SHA-256 `341f3ab8dd8bc9d288845d30635751cdcf0bd6e0361bdbefcac565e751fb02fb`. `pytest -q tests/test_evaluation_network.py tests/test_evaluation.py tests/test_metrics_network.py tests/test_run_episode.py tests/test_scenarios.py`: **25 passed**. Changed-file Ruff: **All checks passed**. Evaluation wall time was 2 h 22 min 53 s; the serial estimate was approximately 6.2 h before launch. A nonfatal Matplotlib tight-layout warning occurred while creating the congestion figure.

**Status and limitations.** T4.8's development harness gate passes. These are synthetic-demand SUMO development seeds, not final-seed results or real-world validation. The 10% development result does not satisfy T4.9 final acceptance. `ai_coverage=none` under the 0.95 ownership rule is an explicit reliability/coverage limitation. The final-seed gate and conditional T4.10 path are recorded below.

## T4.9 final-seed PPO-only audit (pre-T4.10; preserved historical result)

Job `20261101-160643_0cb80208` ran the exact final command `Ai/.venv/Scripts/python.exe -m Ai.evaluation.evaluate --family network --controllers fixed rule rl --seed-set final`, finished with return code 0, and validated 75/75 cells (0 invalid/incomplete) across the five frozen scenarios and seeds 6000–6004. All 25 scenario/seed triplets have one matching route SHA across fixed/rule/RL. RL loaded the frozen T4.7 candidate SHA-256 `758711e7f28e29e69b59af6eade30ba679c3160daadf39e09ed89287f5037757`; no training or final-seed tuning occurred. Actual wall time was 2 h 21 min 30 s. The final grid, original route artifacts and aggregates are retained; the final PPO-only aggregates are snapshotted as `results/summary/*_t49_rl_final_snapshot.csv`.

At the DEC-12 completed-common-trip basis, Metric N headline (unweighted mean across `net_balanced`, `net_medium`, `net_heavy`, `net_rush_hour`) was 277.936 s RL, 375.478 s fixed and 298.471 s rule: **25.74% lower than fixed** (paired-bootstrap 95% CI 22.21–29.28%, `target_met=true`). Completion was 100% (11,500/11,500 common trips); censored travel time was identical to common-trip travel time. Including `net_low`, pooled sensitivity was 26.95% lower than fixed across 12,750 trips. Scenario common-trip results:

| Scenario | Fixed (s) | Rule (s) | PPO (s) | Reduction vs fixed (95% CI) | Common trips | Completion fixed/rule/PPO |
|---|---:|---:|---:|---:|---:|---:|
| `net_balanced` | 406.456 | 333.340 | 321.540 | 19.63% (13.58–28.74%) | 1,750 | 100% / 100% / 100% |
| `net_medium` | 322.390 | 275.869 | 268.933 | 16.56% (15.20–17.81%) | 3,250 | 100% / 100% / 100% |
| `net_heavy` | 470.900 | 315.090 | 264.743 | 42.86% (37.27–48.85%) | 4,000 | 100% / 100% / 100% |
| `net_rush_hour` | 302.165 | 269.584 | 256.527 | 14.71% (11.93–19.90%) | 2,500 | 100% / 100% / 100% |
| `net_low` (separate) | 314.690 | 290.279 | 281.074 | 10.67% (9.54–12.29%) | 1,250 | 100% / 100% / 100% |

**Historical PPO-only coverage:** the final audit found all 25 PPO runs below the configured per-TLS PPO ownership threshold of 0.95, so coverage was `none` at 0/12; weighted fallback ownership averaged 58.64%. Across the 25 PPO cells all 12 TLS had a nonzero but sub-threshold PPO share. Per-TLS PPO share across five scenarios was: `2387385680` 79.18%, `GS_2407671508` 36.21%, `GS_cluster_11178931802_11178931803_2414626606_6887565739` 29.19%, `GS_cluster_12067305554_6017833806_6017833807_6131076159` 72.13%, `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` 33.36%, `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` 42.90%, `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` 36.78%, `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` 35.27%, `cluster_2447849296_306618051` 34.83%, `cluster_266273090_4377707444` 28.20%, `cluster_306608060_6131903446` 37.26%, `cluster_6633301856_7432359269_7432359283_7432359284` 30.96%. There were 147,583 safety rejections, zero forced max-green switches, 0 teleports, average per-cell median batch latency 2.380 ms, and maximum batch latency 1,359.127 ms (latency outlier disclosed).

AI coverage: 0/12 (none)

The 10% network-wide travel-time target is **MET**, but the frozen DEC-14 definition does not support a full-AI coverage claim. Stage 3 and the T4.7 rejection-penalty iteration are complete, so this coverage shortfall triggers conditional T4.10. The PPO-only run is retained as the T4.9 pre-hybrid audit; the final deliverable will be reported from the unchanged-metric hybrid dev/final rerun. Synthetic SUMO demand remains provisional until P1; it is not real-world validation.

### T4.10 hybrid development evaluation (not final)

The 75-cell hybrid development rerun `20261101-184256_d7a67629` exited 0; all 25 scenario/seed pairs use matching routes for fixed/rule/hybrid. Fifty valid fixed/rule dev cells were reused. The frozen PPO model and 11-PPO/1-rule validation gate were used unchanged. All 12,750 trips completed.

| Scenario | Fixed common-trip (s) | Hybrid common-trip (s) | Improvement vs fixed (95% CI) | Common trips |
|---|---:|---:|---:|---:|
| `net_balanced` | 374.202 | 317.977 | 14.94% (13.00–17.10%) | 1,750 |
| `net_medium` | 327.050 | 264.709 | 18.85% (16.08–22.88%) | 3,250 |
| `net_heavy` | 461.409 | 271.905 | 40.20% (33.80–45.60%) | 4,000 |
| `net_rush_hour` | 293.367 | 254.415 | 13.18% (10.87–15.38%) | 2,500 |
| **Headline** (unweighted four non-low scenarios) | **364.007** | **277.252** | **23.79% (22.52–25.23%)** | **11,500** |
| `net_low` (separate) | 323.936 | 286.367 | 11.52% (9.82–13.22%) | 1,250 |

The 10% development target is **MET**. Censored and common-trip travel time coincide because completion is 100%. Pooled 12,750-trip sensitivity is recorded in `results/summary/comparison_t410_hybrid_dev_snapshot.csv`. Development `ai_coverage` remains **none (0/12)** at the 0.95 actual PPO-owned tick threshold: the gate admits 11 TLS to PPO, but runtime safety fallback keeps every TLS below the ownership threshold. Average fallback ownership across those PPO-eligible TLS is 57.51%. This stage demonstrates that the hybrid improves network travel time on dev seeds; it does not establish final performance or full AI coverage. The dev comparison, run, junction and coverage outputs are snapshotted in `results/summary/*t410_hybrid_dev_snapshot.csv`; reaggregation left `comparison.csv` byte-identical at SHA-256 `277be427af4e9c82765547387ec70146306e2be30f08616f12c8ddb04888226f`.

## Part 3 — M2 final-seed result (T4.9/T4.10; Stage 4 hybrid)

**Run and evidence.** The final network grid used the frozen T4.7 PPO model with the validation-derived T4.10 gate, controllers `fixed`, `rule`, and `hybrid`, five frozen network scenarios, and final seeds 6000–6004. Job `20261101-194723_3fa4c619` ran `Ai/.venv/Scripts/python.exe -m Ai.evaluation.evaluate --family network --controllers fixed rule hybrid --seed-set final`, finished with return code 0 at 2026-11-01T20:43:54Z after 56 min 31 s. The evaluator's full artifact/lineage audit reports **75 valid, 0 invalid, 0 incomplete** cells; 50 valid fixed/rule baseline cells were reused and 25 hybrid cells evaluated. The 25 scenario/seed groups have matching route identities across controllers. The frozen T4.1 intended set has 12 TLS (list SHA-256 `4fc1323e1885d0763d8ac0598a1ec5e7446c6a835a63b62136f657c735979bcd`, frozen `2026-10-31T07:20:08Z`); `cluster_263386438_7432382412` is excluded for 16 crossings/1800 s, below the 20-crossing threshold. The full intended set and exclusions are in `docs/network_tls.md` and the final per-junction table below. Hybrid used checkpoint `Ai/rl/models/ppo_net_v2_rejection_penalty_005/evaluations/best_model.zip`, SHA-256 `758711e7f28e29e69b59af6eade30ba679c3160daadf39e09ed89287f5037757`; frozen gate `results/summary/t410_hybrid_gate.json` is unchanged (SHA-256 `655e36c69382dbbbb39d3ef3144691fd0e635598a519bd63de8499672390ff55`). No training or final-seed tuning was done.

**Headline Metric N.** Primary basis is completed common trips; seeds are averaged within each scenario and the four non-low scenarios are equally weighted. All controllers completed all scheduled trips, so censored and common-trip values coincide (100% completion). Improvement intervals below are the paired-bootstrap 95% CIs from `comparison.csv`.

| Scenario / aggregation | Fixed (s) | Rule (s) | Hybrid (s) | Hybrid reduction vs fixed (95% CI) | Common trips | Completion fixed/rule/hybrid |
|---|---:|---:|---:|---:|---:|---:|
| `net_balanced` | 406.456 | 333.340 | 320.975 | 19.77% (13.63–28.86%) | 1,750 | 100% / 100% / 100% |
| `net_medium` | 322.390 | 275.869 | 267.448 | 17.01% (15.66–18.40%) | 3,250 | 100% / 100% / 100% |
| `net_heavy` | 470.900 | 315.090 | 265.796 | 42.64% (37.03–48.37%) | 4,000 | 100% / 100% / 100% |
| `net_rush_hour` | 302.165 | 269.584 | 255.908 | 14.89% (11.73–20.42%) | 2,500 | 100% / 100% / 100% |
| **Headline** (unweighted four non-low scenarios) | **375.478** | **298.471** | **277.532** | **25.84% (22.20–29.49%)** | **11,500** | **100% / 100% / 100%** |
| `net_low` (separate; excluded from headline) | 314.690 | 290.279 | 283.655 | 9.86% (9.54–10.16%) | 1,250 | 100% / 100% / 100% |

The configured 10% final network target is **MET** (`target_met=true`) against fixed-time. Hybrid is 6.97% lower than rule-based on the headline common-trip basis. Pooled sensitivity including `net_low` is 26.94% lower travel time than fixed across 12,750 completed trips. Synthetic SUMO traffic is not real-world validation.

**Coverage and safety.** The final `summary.csv` reports:

AI coverage: 0/12 (none)

This is the DEC-14 **Stage 4 hybrid** level, not complete PPO coverage: the frozen validation gate admits PPO at 11 TLS and rule control at `GS_cluster_11178931802_11178931803_2414626606_6887565739`; nevertheless none meets the 0.95 per-TLS PPO-owned tick threshold in all final runs. Mean per-run fallback share on PPO-eligible TLS is 57.52%. The 25 hybrid runs record 133,335 rejected actions, zero forced max-green switches, and four teleports (all at `net_low`, seed 6002); all 12,750 scheduled trips ultimately completed. Fixed and rule runs record 111 and 30 teleports respectively, also with 100% final completion. Mean per-run median batch inference latency is 2.473 ms; largest per-run median is 2.908 ms, while maximum individual batch latency is 506.507 ms. These results meet the travel-time target but do not demonstrate complete intended-TLS AI ownership.

**Why coverage is 0/12 and what the travel-time comparison establishes.** This is not a reporting mismatch: `ai_coverage` follows the frozen definition and counts a TLS only when PPO owns at least 95% of its ticks in every final hybrid cell. The hybrid configuration admits PPO at 11 TLS and uses rule at the one failed validation-gate TLS. During evaluation, `ppo_tick_share` increments only when that TLS's `FallbackController` is not active; a safety rejection routes that TLS to fixed-time fallback. Across the 11 PPO-eligible TLS, mean PPO tick ownership was 42.48% (fallback 57.52%), and no eligible TLS reached 95% in any final cell. Thus the model produced actions, but the acceptance definition correctly reports zero qualifying TLS. On identical routes and 11,500 common trips, hybrid is 25.84% below fixed and 6.97% below rule; rule alone is 20.26% below fixed. These comparisons establish a measured hybrid-stack improvement, not an isolated causal PPO effect: the hybrid includes PPO, safety-triggered fixed-time fallback, and one rule-controlled TLS, and no PPO-disabled ablation was run. Do not label the full 25.84% as PPO-only improvement.

**Per-junction congestion summary.** Values are means across the five final scenarios' saved junction aggregates. PPO share is the mean `ppo_tick_share`; `rl_fallback` denotes a TLS admitted by the frozen PPO gate whose actual ownership includes safety fallback.

| Intended TLS | Frozen route | Fixed mean queue | Hybrid mean queue | Hybrid queue change | PPO tick share |
|---|---|---:|---:|---:|---:|
| `2387385680` | PPO | 0.024 | 0.007 | −69.3% | 79.3% |
| `GS_2407671508` | PPO | 0.296 | 0.229 | −22.5% | 36.1% |
| `GS_cluster_11178931802_11178931803_2414626606_6887565739` | Rule | 0.270 | 0.188 | −30.4% | 0.0% |
| `GS_cluster_12067305554_6017833806_6017833807_6131076159` | PPO | 0.093 | 0.070 | −25.2% | 72.1% |
| `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` | PPO | 2.756 | 1.178 | −57.3% | 33.4% |
| `cluster11260122965_12067305543_12067305544_cluster_11260122968_1608973468_2110371293` | PPO | 0.913 | 0.464 | −49.2% | 42.9% |
| `cluster11374930007_11374930012_cluster_11374930008_11374930009_11374930010_11374930011` | PPO | 0.564 | 0.288 | −49.0% | 36.7% |
| `cluster618250255_7478115627_cluster_11927462278_11927462280_7478115626_7479633881` | PPO | 0.401 | 0.170 | −57.6% | 35.4% |
| `cluster_2447849296_306618051` | PPO | 0.407 | 0.198 | −51.4% | 34.8% |
| `cluster_266273090_4377707444` | PPO | 0.204 | 0.150 | −26.6% | 28.4% |
| `cluster_306608060_6131903446` | PPO | 0.702 | 0.337 | −52.0% | 37.2% |
| `cluster_6633301856_7432359269_7432359283_7432359284` | PPO | 0.422 | 0.391 | −7.5% | 31.1% |

**Reproducibility and status.** Aggregation was run twice; `results/summary/comparison.csv` was byte-identical both times (SHA-256 `8aefa3c0a2ae2ac13e9528de5da410670a1a74cc95f47adf0d706468f712dcd4`). Final snapshots are `comparison_t410_hybrid_final_snapshot.csv`, `network_runs_t410_hybrid_final_snapshot.csv`, `network_junctions_t410_hybrid_final_snapshot.csv`, and `coverage_t410_hybrid_final_snapshot.csv`; full raw cell artifacts remain under `results/raw/`. T4.9's final-seed reporting gate and conditional T4.10 task are complete; Stage 4 is the documented fallback outcome. The whole-repository Ruff gate passes with a documented exact-path exclusion for the pre-existing untracked PDF helper; no project-source lint rules are disabled. Results are simulated, synthetic-demand, cars-only and provisional until P1; they are not real-world validation.
