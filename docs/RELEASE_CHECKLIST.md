# Release checklist

Updated: 2026-11-07 18:55 +05:30. Release audit/checkpoint passed; local merge/tag pending.

| Area | Status | Evidence / remaining action |
|---|---|---|
| M1 final-seed results (T3.2) | Complete | Commit `b1bae24`; 105/105 unique cells; job `20261106-034321_78312686` RC 0; frozen config SHA-256 `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`. Selected model SHA `9d0e3e82…2c01bc467` was CPU-loaded and packaged with training metadata in `7242ae0`. Report acceptance `tests/test_results_doc.py`: 2 passed. Metric B reduction 9.229%, 10% target not met. Phase 3 checkpoint passed. |
| M2 final result | Complete — DEC-14 Stage 4 hybrid | `docs/results.md` Part 3; Metric N 277.532 s hybrid vs 375.478 s fixed, 25.84% lower (95% CI 22.20–29.49%), 100% completion; AI coverage 0/12 (none). Provisional until P1. |
| Dashboard (Phase 5) | Complete with documented limits | T5.1–T5.4 complete. T5.1 same-config fixed/medium/seed-3000 comparison matched all 31 summary fields except `run_id` and `wall_clock_s`; evidence is in `docs/evidence/t51_equivalence_20261106.json`. Historical config bytes remain unavailable but were not required for this same-config comparison. Freshness evidence and limits are recorded in the report. |
| Demo CLI (T6.1) | Partial | Commit `a2b92fa`; all six required fixed/rule/RL × single/network seed-8000 CLI runs completed RC 0. Network runs completed all 650 trips with zero teleports; network RL is Stage 4 hybrid, AI coverage none (0/12). Post-demo zombie check clean. Dashboard live-view remains unverified because `@oai/sky.list_apps()` still fails with native-pipe error after retry. |
| Whole-repository quality (T6.2) | Done with documented existing-artifact deviation (`55fdc54`) | Final phase checkpoint: whole-repo Ruff passed; default pytest **104 passed/23 deselected**; full SUMO suite **23 passed/104 deselected**, RC 0; pip check and post-suite zombie check clean. Credential-pattern search found only a ContextVar named `token`, no credential; prohibited-scope dependency search empty; no tracked DB; ignore probes and ODbL attribution pass. T5.1 was later closed by the same-config equivalence check; T6.1 desktop blocker remains open. Four pre-existing tracked files >10 MiB (approved SRS and existing SUMO assets, including protected map files) were left untouched; no generated artifact exceeds 50 MiB. The existing PDF scratch helper remains documented and exact-path excluded. |
| Documentation (T6.3) | Done with deviation | Commit `0317a4b`. README overview, architecture, setup, config, command order, outputs, limitations, ODbL attribution and dashboard pointer are documented. SRS deviations, limitations and report/PPT sources are listed. Local Markdown-link audit passed 8/8. Windows checks and the saved M2 job are verified; Ubuntu/fresh-install, demo and exact dashboard launch commands are listed as unrun in README. M1 final values are included and checked against the final comparison CSV. |
| Supervisor items | Pending | P1 headline metric confirmation and P2 SRS deviation acknowledgement remain labels/items; neither blocks release execution. |
| Release merge/tag | In progress | `main` remains at `59e0551`, an ancestor of `agent/autonomous-build` at `189f044`; tag `v1.0-ai-core` does not exist. M1 model/config `7242ae0`, canonical M2 aggregates `189f044`, selected M2 checkpoint/config, final snapshots/figure, network implementation, Flutter dashboard and demo CLI are in the branch. Final checkpoint passed; no tracked file exceeds 50 MiB. Next perform one local `--no-ff` merge and create/verify tag. No remote operations.

## Tasks still Partial or unverified

- **T6.1 — Partial:** all six CLI demos exited RC 0 and the post-demo zombie check is clean. The live-view display of a completed seed-8000 demo is unverified because the desktop helper native pipe remains unavailable; no visual pass is claimed.
- **Supervisor P1/P2 — Pending:** confirm the provisional headline metric choices and acknowledge SRS deviations; labels only, not release execution blockers.
- **Controller level:** DEC-14 Stage 4 hybrid; **strict PPO coverage 0/12 (none)** in the accepted final result. Four separate development candidates each reached only 1/12 on one held-out cell and were not promoted. Do not claim full network-wide AI control. A new final acceptance block still requires a documented seed-protocol decision; accepted final artifacts remain frozen.
- **Worktree preservation:** mixed owner changes remain in the `agent/autonomous-build` worktree and are not part of commits unless explicitly listed; protected `SUMO/No_Polygon_Map/` edits remain unstaged. The local release merge contains commits only; no remote operation is authorized or performed.

## Protected and scope checks

- No changes to `SUMO/No_Polygon_Map/` may be staged or committed.
- No database, backend/API, authentication, computer vision/camera detection, prediction model, or explicit inter-junction messaging is in scope.
- Do not claim full network AI coverage unless the frozen final-seed evidence meets the roadmap's full-coverage criteria; current validated M2 coverage is `0/12 (none)`.
