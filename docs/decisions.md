# Decisions and blockers

## Autonomous decisions

| Date | Task | Decision |
|---|---|---|
| 2026-10-25 | A0 | Adopt roadmap v6.1. Created `agent/autonomous-build` from `agent/phase-2-rl` at `c73efa3`; `main` was already an ancestor, so no other branch merge or rollback tag was needed. Installed the supplied roadmap as `docs/STMS_Agent_Roadmap_FINAL.md`, updated `AGENTS.md`, and added the new v6 configuration keys. Existing worktree changes were carried across unchanged. |
| 2026-10-25 | T2.1-fix | Make action 0 hold the current green for one decision interval via `SignalSafetyLayer.request_extend`; this makes “keep” distinct from SUMO's native signal cycle while preserving the max-green override. Limit default env seeds to the configured pre-generated seed count. |

## Open blockers

| Date | Task | Blocker / exact action needed | Status |
|---|---|---|---|
