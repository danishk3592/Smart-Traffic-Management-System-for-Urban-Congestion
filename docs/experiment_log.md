

## 2026-10-20 ? T0.3 SUMO client and TLS inspection

- Seed 1000, initial client smoke: exited at simulation time 0 because the inspection script referenced a not-yet-exposed validated-network property. No traffic was simulated; added the public property.
- Seed 1000, client smoke: stopped at time 70 s because TraCI had already removed an arrived vehicle subscription. Removed the redundant unsubscribe request; client lifecycle tests then passed.
- Seed 1000, 1800 s native-program run: 298 unique crossing vehicles at the configured TLS; rank 6/13, median 243. Initial foe check reported 21 overlaps. Inspection of SUMO request response bits showed 0 protected G/G conflicts and all 21 overlaps have a yielding response from the native program. Kept the existing static program.
- Seed 1000, 1800 s inspection: simulation completed but report generation failed when the warning-time parser included a trailing period. Tightened the time parser and reran.
- Seed 1000, final 1800 s run: rank 6/13, 298 unique crossings; 4 approaches; 3 green phases; 0 protected G/G foe conflicts; 21 permissive overlaps with network yield responses; 1 unique teleport ID in the first 600 s and 38 through 1800 s; 2 warning lines through 600 s and 71 through 1800 s.
- All run outputs and edgeData were directed to temporary storage; no protected source map path was modified.
- Acceptance: inspect_tls.py exited 0; Ruff passed; default pytest 6 passed/3 deselected; SUMO client tests 3 passed; junction tests 4 passed; zombie check found no SUMO processes.

## 2026-10-24 � T0.4 scenario generation and native measurements

- Initial environment invocation used `Ai\.venv\Scripts\python.exe` as a PowerShell command and failed before Python started (`The module 'Ai' could not be loaded`). Verified the actual project interpreter at `C:\Users\empow\Documents\Major Project\Ai\.venv\Scripts\python.exe` (Python 3.14.2; sumolib 1.27.1) and reran.
- Seed 1000 low-scenario force regeneration completed; route cache matched. Ruff passed and `pytest -q tests/test_scenarios.py` reported 5 passed in 3.90s.
- Early exploratory low run before the arrival-ID counter fix reported 0 arrivals; invalid completion metric. Corrected measurement to accumulate per-step arrived/departed IDs. That early run reported 29 unique teleports / 700 (4.14%); it is superseded by the accepted run below.
- `python scripts/make_scenarios.py --seed 1000 --all` generated routes and completed all seven native runs, but exited 1 at the Section 0 teleport gate. Measured (trips; planned junction share; arrived; unique teleports/share): balanced 1800; .401; 1176; 428/.238. directional_ns 1800; .400; 1203; 405/.225. directional_ew 1800; .403; 1197; 400/.222. low 700; .301; 697; 29/.041. medium 2600; .400; 1492; 846/.325. heavy 3600; .400; 2037; 1269/.352. rush_hour 3200; .402; 1834; 1129/.353. Thus six scenarios exceed 5%; medium/heavy/rush_hour also exceed the <1% design target. Recorded measurements are in docs/scenarios.md.
- Decision: stopped at the roadmap human-review gate. No demand tuning, train-pool generation, commit, or T0.5 work was done. The measurement report date and generator date formatting were corrected to the actual run date.

## 2026-10-24 � T0.4 resume gate and bottleneck TLS verification

- Read roadmap T0.4 through T2.3 dependency/gate blocks and Section 0.6. T1.1 requires accepted T0.4; T2.1 requires T1.4; real PPO training in T2.3 requires T2.1 and T2.2. The measured >5% teleport condition requires stopping for human review, so no PPO work is authorized by the dependency order yet.
- Read the configured net path from SUMO/No_Polygon_Map/osm.sumocfg and queried its 13 TLS IDs with the project Python 3.14.2 and sumolib 1.27.1. Requested ID `cluster11259448953_11259448962_11259448969_cluster_11259448960_7479633881` has no exact match. Closest actual ID: `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963`; docs/tls_inspection.md lists it as rank 3 with 349 crossings in the earlier 1800 s T0.3 ranking. No map or config was changed. Decision: report both blockers and wait for human resolution; do not repeat scenario measurements.

