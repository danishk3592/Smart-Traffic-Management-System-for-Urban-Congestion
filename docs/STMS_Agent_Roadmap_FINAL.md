# STMS — Agent Build Roadmap (FINAL — v4.2 audited: single-junction milestone → network-wide AI control, single-owner workflow)

**Project:** Smart Traffic Management System for Urban Congestion (Bengaluru HSR Layout SUMO map)
**Final objective:** AI control of **all intended (suitable) traffic-light junctions in the SUMO map**, evaluated network-wide. Single-junction control is the **initial milestone (M1)** only and is never the final result (DEC-12).
**Requirements source:** `docs/SRS_Smart_Traffic_Management_System.docx` (SRS v1.0). IDs like `FR-CTL-06` refer to it.
**Repo:** `https://github.com/hannanahmedqureshi786-eng/smart-traffic-management-system` (branch `main`)
**Primary agent:** Codex in VS Code, running **locally** on the owner's Windows laptop. This roadmap is written agent-neutral (no tool-specific features), so another agent could continue it later, but **only one agent works at a time** (Section 0.9).

> This file is an instruction set for a coding agent. Read **Section 0 completely before doing anything**. Execute tasks **in order, one at a time**. The human is a student with a deadline shared with exams and placements — see Section 14 (time plan and cut lines).

---

## H. How the human starts the agent (do this once, by hand)

Because T0.2 creates `AGENTS.md`, the agent cannot read rules that do not exist yet. The human therefore:

1. Copies this file to `docs/STMS_Agent_Roadmap_FINAL.md` in the repo and the SRS to `docs/SRS_Smart_Traffic_Management_System.docx` (commit on `main`).
2. Opens the repo in VS Code with Codex and sends this first prompt:

> Read `docs/STMS_Agent_Roadmap_FINAL.md` completely, starting with Section 0. Then execute **T0.1 only** (audit, no code changes). Report in ≤ 15 lines using the format in Section 0.1, and wait for my reply before starting T0.2.

3. After each task the human reviews the report and replies "continue" or gives corrections. After each **phase** the human merges the phase branch into `main` exactly as described in Section 0.5 and replies "merged". The human does **not** edit repo files while a task is running (Section 0.9).

---

## A. Scope of this version

**Milestones (DEC-12):**
- **M1 — single-junction milestone (Phases 0–3):** develop and validate the whole stack on **one suitable pilot junction**: SUMO + TraCI, safety layer, fixed-time / rule-based / PPO controllers, fair evaluation. M1 results are reported as a milestone, **not** as the final result.
- **M2 — network-wide control (Phase 7, the FINAL DELIVERABLE):** extend control to **all intended traffic-light junctions** (every TLS that passes the T7.1 suitability check), each behind its own safety layer, and evaluate congestion and travel time **across the whole map**. The final deliverable must demonstrate **AI (PPO) control of all intended traffic lights**. If full-map PPO is too expensive, the staged ladder in DEC-14 applies; falling back below full AI coverage requires an explicit human decision (P5) and honest labelling — it is never declared silently.

**IN SCOPE NOW:** SUMO + TraCI · safety layer · fixed-time, rule-based and PPO-RL controllers · fair evaluation of the 10% target (M1 junction-level, M2 network-wide) · **multi-junction control of all intended TLS** · traffic prediction (ML, M1 junction only) · OpenCV + YOLO vehicle detection on a **virtual camera rendered from SUMO-GUI** (simulated-vision prototype, M1 junction only, independent of PPO success) · reproducible CLI demo · docs.

**DEFERRED — DO NOT BUILD, DO NOT START, DO NOT CREATE FOLDERS FOR:**
- FastAPI backend, WebSocket, authentication/JWT/roles, audit log
- Any database (PostgreSQL / SQLite / SQLAlchemy / Supabase)
- Dashboard (Flutter or otherwise)
- Optional emergency-vehicle priority, **explicit communication-based inter-junction coordination (green waves, message passing)**, prediction-as-RL-input — only if the human asks later. (Multi-junction *control* is in scope via Phase 7; coordination there is implicit through a shared policy.)

**Teammates:** none. No teammate hand-off, no teammate analytics deliverable, no per-person folder ownership. Any pre-existing teammate code (e.g. `Ai/analytics/`) is treated as ordinary project code: inventory it in T0.1; it is linted and tested like everything else (Section 0.7). It is not part of the new deliverables and the new code must not depend on it.

**Future-proofing (cheap, mandatory):** keep `IntersectionState.to_dict()` JSON-serialisable, keep the `Controller` interface clean, and keep the safety layer's `Accepted | Rejected(reason)` API, so a backend/dashboard can be added later without refactoring. Build nothing else for it.

**SRS deviations to record in `docs/srs_deviations.md` (T6.3)** so evaluators see them as deliberate and the supervisor can approve them (SRS v1.0 is marked approved, so these need explicit sign-off — see Section 2, "Pending human/supervisor decisions"):

| SRS item | Status | Reason |
|---|---|---|
| FR-DSH-*, FR-OVR-*, FR-AUT-*, FR-DAT-*, §3.1/§3.4 (dashboard, REST/WS, auth, DB) | Deferred | Scope decision: AI core first |
| FR-CV-* | Demonstrated on a **simulated camera** (SUMO-GUI frames), not recorded real footage; results are **not evidence of real-world camera accuracy** | Reproducible ground truth, no footage licensing |
| FR-CV-02 (car/bus/truck/motorcycle classes) | Cars only | DEC-07 |
| FR-SIM-05 (multiple vehicle types) | Supported by config, **not used** | DEC-07 |
| FR-SIM-02 / FR-CTL-10 (multiple controlled junctions) | Implemented in Phase 7 for all **intended** (suitable) TLS; unsuitable TLS are listed and stay on SUMO's native program for every controller; coordination is decentralised (shared policy), no explicit inter-junction communication | Suitability and compute |
| §3.2 explicit SUMO detectors (induction loop / lane-area) | Lane-level TraCI queries used instead | Equivalent measurements, simpler |
| NFR-PRF-06 "average travel time" | Provisional headline is the **controlled-junction trips** metric for M1 (DEC-01) and the **network-wide all-trips** metric for the final M2 result (DEC-12); censored results and completion rates always reported beside it | DEC-01, DEC-12 |
| FR-PRD-04/05, FR-EMG-* | Deferred/optional | Scope |
| FR-PRD-01..03, FR-CV-* (if time runs out) | May be explicitly marked **Skipped/Deferred** per Section 14 cut lines | Time: exams/placements; core is Phases 0–3 and Phase 7 |

---

## 0. Operating rules for the agent (mandatory)

### 0.1 How to work
1. Work on **exactly one task (T-id) at a time**, in listed order. Do not start a task until every task in its `Depends on` line is marked Done in Section 12 (a Phase 4/5 task explicitly marked `Skipped`/`Deferred` under Section 14 does not block tasks that do not need its output).
2. Before editing: run `git status` (must be clean apart from the task's own work), read the whole task block, and **inspect every existing file the task touches**.
3. After coding: run **every command in the task's `Accept` block**. A task is done only when all checks pass. Quote real (trimmed) output in the report.
4. After each task: update Section 12 (status, date, commit hash, one-line note), commit (0.5), and report: *what changed · files touched · commands run · real results · open issues*.
5. If a task fails its acceptance after **3 honest attempts**, or cannot be completed safely → **stop and ask the human** (0.6). Do not skip ahead; do not weaken the check.
6. **Keep reports ≤ 15 lines** unless something failed.
7. Record every experiment, including failed and abandoned ones, in the append-only `docs/experiment_log.md` (date, task, what was tried, seeds used, result, decision).

### 0.2 Honesty rules (most important)
- **Never invent or hand-edit results.** Every number in `results/` and docs must come from a script you actually ran. Do not invent machine specs, versions or timings either — detect them.
- The 10% travel-time reduction is a **target, never an assumed result**. Report what is measured, even if it is 0% or negative.
- Never claim something works unless you ran it. If you could not run something (e.g. SUMO-GUI), say so.
- A script finishing without error does **not** prove correctness; check outputs against the acceptance criteria.
- Existing code and artifacts (RL files, saved models, old baseline numbers, old scripts) are **unverified until tested in T0.1**. Do not describe them as working, validated or "the baseline" until you have re-run them.

### 0.3 File rules
| Area | Rule |
|---|---|
| `SUMO/No_Polygon_Map/*` (existing network/config) | **Never modify.** All derived/new SUMO files go in `SUMO/derived/` and `SUMO/scenarios/`. |
| Existing `Ai/rl/models/ppo_traffic.zip`, `Ai/rl/ppo_evaluation.csv` | Preliminary artifacts. **Do not delete or overwrite**; test them in T0.1 and label them (working / broken / unverified) with evidence. New models go to new versioned folders. |
| `Ai/rl/*.py` | May be rewritten; keep filenames `traffic_env.py`, `test_env.py`, `train_ppo.py`, `evaluate_ppo.py`. |
| Any other existing file | May be edited when a task needs it. Inspect first, keep changes minimal, mention in the report. |
| New folders you may create | `Ai/common/`, `Ai/controllers/`, `Ai/evaluation/`, `prediction/`, `vision/`, `results/`, `docs/`, `scripts/`, `tests/`, `config/`. **Nothing else** (no `backend/`, `frontend/`, `Ai/runtime/`, no database files). |

### 0.4 Output hygiene
- Never overwrite a previous result. Each run writes to `results/raw/<run_id>/`, `run_id = <YYYYMMDD-HHMMSS>_<controller>_<scenario>_s<seed>`.
- Aggregates go to `results/summary/` (schemas in Section 11); figures to `results/figures/`.
- Models: `Ai/rl/models/ppo_v<N>/model.zip` + `config.json` (M1) and `Ai/rl/models/ppo_net_v<N>/…` (M2; same files; `config.json` also records the intended-TLS list hash). `config.json` holds hyper-parameters, reward weights, git commit, seeds, library versions, training wall-clock. Never overwrite an accepted model; increment `N`.
- **Commit** the final accepted model (it is small) and its `config.json`, plus `results/summary/*.csv` and `results/figures/*.png` used in the report.
- Do **not** commit: videos, frames/datasets, model files > 50 MB, `results/raw/`, `prediction/data/raw/`, `vision/data/`, `SUMO/scenarios/*/seed_*/` (regenerable from the committed generator), `.env`, `__pycache__`, TensorBoard logs, virtual environments. Set these in `.gitignore` in T0.2.
- No secrets in the repo. Add `.gitattributes` with `* text=auto` (Windows/Linux line endings).

### 0.5 Git workflow (single owner — this is the only branch/merge rule in this document)
- **Branches:** `main` is always the last state the human merged. Work happens on **one branch per phase**, `agent/phase-<N>-<short-name>`, created by the agent from `main` at the start of that phase's first task (Phase 0: before T0.1 writes `docs/PROJECT_FACTS.md`). Phases run strictly one after another — **no parallel branches**, including Phases 4 and 5 (finish and merge one before starting the other). The agent **never commits to `main`**.
- **Commits:** one per task on the phase branch, `T<id>: <imperative summary>`. A fix to earlier-phase code found later is made on the current phase branch as `T<id>-fix: …` and mentioned in the report (no branching back).
- **Phase start:** `git status` clean → `git switch main` → check `git log --oneline -5` shows the previous phase's merge (Phase 0: the human's initial docs commit) → `git switch -c agent/phase-<N>-<short-name>`. Nobody else pushes, so **no rebase and no pull are needed**; if `git fetch` shows `origin/main` differs from local `main` unexpectedly → stop and ask (0.6).
- **Phase end:** the agent reports "phase branch ready" with the commit list and stops. The **human** merges: `git switch main && git merge --no-ff agent/phase-<N>-<short-name>` then `git push origin main`, and replies "merged". The agent does not start the next phase until the merge is visible in `git log main`.
- Pushing a phase branch to `origin` for backup is allowed. Never force-push; never delete branches (the human decides). The release tag is created on `main` after the final merge (T6.4).

### 0.6 Stop-and-ask conditions
Stop and ask the human (do not guess) if: a needed tool is missing (SUMO, `duarouter`, compatible Python, SUMO-GUI display) and cannot be installed from official sources; dependency installation fails on the active Python; a protected file (Section 0.3) would need to change; acceptance criteria conflict; a measured result looks wrong (RL much worse than fixed-time, > 5% teleports, identical metrics across controllers); a time budget in this roadmap would be exceeded; the selected junction turns out unsuitable (T0.3); a Section 2 pending decision would materially change the project; the intended-TLS count exceeds `network.max_intended`, the network simulation is too slow for the staged budget (T7.1/T7.6), the shared network PPO cannot cover **all** intended TLS within budget (P5), or the human's working tree has uncommitted changes you did not make.

### 0.7 Code quality
- Python version: **whatever T0.1/T0.2 verify as the working interpreter** (project minimum 3.10). Never assume the global Python is the project's Python; use a project virtual environment and record `python --version` and the interpreter path in `docs/PROJECT_FACTS.md`.
- PEP 8, type hints and docstrings on public functions.
- **`ruff check .` and `pytest` cover the whole repository.** Exclusions are allowed only when justified: each excluded path or rule needs a one-line reason in a comment in `pyproject.toml` **and** an entry in `docs/lint_exclusions.md`. Never add a blanket ignore to make a failure disappear; prefer fixing the code.
- Logic modules get pytest unit tests in `tests/`. Tests that need SUMO are marked `@pytest.mark.sumo` and run with `pytest -m sumo`; the default `pytest` run excludes them (`addopts = -m "not sumo"`). Use `pytest-timeout` on SUMO tests.
- No hard-coded absolute paths: use `config/stms.yaml` + `pathlib`. Must work on **Windows and Ubuntu** (no `pgrep`, no bash-only scripts; Python CLIs only). `Ai/`, `scripts/`, `prediction/`, `vision/` have `__init__.py` and the project is installed with `pip install -e .` so `python -m Ai.common.run_episode` works from any directory.
- **All randomness via explicit `seed`.** Same seed + config ⇒ same result. Record seeds in every output.
- SUMO connections: unique label and free port (`sumolib.miscutils.getFreeSocketPort()`), closed in `finally`. Zombie check = `python scripts/check_zombies.py` (uses `psutil`; exits non-zero if `sumo`/`sumo-gui` processes remain).
- Logging via `logging`, not bare `print`, except CLI summaries.

