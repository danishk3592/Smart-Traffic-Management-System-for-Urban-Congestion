# SRS deviations and scope decisions

**Source:** approved SRS v1.0 at `Documents/SRS_Smart_Traffic_Management_System.docx`.
**Supervisor acknowledgement:** pending (P2). The following implementation scope is recorded per DEC-04, DEC-07 and DEC-15; it is not presented as an SRS sign-off.

| SRS item | Status | Reason |
|---|---|---|
| FR-DSH-* (dashboard) | Implemented in Phase 5 as a read-only, local, file-based Windows desktop dashboard limited to the T5.2–T5.3 views; no REST/WebSocket. Exact FR-DSH coverage is mapped in `docs/dashboard.md` against SRS §3.1, including change-log ambiguity A-3. | DEC-15 |
| FR-OVR-*, FR-AUT-*, FR-DAT-*, §3.1/§3.4 (REST/WS, authentication, database, manual override) | Not implemented. Persistence uses CSV/JSON files; no backend, authentication or database. | DEC-04 |
| FR-CV-* (computer vision, camera detection, ROI, annotated video) | Removed from scope; no vision implementation or dependency. | Scope decision |
| Camera-sourced traffic state (camera part of FR-STA-*) | Not implemented; traffic state is obtained from SUMO through TraCI. | Scope decision |
| FR-PRD-01..05 (traffic prediction) | Removed from scope; no prediction model or prediction-based RL input. | Scope decision |
| FR-SIM-05 (multiple vehicle types) | Supported by configuration but not used in the evaluated demand. Cars only. | DEC-07 |
| FR-SIM-02 / FR-CTL-10 (multiple controlled junctions) | Implemented for every intended (suitable) TLS in Phase 4. Unsuitable TLS are listed in `docs/network_tls.md` and remain on SUMO's native program. Coordination uses the shared policy; no explicit inter-junction messaging is implemented. | DEC-12 / DEC-13 / DEC-14 |
| §3.2 explicit SUMO detectors | Lane-level TraCI queries are used instead. | Equivalent state source |
| NFR-PRF-06 (average travel time) | Provisional headline is controlled-junction trips for M1 (DEC-01) and network-wide all trips for final M2 (DEC-12); common-trip, censored travel time and completion rates are reported together. M1 final result remains pending T3.2. | DEC-01 / DEC-12 |
| NFR-PRF-04 (vision FPS) | Not applicable; computer vision is out of scope. | Scope decision |
| NFR-PRF-02/03 (dashboard / REST latency) | Windows real-results page-load median is 1589.084 ms from five Release-process observations. A separate 30-sample live Release measurement recorded maximum status-to-post-frame age 1676.448 ms, below NFR-PRF-02's ≤2 s limit for that interval; this does not establish a universal bound. REST latency is not applicable because there are no REST endpoints. Raw sample: `docs/evidence/t54_live_freshness_20261105.json`. | DEC-15 |
| FR-EMG-* (emergency-vehicle priority) | Deferred optional feature; not implemented. | Roadmap scope |

## Pending supervisor items

- **P1 — headline metric:** pending supervisor confirmation. Until then, headline values remain labelled provisional; use DEC-01 for M1 and DEC-12 for M2.
- **P2 — SRS deviations:** pending supervisor acknowledgement of this table.

## Autonomous decision outcomes

- **P3 — M1 pilot:** selected/confirmed as documented in T0.3 and `config/stms.yaml`.
- **P4 — intended TLS set:** frozen in Phase 4 using the T4.1 suitability criteria; list, exclusions, hash and freeze time are in `docs/network_tls.md` and config.
- **P5 — fallback when shared PPO does not cover all intended TLS:** DEC-14 Stage 4 hybrid triggered and evaluated; final strict PPO coverage is 0/12 (none), reported without a full-coverage claim.
- **P6 — dashboard:** owner-selected Flutter Windows desktop app, local files, read-only, limited to six T5.2–T5.3 views.