## 2026-10-24 - Confirmed bottleneck TLS and T0.4 rerun

- User confirmed the intended junction and TLS. Queried `SUMO/No_Polygon_Map/osm.net.xml` with the project interpreter (Python 3.14.2, sumolib 1.27.1): exact TLS match true and exact junction-node match true.
- Preserved prior `config/stms.yaml`, `docs/tls_inspection.md`, and `docs/scenarios.md` outside the repository at `C:\Users\empow\AppData\Local\Temp\STMS_confirmed_TLS_preserve_20261024-162745` before changing target-related files.
- Updated `sumo.tls_id` to the confirmed ID and reran T0.3. Seed 1000, 1800 s: rank 3/13, 349 crossings, 5 approaches, 4 green phases, no protected foe conflicts, 8 permissive yielding overlaps, 38 teleports. Acceptance: `inspect_tls.py` exited 0; SUMO client tests 3 passed; junction tests 4 passed; zombie check clean; Ruff passed after fixing import ordering.
- Rebuilt seed-1000 routes for the confirmed TLS using unchanged configured scenario trip counts and insertion profiles. T0.4 run completed all seven scenarios but exited 1 under roadmap Section 0.6 because every scenario exceeded 5% teleports. Shares and counts are in `docs/scenarios.md`; medium/heavy/rush_hour also exceed the <1% design target. Junction shares were all above 30%.
- T0.4 unit tests: 5 passed in 3.60s; Ruff passed. `--all --force` and `--train-pool` were not run because the measured stop gate requires human review. No demand reduction, PPO implementation, training, or protected-map writes occurred. Decision: stop and ask the human how to proceed with the gate while retaining unchanged demand.

## 2026-10-24 - Human approval scope after the T0.4 stop gate

- Human explicitly approved proceeding with unchanged-demand experiments, recording excessive teleports/gridlock as unresolved, and prohibited reducing demand or weakening acceptance criteria.
- Approval applies to the remaining experiments within T0.4, including force-reproducibility and cached training-pool generation. It does not mark T0.4 accepted or waive its acceptance criteria.
- Roadmap Section 0.1 requires strict task/dependency order. T1.1 depends on T0.4; T2.1 depends on T1.4; real PPO training in T2.3 requires T2.1 and T2.2. Therefore single-junction PPO implementation/training is not permitted while T0.4 remains blocked/not accepted. Do not start RL tasks under this approval.

## 2026-10-24 - Approved T0.4 experiments, route force check, and training pool

- Approval scope honored: unchanged demand only; excessive teleports/gridlock remain reported, criteria are not weakened. Compared config with the preserved pre-change config: `demand_unchanged=True`.
- After confirming the target TLS and preserving the completed native measurements, ran `python scripts/make_scenarios.py --seed 1000 --all --force`; all seven primary route hashes matched byte-for-byte, 71.1 s.
- First detached `--train-pool` attempt (PID 18116) reached 30/140 progress, then `duarouter` timed out after 600 s at directional_ns/seed_1010. Stderr and stdout are preserved under `results/raw/t04_train_pool_20261024-164322/`. No protected map files were written.
- SUMO duarouter also emitted route alternatives. For subsequent runs, capped alternatives at 1 and sent that auxiliary file to a unique temporary path. Force-regenerating directional_ns/seed_1009 produced an identical primary route; scenario tests passed 5/5 and Ruff passed.
- Resumed detached pool generation (PID 27412) from existing valid caches. CLI output ended with `Pre-generated 140 cached training route files.` after 773 s; stderr was empty. Independently checked all 140 expected scenario/seed manifests: route files present, config hashes current, route hashes match, vehicle counts match; issues=0. Logs are preserved under `results/raw/t04_train_pool_retry_20261024-170158/`.
- Re-ran `scripts/check_zombies.py`: no running SUMO or sumo-gui processes. T0.4 native measurements remain above the Section 0.6 >5% teleport stop threshold; T0.4 stays blocked/not accepted and its criteria were not weakened.
- Roadmap decision: `--train-pool` was permitted as an approved experiment within T0.4. Single-junction PPO implementation and training are not permitted as experimental work while dependency tasks are incomplete: T1.1 depends on accepted T0.4, T2.1 on T1.4, and T2.3 real training on T2.1/T2.2. No PPO/baseline comparison was run.