### 0.8 Long-running jobs (training, evaluation, data collection)
The agent's command tool may time out or be interrupted, and the laptop may sleep. Therefore:
- Launch anything expected to take > 10 minutes as a **detached background process** writing to a log file under `results/` (on Windows, e.g. `Start-Process python -ArgumentList ... -RedirectStandardOutput ...`), then poll the log and the output folder.
- Every long job must be **resumable** (checkpoints / skip-existing run folders) and must print progress with an ETA.
- Before starting a long job, tell the human the expected duration (from measured speed) and remind them: plug in the charger, set the power plan so the laptop does not sleep, keep the lid open, and (for SUMO-GUI capture) do not lock the screen.

### 0.9 Single-owner workflow
- Exactly **one agent** edits the repo at a time; no parallel branches, no overlapping edits, no second agent session running at the same time.
- The human reviews between tasks and performs the single merge step into `main` between phases (Section 0.5); the human commits or edits files only **between** tasks, never during one. If `git status` shows changes the agent did not make, stop and ask (0.6).

---

## 1. Target repository layout

```
smart-traffic-management-system/
├── AGENTS.md                      # short rules + pointer to this roadmap (T0.2)
├── README.md  requirements.txt  requirements-vision.txt  requirements-dev.txt
├── pyproject.toml  .gitignore  .gitattributes  .env.example
├── config/stms.yaml               # ALL constants (Section 3)
├── SUMO/
│   ├── No_Polygon_Map/osm.sumocfg # EXISTING — do not modify
│   ├── derived/                   # derived static-TLS copy, gui settings (only if needed)
│   └── scenarios/<scenario>/      # sumocfg + cached routes per seed
├── Ai/
│   ├── common/                    # config, sumo_client, junction, traffic_state, network_state, metrics, run_episode
│   ├── controllers/               # base, fixed_time, rule_based, rl_controller, network, rl_network_controller, fallback, safety, registry
│   ├── rl/                        # traffic_env, network_vec_env, train_ppo, train_ppo_network, evaluate_ppo, models/
│   └── evaluation/                # evaluate.py, charts
├── prediction/                    # collect, dataset, train, evaluate, predict
├── vision/                        # virtual camera, auto-labelling, YOLO, counting, accuracy
├── results/{raw,summary,figures,vision}/
└── docs/   scripts/   tests/
```
(Pre-existing folders such as `Ai/analytics/` stay where they are.)

---

## 2. Design decisions

| ID | Decision | Value |
|---|---|---|
| DEC-01 | **Headline metric for the 10% claim (PROVISIONAL)** | **Metric B** = average travel time of trips whose **planned route actually uses a movement controlled by the junction's traffic light**, i.e. the route contains a consecutive edge pair `from_edge→to_edge` that is a TLS-controlled connection (the list of controlled movements comes from T0.3). Merely having an incoming edge in the route is **not** enough (e.g. a route that starts or ends on the incoming edge without continuing through the junction is excluded). Membership is decided from the route file, so it is identical for every controller. **Metric A** = all trips in the network, always computed and shown next to B. Evaluation scenarios: `balanced, directional_ns, directional_ew, low, medium, heavy, rush_hour`. **Aggregation (documented in `docs/metrics.md` and `docs/results.md`):** per (scenario, seed) improvement % on the common-trip set → mean over seeds per scenario → **headline = unweighted mean over the six non-`low` scenarios**. The **primary findings** `medium`, `heavy`, `rush_hour` are always shown prominently, separately and in the same table. `low` is reported as its own row and is **never** part of the headline mean and never replaces the primary findings. A pooled-trips aggregation is reported as a sensitivity check. Aim for ≥ 30% of trips through the controlled junction in every scenario designed to evaluate it. **Survivorship-bias rule:** the primary comparison keeps the completed **common-trip** set (trips completed under all three controllers), but every table reports beside it the **censored** average travel time (all scheduled trips in scope; unfinished trips counted up to the end of the run) and the **completion rate** per controller, so a controller that merely finishes fewer hard trips cannot look better unnoticed. The 10% reduction is a target, not an assumed result. Until the supervisor confirms the metric, every document must call it "provisional". |
| DEC-02 | Baseline | Our `FixedTimeController` (30 s green, 3 s yellow) through the safety layer (FR-CTL-01). SUMO's native program is recorded only as a sanity reference. |
| DEC-03 | RL action space | `Discrete(4)` = {0 keep, 1 switch to next green phase, 2 hold longer (+5 s), 3 hold longer (+10 s)} per SRS 4.6.2. One env step = `decision_interval_s` sim-seconds (+5/+10 s extra for actions 2/3) — **M1 single-junction env only**. In the network env (T7.5) all junctions share one simulation clock, so actions 2/3 become hold-lockouts, not extra sim time (DEC-14). |
| DEC-04 | Database / API / dashboard | **Deferred.** All persistence is CSV/JSON files under `results/`. |
| DEC-05 | Approaches | The selected TLS id is a `cluster…` id, i.e. SUMO may have **joined several nodes into one signal**, so it may not have four compass approaches. T0.3 groups incoming lanes by incoming edge and names them by bearing (N/E/S/W where unambiguous, else `A1..An`). Code always reads approaches from `config/stms.yaml`. |
| DEC-06 | Prediction ↔ RL | Separate (FR-PRD-05 optional/deferred). |
| DEC-07 | Vehicle types | **Cars only** (SUMO `passenger`). Mix stays configurable; default 100% car. |
| DEC-08 | Vision approach | **Virtual camera**: top-down SUMO-GUI frames of the controlled junction → OpenCV + YOLO. Try pretrained YOLO first; fine-tune on auto-labelled frames if the accuracy gate fails (T5.2/T5.3). Ground truth comes free from TraCI. YOLO is **never** inside the RL training loop (SRS 2.5). |
| DEC-09 | Seed blocks (never mix) | RL train **1000–1999** (only a cached pool of them is used, T0.4) · prediction data **2000–2029** (full profile, or the explicit reduced subset defined in T4.1) · RL validation **3000–3009** (also used to tune the rule-based controller) · development evaluation **5000–5004** · **final evaluation 6000–6004** (run once, T3.2) · vision frames **7000–7013** · demos **8000–8009**. The same numeric blocks are reused for the **network scenario family** (`net_*`), which are different scenarios from the single-junction family; the M1 final run (T3.2) and the M2 final run (T7.9) are each run **once** on their own family, and no tuning ever touches 5000+/6000+ in either family. |
| DEC-10 | Training budget | **Measured, staged, justified by validation** (T2.3 for M1, T7.6 for M2): smoke → pilot → main. Longer runs only if validation results justify it. |
| DEC-11 | Python/dependencies | Verify the active interpreter and package compatibility first (T0.1/T0.2). The project may use a Python 3.14 install, but heavy packages (`torch`, `ultralytics`, `opencv-python`) may not have wheels for every Python release. If installation fails, **stop and ask** — the likely fix is a project venv on a version that works (e.g. 3.11/3.12), installed by the human. |
| DEC-12 | **Milestones and headline metrics** | **M1** (Phases 0–3): one pilot junction, headline = Metric B (DEC-01). **M2** (Phase 7, final): all intended TLS, evaluated on the **network scenario family** `net_balanced, net_low, net_medium, net_heavy, net_rush_hour`. **M2 headline = Metric N** = average travel time of **all trips** in the network (completed common-trip set, with censored travel time and completion rates beside it, same survivorship rule as DEC-01). Aggregation: per (scenario, seed) improvement % → mean over seeds per scenario → **headline = unweighted mean over the four non-`low` scenarios** (`net_balanced, net_medium, net_heavy, net_rush_hour`); **primary findings** `net_medium, net_heavy, net_rush_hour` shown separately in the same table; `net_low` its own row, never in the headline; pooled-trips sensitivity row. Also reported network-wide: time loss, waiting, speed, throughput, completion rate, teleports, mean and worst-junction queue, congestion share, and a per-junction table. The 10% is a target, not an assumed result; provisional until P1. **M1 numbers are never presented as the final result.** |
| DEC-13 | Intended TLS set | **All TLS that pass the T7.1 suitability check** (≥ 2 verified conflict-free green phases, static or convertible to a static copy of the same phases, non-trivial traffic). Excluded TLS are listed with reasons and stay on SUMO's native program **identically for every controller**. The list is human-approved (P4) and **frozen before the first T7.8 dev evaluation**; it is never edited after seeing results. If the count exceeds `network.max_intended` (default 20) → stop and ask: any cap (e.g. top-K by traffic) is an explicit, documented human decision, never silent. |
| DEC-14 | Network AI architecture and staged ladder | Decentralised **shared-policy PPO** (parameter sharing): one policy, per-junction local observation padded to `network.max_approaches` with a mask, per-junction reward (optional small network-wide term), actions applied at **every** intended TLS through its own safety layer. Built as a custom SB3 `VecEnv` whose slots are the junctions of one shared SUMO simulation (no extra dependencies). **Ladder:** *Stage 0* network fixed-time + rule-based validated on all intended TLS (always; baselines). *Stage 1* smoke → pilot. *Stage 2* main shared PPO, full coverage. *Stage 3* cost reductions that **keep coverage of all intended TLS** (fewer training scenarios, shorter episodes, larger decision interval, early stop on validation, one PPO seed). *Stage 4 — fallback only with the human's explicit decision (P5):* partial-AI hybrid (PPO only at junctions that pass a per-junction non-regression gate, rule-based elsewhere) or a validated multi-junction rule-based controller plus M1 PPO; labelled as such with the AI-coverage fraction reported. Single-junction PPO is never silently declared the final result. **Full-AI definition:** a junction counts as AI-controlled only if PPO supplied the executed decision at ≥ `eval.ai_coverage_min_share` of its decision ticks (T7.7); the final deliverable may be called *full network-wide AI control* only if **every** TLS on the approved intended list is AI-controlled — otherwise it is labelled *partial* with the coverage fraction. |

### Pending human / supervisor decisions (agent never decides these)
| # | Decision | Status |
|---|---|---|
| P1 | Supervisor confirms the **headline metric** (DEC-01 for M1: junction trips; DEC-12 for M2: network-wide all-trips; each with censored/completion beside it) | Pending — results stay "provisional" until confirmed |
| P2 | Supervisor acknowledges the **SRS deviations** in Section A (dashboard/backend/DB deferred, simulated camera, cars only) | Pending |
| P3 | Final choice of the **M1 pilot junction** if T0.3 finds the preselected TLS unsuitable | Only if triggered |
| P4 | Human approves the **intended TLS list** and exclusions (T7.1, DEC-13) before it is frozen | Pending until T7.1 |
| P5 | Human decides how to proceed if shared PPO cannot cover **all** intended TLS within budget or gate (DEC-14 Stage 4) | Only if triggered |

---

## 3. Constants (`config/stms.yaml`, created in T0.2)

