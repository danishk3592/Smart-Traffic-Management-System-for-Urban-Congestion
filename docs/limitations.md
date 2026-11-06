# Limitations and outstanding work

Updated: 2026-11-06 10:50 +05:30. See [`docs/PROGRESS.md`](PROGRESS.md) and the Section 12 tracker in the roadmap for current task state.

## Evaluation and control

- M1 T3.2 final reporting is complete: 105/105 frozen cells passed lineage and the CSV-backed report test. The provisional Metric B headline reduction is 9.229% versus fixed-time; the configured 10% target is not met.
- M2 final metrics are retained from the accepted frozen snapshot; current raw M2 metadata has a different config hash and cannot be reaggregated under current config. Revalidation would require a new final-seed run, which was not performed.
- The final M2 result is DEC-14 Stage 4 hybrid: Metric N is 25.84% lower than fixed-time (paired 95% CI 22.20–29.49%) with 100% completion; strict PPO ownership remains **0/12 (none)**. This is not full network-wide AI coverage.
- Traffic and demand are simulated in SUMO on an OSM-derived map. The results are not real-world deployment evidence. Cars only are used.
- Network-wide fallback mixes PPO and rule control as frozen by the Stage-4 gate; no PPO-disabled ablation isolates the PPO contribution from safety fallback/rule behavior.

## Dashboard

- T5.1 remains Partial because the pre-instrumentation config snapshot matching SHA-256 `6b0b87b8aa135dfc3c160a9aa899eaa87b63774c0fc440cbc363abb7c85b5bef` is not archived. Existing saved fixed/medium/seed-3000 summaries differ in `config_hash`, so strict same-config, all-column observational equivalence is unproven.
- T5.4 is Done. Its post-M1 check reported no running SUMO or SUMO-GUI processes. The fresh 30-sample Windows Release status-to-post-frame measurement: median age 661.151 ms and maximum 1676.448 ms, below the SRS NFR-PRF-02 ≤2 s threshold for this measured 45-second interval. All 30 rendered `Last update` values matched distinct producer timestamps at consecutive 5-s simulation intervals. The raw report is `docs/evidence/t54_live_freshness_20261105.json`. This is one run sample, not a universal bound; the post-evaluation zombie check passed. Flutter analysis, 19 widget tests, Release build, no-database tests and Ruff pass. Five Release real-results page loads separately measured median 1589.084 ms. NFR-PRF-03 is not applicable because the dashboard has no REST endpoints.
- The dashboard is Windows desktop only, local, unauthenticated and read-only. It reads files already on disk; it does not control SUMO. Raw run artifacts are not committed.

## Environment and delivery

- Python 3.14.10 and SUMO 1.27.1 were verified on Windows on 2026-11-05; the earlier 3.14.2 value is historical. Ubuntu CLI support is intended but unverified in this workspace.
- P1 (headline metric confirmation) and P2 (SRS deviation acknowledgement) remain supervisor items; neither blocks execution. Until resolved, headlines remain provisional.
- Computer vision, camera state, prediction, database, backend/API, authentication, manual signal override, emergency priority and explicit message-based junction coordination are out of scope.
- Any task still Partial/Blocked at release, plus its exact next action, must be repeated in `docs/RELEASE_CHECKLIST.md` and the final report.