## 2026-10-24 - Human-approved native-baseline teleport criterion deferral

- Human authorized the minimum roadmap amendment: retain the confirmed-TLS unchanged-demand native measurements and their >5% teleport failures as failed baseline results; defer performance evaluation until PPO is trained and connected to SUMO.
- Updated Section 0.6, T1.4, T2.5 and the T0.4 tracker row. The amendment does not reduce demand, change the recorded measurements, mark the baseline as passed, or waive safety/correctness/dependency gates.
- Updated the T0.4 generator to report native baseline teleports above 5% without aborting, in accordance with the approved amendment. No baseline simulation or route generation was repeated.
- T0.4 acceptance evidence retained: prior `--all` run produced all seven measured results but exited 1 solely at the superseded >5% stop rule; `--all --force` verified byte-identical routes; 140/140 training route/manifest pairs passed verification; `pytest -q tests/test_scenarios.py` passed 5 tests; Ruff passed.
- T0.4 is recorded Done with an explicit deviation; baseline remains failed. The next task is T1.1 after the mandatory Phase 0 merge and human reply under Section 0.5.

## 2026-10-24 - Phase 0 merge, preservation reconciliation, and T1.1

- With the user's approval, quarantined the colliding untracked `Ai/rl/`, `Documents/STMS_Agent_Roadmap_FINAL.md`, and `docs/` paths into `C:\Users\empow\AppData\Local\Temp\STMS_premerge_preserve_20261024-173055`, retaining pre-move copies under `verified_snapshot/`. File counts and SHA256 hashes matched after quarantine. The modified `edgeData.xml` and `✅ HSR Layout.txt` were left in place.
- Verified Phase 0 commits `e2b189d`, `478daff`, and `39b613a`; the branch descended from the current `main`, and its diff contained no `SUMO/No_Polygon_Map/` paths. Merged with `git merge --no-ff --no-edit agent/phase-0-foundation`; merge commit `ee77f85`.
- Compared quarantined RL source against merged Phase 0 source. The old `traffic_env.py` differed in imports/type annotations and less robust close handling; old train/evaluate/test files differed only in formatting. Kept the Phase 0 versions active. Restored the unique `models/ppo_traffic.zip` (191,102 bytes; SHA256 `FC0F74CEB435C5B098B7BC8A99FBF0589B2D6386DD5D704861DBCAD38C079E83`) and `ppo_evaluation.csv` (9,168 bytes; SHA256 `FC023ABAB9C5D1B37EC2967A459CAE537517184E99CCB6F66A9AFD9FAEBF0932`) without overwriting; older source versions and bytecode remain in the backup. Roadmap comparison found only the approved teleport amendment and phase/task status changes; synchronized the duplicate roadmap. Preserved the initial T0.1 package observations as history in `docs/PROJECT_FACTS.md` and retained the verified T0.2 environment as current.
- Verified all 23 protected map files against the pre-merge SHA256 manifest after merge and after SUMO tests: 23/23 unchanged. The pre-existing `edgeData.xml` modification remains uncommitted and untouched.
- Implemented T1.1 on `agent/phase-1-core`: approach/intersection dataclasses, config-derived normalization, `SumoSensorReader`, congestion classification, JSON conversion, and fixed-size observation vector. Full checks: `python -m pytest -q -p no:cacheprovider` → 16 passed, 4 deselected; `python -m ruff check .` → all checks passed; `python -m pytest -q -p no:cacheprovider -m sumo` → 4 passed, 16 deselected; `python scripts/check_zombies.py` → no SUMO processes.
- Full-suite verification also exposed a stale expected TLS ID and a SUMO config parser splitting Windows paths at spaces. Updated the expectation to the user-confirmed TLS and changed file-list parsing to comma/semicolon separators; the complete suites then passed.
- T1.1 commit: `133b0c0`. Next task is T1.2 Signal safety layer.

## 2026-10-24 - T1.3 checkpoint and Antigravity handoff