| Key | Default | Notes |
|---|---|---|
| `sumo.config` | `SUMO/No_Polygon_Map/osm.sumocfg` | existing — verify in T0.1 |
| `sumo.tls_id` | `cluster618250255_7478115627_cluster_11927462278_11927462280_7479633881` | the **M1 pilot junction**; selected during inspection, **not proven busiest — verify in T0.3** |
| `sumo.step_length` | `1.0` s | |
| `sumo.horizon_s` / `max_sim_s` | `3600` / `7200` | demand window / hard cap |
| `sumo.time_to_teleport_s` | SUMO default (300) | keep identical for all controllers; teleports are counted |
| `signal.min_green_s` / `max_green_s` / `yellow_s` / `all_red_s` | `10` / `60` / `3` / `0` | FR-CTL-06, §5.2; yellow/phase structure is verified against the real program in T0.3 |
| `fixed.green_s` | `30` | FR-CTL-01 |
| `rl.decision_interval_s` / `episode_s` | `5` / `3600` | |
| `rl.reward_weights` | `{queue: 1.0, wait: 1.0, throughput: 0.5}` | tune in T2.5 |
| `rl.device` | `cpu` | PPO with an MLP policy is normally faster on CPU |
| `rule.queue_threshold` / `wait_threshold_s` | `8` / `45` | tune on validation seeds in T1.3 |
| `congestion.thresholds` | Low <5, Medium 5–12, High >12 halting vehicles/approach | FR-STA-02 |
| `demand.vehicle_mix` | `{passenger: 1.0}` | DEC-07 |
| `demand.junction_share_min` | `0.30` | DEC-01 |
| `demand.train_pool` | `{scenarios: all 7, seeds_per_scenario: 20}` taken from 1000–1999 | cached before training (T0.4) |
| `eval.scenarios_headline` | `[balanced, directional_ns, directional_ew, medium, heavy, rush_hour]` | DEC-01 |
| `eval.scenarios_primary` | `[medium, heavy, rush_hour]` | always shown separately |
| `eval.scenarios_separate` | `[low]` | never in the headline |
| `eval.dev_seeds` / `eval.final_seeds` | `[5000..5004]` / `[6000..6004]` | DEC-09; used per scenario family (single for M1, network for M2), each final block run once |
| `eval.target_reduction_pct` | `10.0` | target, not result |
| `eval.ai_coverage_min_share` | `0.95` | share of decision ticks at a junction in which PPO (not the fallback) supplied the action for it to count as AI-controlled (DEC-14) |
| `eval.completion_gap_flag_pp` | `2.0` | if a controller's junction completion rate differs from fixed-time by more than this many percentage points, the common-trip result is flagged as possibly survivorship-biased in `docs/results.md` |
| `prediction.split.full` | train `2000–2019`, val `2020–2024`, test `2025–2029` | single source of truth, T4.1 |
| `prediction.split.reduced` | train `2000–2011`, val `2020–2023`, test `2025–2028` | subset of full; used only if compute forces it (T4.1) |
| `network.controlled_tls` / `network.excluded_tls` | filled by T7.1, frozen (DEC-13) | per TLS: id, approaches, green phases, `yellow_after`, movements; excluded with reason |
| `network.max_intended` | `20` | above this → stop and ask |
| `network.min_veh_per_1800s` | `20` | suitability traffic floor (native program, T7.1); human may change |
| `network.max_approaches` / `max_phases` | measured in T7.1 | observation padding |
| `network.scenarios` | `[net_balanced, net_low, net_medium, net_heavy, net_rush_hour]` | DEC-12 |
| `network.headline_scenarios` / `primary_scenarios` / `separate_scenarios` | `[net_balanced, net_medium, net_heavy, net_rush_hour]` / `[net_medium, net_heavy, net_rush_hour]` / `[net_low]` | DEC-12 |
| `network.min_controlled_trip_share` | `0.5` | share of trips using ≥ 1 controlled movement; below → stop and ask (T7.3) |
| `demand.net_train_pool` | 5 net scenarios × 20 seeds from 1000–1999 | cached before training (T7.3) |
| `rl_net.decision_interval_s` / `episode_s` / `device` | `5` / `3600` / `cpu` | start from M1's validated reward weights; `rl_net.network_term_weight` default `0.0` |
| `rl_net.max_train_hours` | `10` | default cap; human may lower |
| `rl_net.validation_pairs` / `validation_every_timesteps` | `[(net_medium,3000),(net_heavy,3001),(net_rush_hour,3002)]` / `20000` | custom validation callback (T7.6) |
| `intersection.approaches` / `intersection.green_phases` / `intersection.yellow_after` | filled by T0.3 | M1 pilot junction; also present as one entry in `network.controlled_tls` after T7.1 |
| `intersection.movements` | filled by T0.3 | TLS-controlled `from_edge→to_edge` movements; used for junction-trip membership |
| `logging.step_log_every_s` | `5` | keeps `steps.csv` small |
| `vision.*` | frame size 1280×720, capture every 5 sim-s, confidence 0.25, recall gate 0.85, max frames budget (T5.1) | T5.* |
| `metrics_version` | `1` | bump when definitions change |

---

# PHASE 0 — Foundation and scenarios
Branch: `agent/phase-0-foundation`

> Phases 0–3 build and validate everything on the one **M1 pilot junction**. Write every module parametrised by `tls_id` / approach config with **no hidden single-junction assumptions** (one `SignalSafetyLayer` per TLS, one `IntersectionState` per TLS), because Phase 7 instantiates them for every intended junction.

### T0.1 — Repository and environment audit (no behaviour changes)
- **Depends on:** nothing
- **Do:** detect and record, never guess:
  1. Repo tree (depth 3), `git status`, `git log --oneline -15`, current branch, remote.
  2. **Machine:** OS and version, CPU model + physical/logical cores, **RAM**, **free disk space**, **GPU** (`nvidia-smi` or "none detected"), power plan. (Windows: PowerShell `Get-CimInstance Win32_Processor/Win32_ComputerSystem/Win32_VideoController`, or `python -c "import os, platform"`.) Known but unverified: HP EliteBook 840 G7, Intel i7 10th gen.
  3. **Python:** the *active* interpreter path and version, every other Python on the machine (`py -0`), whether a venv is active, `pip freeze`. For each planned dependency (Section T0.2 lists) state: installed? version? importable?
  4. **SUMO:** `sumo --version` (previously noted as 1.27.1 — unverified; record what is detected), `SUMO_HOME`, `duarouter`/`netconvert` on PATH, `sumo-gui` present? `python -c "import traci, sumolib"` and their versions vs SUMO.
  5. `SUMO/No_Polygon_Map/osm.sumocfg`: list referenced net/route/additional files, whether each exists, net size (edges, junctions, traffic lights), declared simulation begin/end.
  6. **Existing code inventory:** every `.py` file under `Ai/`, `scripts/`, tests, and any inspection/test scripts; current `requirements.txt` — flag **database/web packages** (`sqlalchemy`, `psycopg2`, `fastapi`, `uvicorn`, `supabase`, `alembic`, …) and `git grep` whether any code imports them.
  7. **Test what exists** (time-box 30 min): run the existing inspection/test scripts and the existing baseline script for 3,600 steps. Compare with the previously recorded result (4,408 recorded trips / 3,323 completed / 1,085 unfinished / ~299 s mean travel time, under the old script's definition) and say whether it reproduced. Read `Ai/rl/*.py` and summarise the env (observation, actions, reward, step duration). Try loading `Ai/rl/models/ppo_traffic.zip` and running one short episode. Classify each item **working / broken / unverified** with evidence.
  8. **Measure SUMO speed:** run the existing config headless for 600 sim-s; record real seconds → sim-seconds per real second (NFR-PRF-05 needs ≥ 5×). Record SUMO warnings.
  9. Briefly list what `Ai/analytics/` contains and whether it lints/tests cleanly (no edits yet).
- **Files:** create `docs/PROJECT_FACTS.md` only (sections: Machine, Python, SUMO, Network, Repo state, Existing-code classification, Measured speed, Missing / needs human).
- **Accept:** file exists with all sections; unknown values say "not detected"; missing tools listed under "Missing / needs human". If Python/dependency compatibility already looks impossible → stop and ask (DEC-11).

### T0.2 — Skeleton, config, tooling
- **Depends on:** T0.1
- **Do:**
  - Create the folders in Section 1 (only those), `__init__.py` files, `.gitignore`, `.gitattributes`, `.env.example`.
  - **Dependencies (corrected):** split into three files.
    - `requirements.txt` (core): `traci`, `sumolib`, `numpy`, `pandas`, `matplotlib`, `pyyaml`, `gymnasium`, `stable-baselines3`, `torch`, `tensorboard`, `scikit-learn`, `joblib`, `psutil`. Prefer `traci`/`sumolib` versions matching the installed SUMO.
    - `requirements-vision.txt`: `opencv-python`, `ultralytics` (installed only when Phase 5 starts, so a vision-package incompatibility cannot block Phases 0–4). If no GPU is detected, install the CPU build of PyTorch.
    - `requirements-dev.txt`: `pytest`, `pytest-cov`, `pytest-timeout`, `ruff`.
    - **Remove** every unused database/web package found in T0.1 (e.g. `sqlalchemy`, `psycopg2`, `fastapi`, `uvicorn`, `supabase`, …). Keep one only if an in-scope component imports it, and write the reason in `docs/PROJECT_FACTS.md`.
    - After a successful install, write `requirements.lock.txt` (`pip freeze`) so versions are the ones actually tested. Do **not** pin versions you did not install.
  - `pyproject.toml`: package metadata so `pip install -e .` works; ruff (line-length 100; **no exclusions yet** — add only per Section 0.7); pytest (`testpaths=["tests"]`, marker `sumo`, `addopts = -m "not sumo"`, timeout).
  - If existing code (including `Ai/analytics/`) fails `ruff`/`pytest`: fix it, or add a justified exclusion per Section 0.7. Never silently skip.
  - `config/stms.yaml` from Section 3; `Ai/common/config.py` typed loader; `scripts/check_zombies.py`.
  - `AGENTS.md`: **short** (≤ 40 lines): "Read `docs/STMS_Agent_Roadmap_FINAL.md` Section 0 in full before any task; one task at a time; real outputs only; ask when blocked", plus the three most critical rules (never modify `SUMO/No_Polygon_Map`, never touch seeds 5000+/6000+ for tuning, never invent results). Do **not** duplicate the whole of Section 0 (avoids drift). No `GEMINI.md`.
  - Create empty `docs/experiment_log.md` and `docs/lint_exclusions.md`.
- **Accept:**
  ```
  pip install -e . -r requirements.txt -r requirements-dev.txt
  ruff check .
  pytest -q
  python -c "from Ai.common.config import load_config; print(load_config()['sumo']['tls_id'])"
  python scripts/check_zombies.py
  ```
  (`requirements-vision.txt` is deferred to T5.1.) If `torch`/`stable-baselines3` will not install → **stop and ask** (DEC-11).

### T0.3 — SUMO client, traffic-light inspection and junction suitability
- **Depends on:** T0.2 · **SRS:** FR-SEN-01/05, FR-SIM-02/06/07
- **Do:**
  1. `Ai/common/sumo_client.py`: `SumoClient` context manager (headless/GUI flag, `--seed`, free port, label, `step()`, `close()` in `finally`; clear error + safe stop on TraCI loss; **refuse to start** if net/route files are missing/invalid).
  2. `scripts/inspect_tls.py`: run 600 s headless; for the selected TLS dump: **program type (static / actuated / other)**, program id, every phase index with duration + state string, controlled links, **the distinct TLS-controlled movements (`from_edge→to_edge`, with link indices)**, incoming lanes grouped by edge, bearing of each incoming edge, lane counts, **whether the TLS is a joined cluster of several nodes**, junction centre coordinates and bounding box (needed by vision). Classify phases as green vs yellow from their state strings; **never assume 0/2/4 vs 1/3/5**. Check that no green phase gives simultaneous green to conflicting (foe) movements, using SUMO's junction foe/request information or a documented manual review.
  3. **Junction suitability check (the TLS was selected during inspection, not proven busiest):** run the existing demand with SUMO's native program for ≥ 1800 s, count vehicles passing each traffic light, and report the selected TLS's rank among all TLS (keep this per-TLS table in `docs/tls_inspection.md`; T7.1 reuses it). Also report approach count, number of green phases, distance to the map edge. **If it has < 3 approaches, < 2 green phases, or is clearly low-traffic (e.g. below the median TLS) → stop and ask the human** (pending decision P3). Never switch junctions silently.
  4. If the program is **actuated** (or otherwise unsafe to hold/extend), create a **static copy of the same phases** under `SUMO/derived/` and reference it from scenario sumocfgs (never edit the original net). Document this.
  5. Write approaches to `config/stms.yaml` → `intersection.approaches` (`{name, lanes[], incoming_edge, bearing}`) and `intersection.green_phases` / `yellow_after`, and the controlled movements to `intersection.movements`. Implement `Ai/common/junction.py` (`controlled_movements(net, tls_id)`, `route_uses_controlled_movement(route_edges, movements)`); this is the **only** definition of junction-trip membership, shared by T0.4 and T1.4.
  6. Record SUMO warnings/teleports in the 600 s run.
- **Files:** `Ai/common/sumo_client.py`, `Ai/common/junction.py`, `scripts/inspect_tls.py`, `docs/tls_inspection.md`, `tests/test_sumo_client.py`, `tests/test_junction.py`.
- **Accept:**
  ```
  python scripts/inspect_tls.py
  pytest -m sumo tests/test_sumo_client.py
  pytest -q tests/test_junction.py     # hand-built routes: uses a controlled movement / only touches the incoming edge / ends on it
  python scripts/check_zombies.py
  ```
  `docs/tls_inspection.md` lists the **real** phases/states, the controlled movements, the suitability ranking and the foe check; config approaches and movements match it. **T1.2 may not start until this is accepted.**

### T0.4 — Scenario and demand generation (reproducible, cached)
- **Depends on:** T0.3 · **SRS:** FR-SIM-03/04/05
- **Do:** `scripts/make_scenarios.py` generating, per scenario, a `.sumocfg` (pointing at the existing net / derived static TLS, never editing them) and **cached route files per seed** at `SUMO/scenarios/<scenario>/seed_<seed>/routes.rou.xml` plus a small `manifest.json` (config hash of net + demand parameters + generator version). Expose `ensure_routes(scenario, seed) -> Path`: reuse if the manifest hash matches, regenerate if missing/stale. **Training must never wait on demand generation:** a CLI flag `--train-pool` pre-generates the whole training pool (`demand.train_pool`: 7 scenarios × 20 seeds from 1000–1999), and the RL environment draws **only from that cached pool** and fails fast if a file is missing instead of generating during training.
  - Scenarios: `balanced, directional_ns, directional_ew, low, medium, heavy, rush_hour`.
  - **Routing method (explicit and seeded):** using `sumolib`, sample origin/destination edge pairs with a seeded RNG over **sorted** edge lists; compute shortest paths; classify pairs whose path **uses a controlled movement** (`Ai/common/junction.py`, not merely an incoming edge); draw `junction_share` of trips from through-junction pairs, the rest from the others; for `directional_*` bias origins to the matching approach bearing; `rush_hour` ramps the insertion rate. Write trips, run `duarouter`. Vehicle type from `demand.vehicle_mix` (cars only by default). Routes are fixed per file (no rerouting during the run), so "route uses a controlled movement" is controller-independent.
  - **Measure** per scenario with SUMO's native program (fixed-time controller does not exist yet): total trips, fraction through the junction, completion rate by `max_sim_s`, teleports, insertion-backlog size. Tune insertion rates so that every scenario designed to evaluate the junction has junction-share ≥ 30% (document `low` honestly if it cannot), and `medium`/`heavy`/`rush_hour` are congested but not gridlocked (teleports < 1% of trips).
- **Files:** `scripts/make_scenarios.py`, `docs/scenarios.md` (measured table), `tests/test_scenarios.py`.
- **Accept:**
  ```
  python scripts/make_scenarios.py --seed 1000 --all
  python scripts/make_scenarios.py --seed 1000 --all --force   # byte-identical route files
  python scripts/make_scenarios.py --train-pool
  pytest -q tests/test_scenarios.py
  ```
  If junction-share < 30% for `medium`/`heavy`/`rush_hour` → **stop and ask**. The "teleports < 1% under fixed-time" re-check is done in T1.4.

---

# PHASE 1 — Core: Traffic State, safety layer, controllers, metrics
Branch: `agent/phase-1-core`

### T1.1 — Traffic State module
- **Depends on:** T0.4 · **SRS:** FR-STA-01..05, FR-SEN-02/03
- **Do:** `Ai/common/traffic_state.py`: dataclasses `ApproachState(name, vehicle_count, halting, mean_speed, waiting_time, queue_length, congestion, available_fields)` and `IntersectionState(timestamp_utc, sim_time, intersection_id, approaches, phase, phase_elapsed_s, mode, totals{waiting_vehicles, avg_wait, throughput_veh_min}, source)` with `source ∈ {"sumo","camera"}`; `SumoSensorReader(tls_config).read(client)` (`tls_config` = `intersection` for M1, or one entry of `network.controlled_tls`) using lane-level TraCI calls aggregated per config approach; `congestion_level(halting, thresholds)`; `to_dict()` (ISO-8601 UTC, JSON-serialisable); `to_vector(state, norm)` → fixed-length numpy vector clipped to [0,1], length computed from config. Unavailable fields (e.g. a camera cannot give waiting time) are `None` and listed in `available_fields`.
- **Accept:**
  ```
  pytest -q tests/test_traffic_state.py            # thresholds, normalisation bounds, None handling, JSON round-trip
  pytest -m sumo tests/test_traffic_state_sumo.py  # 60 s live read: finite values, lengths match config
  ```

### T1.2 — Signal safety layer
- **Depends on:** T1.1, **and T0.3 accepted** · **SRS:** FR-CTL-06, §5.2
- **Do:** `Ai/controllers/safety.py` — `SignalSafetyLayer(client, tls_config)` (one instance per TLS; `tls_config` carries the TLS id, verified phases and `yellow_after`) is the **only** component allowed to call `traci.trafficlight.setPhase/setPhaseDuration/setProgram/setRedYellowGreenState`. Methods: `request_switch()` (next green via the program's own yellow [+ all-red], only if `elapsed_green ≥ min_green`, else `Rejected(reason)`); `request_extend(seconds)` (capped by `max_green`); `tick()` (bookkeeping each step; **forces a switch at `max_green`**; completes yellow/all-red); `request_green_for_approach(name)` (clearance first; rejects if no verified phase serves it — kept for future emergency/manual use). Only phase indices of the **verified conflict-free program from T0.3** (plus all-red) are ever applied. Every call returns `Accepted | Rejected(reason)`.
- **Accept:** `pytest -m sumo tests/test_safety.py` — over 1200 s with a random-command fuzzer prove: (a) no green→green without yellow, (b) no phase < `min_green` unless cleared, (c) no phase > `max_green`, (d) every applied state is in the verified set, (e) rejections carry a reason.

### T1.3 — Controllers, fallback, episode runner
- **Depends on:** T1.2 · **SRS:** FR-CTL-01/02/07/08, §5.2 fallback
- **Do:** `Ai/controllers/base.py` (`Controller.decide(state) -> Action`, `reset()`); `fixed_time.py` (30 s/3 s, cycles the verified greens); `rule_based.py` (extend while current-approach queue/wait above thresholds and < `max_green`; switch when current queue is small and another approach exceeds thresholds; uses only `IntersectionState`); `fallback.py` (`FallbackController` wraps any controller; on exception/timeout/invalid output → fixed-time, logs a warning, sets `fallback_active`); `registry.py` → `get_controller("fixed"|"rule"|"rl")`; `Ai/common/run_episode.py::run_episode(controller, scenario, seed, out_dir, gui=False)` closed loop (observe → decide → safety → step) writing step/trip logs (Section 11). The CLI has `--family {single,network}`, default `single` (the network family is added in T7.2).
- **Rule tuning protocol:** try ≥ 3 threshold settings on the **validation seeds 3000–3002** (never 5000+/6000+), keep the best, record every setting and result in `docs/rule_tuning.md`. This gives the rule-based controller a tuning effort comparable to RL.
- **Accept:**
  ```
  pytest -q tests/test_controllers.py
  python -m Ai.common.run_episode --controller fixed --scenario medium --seed 3000
  python -m Ai.common.run_episode --controller rule  --scenario medium --seed 3000
  ```
  Fixed run shows greens of 30 s ± 1 step (verify from `steps.csv`).

### T1.4 — Metrics
- **Depends on:** T1.3 · **SRS:** FR-SEN-04, FR-EVL-02, DEC-01
- **Do:** `Ai/common/metrics.py` + `docs/metrics.md` (definitions, units, aggregation method of DEC-01). Collect from `--tripinfo-output` (consider `--tripinfo-output.write-unfinished`) **and** TraCI tracking (vehicles that never arrive).
  - **Trip time = `depart_delay + duration`** (time from scheduled departure to arrival), so vehicles stuck in SUMO's insertion backlog are not hidden. Also record `depart_delay` separately.
  - **Junction membership (metric B)** = `route_through_junction`: the planned route contains at least one TLS-controlled movement (`from_edge→to_edge`), evaluated with `Ai/common/junction.py` on the route file; `first_controlled_movement` records which one. It is fixed by the route file, so it is the same for every controller (no selection bias). `passed_controlled_junction` (actually crossed it during the run) is recorded separately and used for throughput only.
  - Per run: **completion rate (all trips and junction trips)**, avg travel time (completed), **censored** travel time (unfinished = `end_time − scheduled_depart`), both also restricted to junction trips (metric B), avg waiting, avg time loss, avg depart delay, avg queue (halting at junction), avg speed, throughput (veh/min through junction), **fraction of time the junction is at High congestion** (FR-EVL-02 congestion level), completed/unfinished, teleports. A run continues until all vehicles arrive or `max_sim_s`.
  - **Cross-check:** in the fixed-time run, every *completed* `route_through_junction` trip must have `passed_controlled_junction = true` (routes are fixed). Report mismatches; any unexplained mismatch → stop and ask.
  - Re-check here that the **fixed-time** controller on `medium`/`heavy`/`rush_hour` has teleports < 1% of trips; if not, **stop and ask** (T0.4 demand may need lowering).
- **Accept:**
  ```
  pytest -q tests/test_metrics.py      # tiny hand-built tripinfo → exact expected numbers incl. unfinished, depart delay, completion rates, junction membership (a route containing an incoming edge but no controlled movement is NOT a junction trip)
  python -m Ai.common.run_episode --controller fixed --scenario medium --seed 3000
  ```
  `summary.csv` has every Section 11 column; no NaN except documented. `docs/metrics.md` also explains how the old "4,408 trips / 3,323 completed / 1,085 unfinished / ~299 s" figure differs from the new definitions (explain; do not "fix" the old number). **Also record wall-clock seconds per run** for each controller/scenario: this feeds the compute budgets in T2.3, T3.1 and T4.1.

---

# PHASE 2 — RL environment and PPO
Branch: `agent/phase-2-rl`

> Gate: **do not train PPO for real until T2.1 and T2.2 pass.**

### T2.1 — Rebuild `Ai/rl/traffic_env.py`
- **Depends on:** T1.4 · **SRS:** FR-CTL-03/04/06, FR-STA-05
- **Do:** Gymnasium `TrafficEnvironment(scenario_pool, seeds, config)` using `SumoClient`, `SumoSensorReader`/`to_vector` and `SignalSafetyLayer` (**no direct phase manipulation in the env**). Observation `Box(0,1,(N,))` with N from config (per-approach count/halting/speed/wait + phase one-hot + normalised elapsed green); document the layout in the docstring. Action `Discrete(4)` (DEC-03); illegal actions become "keep" and are counted in `info["illegal_action"]`. Reward (configurable): `r = −w_q·Δ_norm_queue_total − w_w·norm_wait_total + w_t·norm_vehicles_passed`, all terms normalised; exact formula in `docs/rl_design.md`. `truncated=True` at `episode_s`; `reset(seed=…)` picks scenario deterministically **from the cached training pool** via `ensure_routes()` (no demand generation during training); `close()` idempotent and kills SUMO. `info` has `sim_time, phase, phase_elapsed, action_taken, illegal_action, queue_total, wait_total`.
- **Accept:** `ruff check Ai/rl` clean; `python -c "from Ai.rl.traffic_env import TrafficEnvironment"`.

### T2.2 — Environment tests (blocking gate)
- **Depends on:** T2.1
- **Do:** rewrite `Ai/rl/test_env.py` (mirror as `tests/test_env.py`): 1) `check_env` passes; 2) 3 random-policy episodes: no exception, no conflicting greens/skipped yellows, greens ≤ `max_green` and ≥ `min_green`; 3) scripted-policy sanity: "always keep" on a heavily loaded approach gets **lower cumulative reward** than a hand-written "switch when queue high" policy on the same seed (assert); 4) same seed twice ⇒ identical first 50 observations and rewards; 5) 5 reset/close cycles leave no zombie SUMO (`scripts/check_zombies.py`); 6) env refuses to run if a pool route file is missing (fail-fast).
- **Accept:** `pytest -m sumo tests/test_env.py -q` all green. **If (3) fails, fix reward/observation before anything else.**

