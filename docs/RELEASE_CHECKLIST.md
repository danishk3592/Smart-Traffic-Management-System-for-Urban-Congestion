# Release checklist

Updated: 2026-11-06 13:02 +05:30. This is a working checklist; release is not complete until T6.4 passes its final checkpoint and local release steps.

| Area | Status | Evidence / remaining action |
|---|---|---|
| M1 final-seed results (T3.2) | Complete | Commit `b1bae24`; 105/105 unique cells; job `20261106-034321_78312686` RC 0; frozen config SHA-256 `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`. Report acceptance `tests/test_results_doc.py`: 2 passed. Metric B reduction 9.229%, 10% target not met. Phase 3 checkpoint remains outstanding for T6.2. |
| M2 final result | Complete — DEC-14 Stage 4 hybrid | `docs/results.md` Part 3; Metric N 277.532 s hybrid vs 375.478 s fixed, 25.84% lower (95% CI 22.20–29.49%), 100% completion; AI coverage 0/12 (none). Provisional until P1. |
| Dashboard (Phase 5) | Partial | T5.2 through T5.4 complete; post-evaluation zombie check reported no running SUMO/SUMO-GUI processes. T5.1 stays Partial: historical config snapshot unavailable; freshness evidence and limits are recorded in the report. |
| Demo CLI (T6.1) | In progress | All six required fixed/rule/RL × single/network seed-8000 CLI runs completed RC 0. Network runs completed all 650 trips with zero teleports; network RL is Stage 4 hybrid, AI coverage none (0/12). Post-demo zombie check clean. Dashboard live-view remains unverified because `@oai/sky.list_apps()` still fails with native-pipe error after retry. |
| Whole-repository quality (T6.2) | Done with documented existing-artifact deviation | Whole-repo Ruff passed; default pytest: 102 passed/23 deselected; full SUMO suite job `20261106-065551_97ee54e3`: 23 passed/102 deselected, RC 0; pip check and post-suite zombie check clean. Credential-pattern search found only a ContextVar named `token`, no credential; prohibited-scope dependency search empty; no tracked DB; ignore probes and ODbL attribution pass. T5.1 snapshot and T6.1 desktop blockers were retested and remain open. Four pre-existing tracked files >10 MiB (approved SRS and existing SUMO assets, including protected map files) were left untouched; no generated artifacts were tracked. The existing PDF scratch helper remains documented and exact-path excluded. |
| Documentation (T6.3) | Done with deviation | Commit `0317a4b`. README overview, architecture, setup, config, command order, outputs, limitations, ODbL attribution and dashboard pointer are documented. SRS deviations, limitations and report/PPT sources are listed. Local Markdown-link audit passed 8/8. Windows checks and the saved M2 job are verified; Ubuntu/fresh-install, demo and exact dashboard launch commands are listed as unrun in README. M1 final values are included and checked against the final comparison CSV. |
| Supervisor items | Pending | P1 headline metric confirmation and P2 SRS deviation acknowledgement remain labels/items; neither blocks release execution. |
| Release merge/tag | Not started | After final checkpoint, merge `agent/autonomous-build` locally into `main`, create `v1.0-ai-core` on `main`; do not push. |

## Protected and scope checks

- No changes to `SUMO/No_Polygon_Map/` may be staged or committed.
- No database, backend/API, authentication, computer vision/camera detection, prediction model, or explicit inter-junction messaging is in scope.
- Do not claim full network AI coverage unless the frozen final-seed evidence meets the roadmap's full-coverage criteria; current validated M2 coverage is `0/12 (none)`.