- The user interrupted the tuning batch after six complete cells. q10/w60 seed 3000 was stopped at approximately sim time 5,692/7,200. Preserved folder `results/raw/20261024-224337_rule_medium_s3000/` contains only `steps.csv` (1,246,372 bytes), flushed through sim time 5,450; it has no `trips.csv`, `run.json`, or `summary.csv` and is not a completed trial. Zombie check: no running SUMO processes.
- q10/w60 seeds 3001 and 3002 were not started. To resume after the user directs it, run `Ai/.venv/Scripts/python.exe -m scripts.tune_rule_controller`; it resumes from the six records in `results/raw/t13_rule_tuning_progress.json` and will rerun the incomplete q10/w60 seed 3000 in a new unique output directory before starting the last two cells.
- Preserved the checkpoint and resume instructions in `docs/PROGRESS.md` and `docs/rule_tuning.md`. T1.4's fixed-run diagnostic remains complete and all 210 mismatches are explained by teleport IDs. Phase 1 is not complete.

## 2026-10-24 - T1.4 fixed-run crossing diagnostic

- Ran the authorized current-run fixed controller on unchanged medium demand, seed 3000, using the existing cached route file. Artifact: `results/raw/20261024-210315_fixed_medium_s3000`; wall time 917.1259 s; 2,600 scheduled trips, 1,534 completed, 1,082 teleports.
- The run reproduced the old fixed artifact's 396 completed route-through trips and exact same 210 crossing-mismatch vehicle IDs. All 210 appear in the new per-vehicle teleport IDs; zero crossing-mismatch IDs lack a recorded teleport. The old discrepancies are explained by SUMO teleport events bypassing an observed TLS crossing. No mismatches remain unexplained.
- The 33-field summary matches `SUMMARY_FIELDS`, has no NaN, and is blank only for the documented network-only queue fields. The legacy-metric explanation remains in `docs/metrics.md`. T1.4 current-run evidence is collected; acceptance is pending required test rerun and T1.3 dependency completion. No demand, config, or map changes were made.

## 2026-10-24 - T1.3/T1.4 implementation with acceptance pending

- Implemented controller protocol/actions, fixed-time controller (30-second green requests through the safety layer), observation-only queue/wait rule policy, controller registry, timeout/invalid-action fallback, closed-loop episode runner, rule-tuning script, Section 11 metrics, and metric definitions/tests. No road-specific phase timing boosts or demand changes were introduced.
- Existing unchanged-demand fixed episode, seed 3000: 2,600 trips, 1,534 completed, 1,082 teleports, wall time 862.5367 s. Its `steps.csv` shows fixed greens at 30 seconds (5-second sampling). Existing rule episode, seed 3000: 1,560/2,600 completed and 1,088 teleports; it emitted repeated safety fallback warnings near maximum green and is retained as exploratory, not accepted tuning evidence.
- Completed rule-tuning trial: q6/w30 on seed 3000, 1,544/2,600 completed, 1,145 teleports, mean approach-sample queue 12.2208, mean approach wait 197.6908 s, zero fallback activations, wall time 1,459.7276 s. This is 1/9 required settings/seeds; no threshold is selected.
- On user instruction the tuning process was stopped. The partial q6/w30/3001 output remains in `results/raw/20261024-204907_rule_medium_s3001/` through sim time 1,655 s; the interrupted folder has no trip log or run summary. The initial attempt at `results/raw/20261024-204834_rule_medium_s3001/` retains its zero-byte step file. The completed result and tuning progress JSON remain under `results/raw/`. No further simulation was started; zombie check confirmed no SUMO processes.
- Short checks: controller+metric tests 9 passed; full unit suite 30 passed/5 deselected; SUMO-marked suite 5 passed/30 deselected; Ruff passed. An initial timeout-test assertion failed because the fixed controller correctly returned hold after arming; the assertion was corrected and all listed tests pass.
- Reprocessed copies of the previous fixed episode under `results/raw/20261024-205400_fixed_existing_metrics_recheck/` to verify the Section 11 summary header and no-NaN output without overwriting original artifacts. Because the old run predates unfinished-tripinfo and crossing-ID diagnostics, it does not fulfill T1.4's fixed-run acceptance. Its 396 completed route-through trips include 210 without a recorded crossing; the old artifact has no per-vehicle teleport IDs, so the mismatch remains unexplained.
- T1.3 tuning acceptance and T1.4 current-run/crossing acceptance remain pending. Phase 1 is not complete. The eight remaining full tuning runs and a current-run fixed diagnostic require explicit user approval before launch.