### T2.3 — PPO training pipeline (staged, measured budget)
- **Depends on:** T2.2 · **SRS:** FR-CTL-05/09
- **Do:** rewrite `Ai/rl/train_ppo.py` (CLI: `--timesteps --seed --scenarios --reward-weights --out --resume`); random scenario/seed per episode from the cached pool of training seeds (1000–1999 block); `DummyVecEnv`; `Monitor`; TensorBoard; `training_log.csv` (episode, reward, mean wait, mean queue, illegal-action rate, action histogram); `EvalCallback` on validation seeds 3000–3009; periodic checkpoints; save `ppo_v<N>/{model.zip,config.json}`; `device=cpu`. Launch long runs per Section 0.8.
  - **Staged budget (DEC-10) — numbers are starting points, not promises; real throughput decides:**
    1. **Smoke:** 20,000 steps. Report measured steps/hour and sim-s/real-s.
    2. **Pilot:** ~50,000 steps (or whatever fits ≲ 2–3 h). Continue only if validation reward is moving the right way, or ask the human.
    3. **Main:** the largest count that fits the human's wall-clock limit (default **≤ 10 h** total; human may lower it), up to 300,000. A longer run than the pilot must be justified in the report by the pilot's validation curve.
    4. Projected total > 10 h even for 100,000 steps → **stop and ask**.
  - If time allows, train **≥ 2 PPO seeds** and report all of them; choose the model by **validation** results only (never by dev/final seeds).
  - Runs must be resumable (the laptop will sleep or be closed).
- **Accept:**
  ```
  python -m Ai.rl.train_ppo --timesteps 20000 --out Ai/rl/models/ppo_v2_smoke
  python -m Ai.rl.train_ppo --timesteps <staged budget> --out Ai/rl/models/ppo_v2
  ```
  Report the learning-curve file, measured training speed, and final validation mean reward. Never touch seeds 5000+ / 6000+.

### T2.4 — RL controller wrapper
- **Depends on:** T2.3 · **SRS:** NFR-PRF-01, FR-CTL-07/08
- **Do:** `Ai/controllers/rl_controller.py` (loads `model.zip`, state → vector → action; wrapped by `FallbackController`). Replace `Ai/rl/evaluate_ppo.py` with diagnostics: action histogram, phase-usage histogram, mean green per phase, forced max-green switches, illegal-action rate.
- **Accept:** `pytest -q tests/test_rl_controller.py` (median inference latency < 100 ms over 1000 calls on this machine; corrupt model path → fallback activates) and `python -m Ai.rl.evaluate_ppo --model Ai/rl/models/ppo_v2 --seed 3000`.

### T2.5 — RL sanity gate
- **Depends on:** T2.4
- **Do:** run fixed, rule, RL on `medium` and `heavy`, **validation seeds 3000–3002**; write `docs/rl_diagnostics.md` (table + diagnostics).
- **Pass:** RL uses ≥ 2 distinct actions, serves all green phases, forced-max-green switches < 30% of switches, **and** is not worse than fixed-time by > 5% on junction travel time.
- **If it fails**, iterate in this order, logging each attempt in `docs/experiment_log.md`: (1) reward weights/normalisation, (2) observation (add last action, per-approach wait), (3) decision interval, (4) PPO hyper-parameters (`ent_coef` 0.01–0.05, `n_steps`, `learning_rate`, `gamma`), (5) more timesteps (within the DEC-10 budget), (6) curriculum low→heavy. After 5 failed iterations → **stop and ask**. Never tune on seeds 5000+/6000+.

---

# PHASE 3 — Fair evaluation (single-junction milestone M1)
Branch: `agent/phase-3-evaluation`

