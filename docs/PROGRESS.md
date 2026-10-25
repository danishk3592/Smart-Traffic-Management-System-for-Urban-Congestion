# Project progress

Updated: 2026-10-25

| Current task | Status | Branch | Last completed commit | Resume point |
|---|---|---|---|---|
| T2.2 environment tests | In progress | agent/autonomous-build | 9e0508c (T2.1) | T2.1 follow-up fixes action-0 hold semantics and default cache seed range. T2.2 SUMO gate passed 6/6 selected checks; final task record/commit pending. No PPO training. |

## Completed

- A0 — adopted roadmap v6.1 on `agent/autonomous-build` (`67d8a19`); Phase 1 checkpoint: Ruff passed and pytest reported 30 passed, 5 deselected. All eight completed-task commit hashes are ancestors of this branch.

- T0.1 - repository and environment audit (19d83ad).
- T0.2 - project skeleton, configuration, dependency lock, tooling and tests (50bda08; tracker update d275491).
- T0.3 - safe SUMO client, pilot TLS inspection, suitability ranking, approaches and controlled movements (3a68bb5; confirmed-target fix e2b189d).
- T0.3 target revalidation (2026-10-24): exact junction and TLS ID `cluster11259448953_11259448962_11259448969_cluster_11259448960_11259448961_11259448963` verified in the active net. Native run: rank 3/13, 349 crossings, 5 approaches, 4 green phases, 0 protected foe conflicts, 8 permissive yielding overlaps, 38 teleports over 1800 s. SUMO client tests 3 passed; junction tests 4 passed; zombie check clean; Ruff passed. Updated `config/stms.yaml` and `docs/tls_inspection.md`; report date now generated dynamically.
- Phase 0 merged into `main` as `ee77f85`; Phase 1 branch `agent/phase-1-core` starts at that merge. Pre-merge backup and collision quarantine are at `C:\Users\empow\AppData\Local\Temp\STMS_premerge_preserve_20261024-173055`.
- T1.1 - dataclasses, config-derived vector normalization, lane-level SUMO sensor aggregation, throughput sampling, and JSON conversion (`133b0c0`). Tests: unit suite 16 passed/4 deselected; SUMO-marked suite 4 passed; Ruff passed; zombie check clean. Protected map hash check: 23 files unchanged.
- T1.2 - generic `SignalSafetyLayer` validates the active TLS program and phase transitions, rejects invalid requests with reasons, routes phase changes through verified green/yellow/all-red phases, enforces configured minimum/maximum green, supports approach requests, and caps extensions. Confirmed pilot TLS used; native phase 2's 6-second green is lengthened to the configured 10-second minimum. Safety fuzzer: seed 731, 1200 simulated seconds; pass. Tests: `pytest -q -p no:cacheprovider` 21 passed/5 deselected; `pytest -q -p no:cacheprovider -m sumo` 5 passed/21 deselected; Ruff all checks passed; zombie check clean. No map files modified. Implementation commit `eacb7e0`.
- T1.3 - generic fixed-time, observation-only rule-based, fallback (with timeout latching), registry, and closed-loop episode runner. Tuning completed 9/9 cells across validation seeds 3000–3002 on unchanged medium demand; selected queue=6, wait=30s (lowest mean approach queue 11.256); `config/stms.yaml` updated. Unit tests pass (commit `ef1772a`).
- T1.4 - metrics module, definitions, and 33-column Section 11 summary (no NaN). Crossing cross-check confirmed all 210 mismatches as SUMO teleport bypasses (0 unexplained). High teleport rates preserved per Section 0.6 approved amendment. Human review approved Phase 1 acceptance on 2026-10-25.

## T1.3 and T1.4 completed; Phase 1 accepted

- Implemented generic fixed-time, observation-only rule-based, registry, and fail-safe fallback controllers; the fallback enforces a decision timeout and remains latched after a timed-out policy. Added the single-junction closed-loop runner and resumable threshold tuning script. No edge-specific green bonuses or demand changes were added.
- **T1.3 tuning complete (2026-10-25): all 9/9 cells run.** Six cells (q6/w30 and q8/w45 × seeds 3000–3002) completed in the prior session. Three q10/w60 cells resumed from commit `fb1426d`: seed 3000 (1,568/2,600, 1,094 tp, 0 fb, wall 1,431.9 s); seed 3001 (1,557/2,600, 1,059 tp, 0 fb, wall 3,162.5 s); seed 3002 (1,543/2,600, 1,073 tp, 0 fb, wall 894.3 s). Partial interrupted folder `20261024-224337_rule_medium_s3000` preserved, not counted. Best threshold selected: **queue_threshold=6, wait_threshold_s=30 s** (mean_queue=11.256, lowest of three settings). `config/stms.yaml` updated accordingly.
- T1.4 metric code, definitions, and exact-fixture tests are implemented. Current-run fixed diagnostic: `results/raw/20261024-210315_fixed_medium_s3000`, unchanged medium seed 3000, 2,600 trips, 1,534 completed, 1,082 teleports, 917.126 s wall time. All 210 crossing-mismatch IDs are in the current run's teleport set; zero mismatches remain without a recorded teleport.
- The current fixed summary has all 33 Section 11 fields, no NaN, and only the two documented network-only queue fields blank. The legacy-metric explanation remains in `docs/metrics.md`.
- **Human acceptance review:** Conducted on 2026-10-25. All T1.3 and T1.4 criteria pass. High teleports on unchanged medium demand are preserved and accommodated under the 2026-10-24 Section 0.6 approved deviation (deferred to post-PPO comparative evaluation in T2.5/Phase 3). User explicitly approved Phase 1 closure.

## Boundaries and next gate

- Phase 1 is **Done** on `agent/phase-1-core`.
- Human performs the single merge step into `main` per Roadmap Section 0.5.
- Preserve the user's modified `SUMO/No_Polygon_Map/edgeData.xml` and never write outputs under `SUMO/No_Polygon_Map/`.
- Phase 2 T2.1 is **Done** on `agent/autonomous-build` (`9e0508c`); the owner-approved reward design is documented in `docs/rl_design.md`, the 140-entry training pool validated, and required environment runtime checks completed. T2.2 is now **in progress** and remains the blocking gate before any PPO training.
