# Project progress

Updated: 2026-10-24

| Current task | Status | Branch | Last completed commit | Resume point |
|---|---|---|---|---|
| T1.3/T1.4 - Controllers + metrics | Implementation committed; acceptance pending | agent/phase-1-core | a413e55 | T1.3 tuning stopped at 1/9; T1.4 current-run fixed diagnostics remain. No long simulations without user approval. |

## Completed

- T0.1 - repository and environment audit (19d83ad).
- T0.2 - project skeleton, configuration, dependency lock, tooling and tests (50bda08; tracker update d275491).
- T0.3 - safe SUMO client, pilot TLS inspection, suitability ranking, approaches and controlled movements (3a68bb5; confirmed-target fix e2b189d).
- T0.3 target revalidation (2026-10-24): exact junction and TLS ID `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` verified in the active net. Native run: rank 3/13, 349 crossings, 5 approaches, 4 green phases, 0 protected foe conflicts, 8 permissive yielding overlaps, 38 teleports over 1800 s. SUMO client tests 3 passed; junction tests 4 passed; zombie check clean; Ruff passed. Updated `config/stms.yaml` and `docs/tls_inspection.md`; report date now generated dynamically.
- Phase 0 merged into `main` as `ee77f85`; Phase 1 branch `agent/phase-1-core` starts at that merge. Pre-merge backup and collision quarantine are at `C:\Users\empow\AppData\Local\Temp\STMS_premerge_preserve_20261024-173055`.
- T1.1 - dataclasses, config-derived vector normalization, lane-level SUMO sensor aggregation, throughput sampling, and JSON conversion (`133b0c0`). Tests: unit suite 16 passed/4 deselected; SUMO-marked suite 4 passed; Ruff passed; zombie check clean. Protected map hash check: 23 files unchanged.
- T1.2 - generic `SignalSafetyLayer` validates the active TLS program and phase transitions, rejects invalid requests with reasons, routes phase changes through verified green/yellow/all-red phases, enforces configured minimum/maximum green, supports approach requests, and caps extensions. Confirmed pilot TLS used; native phase 2's 6-second green is lengthened to the configured 10-second minimum. Safety fuzzer: seed 731, 1200 simulated seconds; pass. Tests: `pytest -q -p no:cacheprovider` 21 passed/5 deselected; `pytest -q -p no:cacheprovider -m sumo` 5 passed/21 deselected; Ruff all checks passed; zombie check clean. No map files modified. Implementation commit `eacb7e0`.

## T1.3 and T1.4 implementation; acceptance pending

- Implemented generic fixed-time, observation-only rule-based, registry, and fail-safe fallback controllers; the fallback enforces a decision timeout and remains latched after a timed-out policy. Added the single-junction closed-loop runner and resumable threshold tuning script. No edge-specific green bonuses or demand changes were added.
- Short checks on 2026-10-24: `pytest -q tests/test_controllers.py tests/test_metrics.py` -> 9 passed; full unit suite -> 30 passed, 5 deselected; SUMO-marked suite -> 5 passed, 30 deselected; `ruff check .` -> all checks passed; zombie check -> no running SUMO processes. An initial timeout-test expectation failed, was corrected to match the fixed controller's phase state, and the focused suite then passed.
- Existing fixed episode (`results/raw/20261024-192727_fixed_medium_s3000`): 2,600 scheduled trips, 1,534 completed, 1,082 teleports, 862.5 s wall time. The step log confirms 30-second green intervals. Existing rule episode (`results/raw/20261024-194221_rule_medium_s3000`): 1,560/2,600 completed, 1,088 teleports; repeated safety-fallback warnings at maximum green make it exploratory, not accepted tuning evidence.
- Rule tuning stopped at the user's instruction: 1/9 validation runs complete (q6/w30, seed 3000: 1,544/2,600 completed, 1,145 teleports, 0 fallback activations, 1,459.7 s). A second q6/w30/3001 attempt is preserved as a partial `steps.csv` through simulation time 1,655 s; no trip log or `run.json` exists for it. An earlier startup attempt has a preserved zero-byte `steps.csv`. The eight remaining complete runs were not launched after the stop instruction. No best threshold is selected; config remains at 8/45.
- T1.4 metric code, definitions, and exact-fixture tests are implemented. Existing fixed logs were copied to `results/raw/20261024-205400_fixed_existing_metrics_recheck` and postprocessed without overwriting the source run; the generated summary has all Section 11 columns and no NaN. This old episode predates unfinished-tripinfo and per-vehicle crossing diagnostics, so its unfinished-trip metrics and crossing explanation do not satisfy T1.4 acceptance.
- T1.4 remains pending a fixed run with the current runner and a completed-trip route-through crossing check. The prior fixed artifact has 396 completed route-through trips, of which 210 lack a recorded crossing; its run record lacks teleport IDs, so those mismatches are unexplained. No further simulation was started. The approved baseline teleport amendment remains in force; excessive teleports are reported, not hidden or used to reduce demand.
- Phase 1 is **not complete**. Next action requires user approval for the remaining long validation simulations and the current-run fixed-time diagnostic.

## T0.4 completed with explicit deviation

- T0.4 deterministic scenario generation, cached routes/manifests, measurements and five unit tests are implemented. The confirmed-TLS native baseline measured junction shares >= 0.464 and teleport shares: balanced 0.336, directional_ns 0.406, directional_ew 0.342, low 0.169, medium 0.396, heavy 0.455, rush_hour 0.446. These are failed baseline performance results, preserved in `docs/scenarios.md`; none are treated as passing.
- T0.4 force check passed: `--seed 1000 --all --force`, all seven route SHA256 values matched, 71.1 s. Training pool completed: `--train-pool` printed `Pre-generated 140 cached training route files.`; 140/140 route/manifest pairs verified against current config and route hashes, 0 issues. First detached attempt timed out after 600 s at directional_ns/seed_1010 (30/140 progress); retry with one alternative route succeeded in 773 s. `python -m pytest -q -p no:cacheprovider tests/test_scenarios.py`: 5 passed in 3.59s after the approved gate edit; `ruff check scripts/make_scenarios.py tests/test_scenarios.py`: all checks passed; `git diff --check`: passed; protected-map status empty.
- No PPO implementation or training has started. Human-approved amendment dated 2026-10-24 moves evaluation of the >5% native-baseline teleport criterion until PPO is connected and fixed-time/PPO can be compared on identical unchanged demand and seeds. Other safety, correctness, task-order and PPO acceptance criteria remain active.
- Human approval (2026-10-24): proceed with unchanged-demand experiments and document excessive teleports/gridlock as unresolved. Scope permits remaining T0.4 experiments, including cached training-pool generation; it does not waive acceptance or authorize demand changes.

## Boundaries and next gate

- Continue on `agent/phase-1-core` from merge commit `ee77f85`.
- Preserve the user's modified `SUMO/No_Polygon_Map/edgeData.xml` and never write outputs under `SUMO/No_Polygon_Map/`. The existing edgeData change and HSR file remain in place; RL artifacts were restored after content/hash comparison.
- Database, backend/API and dashboard remain out of scope.
- The 2026-10-24 human-approved amendment changes only when teleport performance is evaluated; it does not erase or pass the native baseline failure. T0.4 is recorded Done with deviation. PPO remains sequenced after T1.4, T2.1 and T2.2.
- Next task: complete T1.3 validation and T1.4 acceptance evidence. The implementation and short-test criteria are verified; remaining requirements need the eight full tuning episodes and a current-run fixed diagnostic. No long simulations without user approval.