### T3.1 — Evaluation harness
- **Depends on:** T2.5 · **SRS:** FR-EVL-01..07
- **Do:** `Ai/evaluation/evaluate.py`: for each `(scenario, seed)` generate routes once (`ensure_routes`) and run `fixed`, `rule`, `rl` on exactly that file and seed. Scenarios: all seven (`balanced, directional_ns, directional_ew, low, medium, heavy, rush_hour`); `--seed-set dev|final` selects `[5000..5004]` or `[6000..6004]`. Run folders are skip-if-complete so the job is resumable (Section 0.8). **Before launching, estimate total wall time** from T1.4's per-run timings (7 scenarios × 5 seeds × 3 controllers = 105 runs per seed set) and tell the human.
  - Aggregate to `results/summary/comparison.csv` (rows `milestone = M1`; mean ± std over seeds, plus a paired-bootstrap 95% CI of the per-seed improvement). **Improvement** = `(baseline − RL)/baseline × 100` (sign-correct for higher-is-better metrics), vs fixed and vs rule. Aggregation follows DEC-01 exactly: per-scenario rows, a headline row over the six non-`low` scenarios, a separate row for the primary findings (`medium, heavy, rush_hour`), a separate `low` row, and a pooled-trips sensitivity row.
  - **Primary travel-time comparison uses the common-trip set** (trips completed under all three controllers for that scenario+seed); **beside it, in the same table, always report** the censored travel time (all scheduled trips in scope, unfinished counted to the end of the run), completion rate per controller, completed/unfinished counts and the common-set size, so survivorship bias is visible. If a controller's junction completion rate differs from fixed-time by more than `eval.completion_gap_flag_pp`, flag the common-trip result as possibly survivorship-biased. Report **metric B (headline, provisional) and metric A**, plus waiting time, time loss, queue length, throughput, congestion, completed/unfinished and teleports.
  - `target_met` = mean RL improvement vs fixed on the headline metric ≥ `eval.target_reduction_pct`, else `false`. Printed per scope (A/B), per trip basis (common-trip and censored) and per aggregation; never forced. If the common-trip and censored results disagree on `target_met`, both are shown and the disagreement is stated.
  - Charts to `results/figures/*.png` (travel time [common-trip and censored], completion rate, waiting, queue, throughput, improvement-% per scenario, error bars; every chart labelled "simulated").
- **Accept:**
  ```
  python -m Ai.evaluation.evaluate --controllers fixed rule rl --seed-set dev
  pytest -q tests/test_evaluation.py   # synthetic inputs → exact improvement %, common-trip filter, censored time and completion rate, sign handling, low excluded from headline
  ```
  Re-running reproduces an identical `comparison.csv`.

### T3.2 — Results gate and honest reporting
- **Depends on:** T3.1
- **Do:** if the dev-seed headline improvement is < 10%: diagnose (per-scenario table, action/phase histograms), then try the remaining levers once each using **training/validation seeds only** (longer training within DEC-10, reward re-weighting, extra scenarios in the training mix); re-evaluate on dev seeds.
  - **Freeze before the final run:** commit the chosen model + `config.json`; record model sha256, config hash, git commit and the exact command in `docs/experiment_log.md`.
  - **Then run the final block once:** `python -m Ai.evaluation.evaluate --controllers fixed rule rl --seed-set final`. ("Once" = one completed run of the frozen configuration. If the process crashes, resuming the same run with identical config is allowed and must be noted. Re-running after changing anything is not.)
  - Use **only** that run for the headline in `docs/results.md`: tables mean ± std (+ CI), figures, `target_met` per metric and scope (A/B), per-scenario results, the `low` row separately, limitations (single junction, synthetic demand, simulation only, cars only, unfinished-trip handling, survivorship bias in the common-trip set), and the statement that the headline metric is **provisional until the supervisor confirms it (P1)**. Common-trip, censored and completion-rate results are presented side by side. Report **all** attempts including failed ones. Do **not** change seeds, scenarios or metric definitions after seeing results to reach 10%.
- `docs/results.md` **Part 1** is titled "M1 — single-junction milestone (not the final result)", states that the final deliverable is network-wide control (Phase 7), and makes no whole-map claim. `comparison.csv` rows carry `milestone = M1`.
- **Accept:** every number in `docs/results.md` equals `results/summary/comparison.csv` exactly (`tests/test_results_doc.py` parses and checks every part present).

---

# PHASE 7 — Network-wide control (M2, the final deliverable; runs right after Phase 3)
Branch: `agent/phase-7-network`

> Numbering note: Phase 7 keeps its number so existing task IDs stay stable, but it is executed **right after Phase 3** and **before** Phases 4/5 (Section 14). It is part of the core. Controller code for one junction already exists from Phases 1–2; Phase 7 instantiates it per junction and adds a shared-policy RL training setup. No database, backend or dashboard. No new dependencies (if one seems needed → stop and ask, DEC-11).

### T7.1 — Network TLS inventory, suitability and intended set
- **Depends on:** T3.2 · **SRS:** FR-SIM-02, FR-CTL-10
- **Do:** `scripts/inspect_network_tls.py` (reusing T0.3 code, parametrised by `tls_id`) over **every** TLS in the net: program type, phases and state strings, green/yellow classification, controlled movements, joined-cluster flag, approach count, junction coordinates, **foe/conflict check per TLS**, and traffic under SUMO's native program for ≥ 1800 s with the existing demand. Classify each TLS **suitable** (≥ 2 verified conflict-free green phases; static, or convertible to a static copy of the same phases; ≥ `network.min_veh_per_1800s` vehicles) or **excluded with a written reason**. The M1 pilot junction must be in the intended set. If actuated TLS need static copies, create them under `SUMO/derived/` (never edit `SUMO/No_Polygon_Map`). Write `network.controlled_tls`, `network.excluded_tls`, `network.max_approaches`, `network.max_phases` to `config/stms.yaml`; write `docs/network_tls.md` (table of all TLS, intended/excluded, reasons, counts).
  - If the intended count > `network.max_intended` → **stop and ask** (cap is a human decision). Report measured sim speed with all intended TLS under TraCI control (extrapolate the training budget; if even 100,000 timesteps looks > 10 h → warn now).
  - **Stop and ask the human to approve the list (P4).** The list is frozen after approval (DEC-13).
- **Files:** `scripts/inspect_network_tls.py`, `docs/network_tls.md`, `tests/test_network_config.py`, `tests/test_network_tls.py`.
- **Accept:**
  ```
  python scripts/inspect_network_tls.py
  pytest -q tests/test_network_config.py        # config lists match the inventory; M1 junction included; no TLS both intended and excluded
  pytest -m sumo tests/test_network_tls.py      # every intended TLS: foe-free green phases, verified yellow structure
  python scripts/check_zombies.py
  ```

