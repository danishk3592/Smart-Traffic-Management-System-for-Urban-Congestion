# Release checklist

Updated 2026-11-05. This is a working checklist; release is not authorized as complete until T6.4 passes its final checkpoint and local release steps.

| Area | Status | Evidence / remaining action |
|---|---|---|
| M1 final-seed results (T3.2) | In progress | Resume job `20261105-091026_edd94e34`; fresh lineage audit accepted 29/105 cells (fixed 10/35, rule 10/35, RL 9/35; 76 missing) at 2026-11-05 17:18 local. Evaluator remains live with six SUMO workers and advancing log. Frozen config SHA `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`. Run full lineage audit and validate every `docs/results.md` value against `results/summary/comparison.csv`. |
| M2 final result | Complete — DEC-14 Stage 4 hybrid | `docs/results.md` Part 3; Metric N 277.532 s hybrid vs 375.478 s fixed, 25.84% lower (95% CI 22.20–29.49%), 100% completion; AI coverage 0/12 (none). Provisional until P1. |
| Dashboard (Phase 5) | Partial | T5.1 missing historical config snapshot. T5.4 live sample passed: 30 consecutive updates, median 661.151 ms, max 1676.448 ms (≤2 s for this sample; see `docs/evidence/t54_live_freshness_20261105.json`). Flutter analysis clean, 19 widget tests pass, Release build succeeds, no-database test 2 passed and Ruff passes. Real-file views and five-process page-load median 1589.084 ms are documented. Run the post-evaluation zombie check before marking T5.4 Done. |
| Demo CLI (T6.1) | In progress | `scripts/run_demo.py` implemented and focused tests pass. Run all six controller/family demos on seed 8000, validate one-hour session and dashboard display, then check zombies. |
| Whole-repository quality (T6.2) | In progress | Scope cleanup and focused checks pass. On 2026-11-05, whole-repo Ruff passes; full default `pytest -q` reports 101 passed, 1 skipped, 23 deselected in 20.62 s (nonfatal cache warning); report test is 1 passed/1 skipped (M1 rows pending). `pip check` found no broken requirements; ignore probes passed for virtualenv, secrets, raw results and job records. Static searches found no removed-scope code/dependency matches; reviewed secret matches were placeholders/comments, a `ContextVar` token and binary diagram names. Four existing tracked files over 10 MB are SUMO map/backup inputs and `Documents/Untitled document.docx`; none changed. The temporary PDF helper is documented and exact-path excluded from Ruff. Full SUMO suite and final dependency/artifact/blocker/zombie audits remain pending. |
| Documentation (T6.3) | Done with deviation | README overview, architecture, setup, config, command order, outputs, limitations, ODbL attribution and dashboard pointer are documented. SRS deviations, limitations and report/PPT sources are listed. Local Markdown-link audit passed 8/8. Windows checks and the saved M2 job are verified; Ubuntu/fresh-install, demo and exact dashboard launch commands are listed as unrun in README. M1 final values remain T3.2 scope and are labelled pending until its exact-value audit passes. |
| Supervisor items | Pending | P1 headline metric confirmation and P2 SRS deviation acknowledgement remain labels/items; neither blocks release execution. |
| Release merge/tag | Not started | After final checkpoint, merge `agent/autonomous-build` locally into `main`, create `v1.0-ai-core` on `main`; do not push. |

## Protected and scope checks

- No changes to `SUMO/No_Polygon_Map/` may be staged or committed.
- No database, backend/API, authentication, computer vision/camera detection, prediction model, or explicit inter-junction messaging is in scope.
- Do not claim full network AI coverage unless the frozen final-seed evidence meets the roadmap's full-coverage criteria; current validated M2 coverage is `0/12 (none)`.
