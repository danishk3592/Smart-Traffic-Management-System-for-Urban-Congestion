# Codex continuation handoff

Updated: 2026-11-07 18:58 +05:30. T6.4 local release is complete; T6.1 live-view remains Partial.

## Current verified state (2026-11-07 18:58 +05:30)

- T6.4 is complete: local merge `9396db5` and annotated tag `v1.0-ai-core` verified; no remote operations. T6.1 desktop live-view remains unverified; T6.2/T6.3 and final checkpoint evidence are summarized below.
- T4.8 is complete and committed as `b806d96`: 29 acceptance/regression tests pass, focused Ruff passes, 75/75 network dev raw cells are structurally complete with matching routes across controllers, and accepted snapshots contain 75 run/180 junction rows. Historical development headline is 23.3451% below fixed with 11,500 common trips; `ai_coverage=none` for all 25 PPO dev cells. Raw dev config hash `99a432c2…a4408e16` differs from current config; saved snapshots remain authoritative for the historical result, and no reaggregation was performed.
- T4.9 final PPO-only audit is complete and committed as `a1d2679`: read-only checks found 75/75 final cells with matching routes; accepted coverage snapshot confirms 0/12 (none), triggering Stage 4. `tests/test_results_doc.py` passed (2). PPO-only final headline is 25.7436% below fixed with 11,500 common trips and 100% completion. No final seeds were rerun; snapshots remain preserved.
- T4.10 is complete and committed as `735f863`: frozen gate rebuilt exactly (11 PPO TLS / 1 rule), hybrid tests 4 passed, T4.8 acceptance tests 29 passed, Ruff clean, final grid 75/75 with 0/12 strict ownership. Preserved snapshots report 25.8429% lower common-trip Metric N versus fixed at 100% completion. No final-seed rerun; current raw config hash mismatch is disclosed.

- Branch: `agent/autonomous-build`. T3.2 is Done in commit `b1bae24`: job `20261106-034321_78312686` RC 0; 105/105 valid cells; report test 2 passed; M1 Metric B reduction 9.229%, target not met. All six T6.1 seed-8000 CLI demos exited RC 0. Network fixed/rule/hybrid each completed 650/650 with zero teleports; hybrid is DEC-14 Stage 4 with AI coverage none (0/12). The single RL first attempt is incomplete/preserved; retry `20261106-062613_f532dad7` succeeded.
- T5.4 is Done after a clean post-M1 zombie check. T5.1 is Done via same-config full-column equivalence: pre-instrumentation and current fixed/medium/seed-3000 runs match all 31 summary fields except `run_id` and `wall_clock_s`; see `docs/evidence/t51_equivalence_20261106.json`.
- M2 coverage remains 0/12 (none), DEC-14 Stage 4 hybrid. Preserve M2 rows from the accepted final snapshot; current raw metadata config hash `99a432c2912d0320ca0bf61f9435781f2d8cbdb1f282fdeddc391c3da4408e16` differs from current config. Do not rerun final seeds or overstate raw reaggregation.
- Strict PPO development coverage work: four separate candidates reached 1/12 on held-out `net_medium/3003`–`/3006`; none met the 12/12 goal or was promoted. Candidate 4 completed 120,000 steps; its best validation censored time was 297.746 s at 100,008 steps, and held-out `/3006` completed 650/650 trips with 3 teleports and 1/12 strict owners. Full details and model/output hashes are recorded in `docs/experiment_log.md` and `docs/PROGRESS.md`. Accepted final stays 0/12; resolve the final seed-block protocol before any new final acceptance run.
- Current comparison composition: 1,782 M1 dev + 1,782 M1 final + 1,457 M2 final rows. Current M1 config SHA-256: `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`.
- T6.2 is Done with documented deviation (`55fdc54`): final Ruff passed, pytest 104 passed/23 deselected, SUMO suite 23 passed/104 deselected, zombie check clean. T6.3 is Done with deviation (`0317a4b`). T6.1 is Partial: six CLI demos passed and `a2b92fa` adds the CLI/tests; dashboard live-view remains unverified due native-pipe failure. Phase 3 and 5 checkpoints passed. T6.4 local merge/tag are complete.
- Release artifacts: selected M1 checkpoint/config `7242ae0`; M2 canonical aggregates `189f044`; accepted M2 model/config, snapshots/figure, network implementation and Flutter app are on the branch. Four separate strict PPO development candidates reached only 1/12 each; the accepted final remains 0/12 and DEC-14 Stage 4 hybrid.
- Preserve mixed owner work. Never touch/stage `SUMO/No_Polygon_Map/`; use explicit git paths only; stay on this branch; never push/fetch/pull.

## Prompt for the next Codex

```text
Continue the Smart Traffic Management System goal through T6.4 on local branch `agent/autonomous-build`. Read `AGENTS.md`, Sections 0 and 12 of `docs/STMS_Agent_Roadmap_FINAL.md`, then follow A0/resume. Read the current `docs/PROGRESS.md`, `docs/decisions.md`, `docs/RELEASE_CHECKLIST.md`, and this handoff. Continue autonomously and keep the full goal active until the T6.4 completion audit passes.

Send a brief update after each completed task and keep roadmap, progress, decisions, experiment log, release checklist, and handoff current.

Current verified state (2026-11-07 18:58 +05:30): T3.2 is Done with 105/105 lineage cells; M1 provisional Metric B improvement 9.229%, 10% target not met. T4.7 `44c2355`, T4.8 `b806d96`, T4.9 `a1d2679`, and T4.10 `735f863` are committed. T5.1 is Done; T6.1 remains Partial because desktop live-view evidence is unavailable; T6.2/T6.3 are Done with documented deviations. Work branch `a7d1cbe` is contained in local `main` merge `9396db5`; annotated tag `v1.0-ai-core` points to the merge. T6.4 is complete. Preserve owner/protected changes; no remote operations.

M2 remains DEC-14 Stage 4 hybrid with strict PPO coverage 0/12 (none). The user requests a separate development candidate experiment; preserve accepted final model/config/seeds/scenarios/metrics/outputs and do not rerun final seeds. Accepted final comparison rows are preserved from `comparison_t410_hybrid_final_snapshot.csv`; raw M2 metadata uses config SHA `99a432c2912d0320ca0bf61f9435781f2d8cbdb1f282fdeddc391c3da4408e16`, differing from current config `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`.

Never modify or stage `SUMO/No_Polygon_Map/`. Preserve owner changes; inspect status before staging and use explicit paths only. Never use `git add -A` or `git add .`; never push, fetch, or pull. Stay on `agent/autonomous-build`. Do not tune with seeds 5000+ or 6000+; demos use seed 8000+. Do not claim full AI coverage. T5.1 is Done; T6.1 and supervisor P1/P2 remain open. Strict PPO coverage development work is requested; keep accepted final artifacts frozen, and document that a new final block needs seed-protocol authorization.```

## Handoff evidence files

- `docs/PROGRESS.md`
- `docs/decisions.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/STMS_Agent_Roadmap_FINAL.md` Section 12
- `results/jobs/20261105-091026_edd94e34.json`
- `results/raw/t32_m1_final_cfg322_resume.log`
- `docs/evidence/t54_live_freshness_20261105.json`