## 2026-10-24 - T1.2 Signal Safety Layer

- Implemented and unit-tested `SignalSafetyLayer` for the confirmed pilot TLS. It checks the active SUMO program against configured green/yellow/all-red indices, verifies sequential clearance transitions, rejects invalid/early requests with reasons, enforces minimum green at phase entry, forces clearance at maximum green, and caps extension requests. Approach phase mapping derives from configured incoming lanes/edges and the network TLS link map; no approach receives a timing boost.
- The inspected native program has a 6-second green (phase 2) below the configured 10-second minimum. The layer extends this phase on entry from the configured bound; other green timing remains governed by the program or accepted requests.
- SUMO fuzzer: explicit seed 731, 1200 simulation seconds, random switch/extension/approach requests; verified clearance before changing green, minimum/maximum duration, and allowed phase indices. Passed. No route or demand was changed.
- Commands: `python -m pytest -q -p no:cacheprovider tests/test_safety_unit.py` -> 5 passed; `python -m pytest -q -p no:cacheprovider -m sumo tests/test_safety.py` -> 1 passed; full unit suite -> 21 passed, 5 deselected; full SUMO suite -> 5 passed, 21 deselected; `python -m ruff check .` -> all checks passed; `python scripts/check_zombies.py` -> no SUMO processes.
- No experiments failed after the initial fake-clock fixture correction. The pre-existing modified `edgeData.xml` and untracked RL artifacts were not staged or modified; protected original map files were not written.
- Decision: T1.2 implementation and safety acceptance checks pass (`eacb7e0`). Next task: T1.3 Controllers + runner.

## 2026-10-24 - Phase 0 merge, preservation reconciliation, and T1.1

- With the user's approval, quarantined the colliding untracked `Ai/rl/`, `Documents/STMS_Agent_Roadmap_FINAL.md`, and `docs/` paths into `C:\Users\empow\AppData\Local\Temp\STMS_premerge_preserve_20261024-173055`, retaining the earlier verified copies under `verified_snapshot/`. File counts and SHA256 hashes matched after quarantine. The modified `edgeData.xml` and `✅ HSR Layout.txt` were left in place.
- Verified Phase 0 commits `e2b189d`, `478daff`, and `39b613a`; the branch descended from the current `main`, and its diff contained no `SUMO/No_Polygon_Map/` paths. Merged with `git merge --no-ff --no-edit agent/phase-0-foundation`; merge commit `ee77f85`.
- Compared quarantined RL source against merged Phase 0 source. The old `traffic_env.py` differed in imports/type annotations and less robust close handling; old train/evaluate/test files differed only in formatting. Kept the Phase 0 versions active. Restored the unique `models/ppo_traffic.zip` (191,102 bytes; SHA256 `FC0F74CEB435C5B098B7BC8A99FBF0589B2D6386DD5D704861DBCAD38C079E83`) and `ppo_evaluation.csv` (9,168 bytes; SHA256 `FC023ABAB9C5D1B37EC2967A459CAE537517184E99CCB6F66A9AFD9FAEBF0932`) without overwriting; retained the older source versions and bytecode in the backup. The roadmap diff contained the approved teleport amendment and Phase 0 status updates; the original copy remains preserved.
- Verified all 23 protected map files against the pre-merge SHA256 manifest after merge and after SUMO tests: 23/23 unchanged. The pre-existing `edgeData.xml` modification remains uncommitted and untouched.
- Implemented T1.1 on `agent/phase-1-core`: approach/intersection dataclasses, config-derived normalization, `SumoSensorReader`, congestion classification, JSON conversion, and fixed-size observation vector. Full checks: `python -m pytest -q -p no:cacheprovider` → 16 passed, 4 deselected; `python -m ruff check .` → all checks passed; `python -m pytest -q -p no:cacheprovider -m sumo` → 4 passed, 16 deselected; `python scripts/check_zombies.py` → no SUMO processes.
- Full-suite verification also exposed a stale expected TLS ID and a SUMO config parser splitting Windows paths at spaces. Updated the expectation to the user-confirmed TLS and changed file-list parsing to comma/semicolon separators; the complete suites then passed.
- T1.1 commit: `133b0c0`. Next task is T1.2 Signal safety layer.