### T7.2 — Multi-junction state, safety, controllers and runner
- **Depends on:** T7.1, T1.3 · **SRS:** FR-CTL-01/02/06/07/08/10, §5.2
- **Do:** `Ai/common/network_state.py` (`NetworkState{sim_time, junctions:{tls_id: IntersectionState}, totals}`, JSON-serialisable `to_dict()`, `NetworkSensorReader`); extend `Ai/controllers/safety.py` with `NetworkSafetyManager` holding **one `SignalSafetyLayer` per intended TLS** (still the only code that calls TLS setters; `tick_all()` runs after **every** `simulationStep`, not only at decision ticks, so yellow, min-green and max-green are enforced each second; excluded TLS are never commanded); `Ai/controllers/network.py` (`NetworkController.decide(NetworkState) -> {tls_id: Action}`; `PerJunctionController` applying a single-junction fixed/rule controller at every TLS, each wrapped in its own `FallbackController` so one junction's failure never affects another); `registry.get_network_controller("fixed"|"rule"|"rl")` (`rl` arrives in T7.7). Extend `run_episode` with `--family network` (closed loop observe → decide → safety → step for all intended TLS; `steps.csv` per `intersection_id`, `junctions.csv`).
- **Files:** the above + `tests/test_network_state.py`, `tests/test_network_safety.py`, `tests/test_network_controllers.py`.
- **Accept:**
  ```
  pytest -q tests/test_network_state.py tests/test_network_controllers.py
  pytest -m sumo tests/test_network_safety.py   # 1200 s random-command fuzzer on ALL intended junctions at once
  python scripts/check_zombies.py
  ```
  Safety properties (a)–(e) of T1.2 hold **at every junction**, plus (f) excluded TLS never receive a command, (g) forcing a fallback at one junction leaves the others unaffected. Record real wall-clock per sim-second with all junctions controlled.

### T7.3 — Network scenarios and cached pool
- **Depends on:** T7.2 · **SRS:** FR-SIM-03/04/05
- **Do:** extend `scripts/make_scenarios.py` with `--family {single,network}` (default `single`, so T0.4 commands keep working); for `network`: scenarios `net_balanced, net_low, net_medium, net_heavy, net_rush_hour`; origin/destination pairs sampled over the **whole map** (seeded RNG, sorted edge lists, `sumolib` shortest paths, `duarouter`, cars only, fixed routes); `net_rush_hour` ramps insertion. Cached routes per seed with a manifest hash that includes the intended-TLS list; `ensure_routes()` and `--train-pool` (`demand.net_train_pool`, 5 × 20 seeds from 1000–1999) as in T0.4; training never generates demand. **Measure** with SUMO's native program: trips, **fraction of trips using ≥ 1 controlled movement (must be ≥ `network.min_controlled_trip_share`, else stop and ask)**, mean controlled junctions per trip, per-TLS trip counts, completion by `max_sim_s`, teleports, insertion backlog. Tune insertion so `net_medium/heavy/rush_hour` are congested but not gridlocked (teleports < 1%).
- **Files:** `scripts/make_scenarios.py`, `docs/scenarios.md` (network table), `tests/test_scenarios.py`.
- **Accept:**
  ```
  python scripts/make_scenarios.py --family network --seed 1000 --all
  python scripts/make_scenarios.py --family network --seed 1000 --all --force   # byte-identical
  python scripts/make_scenarios.py --family network --train-pool
  pytest -q tests/test_scenarios.py
  ```

### T7.4 — Network metrics and baselines
- **Depends on:** T7.3 · **SRS:** FR-SEN-04, FR-EVL-02, DEC-12
- **Do:** extend `Ai/common/metrics.py` and `docs/metrics.md` with network metrics (additions only, so `metrics_version` stays 1; changing an existing definition would bump it and force re-running M1 and M2): network travel time (completed, censored, common-trip), completion rate, time loss, waiting, speed, throughput (arrivals/min), teleports, mean and **worst-junction** queue, congestion share per junction and network-wide, `n_tls_controlled`, `n_tls_ai`, `n_controlled_junctions_on_route`, per-junction `junctions.csv`. Run network `fixed` and `rule` on all five net scenarios; the rule controller uses **one shared threshold set** tuned on validation seeds **3000–3002** (≥ 3 settings, never 5000+/6000+, logged in `docs/rule_tuning.md` Part 2). **Re-check:** network fixed-time teleports < 1% of trips on `net_medium/heavy/rush_hour`, else stop and ask. Record wall-clock per run and per controller (feeds T7.6/T7.8 budgets).
- **Accept:**
  ```
  pytest -q tests/test_metrics_network.py   # hand-built multi-junction tripinfo → exact network numbers, censored time, completion rates, per-junction rows
  python -m Ai.common.run_episode --family network --controller fixed --scenario net_medium --seed 3000
  python -m Ai.common.run_episode --family network --controller rule  --scenario net_medium --seed 3000
  ```
  `summary.csv` complete, `n_tls_controlled == len(network.controlled_tls)`, no undocumented NaN.

### T7.5 — Network RL environment (blocking gate)
- **Depends on:** T7.4 · **SRS:** FR-CTL-03/04/06
- **Do:** `Ai/rl/network_vec_env.py`: `NetworkVecEnv(VecEnv)` — a custom SB3 `VecEnv` with `num_envs = N` = number of intended TLS; slot *i* is junction `network.controlled_tls[i]` (fixed sorted order, recorded in `config.json`) inside **one** SUMO simulation (parameter sharing). Implement the full abstract `VecEnv` interface (`reset, step_async, step_wait, close, get_attr, set_attr, env_method, env_is_wrapped, get_images, seed`). Built on `SumoClient`, `NetworkSensorReader`/`to_vector` and `NetworkSafetyManager`; **no direct TLS manipulation**. Design rules (each is tested below):
  - **Lockstep clock.** Every `rl_net.decision_interval_s` all junctions decide at the same instant from one batched observation `(N, Nobs)` and one action vector `(N,)`. With a shared clock a junction cannot extend simulated time on its own.
  - **Actions:** shared `Discrete(4)` (DEC-03) reinterpreted for the shared clock: 0 keep; 1 request switch to the next green; 2 / 3 keep **and hold** (no switch) for the next `ceil(5/interval)` / `ceil(10/interval)` decision ticks. A sampled action that is illegal (min-green not reached, hold active, safety rejection) is executed as "keep" and counted per junction (`n_illegal_actions`, `n_hold_overridden`) — the same convention as M1.
  - **Within a tick:** apply each junction's action through its safety layer, then advance `decision_interval_s` single `simulationStep`s, calling `NetworkSafetyManager.tick_all()` after every step.
  - **Observation** per junction `Box(0,1,(Nobs,))`: approach slots padded to `network.max_approaches` + validity mask + phase one-hot padded to `network.max_phases` + normalised elapsed green; identical shape for every junction so one policy serves all; layout documented in `docs/rl_design.md`.
  - **Reward** `(N,)`: M1's local formula and weights over each junction's own approaches for the tick, plus `rl_net.network_term_weight × mean reward over junctions` (default 0.0).
  - **Termination:** all slots end together by **truncation** at `rl_net.episode_s` only. At that point `dones` are all True, every `infos[i]` has `TimeLimit.truncated = True` and `terminal_observation` (so SB3 bootstraps the value), then the env closes SUMO, draws the next (scenario, seed) from the **cached net pool** (seeded RNG, deterministic order; fail fast if a file is missing) and returns the first observation of the new episode. A SUMO/TraCI failure raises; it never fabricates an episode.
  - `close()` idempotent; unique port/label per instance (validation uses a second instance). `infos[i]` also carries `tls_id, illegal_action, hold_overridden, fallback_active`.
- **Accept:** `ruff check Ai/rl` clean and `pytest -m sumo tests/test_network_env.py -q` all green: (1) VecEnv contract: shapes `(N,Nobs)`/`(N,)`, dtypes, spaces, `reset/step/close`, and 100 steps under `VecCheckNan`; (2) 2 random-policy episodes: no exception, safety properties at every junction, excluded TLS never touched; (3) scripted "switch when queue high" beats "always keep" on cumulative reward on a `net_heavy` seed (assert); (4) same seed twice ⇒ identical first 50 observations and rewards for all junctions; (5) 5 reset/close cycles leave no zombie SUMO; (6) missing pool file ⇒ fail-fast; (7) padding: junctions with fewer approaches have zeroed slots and a correct mask; (8) termination: at `episode_s` all slots are done with `TimeLimit.truncated` and `terminal_observation`, and the next episode starts at sim time 0 with a new pool entry; (9) hold semantics: action 3 blocks switching for the stated ticks and overridden samples are counted; (10) batching: row *i* of the observation/reward/action arrays corresponds to `network.controlled_tls[i]`. **If (3) fails, fix reward/observation first.**

### T7.6 — Shared-policy PPO training (staged ladder, DEC-14)
- **Depends on:** T7.5 · **SRS:** FR-CTL-05/09
- **Do:** `Ai/rl/train_ppo_network.py` (CLI: `--timesteps --seed --scenarios --reward-weights --network-term --out --resume`): SB3 `PPO("MlpPolicy")` on `NetworkVecEnv` wrapped in `VecMonitor`, scenario/seed per episode from the cached net pool, TensorBoard, `training_log.csv`, periodic checkpoints, save `ppo_net_v<N>/{model.zip,config.json}` (config: intended-TLS list hash and slot order, reward weights, seeds, library versions, wall-clock). Resumable via `PPO.load(..., reset_num_timesteps=False)`; long runs per Section 0.8.
  - **Timestep semantics:** one vectorised step = N junction decisions = N SB3 timesteps; the rollout buffer holds `n_steps × N` samples. Choose `n_steps` and `batch_size` so `n_steps × N` is divisible by `batch_size` (SB3 warns otherwise); an episode is `episode_s / decision_interval_s` vectorised steps (720 at defaults). Report timesteps, vectorised steps and simulated hours.
  - **Known assumptions/risks (record in `docs/rl_design.md`, make no convergence claim):** samples from different junctions at the same tick are correlated; each junction's environment is non-stationary because the others' policy changes; parameter sharing assumes junctions are similar enough after padding.
  - **Validation:** a custom `NetworkValidationCallback` (SB3 `EvalCallback` is **not** used because it assumes one episode per env slot). Every `rl_net.validation_every_timesteps` it runs one deterministic episode per `rl_net.validation_pairs` entry on a **separate** `NetworkVecEnv`, logs network censored average travel time and mean per-junction return, and keeps the best-by-validation checkpoint (lowest censored travel time). It never uses seeds 5000+/6000+.
  - **Staged budget** (starting points, not promises; measured throughput decides; coverage of all intended TLS is never reduced):
    1. **Smoke:** 20,000 timesteps; report timesteps/hour and sim-s/real-s with all intended TLS controlled.
    2. **Pilot:** ~100,000 timesteps (or ≲ 3 h). Continue only if validation is improving, else ask.
    3. **Main (Stage 2):** the largest count fitting `rl_net.max_train_hours` (default ≤ 10 h), justified by the pilot curve. Projected > 10 h even for 150,000 timesteps → **Stage 3** reductions: fewer training scenarios, `episode_s` 1800, `decision_interval_s` 10, early stop on validation, single PPO seed; record each in `docs/experiment_log.md`.
    4. If Stage 3 still cannot produce a model that passes T7.7 → **stop and ask (P5)**.
  - If time allows, train ≥ 2 PPO seeds; choose by validation only.
- **Accept:**
  ```
  python -m Ai.rl.train_ppo_network --timesteps 20000 --out Ai/rl/models/ppo_net_v1_smoke
  python -m Ai.rl.train_ppo_network --timesteps <staged budget> --out Ai/rl/models/ppo_net_v1
  pytest -q tests/test_network_validation_callback.py   # fake env: best checkpoint chosen by lowest censored time, never by training reward
  ```
  Report the learning-curve file, measured speed (real numbers only) and the best validation result.

### T7.7 — Network RL controller and sanity gate
- **Depends on:** T7.6 · **SRS:** NFR-PRF-01, FR-CTL-07/08/10
- **Do:** `Ai/controllers/rl_network_controller.py` (loads `ppo_net_v<N>`, builds all junction observations in slot order, **one batched forward pass**, per-junction `FallbackController`); per-junction diagnostics (action histogram, phase usage, mean green, forced max-green switches, illegal/hold-overridden rate, `ppo_tick_share`). Run network `fixed`, `rule`, `rl` on `net_medium` and `net_heavy`, validation seeds 3000–3002 → `docs/rl_diagnostics.md` Part 2.
- **Pass (defaults):** (a) **PPO decisions applied at every approved intended TLS**: `ai_coverage = full` (`controlled_by = rl` for all junctions); (b) ≥ 80% of junctions use ≥ 2 distinct actions; (c) forced max-green < 30% of switches network-wide; (d) network censored travel time not worse than fixed-time by > 5%; (e) worst-junction queue regression vs fixed reported, a junction > 50% worse triggers investigation; (f) batched-inference median latency < 100 ms on this machine (measured).
- **If it fails**, iterate in order, logging each attempt: (1) reward weights / `network_term_weight` (try 0.25 once), (2) observation (last action, per-approach wait, neighbour-junction halting if time allows), (3) decision interval, (4) PPO hyper-parameters, (5) more timesteps within budget, (6) curriculum low → heavy. After 5 failed iterations → **stop and ask (P5)**.
- **Files:** the controller, `docs/rl_diagnostics.md`, `tests/test_rl_network_controller.py`.
- **Accept:** `pytest -q tests/test_rl_network_controller.py` (latency measured, corrupt-model path activates per-junction fallback and lowers that junction's `ppo_tick_share`) and the gate table in `docs/rl_diagnostics.md` produced by an actual run.

### T7.8 — Network evaluation harness
- **Depends on:** T7.7 · **SRS:** FR-EVL-01..07
- **Do:** extend `Ai/evaluation/evaluate.py` with `--family {single,network}` (default `single`, so T3.1 commands are unchanged). For `network`: scenarios `net_*`, `--seed-set dev|final`; for each `(scenario, seed)` generate routes once and run `fixed`, `rule`, `rl` on the same file and seed; skip-if-complete, resumable. **Before launching, estimate wall time** from T7.4 timings (5 scenarios × 5 seeds × 3 controllers = 75 runs per seed set) and tell the human. Aggregate into `comparison.csv` (`milestone = M2`, rebuilt from all raw runs per Section 11) exactly per DEC-12: per-scenario rows, headline row (four non-`low` scenarios), primary row, separate `net_low` row, pooled sensitivity row; paired-bootstrap 95% CI. Primary comparison is the completed **common-trip set**, **always beside** censored travel time, completion rates and common-set size; flag survivorship risk per `eval.completion_gap_flag_pp`. Also write `network_junctions.csv` and a per-junction congestion figure. `target_met` per trip basis and aggregation, never forced. **Coverage:** `ai_coverage` is computed per `rl` run; any run with `ai_coverage != full` is flagged and the report must call it partial. Charts labelled "simulated".
- **Accept:**
  ```
  python -m Ai.evaluation.evaluate --family network --controllers fixed rule rl --seed-set dev
  pytest -q tests/test_evaluation_network.py   # exact improvement %, common-trip filter, censored/completion, low excluded from headline, ai_coverage full/partial/none, M1 rows untouched
  ```
  Re-running reproduces an identical `comparison.csv`.

### T7.9 — Network results gate (FINAL result)
- **Depends on:** T7.8
- **Do:** if the dev headline improvement is < 10%: diagnose (per-scenario and per-junction tables, action/phase histograms), then try the remaining levers once each using **training/validation seeds only** (longer training within budget, reward re-weighting, scenario mix, network term). **Freeze:** commit model + `config.json`; record model sha256, config hash, intended-TLS list hash, git commit and exact command in `docs/experiment_log.md`. **Then run the final block once:** `python -m Ai.evaluation.evaluate --family network --controllers fixed rule rl --seed-set final` (crash-resume with identical config allowed and noted). Write `docs/results.md` **Part 2 — M2, final**: the intended-TLS list and exclusions; a line `AI coverage: <n_tls_ai>/<n_tls_controlled> (<full|partial|none>)` copied from `summary.csv`; the **controller level reached** (full shared-PPO / Stage 3 reductions / Stage 4 labelled fallback); headline Metric N with CI, `target_met`, common-trip beside censored and completion rates, per-scenario rows, `net_low` separate, per-junction congestion table, limitations (simulation only, synthetic demand, cars only, decentralised shared policy, excluded TLS on native program, no real-world validation) and "provisional until P1". Report all attempts, including failed ones. Do not change seeds, scenarios, TLS list or metrics after seeing results. The words "full network-wide AI control" may appear only if `ai_coverage = full`.
- **Accept:** every number in `docs/results.md` (both parts) equals `results/summary/comparison.csv`/`summary.csv`; `pytest -q tests/test_results_doc.py` also checks the `AI coverage:` line against `summary.csv` and fails if "full network-wide AI control" appears while `ai_coverage != full`.

### T7.10 — Stage-4 fallback (CONDITIONAL: only if the human selects it under P5)
- **Depends on:** the human's written P5 decision, T7.5 · **Not triggered by default.**
- **Do:** the human and agent first agree a short written spec in `docs/experiment_log.md` (partial-AI hybrid with a per-junction non-regression gate, or validated multi-junction rule-based controller plus M1 PPO). Implement it as `HybridNetworkController` in `Ai/controllers/network.py`, then run it through T7.8/T7.9 unchanged. Every report states `ai_coverage = partial` (or `none`) with the coverage fraction; it is never described as full network-wide AI control.
- **Accept:** `pytest -q tests/test_hybrid_controller.py` (exactly the declared junctions are PPO-driven, the rest rule-based; `ai_coverage` computed correctly) and the T7.8 acceptance commands.

---

# PHASE 4 — Traffic prediction (time-boxed; may be explicitly marked Skipped/Deferred if behind schedule, Section 14)
Branch: `agent/phase-4-prediction`

> Scope: uses the M1 pilot junction only; it need not cover the whole network. By default it runs **after Phase 7** (Section 14).

### T4.1 — Data collection
- **Depends on:** T1.4 (start with `fixed` and `rule`; add `rl` rows after T2.4 exists) · **SRS:** FR-PRD-01
- **Do:** `prediction/collect_data.py`: run controllers over scenarios with the seeds of the chosen **split profile** (table below, from `prediction.split` in config); log per-approach `vehicle_count, halting, mean_speed, wait, phase` every 5 s to `prediction/data/raw/*.csv` (gitignored; keep a small sample in `prediction/data/sample/`). **Compute check first:** 30 seeds × 7 scenarios × 2–3 controllers can be hundreds of runs; use T1.4 timings to size it, and tell the human. If too slow, use the **reduced** profile instead of the full one, and say so in `docs/prediction.md`. Both profiles are defined explicitly here and in config (the same table is used by T4.2):

    | Profile | Train seeds | Validation seeds | Test seeds |
    |---|---|---|---|
    | `full` | 2000–2019 (20) | 2020–2024 (5) | 2025–2029 (5) |
    | `reduced` | 2000–2011 (12) | 2020–2023 (4) | 2025–2028 (4) |

    The reduced seeds are strict subsets of the full ones, the three sets are disjoint in both profiles, and unused seeds (2012–2019, 2024, 2029 in `reduced`) are simply not collected. Never mix profiles within one trained model. Collection must be resumable.
- **Accept:** `python prediction/collect_data.py --profile full` (or `--profile reduced`) and `python prediction/check_data.py --profile <same>` (row counts, no NaN, expected columns, collected seeds exactly equal the profile's train/val/test seeds).

### T4.2 — Dataset and baselines
- **Depends on:** T4.1
- **Do:** windows of the last 12 samples (60 s) → target = approach vehicle count (and congestion class) 60 s ahead (configurable). **Run-level split by seed**, exactly the train/validation/test seeds of the profile chosen in T4.1 (`prediction.split.full` or `.reduced`; same seeds for every model and baseline), never random row shuffling. Implement **last-value** and **moving-average** baselines.
- **Accept:** `pytest -q tests/test_prediction_dataset.py` (no window crosses runs; no test-run row in train; split seeds equal the config profile for both `full` and `reduced`; sets disjoint; reduced ⊂ full).

### T4.3 — Model, evaluation, inference
- **Depends on:** T4.2 · **SRS:** FR-PRD-01..03
- **Do:** train Random Forest (plus XGBoost or GRU only if time allows; add `xgboost` to requirements only then); evaluate on the **test seeds of the profile that was collected** and record that profile in `docs/prediction.md` and the `split_profile` column; report **MAE and RMSE per approach** and congestion-class accuracy on test vs baselines; save `prediction/models/predictor_v1.joblib` + `metadata.json`; `prediction/predict.py::predict(window) -> {approach: {predicted_count, predicted_congestion}}`.
- **Accept:** `python prediction/train.py && python prediction/evaluate.py` writes `results/summary/prediction_metrics.csv`; `pytest -q tests/test_predict.py` (all approaches returned; short window → clear error). If the model does not beat last-value, say so in `docs/prediction.md`.

---

# PHASE 5 — Virtual camera: OpenCV + YOLO (time-boxed)
Branch: `agent/phase-5-vision`

> **Independence from PPO:** Phase 5 depends only on Phase 0/1 outputs (T0.3, T1.3, T1.4) — never on T2.x/T3.x/T7.x. Its results are reported whether or not PPO succeeded, and PPO is never fed camera data. It is a **simulated-vision prototype on SUMO-rendered frames; its numbers are not evidence of real-world camera accuracy.** It uses the M1 pilot junction only and may be marked Skipped/Deferred per Section 14.

> No real video is needed. The "camera" is SUMO-GUI looking down at the controlled junction. SUMO's TraCI positions are the **free ground truth**. Needs `sumo-gui` and a display on the human's PC (screen on, unlocked, window not minimised during capture); if unavailable → **stop and ask**.

### T5.1 — Virtual camera capture + auto-labels
- **Depends on:** T1.4, T0.3 (junction bounding box); install `requirements-vision.txt` first (if it will not install on the active Python → **stop and ask**, DEC-11) · **SRS:** FR-CV-01/03
- **Do:** `vision/capture_frames.py`: run SUMO-GUI (`SumoClient(gui=True)`) on scenarios `medium/heavy/rush_hour` with seeds **7000–7013**; set the view to the junction bounding box (`traci.gui.setBoundary` / `setZoom`) using a copied GUI settings file `vision/gui_settings.xml` that draws vehicles large and clear (no polygons/POIs that confuse detection); save a frame every `vision.capture_every_s` via `traci.gui.screenshot` to `vision/data/frames/<run>/frame_<t>.png`.
  - **Storage/time budget:** at 1280×720 PNG, 14 runs × 720 frames is several GB. Capture only a window of each run (e.g. 600–2400 s) and cap the total number of frames in config (`vision.max_frames`, default ~2,000 train / 300 val / 300 test); check free disk from T0.1 first.
  - **At the same instant** write ground truth from TraCI: each vehicle's position → pixel box (known boundary + image size; remember SUMO's y-axis points up, image y points down, and the GUI may letterbox to keep the aspect ratio — calibrate, don't assume) → YOLO label file (single class `car`) plus per-approach true counts to `truth.csv`. Auto-generate **ROI polygons per approach** from the incoming lane shapes mapped to pixels → `vision/config/roi_junction.json`.
  - `vision/define_roi.py`: a small OpenCV mouse tool to define/override ROI polygons manually (SRS FR-CV-03 requires user-definable ROIs); output same JSON format.
  - Split by run: seeds 7000–7009 train, 7010–7011 val, 7012–7013 test.
- **Privacy/size:** frames are synthetic, gitignored; commit only 5 sample frames.
- **Accept:** `python vision/capture_frames.py --seeds 7000-7013` then `python vision/check_labels.py` (writes 10 overlay images with label boxes for visual sanity; box count == vehicles in view; **inspect the overlays** and describe what you see) and `python scripts/check_zombies.py`.

### T5.2 — Pretrained YOLO test (accuracy gate)
- **Depends on:** T5.1 · **SRS:** FR-CV-01/02/04/07
- **Do:** `vision/detector.py`: OpenCV frame reader for **video file (MP4), folder or stream** (also assemble a short MP4 from test frames and run the detector on it, to prove FR-CV-01 on a real video file) + Ultralytics pretrained `yolov8n` (COCO `car` class; also count bus/truck/motorcycle as vehicles); per-approach counting inside ROI polygons; density Low/Medium/High from config thresholds. `vision/evaluate_vision.py` compares detections with `truth.csv`/labels on the **test** split (seeds 7012–7013): per-frame per-approach count MAE, precision/recall at IoU 0.5, and CPU/GPU FPS (NFR-PRF-04: ≥ 10 FPS on GPU / ≥ 3 FPS on CPU; report only what hardware was actually detected).
- **Gate:** vehicle **recall ≥ 0.85** and per-approach count MAE ≤ 1.5 → pretrained accepted; skip T5.3. Otherwise do T5.3. (Pretrained COCO models may struggle on synthetic top-down rectangles; plan for T5.3, and report honestly either way. If T5.3 is deferred by a cut line and the gate failed, report the failed gate and numbers as they are.) All numbers describe SUMO-rendered frames only.
- **Accept:** `python vision/evaluate_vision.py --weights yolov8n.pt --split test` writes `results/summary/vision_metrics.csv`; `pytest -q tests/test_vision.py` (synthetic frames + stub detector: ROI membership, no double counting, density thresholds).

### T5.3 — Fine-tune YOLO on auto-labelled frames (only if T5.2 gate failed)
- **Depends on:** T5.2
- **Do:** `vision/train_yolo.py` fine-tunes `yolov8n` on train/val splits (single class `car`). **Measure one epoch's time first**; on a CPU-only laptop choose image size / frame count / epochs so the run fits a stated time budget (start with ≈ 30 epochs or until val mAP plateaus, and tell the human the ETA). Save `vision/models/yolo_sumo_v1.pt` (gitignored if > 50 MB; record sha256 in docs); re-run T5.2's evaluation on the same **test** split with the new weights; report both rows (pretrained vs fine-tuned).
- **Accept:** `python vision/evaluate_vision.py --weights vision/models/yolo_sumo_v1.pt --split test`; if still below the gate, state it honestly in `docs/vision.md`.

### T5.4 — Camera → Traffic State, and camera-driven control demo
- **Depends on:** T5.2 (or T5.3 if it was run), T1.3 (no dependency on T2.x/T3.x) · **SRS:** FR-STA-04, FR-CV-05/06, FR-CTL-07
- **Do:** (a) `vision/camera_state.py` → `IntersectionState(source="camera")` per frame with unavailable fields `None` and listed in `available_fields`; annotated frames/MP4 on request (FR-CV-06) to `results/vision/`. (b) `scripts/run_camera_demo.py`: SUMO-GUI runs with the **rule-based** controller fed by camera-derived states (not PPO, because a camera cannot give waiting time), and a second run with the same controller fed by TraCI states, on the **demo seed block 8000–8009**; report the travel-time difference on one scenario/seed. Camera in a closed loop is a **demo only**, never part of RL training/evaluation.
- **Privacy:** only aggregated counts are persisted besides the synthetic demo frames.
- **Accept:** `python scripts/run_camera_demo.py --scenario medium --seed 8000` completes; `docs/vision.md` holds the metrics table, FPS, the camera-vs-TraCI demo result, and a prominent statement that this is a simulated-vision prototype whose numbers are **not** evidence of real-world camera accuracy, and limitations (rendering style, one fixed view, no occlusion/lighting realism).

---

# PHASE 6 — Demo, quality, documentation (lean)
Branch: `agent/phase-6-release`

### T6.1 — One-command demo
- **Depends on:** T7.9 (and T3.2; T5.4 if done)
- **Do:** `python -m scripts.run_demo --family {single,network} --controller {fixed,rule,rl} --scenario <medium|net_medium> --seed 8000 [--gui] [--camera]` (`--camera` only with `--family single --controller rule`, and only if T5.4 was done; `--family network --gui` shows the whole map) — runs SUMO(-GUI) with the chosen controller, prints live-ish metrics, writes outputs to `results/raw/`. The demo uses the **demo seed block (8000+)**, never the final-evaluation seeds. Add `scripts/run_all.md` listing the exact command order (scenarios → fixed → rule → train → evaluate → predict → vision → demo; steps for a skipped/deferred phase are marked "skipped").
- **Accept:** the three controllers each run once via this CLI for **both** families (`single` = M1 junction, `network` = all intended TLS; the network `rl` demo prints `n_tls_ai` vs `n_tls_controlled` and states the controller level reached, DEC-14); `python scripts/check_zombies.py` clean; a 1-hour simulated session completes without crash (NFR reliability, §5.4).

### T6.2 — Quality pass
- **Do:** `ruff check .` clean over the **whole repo** (any exclusion justified per 0.7 and listed in `docs/lint_exclusions.md`); `pytest -q` and `pytest -m sumo` pass; `git grep -nEi "password|secret|apikey|token"` reviewed; confirm `.gitignore` works (no large files tracked); remove/label temp scripts; confirm no unused DB/web packages remain in requirements; OSM (ODbL) attribution in README.
- **Accept:** command outputs pasted in the report. (Coverage report optional.)

### T6.3 — Documentation
- **Do:** `README.md` (overview, mermaid architecture diagram, prerequisites, setup for Windows and Ubuntu including the verified Python version, config, **exact command sequence**, outputs map, limitations, ODbL attribution); `docs/srs_deviations.md` (the table in Section A, with P1/P2 status; P4/P5 outcomes stated); `docs/limitations.md` (including any skipped/deferred phase and why); `docs/report_inputs.md` (checklist of validated tables/figures/screenshots for the human's report and PPT, each with source file path; SUMO-GUI screenshots captured by the human or by script).
- **Accept:** every README command was executed by you at least once; list those you could not run.

### T6.4 — Release
- **Do:** tell the human to merge the final phase branch into `main` (Section 0.5), then tag `v1.0-ai-core` **on `main`**; list any Skipped/Deferred tasks; fill `docs/RELEASE_CHECKLIST.md` with real results; state which of P1/P2/P4/P5 are still pending and **which controller level was reached (full network AI / partial-AI / rule-only, DEC-14)**.

---

# DEFERRED (do not start unless the human explicitly says so)
- **Backend:** simulation service thread, FastAPI REST + WebSocket, authentication/roles, audit log, `docs/openapi.json`.
- **Database:** PostgreSQL/SQLite via SQLAlchemy; tables `intersections, traffic_records, signal_events, decisions, experiments, users, audit_log`.
- **Dashboard** (SRS §3.1 screens, FR-DSH/OVR/AUT).
- **Optional (only if the human asks later):** emergency-vehicle priority, **explicit communication-based inter-junction coordination (green waves, message passing)**, prediction as RL input.
- **Not deferred:** multi-junction *control itself* is **mandatory** in Phase 7 (M2). Only explicit coordination *between* junctions is deferred; the shared policy of DEC-14 is the only coordination mechanism in scope.

The only things these need from today's work: JSON-serialisable `IntersectionState`, the `Controller` interface, the safety layer's `Accepted/Rejected(reason)` API, and the CSV schemas in Section 11.

---

# 10. Requirement → task traceability

| SRS requirement(s) | Task(s) / status |
|---|---|
| FR-SIM-01..07 | T0.3, T0.4 (M1 pilot junction); T7.1, T7.3 (all intended TLS, network scenarios). FR-SIM-01 satisfied by the existing OSM→SUMO map |
| FR-SEN-01..05 | T0.3, T1.1, T1.4 |
| FR-CV-01..07 | T5.1–T5.4 (simulated camera, cars only; independent of RL; may be Skipped/Deferred; deviation logged) |
| FR-STA-01..05 | T1.1, T5.4 |
| FR-PRD-01..03 | T4.1–T4.3 (may be Skipped/Deferred, Section 14) · FR-PRD-04/05 deferred |
| FR-CTL-01, 02, 08 | T1.3 (M1), T7.2 (every intended TLS) |
| FR-CTL-03, 04, 05, 09 | T2.1, T2.3 (M1); T7.5, T7.6 (shared policy, all intended TLS) |
| FR-CTL-06 (safety) | T1.2, T2.2 (M1); T7.2, T7.5 (every intended junction) |
| FR-CTL-07 | T1.3, T2.4, T5.4, T7.7 |
| FR-CTL-10 | T7.1–T7.9 (multi-junction control, M2; T7.10 only if P5 selects Stage 4) |
| FR-EMG-* | Deferred (optional) |
| FR-EVL-01..07 | T3.1, T3.2 (M1); T7.4, T7.8, T7.9 (network-wide) |
| FR-DSH-*, FR-OVR-*, FR-AUT-*, FR-DAT-* | **Deferred** (backend/DB/dashboard) |
| NFR-PRF-01 | T2.4, T7.7 · NFR-PRF-04 → T5.2 · NFR-PRF-05 → T0.1 and T7.2 (measured sim speed, whole network) |
| NFR-PRF-02, 03 (dashboard/REST latency) | Deferred with the dashboard/backend |
| NFR-PRF-06 (≥ 10%) | T3.1, T3.2 (M1, milestone); **T7.8, T7.9 (M2 network-wide, final)** — **measured, never asserted; provisional metric (P1)** |
| §5.2 Safety | T1.2, T1.3 (fallback); T7.2 (all junctions) |
| §5.3 Security | Deferred, except camera-privacy rule (T5.1/T5.4) |
| §5.4 Reliability / Reproducibility / Testability | T0.2, T3.1, T6.1, T6.2 |
| §5.5 Business rule: identical scenarios/seeds | T3.1, T7.8 |
| §6 Delivery (code, model, scenarios, docs, demo script) | T0.4, T3.2, T7.3, T7.9, T6.1, T6.3 |

---

# 11. Data schemas (CSV; UTF-8; header row; one schema for every controller)

**`results/raw/<run_id>/steps.csv`** (logged every `logging.step_log_every_s`) — `run_id, controller, scenario, seed, sim_time, intersection_id, approach, vehicles, halting, mean_speed, wait_time, phase, phase_elapsed, signal_state, action, action_accepted, congestion`

**`results/raw/<run_id>/trips.csv`** — `run_id, controller, scenario, seed, vehicle_id, vtype, scheduled_depart, actual_depart, depart_delay, arrival, duration, trip_time, waiting_time, time_loss, route_length, completed, route_through_junction, first_controlled_movement, n_controlled_junctions_on_route, passed_controlled_junction` (unfinished: `trip_time = end_time − scheduled_depart`, `completed=false`)

**`results/raw/<run_id>/summary.csv`** (one row) — `run_id, controller, scenario, seed, git_commit, config_hash, metrics_version, n_trips, n_trips_junction, n_completed, n_unfinished, completion_rate, completion_rate_junction, avg_travel_time_completed, avg_travel_time_censored, avg_travel_time_junction_completed, avg_travel_time_junction_censored, avg_wait, avg_time_loss, avg_depart_delay, avg_queue, avg_speed, throughput_veh_per_min, frac_time_high_congestion, teleports, sim_end_time, wall_clock_s, family(single|network), n_tls_controlled, n_tls_ai, ai_coverage(full|partial|none), avg_junction_queue_mean, worst_junction_avg_queue`
(For `family=network` the "junction" columns mean trips using ≥ 1 controlled movement of any intended TLS; the M2 headline uses the all-trips columns. Network-only columns are documented-blank for `family=single`.)

**`results/raw/<run_id>/junctions.csv`** (network family; one row per controlled TLS) — `run_id, controller, scenario, seed, tls_id, controlled_by(fixed|rule|rl|rl_fallback|native), avg_queue, max_queue, avg_wait, frac_time_high_congestion, throughput_veh_per_min, n_switches, n_forced_max_green, n_illegal_actions, n_hold_overridden, fallback_activations, n_ticks, ppo_tick_share`
(`ppo_tick_share` = decision ticks in which PPO supplied the action passed to the safety layer ÷ `n_ticks`; an illegal or hold-overridden PPO action still counts as a PPO decision, a tick taken over by `FallbackController` does not. `controlled_by = rl` only if `ppo_tick_share ≥ eval.ai_coverage_min_share`, else `rl_fallback`. In `summary.csv`, `n_tls_ai` counts junctions with `controlled_by = rl`, `n_tls_controlled` counts all junctions on the approved intended list, and `ai_coverage` = `full` if `n_tls_ai == n_tls_controlled == len(network.controlled_tls)`, `partial` if 0 < `n_tls_ai` < that, else `none`. Computed by the evaluation code, never typed by hand.)

**`results/summary/comparison.csv`** — `milestone(M1|M2), scenario, aggregation(scenario|headline|primary|low|pooled), controller, metric, scope(all|junction), trip_basis(common|all), mean, std, ci95_low, ci95_high, n_seeds, n_trips_basis, completion_rate_mean, seed_set(dev|final), improvement_vs_fixed_pct, improvement_vs_rule_pct, target_met`

**`results/summary/network_junctions.csv`** — `scenario, tls_id, controller, avg_queue_mean, avg_wait_mean, ci95_low, ci95_high, n_seeds, seed_set(dev|final)`

**`results/summary/prediction_metrics.csv`** — `split_profile(full|reduced), approach, model, horizon_s, mae, rmse, congestion_accuracy`

**`results/summary/vision_metrics.csv`** — `weights, split, approach, precision, recall, count_mae, fps, device`

`comparison.csv` is rebuilt from **all** runs present in `results/raw/` (every milestone and seed set) each time, so evaluating one family never removes or alters rows of another; rows are keyed by `(milestone, seed_set, scenario, aggregation, controller, metric, scope, trip_basis)`. Metric definitions live in `docs/metrics.md` (T1.4). Whenever a definition changes: bump `metrics_version` and re-run evaluation.

---

# 12. Progress tracker (the agent updates this after every task)

Status values: `Not started` · `In progress` · `Blocked (reason)` · `Done` · `Skipped (reason)` · `Deferred (reason)` · `Not triggered` (T7.10 only). `Skipped`/`Deferred` are allowed **only** for Phase 4/5 tasks (T4.1–T5.4), only per Section 14, and only with the human's agreement. Phases 0–3, Phase 7 and Phase 6 are core and cannot be skipped. Fill date and commit hash when Done.

**Checkboxes:** the agent changes `[ ]` to `[x]` on a task row **only when its status is `Done` and every `Accept` command has passed**, in the same commit that updates the status, date and hash. Use `[-]` for `Skipped`/`Deferred` (Phase 4/5 only) and leave T7.10 as `[ ]` unless P5 triggers it. A phase box below is ticked only when every non-skipped task in it is `[x]` **and** the human has merged the phase branch (Section 0.5).

**Phase checklist**
- [ ] Phase 0 — Foundation and scenarios (T0.1–T0.4)
- [ ] Phase 1 — Core: state, safety, controllers, metrics (T1.1–T1.4)
- [ ] Phase 2 — RL environment and PPO (T2.1–T2.5)
- [ ] Phase 3 — Fair evaluation → **M1 reached** (T3.1–T3.2)
- [ ] Phase 7 — Network-wide control → **M2, final deliverable** (T7.1–T7.9; T7.10 only if P5)
- [ ] Phase 4 — Prediction (T4.1–T4.3) — may be `[-]` skipped/deferred
- [ ] Phase 5 — Virtual camera (T5.1–T5.4) — may be `[-]` skipped/deferred
- [ ] Phase 6 — Demo, quality, documentation, release (T6.1–T6.4)

| Task | Status | Date | Commit | Note |
|---|---|---|---|---|
| [ ] T0.1 Audit | Not started | | | |
| [ ] T0.2 Skeleton, config, tooling | Not started | | | |
| [ ] T0.3 SUMO client + TLS + suitability (M1 pilot junction) | Not started | | | |
| [ ] T0.4 Scenarios + cached pool | Not started | | | |
| [ ] T1.1 Traffic State | Not started | | | |
| [ ] T1.2 Safety layer | Not started | | | |
| [ ] T1.3 Controllers + runner | Not started | | | |
| [ ] T1.4 Metrics | Not started | | | |
| [ ] T2.1 Env | Not started | | | |
| [ ] T2.2 Env tests (gate) | Not started | | | |
| [ ] T2.3 PPO training (staged) | Not started | | | |
| [ ] T2.4 RL controller | Not started | | | |
| [ ] T2.5 RL sanity gate | Not started | | | |
| [ ] T3.1 Evaluation harness (M1) | Not started | | | |
| [ ] T3.2 Results gate — M1 milestone | Not started | | | |
| [ ] T7.1 Network TLS inventory + intended set (P4) | Not started | | | |
| [ ] T7.2 Multi-junction state, safety, controllers | Not started | | | |
| [ ] T7.3 Network scenarios + cached pool | Not started | | | |
| [ ] T7.4 Network metrics + baselines | Not started | | | |
| [ ] T7.5 Network RL env (gate) | Not started | | | |
| [ ] T7.6 Shared-policy PPO (staged ladder) | Not started | | | |
| [ ] T7.7 Network RL controller + sanity gate | Not started | | | |
| [ ] T7.8 Network evaluation harness | Not started | | | |
| [ ] T7.9 Network results gate — FINAL | Not started | | | |
| [ ] T7.10 Stage-4 fallback (ONLY if P5 selects it) | Not triggered | | | |
| [ ] T4.1 Prediction data | Not started | | | |
| [ ] T4.2 Dataset + baselines | Not started | | | |
| [ ] T4.3 Prediction model | Not started | | | |
| [ ] T5.1 Capture + labels | Not started | | | |
| [ ] T5.2 Pretrained YOLO test | Not started | | | |
| [ ] T5.3 Fine-tune (if needed) | Not started | | | |
| [ ] T5.4 Camera state + demo | Not started | | | |
| [ ] T6.1 Demo CLI | Not started | | | |
| [ ] T6.2 Quality pass | Not started | | | |
| [ ] T6.3 Documentation | Not started | | | |
| [ ] T6.4 Release | Not started | | | |

| Pending decision | Status |
|---|---|
| P1 Supervisor confirms headline metrics (M1 junction trips; M2 network-wide) | Pending |
| P2 Supervisor acknowledges SRS deviations | Pending |
| P3 M1 pilot junction choice (only if T0.3 triggers) | Not triggered |
| P4 Human approves intended TLS list (T7.1) | Pending until T7.1 |
| P5 Fallback level if shared PPO cannot cover all intended TLS (DEC-14 Stage 4) | Not triggered |

**Order:** 0 → 1 → 2 → 3 (**M1 reached**) → **7 (M2, the final deliverable)** → then 4 and 5 (either order, one at a time, each merged before the next) → 6. Phases 4 and 5 depend on Phase 1 only, not on PPO success or on Phase 7; they run after Phase 7 by default and are the first things cut (Section 14). Backend/DB/dashboard/optional features: not now.

---

# 13. Definition of done

**Core (always required): items 1–7 and 10–12.** Items 8 and 9 are required only if their phase was not explicitly marked `Skipped`/`Deferred` under the Section 14 cut lines; a skipped/deferred phase must be stated as such in Section 12, `docs/results.md`, `docs/limitations.md` and the release checklist (never silently omitted). The single-junction milestone (items 3–4) is **necessary but not sufficient**: without items 5–7 the project is not complete.

1. SUMO starts from the documented command with the intended map and no unexplained warnings.
2. Safety tests prove — for the M1 junction (T1.2) **and for every intended junction simultaneously** (T7.2): no conflicting greens, yellow on every change, min/max green enforced, fallback works, excluded TLS never commanded.
3. **M1:** fixed, rule-based and RL controllers run on identical scenarios and seeds (≥ 5 per scenario, all seven single-junction scenarios); results regenerate from documented commands.
4. **M1 results:** `docs/results.md` Part 1 reports the measured reduction from the final seed block (run once on the frozen model) for metric B (headline, provisional) and A, per scenario, `low` separate, common-trip beside censored time and completion rates, with limitations — labelled "milestone, not the final result".
5. **M2 scope:** the intended TLS list is documented (`docs/network_tls.md`), human-approved (P4), frozen before dev evaluation, with every excluded TLS and its reason.
6. **M2 AI control of all intended traffic lights:** in the final-seed `rl` runs, `summary.csv` shows `n_tls_ai == n_tls_controlled == len(network.controlled_tls)` (`ai_coverage = full`), with every junction's `ppo_tick_share ≥ eval.ai_coverage_min_share` in `junctions.csv` — i.e. PPO supplied the executed decisions at every approved intended TLS. If that was not achieved, the deliverable is explicitly labelled with its DEC-14 level (Stage 4 fallback, AI-coverage fraction stated, P5 decision recorded) and is **not** described as full AI control.
7. **M2 network-level results:** `docs/results.md` Part 2 reports, from the final network seed block (run once on the frozen model), Metric N (network-wide travel time), measured reduction, `target_met` yes/no, common-trip beside censored and completion rates, per-scenario rows with `net_low` separate, the per-junction congestion table, and limitations.
8. **Prediction (Phase 4, M1 junction):** held-out MAE/RMSE vs baselines on the stated split profile (`full` or `reduced`), **or** explicitly marked Skipped/Deferred with the reason.
9. **Virtual camera (Phase 5, M1 junction):** independent of PPO and Phase 7; measured precision/recall/count error/FPS vs TraCI ground truth on SUMO-rendered frames, labelled a simulated-vision prototype (not real-world accuracy), **or** explicitly marked Skipped/Deferred. The camera-driven control demo (T5.4b) may be deferred on its own while T5.2 metrics are still reported.
10. Tests, lint (whole repo, justified exclusions only), README and docs pass; no secrets, no unused DB/web dependencies, no large artifacts committed; no database, backend or dashboard code exists.
11. SRS deviations are documented (`docs/srs_deviations.md`); pending decisions P1/P2/P4/P5 are listed honestly.
12. Report, PPT and demo use only validated numbers from `results/`; the one-command demo runs for both families, and the network `rl` demo shows AI control across the intended TLS (or states the DEC-14 level reached).

---

# 14. Time plan and cut lines (for the human's exams and placements)

The human should replace the weeks with real dates; the agent does not change the cut lines without asking. The network phase makes the core about five weeks; if the deadline is shorter, tell the agent now so the staged ladder (DEC-14) and cut lines are applied from the start.

| Week | Target | Notes |
|---|---|---|
| 1 | Phase 0 + Phase 1 | First baseline numbers (fixed vs rule). T0.1 may reveal a Python/dependency problem — fix it first. |
| 2 | Phase 2 | Smoke → pilot → overnight main PPO (resumable; charger on, no sleep). |
| 3 | Phase 3 → **M1 reached** | Single-junction result; start T7.1 (inventory, P4 approval). |
| 4 | Phase 7: T7.2–T7.6 | Multi-junction safety/controllers, network scenarios, baselines, env gate, staged shared-PPO training (overnight). |
| 5 | Phase 7: T7.7–T7.9, then Phase 6 (lean) | **After T7.9 you have the final headline result.** Docs last; keep screenshots and `report_inputs.md` handy. |
| 6 (if time) | Phase 4 and/or Phase 5 | Optional extras on the M1 junction; Phase 6 docs updated afterwards. |

**Cut lines (decide with the agent, in this order):**
1. **Phases 4 and 5 are cut first.** If M1 is not reached by the end of week 3 (or the deadline is tight), mark Phase 4 and Phase 5 `Skipped`/`Deferred` without starting them. If time remains afterwards, Phase 4 may run in the `reduced` profile with baselines + Random Forest only, and Phase 5 as T5.1, T5.2, T5.4(a) only (T5.3 and the control demo T5.4(b) deferred; a failed T5.2 gate is reported honestly).
2. **Within Phase 7, reduce cost, never coverage:** fewer training scenarios, shorter episodes, larger decision interval, one PPO seed, fewer evaluation seeds only if the human agrees and it is documented (DEC-14 Stage 3). The intended TLS list is not shrunk to save time unless the human changes it before dev evaluation (P4).
3. **If shared PPO cannot cover all intended TLS or pass T7.7 within budget → stop and ask (P5).** Options: extend budget; Stage 4 fallback (task T7.10: partial-AI hybrid, or validated multi-junction rule-based controller plus M1 PPO), always labelled with the level reached and AI-coverage fraction. Single-junction control is never silently reported as the final result.
4. **Never cut:** Phases 0–3 (M1), Phase 7 with a validated, honestly labelled result in `docs/results.md`, and lean Phase 6 (T6.1–T6.4, incl. T6.3 docs) over whatever exists.