## 2026-10-24/25 - T1.3 resumed tuning: q10/w60 seeds 3000, 3001, 3002

- Resumed from commit `fb1426d` (checkpoint at 6/9 cells). Verified 6 completed cells in `t13_rule_tuning_progress.json`; partial interrupted folder `20261024-224337_rule_medium_s3000` (steps.csv only, no run.json) left untouched and not counted as accepted.
- Command: `Ai/.venv/Scripts/python.exe -m scripts.tune_rule_controller`; script skipped all 6 completed keys and ran the 3 missing q10/w60 cells in order.
- q10/w60 seed 3000: run `20261024-231306_rule_medium_s3000`; 1,568/2,600 completed; 1,094 teleports; 0 fallbacks; avg_queue 12.211; avg_wait 210.877 s; wall 1,431.9 s.
- q10/w60 seed 3001: run `20261024-233704_rule_medium_s3001`; 1,557/2,600 completed; 1,059 teleports; 0 fallbacks; avg_queue 11.270; avg_wait 198.708 s; wall 3,162.5 s.
- q10/w60 seed 3002: run `20261025-002952_rule_medium_s3002`; 1,543/2,600 completed; 1,073 teleports; 0 fallbacks; avg_queue 10.743; avg_wait 170.291 s; wall 894.3 s.
- All 9/9 cells complete; progress JSON and docs/rule_tuning.md updated automatically by script after each cell.
- Threshold selection (lowest mean approach queue): q6/w30 mean_queue=11.256 mean_wait=185.918 s; q8/w45 mean_queue=11.317 mean_wait=211.226 s; q10/w60 mean_queue=11.408 mean_wait=193.292 s. **Selected: queue_threshold=6, wait_threshold_s=30 s** (best mean queue).
- Updated `config/stms.yaml` rule thresholds from 8/45 to 6/30.
- Tests: focused suite (test_controllers + test_metrics) 9 passed; full unit suite 30 passed, 5 deselected; Ruff all checks passed. Two ERROR lines in first invocation were Windows tmpdir permission issue on pytest-of-hannan; resolved by --basetemp; no code failures.
- Decision: T1.3 tuning complete. Best threshold selected and applied. T1.4 fixed diagnostic evidence already collected at `results/raw/20261024-210315_fixed_medium_s3000`; required test rerun passes. Phase 1 acceptance pending human review gate.

## 2026-10-25 - Phase 1 Human Acceptance and Closure

- Human review completed for T1.3 (rule tuning 9/9 cells, threshold queue=6, wait=30s) and T1.4 (metrics and crossing diagnostics). All 210 crossing mismatches in the fixed diagnostic are accounted for as SUMO gridlock teleports bypassing the junction (0 unexplained).
- User explicitly approved Phase 1 acceptance. T1.1, T1.2, T1.3, and T1.4 are marked Done.
- High teleport count on unchanged medium demand (~40-44%) is preserved as an unresolved baseline performance characteristic under the 2026-10-24 Section 0.6 approved amendment, to be comparatively evaluated in T2.5 and Phase 3 against PPO on identical demand and seeds.
- Phase 1 closed on `agent/phase-1-core`. Phase 2 is not started automatically. Next task at boundary: human review and merge of `agent/phase-1-core` into `main`, then T2.1 on `agent/phase-2-rl`.

## 2026-10-25 - A0 v6.1 repository checkpoint

- Task: A0 roadmap adoption; no random seeds used.
- First check: `Ai/.venv/Scripts/python.exe -m ruff check .` failed with TRY004 in `scripts/make_scenarios.py:331` because a JSON manifest with the wrong top-level type was raised as `ValueError`.
- Correction: changed that invalid-type exception to `TypeError`, preserving the clear message and fail-fast behavior.
- Checkpoint rerun: `Ai/.venv/Scripts/ruff.exe check .` → `All checks passed!`; `Ai/.venv/Scripts/python.exe -m pytest -q` → `30 passed, 5 deselected in 4.93s`.
- Decision: checkpoint passes; proceed with T2.1 on the v6.1 autonomous work branch.
