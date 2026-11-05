# STMS — Agent Build Roadmap (FINAL — v6.1 autonomous-first, single persistent work branch; scope unchanged from v5.0: single-junction milestone → network-wide AI control → read-only file-based dashboard; no computer vision, no prediction model, no database, no backend)

**Project:** Smart Traffic Management System for Urban Congestion (Bengaluru HSR Layout SUMO map)
**Final objective:** AI control of **all intended (suitable) traffic-light junctions in the SUMO map**, evaluated network-wide. Single-junction control is the **initial milestone (M1)** only and is never the final result (DEC-12).
**Requirements source:** `docs/SRS_Smart_Traffic_Management_System.docx` (SRS v1.0). IDs like `FR-CTL-06` refer to it.
**Repo:** `https://github.com/hannanahmedqureshi786-eng/smart-traffic-management-system` (branch `main`). **Work happens on the single local branch `agent/autonomous-build`; nothing is pushed unless the owner explicitly authorizes it (Section 0.5).**
**Primary agent:** Codex in VS Code, running **locally** on the owner's Windows laptop. The roadmap is agent-neutral (no tool-specific features); **only one agent works at a time** (Section 0.9).

> **This file is an autonomous execution plan.** Read **Section 0 and Section 12 completely**, then execute every task from the first one that is not `Done` through T6.4 **without waiting for the human**: no "continue" prompts, no per-task approvals, no merge or push approvals. The agent decides routine technical matters itself, uses the defaults in Section 2 for every pending decision, and contacts the human **only** under Section 0.6 (genuine blockers) and in the final report. Where any other sentence in this document seems to require waiting for the human, Section 0 wins.

---

## H. How the human starts the agent (once, nothing else needed)

1. Put this file at `docs/STMS_Agent_Roadmap_FINAL.md` (replace the old copy) and keep the SRS at `docs/SRS_Smart_Traffic_Management_System.docx`. Leaving the replaced file uncommitted is fine; the agent commits it (step A0).
2. Open the repo in VS Code with Codex and send this **single** prompt:

> Read `docs/STMS_Agent_Roadmap_FINAL.md` Section 0 and Section 12, then execute the whole roadmap autonomously from the first task that is not Done through Phase 6, following Section 0. Do not wait for "continue" or any approval. Commit to the single local branch `agent/autonomous-build` and do not push. Ask me only for genuine blockers (Section 0.6) and finish with the final report of Section 0.1.

3. The human may use the laptop normally. Edits the human makes while the agent runs are tolerated and never discarded (Section 0.9). The human is needed afterwards only for: answering a consolidated blocker list (if any), and the supervisor items P1/P2 (Section 2), which never stop execution. **Git:** Codex commits only to the local branch `agent/autonomous-build` and performs the single local merge into `main` itself at T6.4 (Section 0.5). Nothing is pushed to any remote unless you explicitly authorize it in chat. **Do not switch branches, check out other commits, or run Git commands that change the repository while Codex is running** — it assumes it stays on `agent/autonomous-build`; wait for the final report (or stop the agent first) before switching to `main` or pushing. Reading files and normal editing stay fine (Section 0.9). If a branch switch happens anyway, the agent returns to `agent/autonomous-build` on its next start (Section 0.12) and never discards your changes.

### A0 — One-time adoption and branch reconciliation (automatic, idempotent, not a numbered task)
**Skip A0 entirely** only if `AGENTS.md` contains the marker `roadmap-v6.1` **and** `HEAD` is on `agent/autonomous-build` **and** every commit hash listed as `Done` in Section 12 is an ancestor of `HEAD` (cheap loop of `git merge-base --is-ancestor <hash> HEAD`); then go straight to the first non-`Done` task. Otherwise, in one pass:
1. **Safety first (nothing may be lost):** note the current branch and `git status --short`. If the working tree has uncommitted changes, they travel with a plain `git switch`; if Git refuses the switch, run `git stash push --include-untracked -m a0-owner-wip`, switch, and re-apply with `git stash apply` (never `pop`; the stash is kept until the changes are verified present, and conflicts are resolved by keeping both sides). If `agent/autonomous-build` already exists, mark its current tip with a lightweight tag `a0-pre-reconcile-<UTC timestamp>` (a rollback point; tags are never deleted).
2. **Branch and reconcile:**
   - *Branch does not exist:* create `agent/autonomous-build` from the local branch whose history contains the most recent completed work (an unmerged `agent/phase-1-core` if it holds the latest `T1.x` commit, otherwise `main`).
   - *Branch exists:* switch to it, then find every other local branch tip (`main`, `agent/phase-*`) and check with `git merge-base --is-ancestor <tip> agent/autonomous-build`. For each tip that is **not** an ancestor, bring its commits in with `git merge --no-ff <tip>` **on `agent/autonomous-build`** (a fast-forward is fine when the branch is simply behind; if it has diverged, the merge combines both histories). Resolve conflicts by keeping the content of both sides' completed work, never by discarding commits. Never `reset`, `rebase`, force-move or delete a branch, and never touch `main` (merging `main` *into* the work branch is allowed; the reverse is T6.4 only, 0.5).
   - *Verify:* every `Done` commit hash in Section 12 must now be an ancestor of `HEAD`. A hash that is reachable from no local branch is searched for with `git reflog`/`git branch -a --contains`; if it cannot be found anywhere, record it in `docs/decisions.md`, re-run that task's `Accept` commands, and set its row to `Not started` only if they fail.
3. **Phase 1 checkpoint (once, on the reconciled branch):** `ruff check .` and `pytest -q`; fix failures (0.6.3).
4. **`AGENTS.md`** (≤ 40 lines, containing the marker `roadmap-v6.1`): "read Section 0 + Section 12 of the roadmap; run autonomously on `agent/autonomous-build`; no push without explicit authorization; ask only per Section 0.6; real outputs only; never modify `SUMO/No_Polygon_Map`; never touch seeds 5000+/6000+ for tuning; never claim full AI coverage without evidence". Remove older wording such as "one task at a time and wait", "ask when blocked" or per-phase branch/merge rules.
5. Add any missing keys marked *(new v6)* in Section 3 to `config/stms.yaml`; create `docs/decisions.md` (tables "Autonomous decisions" and "Open blockers") if missing, and log the reconciliation (tag name, branches merged) there.
6. **One commit** `A0: adopt autonomous roadmap v6.1` (explicit paths: roadmap/SRS copies, `AGENTS.md`, config, `docs/decisions.md`, the Phase 1 tracker tick) and continue directly with the first non-`Done` task. The reconciliation merges of step 2 are their own commits and are not repeated.

---

## A. Scope of this version

**Milestones (DEC-12):**
- **M1 — single-junction milestone (Phases 0–3):** develop and validate the whole stack on **one suitable pilot junction**: SUMO + TraCI, safety layer, fixed-time / rule-based / PPO controllers, fair evaluation. M1 results are reported as a milestone, **not** as the final result.
- **M2 — network-wide control (Phase 4, the FINAL DELIVERABLE):** extend control to **all intended traffic-light junctions** (every TLS that passes the T4.1 suitability check), each behind its own safety layer, and evaluate congestion and travel time **across the whole map**. The final deliverable must demonstrate **AI (PPO) control of all intended traffic lights**. If full-map PPO cannot be reached within budget, the staged ladder of DEC-14 is applied **automatically**; any result below full AI coverage is labelled honestly with its coverage fraction and is never declared as full.

**IN SCOPE NOW:** SUMO + TraCI · safety layer · fixed-time, rule-based and PPO-RL controllers · fair evaluation of the 10% target (M1 junction-level, M2 network-wide) · **multi-junction control of all intended TLS** · **read-only, file-based dashboard (Phase 5, DEC-15)** showing simulation status, signal states/phases, queues and waiting times, congestion and flow metrics, fixed/rule/PPO comparison, evaluation results and historical experiment results from saved CSV/JSON · CSV/JSON persistence · reproducible CLI demo · docs. **All traffic states come from SUMO via TraCI.**

**REMOVED FROM SCOPE (not deferred, not optional):** OpenCV and computer vision; YOLO and camera-based vehicle detection; any separate traffic-prediction / future-traffic model (and prediction-as-RL-input); any database. The original assignment mentions cameras and traffic prediction; they are **not implemented and must never be presented as implemented**. The PPO controller acts on the SUMO/TraCI traffic state only.

**NOT BUILT — DO NOT START, DO NOT CREATE FOLDERS FOR:**
- FastAPI/REST backend, WebSocket, authentication/JWT/roles, audit log (the dashboard reads files, DEC-15)
- Any database (PostgreSQL / SQLite / SQLAlchemy / Supabase / other); persistence is CSV/JSON files only (DEC-04)
- Dashboard features beyond the views listed in T5.2–T5.3 (including manual override / remote control of signals, login, roles)
- Optional emergency-vehicle priority and **explicit communication-based inter-junction coordination (green waves, message passing)** — only if the human asks later. (Multi-junction *control* is in scope via Phase 4; coordination there is implicit through a shared policy.)

**Teammates:** none. Pre-existing teammate code (e.g. `Ai/analytics/`) is ordinary project code: linted and tested like everything else (Section 0.7); new code must not depend on it.

**Future-proofing (cheap, mandatory):** keep `IntersectionState.to_dict()` JSON-serialisable, keep the `Controller` interface clean, and keep the safety layer's `Accepted | Rejected(reason)` API, so a backend could be added later without refactoring. Build nothing else for it.

**SRS deviations to record in `docs/srs_deviations.md` (T6.3)** (SRS v1.0 is marked approved; supervisor sign-off is item P2 and never blocks execution):

| SRS item | Status | Reason |
|---|---|---|
| FR-DSH-* (dashboard) | Implemented in Phase 5 as a **read-only, local, file-based** dashboard limited to the views of T5.2–T5.3; no REST/WebSocket. The exact FR-DSH items covered are checked against SRS §3.1 (change-log ambiguity A-3) | Scope decision (DEC-15) |
| FR-OVR-*, FR-AUT-*, FR-DAT-*, §3.1/§3.4 (REST/WS, authentication, database, manual override) | **Not implemented** — no backend, authentication or database; CSV/JSON files are the persistence | Scope decision (DEC-04) |
| FR-CV-* (computer vision, camera detection, ROI, annotated video) | **Removed from scope** | Scope decision |
| Camera-sourced traffic state (camera part of FR-STA-*) | Not implemented; every traffic state comes from SUMO via TraCI | Scope decision |
| FR-PRD-01..05 (traffic prediction) | **Removed from scope** — no prediction model | Scope decision |
| FR-SIM-05 (multiple vehicle types) | Supported by config, **not used** | DEC-07 |
| FR-SIM-02 / FR-CTL-10 (multiple controlled junctions) | Implemented in Phase 4 for all **intended** (suitable) TLS; unsuitable TLS are listed and stay on SUMO's native program for every controller; coordination is decentralised (shared policy) | Suitability and compute |
| §3.2 explicit SUMO detectors | Lane-level TraCI queries used instead | Equivalent, simpler |
| NFR-PRF-06 "average travel time" | Provisional headline is the **controlled-junction trips** metric for M1 (DEC-01) and the **network-wide all-trips** metric for the final M2 result (DEC-12); censored results and completion rates always beside it | DEC-01, DEC-12 |
| NFR-PRF-04 (vision FPS) | Not applicable | Scope decision |
| NFR-PRF-02/03 (dashboard / REST latency) | Dashboard latency measured locally in T5.4; REST latency not applicable | DEC-15 |
| FR-EMG-* | Deferred/optional | Scope |

---

## 0. Operating rules for the agent (mandatory; these override any conflicting sentence elsewhere)

### 0.1 Autonomous execution contract
1. **Run continuously** from the first task that is not `Done` (Section 12) through T6.4. Never wait for "continue", for review, or for any approval. Finishing a task or a phase checkpoint is followed immediately by the next task.
2. **Per task:** (a) check `git status` only at session start and before staging paths you did not create (0.9); (b) read the task block and only the existing files it touches (no repo-wide re-scans, 0.10); (c) implement; (d) run the task's `Accept` commands; (e) troubleshoot adaptively (0.6.3); (f) update the Section 12 row (status, date, commit hash, ≤ 1-line note) in the same commit; commit with explicit paths to `agent/autonomous-build` (0.5); (g) go on to the next task.
3. **Routine technical decisions belong to the agent:** library/API choices, module structure inside the allowed folders (0.3), hyper-parameters within the documented ranges, test design, bug-fix strategy, threshold tuning on the allowed seed blocks, dependency workarounds, justified compatible dependency additions and implementation changes (0.7), resource scheduling, and the defaults for every pending decision (Section 2 register). Record only non-trivial choices as one line in `docs/decisions.md` ("Autonomous decisions").
4. A task is `Done` only when **all** its `Accept` checks pass. Never weaken a check, a safety rule or a definition to get a pass. If a check cannot be met, follow 0.6 (fix, fallback, or blocker handling) and label the outcome honestly.
5. **Communication is minimal:** no per-task reports in chat (at most one short progress line). Progress lives in Section 12; experiments in `docs/experiment_log.md`; decisions/blockers in `docs/decisions.md`. Keep task notes short; quote real trimmed output only where it evidences a pass/fail.
6. Record every experiment, including failed and abandoned ones, in the append-only `docs/experiment_log.md` (date, task, what was tried, seeds used, result, decision).
7. **Final report** (only at the end of the whole roadmap, or when nothing independent is left to do — 0.6): ≤ 30 lines — task/phase status; M1 and M2 headline numbers exactly as in `docs/results.md` with "provisional" labels; the `AI coverage: n/N (full|partial|none)` line; the controller level reached (DEC-14); the autonomous decisions that matter; open blockers, each with the exact question or action needed; supervisor items P1/P2 still pending.

### 0.2 Honesty rules (most important)
- **Never invent or hand-edit results.** Every number in `results/` and docs must come from a script you actually ran. Detect machine specs, versions and timings; never invent them.
- The 10% travel-time reduction is a **target, never an assumed result**. Report what is measured, even if it is 0% or negative.
- Never claim something works unless you ran it. If you could not run something (e.g. SUMO-GUI, a browser), say so.
- A script finishing without error does **not** prove correctness; check outputs against the acceptance criteria.
- Existing code and artifacts (RL files, saved models, old baseline numbers, old scripts) are **unverified until tested** (T0.1 did this; re-test whenever you depend on them). Do not call them working or "the baseline" without evidence.
- **Never claim full network-wide AI coverage without evidence:** the words "full network-wide AI control" are allowed only where `summary.csv` shows `ai_coverage = full` for the final-seed `rl` runs and `junctions.csv` confirms every junction (DEC-14, T4.9).
- Autonomy never relaxes honesty: failed gates, `target_met = false`, partial coverage and blocked items are reported as such.

### 0.3 File rules
| Area | Rule |
|---|---|
| `SUMO/No_Polygon_Map/*` (existing network/config) | **Never modify.** All derived/new SUMO files go in `SUMO/derived/` and `SUMO/scenarios/`. |
| Existing `Ai/rl/models/ppo_traffic.zip`, `Ai/rl/ppo_evaluation.csv` | Preliminary artifacts. **Do not delete or overwrite**; label them (working / broken / unverified) with evidence. New models go to new versioned folders. |
| `Ai/rl/*.py` | May be rewritten; keep filenames `traffic_env.py`, `test_env.py`, `train_ppo.py`, `evaluate_ppo.py`. |
| Any other existing file | May be edited when a task needs it. Inspect first, keep changes minimal. |
| New folders you may create | `Ai/common/`, `Ai/controllers/`, `Ai/evaluation/`, `dashboard/`, `results/`, `docs/`, `scripts/`, `tests/`, `config/`. **Nothing else** (no `backend/`, `frontend/`, `Ai/runtime/`, no database files). |

### 0.4 Output hygiene
- Never overwrite a previous result. Each run writes to `results/raw/<run_id>/`, `run_id = <YYYYMMDD-HHMMSS>_<controller>_<scenario>_s<seed>`.
- Aggregates go to `results/summary/` (schemas in Section 11); figures to `results/figures/`; job records to `results/jobs/` (0.8).
- Models: `Ai/rl/models/ppo_v<N>/model.zip` + `config.json` (M1) and `Ai/rl/models/ppo_net_v<N>/…` (M2; same files; `config.json` also records the intended-TLS list hash and slot order). `config.json` holds hyper-parameters, reward weights, git commit, seeds, library versions, training wall-clock. Never overwrite an accepted model; increment `N`.
- **Commit** the final accepted model and its `config.json`, plus `results/summary/*.csv` and `results/figures/*.png` used in the report.
- Do **not** commit: videos, model files > 50 MB, `results/raw/`, `results/jobs/`, `SUMO/scenarios/*/seed_*/` (regenerable), `.env`, `__pycache__`, TensorBoard logs, virtual environments (all in `.gitignore`, set in T0.2; add `results/jobs/` if missing).
- No secrets in the repo. `.gitattributes` has `* text=auto`.

### 0.5 Git workflow (single owner, one persistent branch, local only)
- **Branch:** all work is committed to one persistent local branch, `agent/autonomous-build` (created in A0 or at first start). There are no per-phase branches, no branch switching during the run (A0's one-time reconcile at the start is the only exception: it merges other local branch tips *into* this branch, never rewriting or discarding commits), and no direct commits to `main`.
- **Commits:** one per completed task, `T<id>: <imperative summary>`, containing the code, tests and the Section 12 row update; stage **explicit paths** (never `git add -A`/`.`). A fix to earlier work found later is `T<id>-fix: …`. Commit only finished, passing work (no WIP commits, except the `owner-wip` snapshot of 0.9); extra docs/experiment commits are optional.
- **Phase checkpoint (replaces the old phase gate; no Git operations):** at the end of each phase run whole-repo `ruff check .`, `pytest -q`, `pytest -m sumo <this phase's SUMO test files>` and `python scripts/check_zombies.py`; fix failures (0.6.3); tick the phase box in Section 12 and commit. A phase with `Blocked`/`Partial` tasks is check-pointed once its other tasks pass; later phases proceed (0.11).
- **Merge to `main` only when genuinely necessary** — default is never. Necessary means: (a) **T6.4 release**, where `main` must carry the deliverable and the tag (the agent itself performs one local `git merge --no-ff agent/autonomous-build` into `main` after the final checkpoint; if `main` gained commits meanwhile, merge `main` into the branch first); (b) the owner asks; or (c) a task provably cannot work from the branch. Record the reason in `docs/decisions.md`.
- **Remote:** never `git push`, `fetch` or `pull` unless the owner explicitly authorizes it in chat; without authorization there are no remote operations (and therefore no remote failure modes).
- Never force-push, rewrite history, delete branches, or use `git reset --hard`/`git clean` on work that is not the agent's own. The release tag `v1.0-ai-core` is created by the agent on `main` in T6.4.

### 0.6 Blocker policy (replaces all old "stop and ask" rules)
**6.1 Not blockers — the agent resolves them itself** (log in `docs/decisions.md`/`experiment_log.md`, never ask): failing tests or lint; surprising measurements (RL worse than fixed-time, > 5% teleports, identical metrics across controllers, a mismatch in a cross-check) → diagnose and fix, adaptively per 6.3; dependency or Python-version problems (DEC-11 fallbacks); time or compute budgets (staged ladders DEC-10/DEC-14); demand or threshold tuning on the allowed seed blocks; a TLS count above `network.max_intended` (a planning threshold, not a cap — DEC-13); git housekeeping (single local branch, no remote operations, 0.5); the pending decisions P3–P6 (defaults in Section 2); owner edits in the working tree (0.9).

**6.2 Genuine blockers — the only reasons to involve the human:**
- **B1 Missing tool/dependency** (SUMO, `duarouter`, a compatible Python/`torch`, a display for SUMO-GUI) that cannot be installed or worked around from official sources with the permissions available.
- **B2 Permission/credential problem** that prevents a *required* action (filesystem permission, protected path). Remote operations are not performed (0.5), so they cannot block.
- **B3 Irreversible destructive action** that a task would need: deleting or overwriting protected artifacts (0.3) or accepted final results, modifying `SUMO/No_Polygon_Map`, force-push/history rewrite, deleting branches.
- **B4 Unavoidable scope conflict:** the only way to meet a task needs a prohibited component (database, backend/API, OpenCV/YOLO, prediction model), or two acceptance criteria contradict each other after a documented attempt to reconcile them.
- **B5 Mandatory supervisor approval:** only P1/P2. They change **labels** ("provisional"), never execution, so they do not stop work.
- **B6 Further troubleshooting is unproductive and no documented fallback exists** (6.3).

**6.3 Adaptive troubleshooting (no fixed attempt count).** For any failure: reproduce it → read the real error/output → form a root-cause hypothesis → fix → re-run the failing check; if it still fails, try a **materially different** approach (different cause, algorithm, tool, library version, parameterisation, workaround, or the task's documented fallback) — never repeat the same fix. Prefer cheap diagnostics (minimal repro, logging, unit-level isolation) before expensive reruns. Keep one line per approach tried in `docs/experiment_log.md` (or `docs/decisions.md` for non-experiments) so approaches are not repeated, even after a restart. **Stop working on a problem only when** (i) it is *unproductive*: no new credible hypothesis remains, or several materially different approaches (typically 4–6) left the failure signature and validation metrics unchanged, or further effort is clearly out of proportion to the task's value and a documented fallback exists; (ii) it is *unsafe*: continuing would violate an invariant (6.5) or need a prohibited/destructive step; or (iii) it is *externally blocked* (B1–B4). Then apply the task's documented fallback if one exists (e.g. the T2.5/T4.7 deviation labelling, T4.10, the DEC-10/DEC-14 cost reductions); otherwise block the task per 6.4. RL gates: work through the listed levers and their combinations while validation keeps improving, and stop when two consecutive rounds bring no validation improvement. Protocol limits that protect fairness (seed blocks, "run the final block once", "each remaining lever once on dev seeds") are not troubleshooting limits and stay as written.

**6.4 Handling a blocker.** Mark the task `Blocked (reason)`, add a row to "Open blockers" in `docs/decisions.md` (id, task, what failed, approaches tried, the **exact question or action needed**, and the safe default that applies if the owner does not answer), **do not stop**: continue every task whose hard dependencies allow it (0.11). Re-test open blockers once cheaply at the pre-release sweep (T6.2). Contact the human with one consolidated list **only when nothing independent is left to do** (or at the final report) — never at the first blocker, never one question at a time.

**6.5 Invariants (never relaxed, never "asked about"):** no conflicting greens / yellow on every change / min–max green enforced; protected files; seed-block discipline (DEC-09); no fabricated results; no prohibited components. A violation is a bug to fix, not a question.

**Human-approved amendment (2026-10-24, retained):** For the unchanged-demand native-signal baseline in T0.4, a teleport share above 5% is recorded as a failed baseline performance result and does not block T0.4 or implementation through PPO connection. Preserve the measured results; do not reduce demand or mark the baseline as passed. Evaluate the >5% criterion after PPO is trained and connected to SUMO, using identical demand and seeds for fixed-time and PPO and reporting teleports alongside completions, queues, waiting time and time loss (T2.5/T3.1). It supersedes only the native-baseline >5% stop condition and the T1.4 fixed-time teleport check. The same principle (record, never hide, never reduce demand to pass) applies to the network baseline teleport re-check in T4.4 after demand design is frozen (T4.3).

### 0.7 Code quality
- Python version: **whatever T0.1/T0.2 verified as the working interpreter** (project minimum 3.10), in a project virtual environment; interpreter path and version are recorded in `docs/PROJECT_FACTS.md`.
- PEP 8, type hints and docstrings on public functions.
- **`ruff check .` and `pytest` cover the whole repository.** Exclusions only when justified: each needs a one-line reason in `pyproject.toml` **and** an entry in `docs/lint_exclusions.md`. No blanket ignores; prefer fixing the code.
- Logic modules get pytest unit tests in `tests/`. Tests needing SUMO are `@pytest.mark.sumo`, run with `pytest -m sumo`; default `pytest` excludes them (`addopts = -m "not sumo"`). Use `pytest-timeout` on SUMO tests.
- No hard-coded absolute paths: `config/stms.yaml` + `pathlib`. Must work on **Windows and Ubuntu** (Python CLIs only; no bash-only scripts). `Ai/`, `scripts/`, `dashboard/` have `__init__.py`; the project is installed with `pip install -e .`.
- **All randomness via explicit `seed`.** Same seed + config ⇒ same result. Record seeds in every output.
- SUMO connections: unique label and free port (`sumolib.miscutils.getFreeSocketPort()`), closed in `finally`. Zombie check = `python scripts/check_zombies.py` (psutil; non-zero exit if `sumo`/`sumo-gui` processes remain; the agent may terminate zombie processes that its own runs created).
- Logging via `logging`, not bare `print`, except CLI summaries.
- **Dependencies and implementation changes (justified, compatible, minimal):** the agent may add, upgrade or swap a package, or change a task's implementation approach (module layout, algorithm, data structure), when needed to meet a task's `Accept` criteria, fix an incompatibility, or materially reduce risk, runtime or complexity. Conditions: compatible with the active Python and the lock file, permissive licence, installable from official indexes, **not** a removed feature (database/ORM, web/API server, OpenCV/YOLO/vision, prediction/forecasting) and no unnecessary complexity (prefer the stdlib and the existing stack). Update `requirements*.txt` and `requirements.lock.txt` and add one line to `docs/decisions.md`. Such changes never alter acceptance criteria, safety rules, scope, seed blocks or metric definitions; `streamlit` (dashboard only) remains the only web-facing package.

### 0.8 Long-running jobs (training, evaluation, data collection) — resumable and unattended
- Launch anything expected to take > 10 minutes as a **detached background process** writing a log under `results/` (Windows: `Start-Process python -ArgumentList … -RedirectStandardOutput …`; Ubuntu: `nohup`). Use `scripts/job_runner.py` (created at the first long job, T2.3; Python CLI) to start a job, write its record `results/jobs/<job_id>.json` (command, pid, start time, log path, output dir, `state`, exact **resume command**) and update `state` at the end.
- **Keep the laptop awake without touching system settings:** `scripts/keep_awake.py` (created with the job runner) holds the OS "stay awake" request (`SetThreadExecutionState` on Windows, `systemd-inhibit`/no-op elsewhere) for the life of the job. Do not ask the human to adjust power plans, plug in chargers or keep the lid open; if the OS still suspends the job, the resume protocol (0.12) recovers it.
- Every long job is **resumable** (checkpoints / skip-if-complete run folders / `--resume`) and logs progress with an ETA. Estimating wall time before a job is for the agent's own scheduling and is written to `docs/experiment_log.md`; it needs no approval.
- **Polling is cheap:** sleep between polls (start at 60 s, back off to 10 min), read only the log tail and the job record, and never re-print whole logs. Use the waiting time for independent tasks (0.11) instead of idling.
- **Parallelism:** independent SUMO runs (evaluation grid, scenario generation, baselines) run as parallel processes up to `jobs.parallel_runs`; PPO training is one process per run. Each process has its own port/label (0.7).

### 0.9 Single-owner workflow (tolerates owner edits)
- Exactly **one agent** edits the repo at a time; no parallel branches; no second agent session.
- If `git status` shows changes the agent did not make, **do not stop and do not discard them**: leave unrelated files alone (explicit-path staging keeps them out of commits). If they overlap files the current task must edit, first snapshot them as a commit `owner-wip: <paths>` on the active branch (non-destructive, reversible), then proceed. Never use `git reset --hard`, `git checkout -- .`, `git clean` or `git stash drop` on the owner's changes.

### 0.10 Efficiency (tokens and runtime)
- **Read narrowly:** keep Section 0 and Section 12 in mind; read only the block of the current task (and the Section 2/3/11 rows it cites). Do not re-read this whole file per task.
- **Test narrowly while working:** run the task's own `Accept` commands; run the whole-repo `ruff check .`/`pytest -q` and the phase's SUMO tests at phase checkpoints (0.5) and after cross-cutting edits; run the full `pytest -m sumo` once in T6.2.
- **No repeated scans or setup:** machine/Python/SUMO facts come from `docs/PROJECT_FACTS.md` (never re-detected unless a command fails); re-read a file only if it changed; one repo-wide search per question; run only the tests affected by a change (whole-repo runs only at checkpoints and T6.2); no re-install if imports already work; no confirmation steps, duplicate commits or separate "status" commits.
- **Cap tool output:** pipe long outputs through `tail`/`head`/`Select-Object -Last`, summarise logs, never paste full CSVs; write detail to files.
- **Never redo finished work:** skip-if-complete run folders, cached scenario pools, cached model/validation results, reuse measured timings (T1.4, T4.4) for estimates. Never regenerate artifacts whose manifest hash matches.
- **Batch edits** (several files per tool call), reuse code from the single-junction modules for the network (parametrise by `tls_id`), and prefer deterministic scripts over interactive exploration.
- **Spend compute where it matters:** smoke → pilot → main (DEC-10/DEC-14); abandon a variant early when validation clearly stalls; run evaluation grids in parallel (0.8).
- Keep documents concise; tables over prose; no duplicated explanations across docs (link instead).

### 0.11 Dependencies and blocked work
- Each task's `Depends on` lists **hard** dependencies (the task cannot be done without them). `Soft:` lists nice-to-have inputs: if the soft dependency is unavailable, use the stated default, record it, and continue.
- Default order is numeric. If a task is `Blocked`, **do not stop**: pick the next task whose hard dependencies are `Done` (or `Partial`) and continue; return to the blocked one when its blocker clears or at the T6.2 sweep.
- **Partial:** a task whose code and tests pass but whose real-data/evidence step waits on an unavailable predecessor is `Partial (pending: <item>)`. It is completed (and set to `Done`) as soon as the item exists. `Partial` counts as satisfying a dependency only for code-level tasks, never for result or evidence tasks (T3.2, T4.9, T6.4).
- Work that is always independent of PPO outcomes and may proceed whenever PPO is blocked: network inventory/safety/scenarios/baselines (T4.1–T4.4), the network RL env (T4.5), fixed/rule parts of the evaluation harnesses (T3.1, T4.8), the dashboard data layer, status files and views on synthetic fixtures (T5.1–T5.4), and docs/quality work (T6.2–T6.3 on what exists).
- Out-of-order execution needs no branch operations: simply continue on `agent/autonomous-build`.

### 0.12 Resume protocol (sessions may end, laptops sleep)
On every (re)start of the agent, before anything else: read Section 12; `git status --short` and the current branch (switch to `agent/autonomous-build` if needed); list `results/jobs/*.json` and, for each job with `state = running`, check whether its pid is alive — if alive, keep polling; if dead and incomplete, run its recorded resume command; then continue with the first task that is not `Done`. All state needed to continue lives in Section 12, `docs/decisions.md`, `docs/experiment_log.md`, `results/jobs/` and git — never rely on chat memory.

---

## 1. Target repository layout

```
smart-traffic-management-system/
├── AGENTS.md                      # short rules + pointer to this roadmap (A0)
├── README.md  requirements.txt  requirements-dashboard.txt  requirements-dev.txt
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
├── dashboard/                     # read-only file-based dashboard (Phase 5): data_loader, app, views/
├── results/{raw,summary,figures,jobs}/   # CSV/JSON only; raw/<run_id>/ also holds status.json (Section 11)
└── docs/ (incl. decisions.md, experiment_log.md)   scripts/ (incl. job_runner.py, keep_awake.py)   tests/
```
(Pre-existing folders such as `Ai/analytics/` stay where they are.)

---

## 2. Design decisions

| ID | Decision | Value |
|---|---|---|
| DEC-01 | **Headline metric for the 10% claim (PROVISIONAL)** | **Metric B** = average travel time of trips whose **planned route actually uses a movement controlled by the junction's traffic light**, i.e. the route contains a consecutive edge pair `from_edge→to_edge` that is a TLS-controlled connection (list of controlled movements from T0.3). Merely having an incoming edge in the route is **not** enough. Membership is decided from the route file, so it is identical for every controller. **Metric A** = all trips in the network, always computed and shown next to B. Evaluation scenarios: `balanced, directional_ns, directional_ew, low, medium, heavy, rush_hour`. **Aggregation (documented in `docs/metrics.md` and `docs/results.md`):** per (scenario, seed) improvement % on the common-trip set → mean over seeds per scenario → **headline = unweighted mean over the six non-`low` scenarios**. The **primary findings** `medium`, `heavy`, `rush_hour` are always shown prominently, separately and in the same table. `low` is its own row and is **never** part of the headline mean. A pooled-trips aggregation is reported as a sensitivity check. Aim for ≥ 30% of trips through the controlled junction in every scenario designed to evaluate it. **Survivorship-bias rule:** the primary comparison keeps the completed **common-trip** set (trips completed under all three controllers), but every table reports beside it the **censored** average travel time (all scheduled trips in scope; unfinished trips counted up to the end of the run) and the **completion rate** per controller. The 10% reduction is a target, not an assumed result. Until the supervisor confirms the metric (P1), every document calls it "provisional". |
| DEC-02 | Baseline | Our `FixedTimeController` (30 s green, 3 s yellow) through the safety layer (FR-CTL-01). SUMO's native program is recorded only as a sanity reference. |
| DEC-03 | RL action space | `Discrete(4)` = {0 keep, 1 switch to next green phase, 2 hold longer (+5 s), 3 hold longer (+10 s)} per SRS 4.6.2. One env step = `decision_interval_s` sim-seconds (+5/+10 s extra for actions 2/3) — **M1 single-junction env only**. In the network env (T4.5) all junctions share one simulation clock, so actions 2/3 become hold-lockouts (DEC-14). |
| DEC-04 | Database / API | **No database and no backend/API.** All persistence is CSV/JSON under `results/` (plus `config/stms.yaml` and each model's `config.json`). The dashboard reads them directly (DEC-15). |
| DEC-05 | Approaches | The selected TLS id is a `cluster…` id, i.e. SUMO may have **joined several nodes into one signal**, so it may not have four compass approaches. T0.3 groups incoming lanes by incoming edge and names them by bearing (N/E/S/W where unambiguous, else `A1..An`). Code always reads approaches from `config/stms.yaml`. |
| DEC-06 | Prediction ↔ RL | **Withdrawn.** No traffic-prediction model; RL observations come only from SUMO/TraCI. |
| DEC-07 | Vehicle types | **Cars only** (SUMO `passenger`). Mix stays configurable; default 100% car. |
| DEC-08 | Vision approach | **Withdrawn.** No OpenCV, YOLO or camera-based detection. |
| DEC-09 | Seed blocks (never mix) | RL train **1000–1999** (only a cached pool of them is used, T0.4) · seeds **2000–2029 reserved, unused** · RL validation **3000–3009** (also used to tune the rule-based controller) · development evaluation **5000–5004** · **final evaluation 6000–6004** (run once, T3.2) · seeds **7000–7013 reserved, unused** · demos **8000–8009**. The same numeric blocks are reused for the **network scenario family** (`net_*`), which are different scenarios; the M1 final run (T3.2) and the M2 final run (T4.9) are each run **once** on their own family; no tuning ever touches 5000+/6000+ in either family. |
| DEC-10 | Training budget | **Measured, staged, justified by validation** (T2.3 for M1, T4.6 for M2): smoke → pilot → main, capped by `rl.max_train_hours` / `rl_net.max_train_hours`. The agent decides the stage sizes from measured throughput; over-budget projections trigger the cost-reduction levers of the task automatically (no approval). |
| DEC-11 | Python/dependencies | The project may use a Python 3.14 install, but heavy packages (`torch`) may lack wheels for it. **Autonomous fallback order:** (1) upgrade pip and retry; (2) CPU wheel index for `torch`; (3) create a project venv with another interpreter already installed (from T0.1's `py -0` inventory, preferring 3.12 then 3.11); (4) install a supported Python from official sources if permitted without elevated rights. Record the final choice in `docs/PROJECT_FACTS.md`. Only if all fail → B1. |
| DEC-12 | **Milestones and headline metrics** | **M1** (Phases 0–3): one pilot junction, headline = Metric B (DEC-01). **M2** (Phase 4, final): all intended TLS, evaluated on the **network scenario family** `net_balanced, net_low, net_medium, net_heavy, net_rush_hour`. **M2 headline = Metric N** = average travel time of **all trips** in the network (completed common-trip set, with censored travel time and completion rates beside it, same survivorship rule as DEC-01). Aggregation: per (scenario, seed) improvement % → mean over seeds per scenario → **headline = unweighted mean over the four non-`low` scenarios** (`net_balanced, net_medium, net_heavy, net_rush_hour`); **primary findings** `net_medium, net_heavy, net_rush_hour` shown separately in the same table; `net_low` its own row, never in the headline; pooled-trips sensitivity row. Also reported network-wide: time loss, waiting, speed, throughput, completion rate, teleports, mean and worst-junction queue, congestion share, and a per-junction table. The 10% is a target, not an assumed result; provisional until P1. **M1 numbers are never presented as the final result.** |
| DEC-13 | Intended TLS set | **All TLS that pass the T4.1 suitability check** (≥ 2 verified conflict-free green phases, static or convertible to a static copy of the same phases, non-trivial traffic). Excluded TLS are listed with reasons and stay on SUMO's native program **identically for every controller**. The list is **frozen by the agent at the end of T4.1** (`network.tls_list_hash`, `network.frozen_utc` written to config and `docs/network_tls.md`) and is **never edited after any evaluation result exists**. `network.max_intended` (default 20) is a **compute-planning threshold, not a cap**: above it the agent keeps every suitable TLS (coverage is never reduced for cost), records the measured cost, and applies the DEC-14 Stage 3 reductions proactively. |
| DEC-14 | Network AI architecture and staged ladder | Decentralised **shared-policy PPO** (parameter sharing): one policy, per-junction local observation padded to `network.max_approaches` with a mask, per-junction reward (optional small network-wide term), actions applied at **every** intended TLS through its own safety layer. Built as a custom SB3 `VecEnv` whose slots are the junctions of one shared SUMO simulation (no extra dependencies needed). **Ladder (applied automatically, in order):** *Stage 0* network fixed-time + rule-based validated on all intended TLS (always; baselines). *Stage 1* smoke → pilot. *Stage 2* main shared PPO, full coverage. *Stage 3* cost reductions that **keep coverage of all intended TLS** (fewer training scenarios, shorter episodes, larger decision interval, early stop on validation, one PPO seed). *Stage 4 — automatic fallback when Stages 1–3 and the T4.7 iteration list are exhausted (T4.10):* partial-AI hybrid (PPO only at junctions that pass a per-junction non-regression gate, rule-based elsewhere); if no junction passes, a validated multi-junction rule-based controller reported with `ai_coverage = none`. It is always labelled with the AI-coverage fraction; single-junction PPO is never silently declared the final result. **Full-AI definition:** a junction counts as AI-controlled only if PPO supplied the executed decision at ≥ `eval.ai_coverage_min_share` of its decision ticks (T4.7); the final deliverable may be called *full network-wide AI control* only if **every** TLS on the frozen intended list is AI-controlled — otherwise it is labelled *partial* (or *none*) with the coverage fraction. |
| DEC-15 | Dashboard (required deliverable, Phase 5) | Owner-directed implementation uses supplied Flutter app (`dashboard_flutter/`) on Windows desktop. It remains **read-only, local and file-based**. **No backend, REST, WebSocket, authentication or database layer is added.** It reads saved CSV/JSON under `results/`, model `config.json` files, and live status files. It never opens TraCI or commands a signal. It shows only the six T5.2–T5.3 views, never fabricates or recomputes results, preserves survivorship and `low`-exclusion rules, and labels results simulated. The `dart:io` app does not claim web support. |

### Decision register (pending items and their autonomous defaults)
| # | Decision | Default applied by the agent | Blocks execution? |
|---|---|---|---|
| P1 | Supervisor confirms the **headline metric** (DEC-01 for M1; DEC-12 for M2; each with censored/completion beside it) | Use DEC-01/DEC-12 as written; every document says "provisional until P1" | **No** (labels only) |
| P2 | Supervisor acknowledges the **SRS deviations** in Section A | Document them in `docs/srs_deviations.md` (T6.3) with status "pending supervisor sign-off" | **No** (labels only) |
| P3 | M1 pilot junction | **Resolved:** the preselected cluster TLS was confirmed in T0.3 (rank 3/13, 5 approaches, 4 green phases). If a later check ever invalidated it, the agent would pick the highest-traffic suitable TLS and record it | No |
| P4 | Intended TLS list | **Agent freezes it at the end of T4.1 by the DEC-13 criteria** and records hash/time; the owner can request changes later, which would require re-running T4.5 onward | No |
| P5 | Fallback if shared PPO cannot cover all intended TLS | **Automatic Stage 4 (T4.10)** after the ladder is exhausted, labelled with the coverage fraction | No |
| P6 | Dashboard technology and view list | **Owner-selected Flutter Windows desktop app, local files, the six views of T5.2–T5.3** | Owner supplied Flutter frontend |

---

## 3. Constants (`config/stms.yaml`, created in T0.2; keys marked *(new v6)* are added in A0)

| Key | Default | Notes |
|---|---|---|
| `sumo.config` | `SUMO/No_Polygon_Map/osm.sumocfg` | existing |
| `sumo.tls_id` | `cluster618250255_7478115627_cluster_11927462278_11927462280_7479633881` | the **M1 pilot junction** (confirmed in T0.3: rank 3/13) |
| `sumo.step_length` | `1.0` s | |
| `sumo.horizon_s` / `max_sim_s` | `3600` / `7200` | demand window / hard cap |
| `sumo.time_to_teleport_s` | SUMO default (300) | identical for all controllers; teleports are counted |
| `signal.min_green_s` / `max_green_s` / `yellow_s` / `all_red_s` | `10` / `60` / `3` / `0` | FR-CTL-06, §5.2; structure verified against the real program in T0.3 |
| `fixed.green_s` | `30` | FR-CTL-01 |
| `rl.decision_interval_s` / `episode_s` | `5` / `3600` | |
| `rl.reward_weights` | `{queue: 1.0, wait: 1.0, throughput: 0.5}` | tune in T2.5 |
| `rl.device` | `cpu` | MLP policy is normally faster on CPU |
| `rl.max_train_hours` *(new v6)* | `10` | cap for the M1 main run (DEC-10) |
| `rule.queue_threshold` / `wait_threshold_s` | `8` / `45` → tuned `6` / `30` (T1.3) | tuned on validation seeds |
| `congestion.thresholds` | Low <5, Medium 5–12, High >12 halting vehicles/approach | FR-STA-02 |
| `demand.vehicle_mix` | `{passenger: 1.0}` | DEC-07 |
| `demand.junction_share_min` | `0.30` | DEC-01 |
| `demand.train_pool` | `{scenarios: all 7, seeds_per_scenario: 20}` from 1000–1999 | cached before training (T0.4) |
| `eval.scenarios_headline` | `[balanced, directional_ns, directional_ew, medium, heavy, rush_hour]` | DEC-01 |
| `eval.scenarios_primary` | `[medium, heavy, rush_hour]` | always shown separately |
| `eval.scenarios_separate` | `[low]` | never in the headline |
| `eval.dev_seeds` / `eval.final_seeds` | `[5000..5004]` / `[6000..6004]` | DEC-09; per scenario family, each final block run once |
| `eval.target_reduction_pct` | `10.0` | target, not result |
| `eval.ai_coverage_min_share` | `0.95` | PPO share of decision ticks for a junction to count as AI-controlled (DEC-14) |
| `eval.completion_gap_flag_pp` | `2.0` | completion-rate gap vs fixed-time that flags possible survivorship bias |
| `network.controlled_tls` / `network.excluded_tls` | filled and frozen by T4.1 | per TLS: id, approaches, green phases, `yellow_after`, movements; excluded with reason |
| `network.tls_list_hash` / `network.frozen_utc` *(new v6)* | written by T4.1 | DEC-13 |
| `network.max_intended` | `20` | planning threshold, **not** a cap (DEC-13) |
| `network.min_veh_per_1800s` | `20` | suitability traffic floor (native program, T4.1) |
| `network.max_approaches` / `max_phases` | measured in T4.1 | observation padding |
| `network.scenarios` | `[net_balanced, net_low, net_medium, net_heavy, net_rush_hour]` | DEC-12 |
| `network.headline_scenarios` / `primary_scenarios` / `separate_scenarios` | `[net_balanced, net_medium, net_heavy, net_rush_hour]` / `[net_medium, net_heavy, net_rush_hour]` / `[net_low]` | DEC-12 |
| `network.min_controlled_trip_share` | `0.5` | design target for trips using ≥ 1 controlled movement (T4.3 tunes toward it) |
| `demand.net_train_pool` | 5 net scenarios × 20 seeds from 1000–1999 | cached before training (T4.3) |
| `rl_net.decision_interval_s` / `episode_s` / `device` | `5` / `3600` / `cpu` | start from M1's validated reward weights; `rl_net.network_term_weight` default `0.0` |
| `rl_net.max_train_hours` | `10` | cap for the M2 main run |
| `rl_net.validation_pairs` / `validation_every_timesteps` | `[(net_medium,3000),(net_heavy,3001),(net_rush_hour,3002)]` / `20000` | custom validation callback (T4.6) |
| `intersection.approaches` / `green_phases` / `yellow_after` / `movements` | filled by T0.3 | M1 pilot junction; also one entry of `network.controlled_tls` after T4.1 |
| `logging.step_log_every_s` | `5` | keeps `steps.csv` small; also the update cadence of `status.json` (T5.1) |
| `jobs.parallel_runs` *(new v6)* | `auto` | = min(physical cores − 1, 4), at least 1; reduced if measured RAM per SUMO process × runs exceeds 70% of free RAM |
| `project.deadline_utc` *(new v6)* | `null` | optional; if set, Section 14 cut lines are applied earlier (never below the "never cut" list) |
| `dashboard.refresh_s` / `stale_after_s` / `server_address` | `5` / `30` / `localhost` | read-only dashboard (DEC-15; Phase 5) |
| `metrics_version` | `1` | bump when definitions change |

---

# PHASE 0 — Foundation and scenarios
Work branch: `agent/autonomous-build` (T0.1–T0.4 are Done — the blocks below stay as the specification the later phases rely on and as regression references)

> Phases 0–3 build and validate everything on the one **M1 pilot junction**. Every module is parametrised by `tls_id` / approach config with **no hidden single-junction assumptions** (one `SignalSafetyLayer` per TLS, one `IntersectionState` per TLS), because Phase 4 instantiates them for every intended junction.

### T0.1 — Repository and environment audit (Done)
- **Depends on:** nothing
- **Did/spec:** detect and record, never guess: repo tree/state; machine (OS, CPU, RAM, free disk, GPU, power plan); Python (active interpreter, other Pythons via `py -0`, venv, `pip freeze`, planned-dependency importability); SUMO (`sumo --version`, `SUMO_HOME`, `duarouter`/`netconvert`, `sumo-gui`, `traci`/`sumolib` versions); `osm.sumocfg` references and net size; existing code inventory incl. database/web packages; test of existing scripts/baseline/RL files (classified working / broken / unverified with evidence); SUMO speed over 600 sim-s (NFR-PRF-05 ≥ 5×); `Ai/analytics/` lint/test status.
- **Files:** `docs/PROJECT_FACTS.md`. **Accept:** file exists with all sections; unknowns say "not detected"; missing tools listed under "Missing / needs human" (any item there is handled per 0.6/DEC-11, not by waiting).

### T0.2 — Skeleton, config, tooling (Done)
- **Depends on:** T0.1
- **Did/spec:** Section 1 folders, `__init__.py`, `.gitignore`, `.gitattributes`, `.env.example`; dependencies in three files — `requirements.txt` (`traci, sumolib, numpy, pandas, matplotlib, pyyaml, gymnasium, stable-baselines3, torch, tensorboard, psutil`; CPU torch if no GPU), `requirements-dashboard.txt` (`streamlit`, created in T5.1 only), `requirements-dev.txt` (`pytest, pytest-cov, pytest-timeout, ruff`); unused database/web packages removed; `requirements.lock.txt` from the actually installed set; `pyproject.toml` (editable install, ruff line-length 100, pytest `testpaths=["tests"]`, marker `sumo`, `addopts = -m "not sumo"`, timeout); typed `Ai/common/config.py`; `scripts/check_zombies.py`; `AGENTS.md` (rewritten by A0); empty `docs/experiment_log.md`, `docs/lint_exclusions.md`.
- **Accept:**
  ```
  pip install -e . -r requirements.txt -r requirements-dev.txt
  ruff check .
  pytest -q
  python -c "from Ai.common.config import load_config; print(load_config()['sumo']['tls_id'])"
  python scripts/check_zombies.py
  ```
  A `torch`/`stable-baselines3` install failure follows the DEC-11 fallback order.

### T0.3 — SUMO client, traffic-light inspection and junction suitability (Done)
- **Depends on:** T0.2 · **SRS:** FR-SEN-01/05, FR-SIM-02/06/07
- **Did/spec:**
  1. `Ai/common/sumo_client.py`: `SumoClient` context manager (headless/GUI flag, `--seed`, free port, label, `step()`, `close()` in `finally`; clear error + safe stop on TraCI loss; **refuses to start** if net/route files are missing/invalid).
  2. `scripts/inspect_tls.py`: run 600 s headless; dump program type (static/actuated/other), program id, every phase index with duration + state string, controlled links, the distinct **TLS-controlled movements (`from_edge→to_edge`, link indices)**, incoming lanes grouped by edge, bearings, lane counts, joined-cluster flag, junction coordinates. Classify phases green vs yellow from state strings (never assume index parity). Check that no green phase gives simultaneous green to conflicting (foe) movements.
  3. **Suitability:** native program for ≥ 1800 s, vehicles per traffic light, rank of the selected TLS (per-TLS table kept in `docs/tls_inspection.md`; T4.1 reuses it), approach count, green phases, distance to map edge. Unsuitable selection (< 3 approaches, < 2 green phases, or clearly low-traffic) → P3 default: pick the highest-traffic suitable TLS and record it (never silently).
  4. Actuated/unsafe-to-hold program → **static copy of the same phases** under `SUMO/derived/`, referenced from scenario sumocfgs (original net never edited).
  5. Write `intersection.approaches` (`{name, lanes[], incoming_edge, bearing}`), `green_phases`, `yellow_after`, `movements` to config. `Ai/common/junction.py` (`controlled_movements(net, tls_id)`, `route_uses_controlled_movement(route_edges, movements)`) is the **only** definition of junction-trip membership, shared by T0.4 and T1.4.
  6. Record SUMO warnings/teleports of the 600 s run.
- **Files:** `Ai/common/sumo_client.py`, `Ai/common/junction.py`, `scripts/inspect_tls.py`, `docs/tls_inspection.md`, `tests/test_sumo_client.py`, `tests/test_junction.py`.
- **Accept:**
  ```
  python scripts/inspect_tls.py
  pytest -m sumo tests/test_sumo_client.py
  pytest -q tests/test_junction.py     # hand-built routes: uses a controlled movement / only touches the incoming edge / ends on it
  python scripts/check_zombies.py
  ```
  `docs/tls_inspection.md` lists the **real** phases/states, controlled movements, suitability ranking and foe check; config matches it.

### T0.4 — Scenario and demand generation (reproducible, cached) (Done with approved deviation)
- **Depends on:** T0.3 · **SRS:** FR-SIM-03/04/05
- **Did/spec:** `scripts/make_scenarios.py` generating per scenario a `.sumocfg` (existing net / derived static TLS, never edited) and **cached route files per seed** at `SUMO/scenarios/<scenario>/seed_<seed>/routes.rou.xml` plus `manifest.json` (config hash of net + demand parameters + generator version). `ensure_routes(scenario, seed) -> Path` reuses a matching manifest, regenerates if missing/stale. `--train-pool` pre-generates `demand.train_pool` (7 scenarios × 20 seeds from 1000–1999); the RL env draws **only from the cached pool** and fails fast if a file is missing.
  - Scenarios: `balanced, directional_ns, directional_ew, low, medium, heavy, rush_hour`.
  - **Routing (explicit, seeded):** `sumolib`, seeded RNG over **sorted** edge lists, shortest paths; classify pairs whose path **uses a controlled movement** (`junction.py`); draw `junction_share` of trips from through-junction pairs; `directional_*` bias origins to the approach bearing; `rush_hour` ramps insertion; `duarouter`; cars only; fixed routes (no rerouting).
  - **Measure** with the native program: total trips, fraction through the junction, completion by `max_sim_s`, teleports, insertion backlog. Tune insertion so every scenario designed to evaluate the junction has junction-share ≥ 30% (**the agent tunes the through-pair draw and insertion rates itself; document `low` honestly if it cannot reach it**). Teleport results follow the 0.6 amendment (recorded, not blocking, evaluated after PPO is connected).
- **Files:** `scripts/make_scenarios.py`, `docs/scenarios.md`, `tests/test_scenarios.py`.
- **Accept:**
  ```
  python scripts/make_scenarios.py --seed 1000 --all
  python scripts/make_scenarios.py --seed 1000 --all --force   # byte-identical route files
  python scripts/make_scenarios.py --train-pool
  pytest -q tests/test_scenarios.py
  ```

---

# PHASE 1 — Core: Traffic State, safety layer, controllers, metrics
Work branch: `agent/autonomous-build` (T1.1–T1.4 are Done; A0 runs the Phase 1 checkpoint once)

### T1.1 — Traffic State module (Done)
- **Depends on:** T0.4 · **SRS:** FR-STA-01..05, FR-SEN-02/03
- **Spec:** `Ai/common/traffic_state.py`: dataclasses `ApproachState(name, vehicle_count, halting, mean_speed, waiting_time, queue_length, congestion, available_fields)` and `IntersectionState(timestamp_utc, sim_time, intersection_id, approaches, phase, phase_elapsed_s, mode, totals{waiting_vehicles, avg_wait, throughput_veh_min}, source)` with `source = "sumo"` only (a leftover `camera` value is removed in T6.2); `SumoSensorReader(tls_config).read(client)` (`tls_config` = `intersection` for M1 or one entry of `network.controlled_tls`) with lane-level TraCI calls; `congestion_level(halting, thresholds)`; `to_dict()` (ISO-8601 UTC, JSON-serialisable); `to_vector(state, norm)` → fixed-length numpy vector clipped to [0,1]. Unavailable fields are `None` and listed in `available_fields`.
- **Accept:**
  ```
  pytest -q tests/test_traffic_state.py
  pytest -m sumo tests/test_traffic_state_sumo.py
  ```

### T1.2 — Signal safety layer (Done)
- **Depends on:** T1.1, T0.3 · **SRS:** FR-CTL-06, §5.2
- **Spec:** `Ai/controllers/safety.py` — `SignalSafetyLayer(client, tls_config)` (one per TLS) is the **only** component allowed to call `traci.trafficlight.setPhase/setPhaseDuration/setProgram/setRedYellowGreenState`. Methods: `request_switch()` (next green via the program's own yellow [+ all-red], only if `elapsed_green ≥ min_green`, else `Rejected(reason)`); `request_extend(seconds)` (capped by `max_green`); `tick()` (each step; **forces a switch at `max_green`**; completes yellow/all-red); `request_green_for_approach(name)`. Only phase indices of the **verified conflict-free program** (plus all-red) are applied. Every call returns `Accepted | Rejected(reason)`.
- **Accept:** `pytest -m sumo tests/test_safety.py` — over 1200 s with a random-command fuzzer: (a) no green→green without yellow, (b) no phase < `min_green` unless cleared, (c) no phase > `max_green`, (d) every applied state is in the verified set, (e) rejections carry a reason.

### T1.3 — Controllers, fallback, episode runner (Done)
- **Depends on:** T1.2 · **SRS:** FR-CTL-01/02/07/08, §5.2
- **Spec:** `base.py` (`Controller.decide(state) -> Action`, `reset()`); `fixed_time.py` (30 s/3 s, cycles verified greens); `rule_based.py` (extend while current-approach queue/wait above thresholds and < `max_green`; switch when current queue is small and another approach exceeds thresholds; uses only `IntersectionState`); `fallback.py` (`FallbackController` wraps any controller; on exception/timeout/invalid output → fixed-time, logs a warning, sets `fallback_active`); `registry.py` → `get_controller("fixed"|"rule"|"rl")`; `Ai/common/run_episode.py::run_episode(controller, scenario, seed, out_dir, gui=False)` closed loop (observe → decide → safety → step) writing step/trip logs (Section 11); CLI has `--family {single,network}`, default `single`.
- **Rule tuning protocol:** ≥ 3 threshold settings on **validation seeds 3000–3002** (never 5000+/6000+), keep the best, log all in `docs/rule_tuning.md` (result: queue=6, wait=30 s).
- **Accept:**
  ```
  pytest -q tests/test_controllers.py
  python -m Ai.common.run_episode --controller fixed --scenario medium --seed 3000
  python -m Ai.common.run_episode --controller rule  --scenario medium --seed 3000
  ```
  Fixed run shows greens of 30 s ± 1 step (from `steps.csv`).

### T1.4 — Metrics (Done with approved deviation)
- **Depends on:** T1.3 · **SRS:** FR-SEN-04, FR-EVL-02, DEC-01
- **Spec:** `Ai/common/metrics.py` + `docs/metrics.md` (definitions, units, DEC-01 aggregation). Collect from `--tripinfo-output` (+ `write-unfinished`) **and** TraCI tracking.
  - **Trip time = `depart_delay + duration`**; `depart_delay` recorded separately.
  - **Junction membership (metric B)** = `route_through_junction` (route contains ≥ 1 TLS-controlled movement via `junction.py`, evaluated on the route file; `first_controlled_movement` recorded); `passed_controlled_junction` (actually crossed) recorded separately, used for throughput only.
  - Per run: completion rate (all and junction trips), avg travel time (completed), **censored** travel time (unfinished = `end_time − scheduled_depart`), both also for junction trips, avg waiting, time loss, depart delay, avg queue (halting at junction), avg speed, throughput (veh/min through junction), fraction of time at High congestion, completed/unfinished, teleports. A run continues until all vehicles arrive or `max_sim_s`.
  - **Cross-check:** in the fixed-time run every *completed* `route_through_junction` trip must have `passed_controlled_junction = true`; report mismatches; **an unexplained mismatch is investigated and fixed (0.6.3)** (the recorded 210 mismatches were all explained by teleports).
  - Fixed-time teleports for `medium/heavy/rush_hour` are recorded without blocking (0.6 amendment).
- **Accept:**
  ```
  pytest -q tests/test_metrics.py      # hand-built tripinfo → exact numbers incl. unfinished, depart delay, completion rates, junction membership (a route containing an incoming edge but no controlled movement is NOT a junction trip)
  python -m Ai.common.run_episode --controller fixed --scenario medium --seed 3000
  ```
  `summary.csv` has every Section 11 column; no NaN except documented. `docs/metrics.md` explains how the old "4,408 trips / 3,323 completed / 1,085 unfinished / ~299 s" figure differs from the new definitions. Wall-clock seconds per run are recorded (they feed T2.3/T3.1 scheduling).

---

# PHASE 2 — RL environment and PPO
Work branch: `agent/autonomous-build` (checkpoint at phase end, 0.5)

> Gate: **no real PPO training until T2.1 and T2.2 pass.**

### T2.1 — Rebuild `Ai/rl/traffic_env.py`
- **Depends on:** T1.4 · **SRS:** FR-CTL-03/04/06, FR-STA-05
- **Do:** Gymnasium `TrafficEnvironment(scenario_pool, seeds, config)` using `SumoClient`, `SumoSensorReader`/`to_vector` and `SignalSafetyLayer` (**no direct phase manipulation in the env**). Observation `Box(0,1,(N,))` with N from config (per-approach count/halting/speed/wait + phase one-hot + normalised elapsed green; layout in the docstring). Action `Discrete(4)` (DEC-03); illegal actions become "keep" and are counted in `info["illegal_action"]`. Reward (configurable): `r = −w_q·Δ_norm_queue_total − w_w·norm_wait_total + w_t·norm_vehicles_passed`, all terms normalised; exact formula in `docs/rl_design.md`. `truncated=True` at `episode_s`; `reset(seed=…)` picks the scenario deterministically **from the cached training pool** via `ensure_routes()` (no demand generation during training); `close()` idempotent and kills SUMO. `info` has `sim_time, phase, phase_elapsed, action_taken, illegal_action, queue_total, wait_total`.
- **Accept:** `ruff check Ai/rl` clean; `python -c "from Ai.rl.traffic_env import TrafficEnvironment"`.

### T2.2 — Environment tests (blocking gate)
- **Depends on:** T2.1
- **Do:** rewrite `Ai/rl/test_env.py` (mirror `tests/test_env.py`): 1) `check_env` passes; 2) 3 random-policy episodes: no exception, no conflicting greens/skipped yellows, greens within `[min_green, max_green]`; 3) scripted-policy sanity: "always keep" on a heavily loaded approach gets **lower cumulative reward** than a hand-written "switch when queue high" policy on the same seed (assert); 4) same seed twice ⇒ identical first 50 observations and rewards; 5) 5 reset/close cycles leave no zombie SUMO; 6) the env refuses to run if a pool route file is missing.
- **Accept:** `pytest -m sumo tests/test_env.py -q` all green. **If (3) fails, fix reward/observation first** (adaptively, 0.6.3).

### T2.3 — PPO training pipeline (staged, measured budget)
- **Depends on:** T2.2 · **SRS:** FR-CTL-05/09
- **Do:** first create `scripts/job_runner.py` and `scripts/keep_awake.py` (0.8). Rewrite `Ai/rl/train_ppo.py` (CLI: `--timesteps --seed --scenarios --reward-weights --out --resume`); random scenario/seed per episode from the cached pool (1000–1999 block); `DummyVecEnv`; `Monitor`; TensorBoard; `training_log.csv` (episode, reward, mean wait, mean queue, illegal-action rate, action histogram); `EvalCallback` on validation seeds 3000–3009; periodic checkpoints; save `ppo_v<N>/{model.zip,config.json}`; `device=cpu`. Runs are detached and resumable (0.8).
  - **Staged budget (DEC-10) — starting points; measured throughput decides; no approvals:**
    1. **Smoke:** 20,000 steps; record steps/hour and sim-s/real-s.
    2. **Pilot:** ~50,000 steps (or what fits ≲ 2–3 h). Continue to main if validation reward is improving; if not, run a few pilot variants using the T2.5 levers (reward weights → observation → PPO hyper-parameters) and continue with the best by validation.
    3. **Main:** the largest count that fits `rl.max_train_hours` (default ≤ 10 h), up to 300,000, justified in `docs/experiment_log.md` by the pilot curve.
    4. If even 100,000 steps projects > `rl.max_train_hours`: automatically reduce cost (decision interval 10 s, `episode_s` 1800, fewer training scenarios), record it, and continue.
  - If time allows, train ≥ 2 PPO seeds and choose by **validation** only (never dev/final seeds).
- **Accept:**
  ```
  python -m Ai.rl.train_ppo --timesteps 20000 --out Ai/rl/models/ppo_v2_smoke
  python -m Ai.rl.train_ppo --timesteps <staged budget> --out Ai/rl/models/ppo_v2
  ```
  Record the learning-curve file, measured training speed and final validation mean reward. Never touch seeds 5000+/6000+.

### T2.4 — RL controller wrapper
- **Depends on:** T2.3 · **SRS:** NFR-PRF-01, FR-CTL-07/08
- **Do:** `Ai/controllers/rl_controller.py` (loads `model.zip`, state → vector → action; wrapped by `FallbackController`). Replace `Ai/rl/evaluate_ppo.py` with diagnostics: action histogram, phase-usage histogram, mean green per phase, forced max-green switches, illegal-action rate.
- **Accept:** `pytest -q tests/test_rl_controller.py` (median inference latency < 100 ms over 1000 calls on this machine; corrupt model path → fallback activates) and `python -m Ai.rl.evaluate_ppo --model Ai/rl/models/ppo_v2 --seed 3000`.

### T2.5 — RL sanity gate
- **Depends on:** T2.4
- **Do:** run fixed, rule, RL on `medium` and `heavy`, **validation seeds 3000–3002**; write `docs/rl_diagnostics.md` (table + diagnostics). **Teleport performance evaluation (2026-10-24 amendment):** compare fixed-time and PPO on the same unchanged medium/heavy scenarios and seeds 3000–3002; report teleports, completed trips, queues, waiting time, time loss. The >5% criterion is a performance result here and does not retroactively pass the native baseline.
- **Pass:** RL uses ≥ 2 distinct actions, serves all green phases, forced-max-green switches < 30% of switches, **and** is not worse than fixed-time by > 5% on junction travel time.
- **If it fails**, iterate autonomously in this order, logging each attempt: (1) reward weights/normalisation, (2) observation (add last action, per-approach wait), (3) decision interval, (4) PPO hyper-parameters (`ent_coef` 0.01–0.05, `n_steps`, `learning_rate`, `gamma`), (5) more timesteps within budget, (6) curriculum low→heavy. Then try combinations of the same levers while validation keeps improving (stop after two consecutive rounds without validation improvement, 0.6.3); if the gate still fails, **record the gate as FAILED, mark T2.5 `Done with deviation (gate failed; best-by-validation model carried forward)`, and continue** — M1 evaluation then reports the measured result honestly, `docs/rl_diagnostics.md` and `docs/results.md` state the failed gate, and M2 reuses the lessons learned. Never tune on seeds 5000+/6000+.

---

# PHASE 3 — Fair evaluation (single-junction milestone M1)
Work branch: `agent/autonomous-build` (checkpoint at phase end, 0.5)

### T3.1 — Evaluation harness
- **Depends on:** T2.5 (for the `rl` controller; the fixed/rule parts need only T1.4 — if PPO is blocked, build and run the harness for `fixed` and `rule` and mark `Partial (pending: rl model)`) · **SRS:** FR-EVL-01..07
- **Do:** `Ai/evaluation/evaluate.py`: for each `(scenario, seed)` generate routes once (`ensure_routes`) and run `fixed`, `rule`, `rl` on exactly that file and seed. Scenarios: all seven; `--seed-set dev|final` selects `[5000..5004]` or `[6000..6004]`; `--jobs` runs independent runs in parallel (`jobs.parallel_runs`); folders are skip-if-complete so the job is resumable (0.8). Estimate wall time from T1.4's per-run timings (7 × 5 × 3 = 105 runs per seed set), log it, and launch — no approval.
  - Aggregate to `results/summary/comparison.csv` (rows `milestone = M1`; mean ± std over seeds, paired-bootstrap 95% CI of the per-seed improvement). **Improvement** = `(baseline − RL)/baseline × 100` (sign-correct for higher-is-better metrics), vs fixed and vs rule. Aggregation exactly per DEC-01: per-scenario rows, headline row over the six non-`low` scenarios, primary row (`medium, heavy, rush_hour`), separate `low` row, pooled-trips sensitivity row.
  - **Primary travel-time comparison uses the common-trip set**; **beside it, in the same table**, always the censored travel time, completion rate per controller, completed/unfinished counts and common-set size. If a controller's junction completion rate differs from fixed-time by more than `eval.completion_gap_flag_pp`, flag the common-trip result as possibly survivorship-biased. Report **metric B (headline, provisional) and metric A**, plus waiting, time loss, queue, throughput, congestion, completed/unfinished, teleports.
  - `target_met` = mean RL improvement vs fixed on the headline metric ≥ `eval.target_reduction_pct`, else `false`; printed per scope (A/B), trip basis (common-trip and censored) and aggregation; never forced; if the bases disagree, both are shown and the disagreement is stated.
  - Charts to `results/figures/*.png` (travel time [common-trip and censored], completion rate, waiting, queue, throughput, improvement-% per scenario, error bars; labelled "simulated").
- **Accept:**
  ```
  python -m Ai.evaluation.evaluate --controllers fixed rule rl --seed-set dev
  pytest -q tests/test_evaluation.py   # synthetic inputs → exact improvement %, common-trip filter, censored time and completion rate, sign handling, low excluded from headline
  ```
  Re-running reproduces an identical `comparison.csv`.

### T3.2 — Results gate and honest reporting
- **Depends on:** T3.1 (hard, with the `rl` runs)
- **Do:** if the dev-seed headline improvement is < 10%: diagnose (per-scenario table, action/phase histograms), then try each remaining lever **once** using **training/validation seeds only** (longer training within DEC-10, reward re-weighting, extra scenarios in the training mix); re-evaluate on dev seeds. Then **freeze automatically:** commit the chosen model + `config.json`; record model sha256, config hash, git commit and the exact command in `docs/experiment_log.md`.
  - **Run the final block once:** `python -m Ai.evaluation.evaluate --controllers fixed rule rl --seed-set final` ("once" = one completed run of the frozen configuration; resuming the same run after a crash with identical config is allowed and noted; re-running after changing anything is not).
  - Use **only** that run for the headline in `docs/results.md` Part 1, titled "M1 — single-junction milestone (not the final result)": tables mean ± std (+ CI), figures, `target_met` per metric and scope, per-scenario results, `low` separate, common-trip beside censored time and completion rates, limitations (single junction, synthetic demand, simulation only, cars only, unfinished-trip handling, survivorship bias), the failed-gate statement if T2.5 deviated, and "provisional until P1". It states that the final deliverable is network-wide control (Phase 4) and makes no whole-map claim. Report **all** attempts including failed ones. Do **not** change seeds, scenarios or metric definitions after seeing results.
- **Accept:** every number in `docs/results.md` equals `results/summary/comparison.csv` exactly (`tests/test_results_doc.py` parses and checks every part present).

---

# PHASE 4 — Network-wide control (M2, the final deliverable)
Work branch: `agent/autonomous-build` (checkpoint at phase end, 0.5)

> Controller code for one junction exists from Phases 1–2; Phase 4 instantiates it per junction and adds a shared-policy RL setup. No database or backend is built here (the read-only dashboard is Phase 5). New dependencies only under the 0.7 rule (justified, compatible, not a removed feature). Hard dependencies below are the code-level ones; M1 results (T3.2) and the validated M1 reward weights (T2.5) are **soft** inputs — if M1 is blocked, use the `config/stms.yaml` defaults and record that choice.

### T4.1 — Network TLS inventory, suitability and intended set
- **Depends on:** T1.4 · **Soft:** T3.2 · **SRS:** FR-SIM-02, FR-CTL-10
- **Do:** `scripts/inspect_network_tls.py` (reusing T0.3 code, parametrised by `tls_id`) over **every** TLS: program type, phases and state strings, green/yellow classification, controlled movements, joined-cluster flag, approach count, junction coordinates, **foe/conflict check per TLS**, and traffic under SUMO's native program for ≥ 1800 s with the existing demand. Classify each TLS **suitable** (≥ 2 verified conflict-free green phases; static, or convertible to a static copy of the same phases; ≥ `network.min_veh_per_1800s` vehicles) or **excluded with a written reason**. The M1 pilot junction must be in the intended set. Static copies for actuated TLS go under `SUMO/derived/` (never edit `SUMO/No_Polygon_Map`). Write `network.controlled_tls`, `network.excluded_tls`, `network.max_approaches`, `network.max_phases` to `config/stms.yaml`; write `docs/network_tls.md` (table of all TLS, intended/excluded, reasons, counts).
  - **Freeze (DEC-13, P4 default):** at the end of this task the agent writes `network.tls_list_hash` and `network.frozen_utc` and states the freeze in `docs/network_tls.md`. No human approval is awaited. If the intended count exceeds `network.max_intended`, keep all suitable TLS, record the count and measured cost, and plan Stage 3 reductions (DEC-14) — never a silent cap.
  - Measure sim speed with all intended TLS under TraCI control and extrapolate the training budget; record it (it drives T4.6 staging).
- **Files:** `scripts/inspect_network_tls.py`, `docs/network_tls.md`, `tests/test_network_config.py`, `tests/test_network_tls.py`.
- **Accept:**
  ```
  python scripts/inspect_network_tls.py
  pytest -q tests/test_network_config.py        # config lists match the inventory; M1 junction included; no TLS both intended and excluded; list hash matches
  pytest -m sumo tests/test_network_tls.py      # every intended TLS: foe-free green phases, verified yellow structure
  python scripts/check_zombies.py
  ```

### T4.2 — Multi-junction state, safety, controllers and runner
- **Depends on:** T4.1, T1.3 · **SRS:** FR-CTL-01/02/06/07/08/10, §5.2
- **Do:** `Ai/common/network_state.py` (`NetworkState{sim_time, junctions:{tls_id: IntersectionState}, totals}`, JSON-serialisable `to_dict()`, `NetworkSensorReader`); extend `Ai/controllers/safety.py` with `NetworkSafetyManager` holding **one `SignalSafetyLayer` per intended TLS** (still the only code that calls TLS setters; `tick_all()` runs after **every** `simulationStep`, so yellow, min-green and max-green are enforced each second; excluded TLS are never commanded); `Ai/controllers/network.py` (`NetworkController.decide(NetworkState) -> {tls_id: Action}`; `PerJunctionController` applying a single-junction fixed/rule controller at every TLS, each in its own `FallbackController` so one junction's failure never affects another); `registry.get_network_controller("fixed"|"rule"|"rl")` (`rl` arrives in T4.7). Extend `run_episode` with `--family network` (`steps.csv` per `intersection_id`, `junctions.csv`).
- **Files:** the above + `tests/test_network_state.py`, `tests/test_network_safety.py`, `tests/test_network_controllers.py`.
- **Accept:**
  ```
  pytest -q tests/test_network_state.py tests/test_network_controllers.py
  pytest -m sumo tests/test_network_safety.py   # 1200 s random-command fuzzer on ALL intended junctions at once
  python scripts/check_zombies.py
  ```
  Safety properties (a)–(e) of T1.2 hold **at every junction**, plus (f) excluded TLS never receive a command, (g) forcing a fallback at one junction leaves the others unaffected. Record real wall-clock per sim-second with all junctions controlled.

### T4.3 — Network scenarios and cached pool
- **Depends on:** T4.2 · **SRS:** FR-SIM-03/04/05
- **Do:** extend `scripts/make_scenarios.py` with `--family {single,network}` (default `single`, so T0.4 commands keep working); for `network`: scenarios `net_balanced, net_low, net_medium, net_heavy, net_rush_hour`; origin/destination pairs over the **whole map** (seeded RNG, sorted edge lists, `sumolib` shortest paths, `duarouter`, cars only, fixed routes); `net_rush_hour` ramps insertion. Manifest hash includes the intended-TLS list hash; `ensure_routes()` and `--train-pool` (`demand.net_train_pool`, 5 × 20 seeds from 1000–1999) as in T0.4; training never generates demand. **Measure** with the native program: trips, **fraction of trips using ≥ 1 controlled movement**, mean controlled junctions per trip, per-TLS trip counts, completion by `max_sim_s`, teleports, insertion backlog.
  - **Demand design (done here, before any evaluation seed is used):** tune insertion so `net_medium/heavy/rush_hour` are congested but not gridlocked (teleports < 1% target) and the controlled-trip share reaches `network.min_controlled_trip_share`. Tuning uses only seeds 1000–1999 and 3000–3002, adaptively (0.6.3), each attempt logged. If the share still falls short because of map geometry, accept the best achieved value **provided it is ≥ `demand.junction_share_min` (0.30)**, document it as a deviation in `docs/scenarios.md`; below 0.30 after adaptive effort → 0.6.3 fallback/blocker handling for this task. After this task the network demand design is **frozen**.
- **Files:** `scripts/make_scenarios.py`, `docs/scenarios.md` (network table), `tests/test_scenarios.py`.
- **Accept:**
  ```
  python scripts/make_scenarios.py --family network --seed 1000 --all
  python scripts/make_scenarios.py --family network --seed 1000 --all --force   # byte-identical
  python scripts/make_scenarios.py --family network --train-pool
  pytest -q tests/test_scenarios.py
  ```

### T4.4 — Network metrics and baselines
- **Depends on:** T4.3 · **SRS:** FR-SEN-04, FR-EVL-02, DEC-12
- **Do:** extend `Ai/common/metrics.py` and `docs/metrics.md` with network metrics (additions only, so `metrics_version` stays 1; changing an existing definition bumps it and forces re-running M1 and M2): network travel time (completed, censored, common-trip), completion rate, time loss, waiting, speed, throughput (arrivals/min), teleports, mean and **worst-junction** queue, congestion share per junction and network-wide, `n_tls_controlled`, `n_tls_ai`, `n_controlled_junctions_on_route`, per-junction `junctions.csv`. Run network `fixed` and `rule` on all five net scenarios; the rule controller uses **one shared threshold set** tuned on validation seeds **3000–3002** (≥ 3 settings, never 5000+/6000+, logged in `docs/rule_tuning.md` Part 2). Run independent runs in parallel (0.8).
  - **Teleport re-check:** network fixed-time teleports on `net_medium/heavy/rush_hour` are measured against the 1% design target. If exceeded, the agent may re-tune insertion (as needed) in T4.3-style design (seeds 1000–1999/3000–3002 only, logged, before T4.5 starts) and regenerate the pool; otherwise the result is preserved and reported per the 0.6 amendment principle (no hiding, no demand reduction after results are seen).
  - Record wall-clock per run and controller (feeds T4.6/T4.8 scheduling).
- **Accept:**
  ```
  pytest -q tests/test_metrics_network.py   # hand-built multi-junction tripinfo → exact network numbers, censored time, completion rates, per-junction rows
  python -m Ai.common.run_episode --family network --controller fixed --scenario net_medium --seed 3000
  python -m Ai.common.run_episode --family network --controller rule  --scenario net_medium --seed 3000
  ```
  `summary.csv` complete, `n_tls_controlled == len(network.controlled_tls)`, no undocumented NaN.

### T4.5 — Network RL environment (blocking gate)
- **Depends on:** T4.4, T2.2 (env conventions) · **Soft:** T2.5 (validated reward weights; default weights otherwise) · **SRS:** FR-CTL-03/04/06
- **Do:** `Ai/rl/network_vec_env.py`: `NetworkVecEnv(VecEnv)` — a custom SB3 `VecEnv` with `num_envs = N` = number of intended TLS; slot *i* is junction `network.controlled_tls[i]` (fixed sorted order, recorded in `config.json`) inside **one** SUMO simulation (parameter sharing). Implement the full abstract `VecEnv` interface (`reset, step_async, step_wait, close, get_attr, set_attr, env_method, env_is_wrapped, get_images, seed`). Built on `SumoClient`, `NetworkSensorReader`/`to_vector` and `NetworkSafetyManager`; **no direct TLS manipulation**. Design rules (each tested below):
  - **Lockstep clock.** Every `rl_net.decision_interval_s` all junctions decide at the same instant from one batched observation `(N, Nobs)` and one action vector `(N,)`.
  - **Actions:** shared `Discrete(4)` (DEC-03) reinterpreted for the shared clock: 0 keep; 1 request switch to the next green; 2 / 3 keep **and hold** (no switch) for the next `ceil(5/interval)` / `ceil(10/interval)` decision ticks. An illegal sampled action (min-green not reached, hold active, safety rejection) is executed as "keep" and counted per junction (`n_illegal_actions`, `n_hold_overridden`).
  - **Within a tick:** apply each junction's action through its safety layer, then advance `decision_interval_s` single `simulationStep`s, calling `NetworkSafetyManager.tick_all()` after every step.
  - **Observation** per junction `Box(0,1,(Nobs,))`: approach slots padded to `network.max_approaches` + validity mask + phase one-hot padded to `network.max_phases` + normalised elapsed green; identical shape for every junction; layout in `docs/rl_design.md`.
  - **Reward** `(N,)`: M1's local formula and weights over each junction's own approaches for the tick, plus `rl_net.network_term_weight × mean reward over junctions` (default 0.0).
  - **Termination:** all slots end together by **truncation** at `rl_net.episode_s` only: `dones` all True, every `infos[i]` has `TimeLimit.truncated = True` and `terminal_observation`, then the env closes SUMO, draws the next (scenario, seed) from the **cached net pool** (seeded RNG, deterministic order; fail fast if a file is missing) and returns the first observation of the new episode. A SUMO/TraCI failure raises; it never fabricates an episode.
  - `close()` idempotent; unique port/label per instance (validation uses a second instance). `infos[i]` also carries `tls_id, illegal_action, hold_overridden, fallback_active`.
- **Accept:** `ruff check Ai/rl` clean and `pytest -m sumo tests/test_network_env.py -q` all green: (1) VecEnv contract: shapes `(N,Nobs)`/`(N,)`, dtypes, spaces, `reset/step/close`, 100 steps under `VecCheckNan`; (2) 2 random-policy episodes: no exception, safety properties at every junction, excluded TLS never touched; (3) scripted "switch when queue high" beats "always keep" on cumulative reward on a `net_heavy` seed (assert); (4) same seed twice ⇒ identical first 50 observations and rewards for all junctions; (5) 5 reset/close cycles leave no zombie SUMO; (6) missing pool file ⇒ fail-fast; (7) padding: junctions with fewer approaches have zeroed slots and a correct mask; (8) termination: at `episode_s` all slots done with `TimeLimit.truncated` and `terminal_observation`, next episode starts at sim time 0 with a new pool entry; (9) hold semantics: action 3 blocks switching for the stated ticks and overridden samples are counted; (10) batching: row *i* corresponds to `network.controlled_tls[i]`. **If (3) fails, fix reward/observation first** (adaptively, 0.6.3).

### T4.6 — Shared-policy PPO training (staged ladder, DEC-14)
- **Depends on:** T4.5 · **SRS:** FR-CTL-05/09
- **Do:** `Ai/rl/train_ppo_network.py` (CLI: `--timesteps --seed --scenarios --reward-weights --network-term --out --resume --stage3-cost-reductions`): SB3 `PPO("MlpPolicy")` on `NetworkVecEnv` wrapped in `VecMonitor`, scenario/seed per episode from the cached net pool, TensorBoard, `training_log.csv`, periodic checkpoints, save `ppo_net_v<N>/{model.zip,config.json}` (config: intended-TLS list hash and slot order, reward weights, seeds, library versions, wall-clock). Resumable via `PPO.load(..., reset_num_timesteps=False)`; detached via the job runner (0.8).
  - **Timestep semantics:** one vectorised step = N junction decisions = N SB3 timesteps; the rollout buffer holds `n_steps × N` samples. Choose `n_steps` and `batch_size` so `n_steps × N` is divisible by `batch_size`; an episode is `episode_s / decision_interval_s` vectorised steps (720 at defaults). Report timesteps, vectorised steps and simulated hours.
  - **Known assumptions/risks (in `docs/rl_design.md`, no convergence claim):** same-tick samples from different junctions are correlated; each junction's environment is non-stationary because the others' policy changes; parameter sharing assumes junctions are similar enough after padding.
  - **Validation:** a custom `NetworkValidationCallback` (SB3 `EvalCallback` is **not** used — it assumes one episode per slot). Every `rl_net.validation_every_timesteps` it runs one deterministic episode per `rl_net.validation_pairs` entry on a **separate** `NetworkVecEnv`, logs network censored average travel time and mean per-junction return, and keeps the best-by-validation checkpoint (lowest censored travel time). It never uses seeds 5000+/6000+.
  - **Staged budget (automatic; measured throughput decides; coverage is never reduced in Stages 1–3):**
    1. **Smoke:** 20,000 timesteps; record timesteps/hour and sim-s/real-s with all intended TLS controlled.
    2. **Pilot:** ~100,000 timesteps (or ≲ 3 h). Continue to main if validation improves; otherwise run a few pilot variants with the T4.7 levers and continue with the best.
    3. **Main (Stage 2):** the largest count fitting `rl_net.max_train_hours` (default ≤ 10 h), justified by the pilot curve. If even 150,000 timesteps projects over budget → **Stage 3** reductions (fewer training scenarios, `episode_s` 1800, `decision_interval_s` 10, early stop on validation, single PPO seed), each logged in `docs/experiment_log.md`.
       - `--stage3-cost-reductions` uses the three primary network scenarios by default, sets training episodes to 1,800 s and decision intervals to 10 s, and defaults to early-stop patience 2. Fixed validation keeps the baseline 3,600 s / 5 s settings so its scores remain comparable with earlier rounds. The resume guard permits only an explicit strict scenario-pool reduction.
    4. If Stage 3 still cannot produce a model that passes T4.7 → **Stage 4 is triggered automatically (T4.10)**; no human decision is awaited.
  - If time allows, train ≥ 2 PPO seeds; choose by validation only.
- **Accept:**
  ```
  python -m Ai.rl.train_ppo_network --timesteps 20000 --out Ai/rl/models/ppo_net_v1_smoke
  python -m Ai.rl.train_ppo_network --timesteps <staged budget> --out Ai/rl/models/ppo_net_v1
  pytest -q tests/test_network_validation_callback.py   # fake env: best checkpoint chosen by lowest censored time, never by training reward
  ```
  Record the learning-curve file, measured speed (real numbers only) and the best validation result.

### T4.7 — Network RL controller and sanity gate
- **Depends on:** T4.6 · **SRS:** NFR-PRF-01, FR-CTL-07/08/10
- **Do:** `Ai/controllers/rl_network_controller.py` (loads `ppo_net_v<N>`, builds all junction observations in slot order, **one batched forward pass**, per-junction `FallbackController`); per-junction diagnostics (action histogram, phase usage, mean green, forced max-green switches, illegal/hold-overridden rate, `ppo_tick_share`). Run network `fixed`, `rule`, `rl` on `net_medium` and `net_heavy`, validation seeds 3000–3002 → `docs/rl_diagnostics.md` Part 2.
- **Pass (defaults):** (a) **PPO decisions applied at every frozen intended TLS**: `ai_coverage = full` (`controlled_by = rl` for all junctions); (b) ≥ 80% of junctions use ≥ 2 distinct actions; (c) forced max-green < 30% of switches network-wide; (d) network censored travel time not worse than fixed-time by > 5%; (e) worst-junction queue regression vs fixed is reported, a junction > 50% worse triggers investigation (logged); (f) batched-inference median latency < 100 ms on this machine (measured).
- **If it fails**, iterate autonomously in order, logging each attempt: (1) reward weights / `network_term_weight` (try 0.25 once), (2) observation (last action, per-approach wait, neighbour-junction halting if time allows), (3) decision interval, (4) PPO hyper-parameters, (5) more timesteps within budget, (6) curriculum low → heavy. Then apply the T4.6 Stage 3 reductions and combinations of the levers while validation keeps improving (stop after two consecutive rounds without validation improvement, 0.6.3); if the gate is still failed, **trigger T4.10 automatically** (the best-by-validation network model is kept and used by the hybrid for junctions that pass its gate).
- **Accept:** `pytest -q tests/test_rl_network_controller.py` (latency measured; corrupt-model path activates per-junction fallback and lowers that junction's `ppo_tick_share`) and the gate table in `docs/rl_diagnostics.md` produced by an actual run.

### T4.8 — Network evaluation harness
- **Depends on:** T4.4 (fixed/rule), T4.7 (for `rl`; if `rl` is unavailable build and run for `fixed`/`rule` and mark `Partial (pending: rl model)`) · **SRS:** FR-EVL-01..07
- **Do:** extend `Ai/evaluation/evaluate.py` with `--family {single,network}` (default `single`, so T3.1 commands are unchanged). For `network`: scenarios `net_*`, `--seed-set dev|final`; for each `(scenario, seed)` generate routes once and run `fixed`, `rule`, `rl` (or `hybrid` after T4.10) on the same file and seed; skip-if-complete, resumable, parallel (`--jobs`). Estimate wall time from T4.4 timings (5 × 5 × 3 = 75 runs per seed set), log it, launch. Aggregate into `comparison.csv` (`milestone = M2`, rebuilt from all raw runs per Section 11) exactly per DEC-12: per-scenario rows, headline row (four non-`low` scenarios), primary row, separate `net_low` row, pooled sensitivity row; paired-bootstrap 95% CI. Primary comparison is the completed **common-trip set**, **always beside** censored travel time, completion rates and common-set size; flag survivorship risk per `eval.completion_gap_flag_pp`. Also write `network_junctions.csv` and a per-junction congestion figure. `target_met` per trip basis and aggregation, never forced. **Coverage:** `ai_coverage` is computed per `rl` run by code; any run with `ai_coverage != full` is flagged and reported as partial/none. Charts labelled "simulated".
- **Accept:**
  ```
  python -m Ai.evaluation.evaluate --family network --controllers fixed rule rl --seed-set dev
  pytest -q tests/test_evaluation_network.py   # exact improvement %, common-trip filter, censored/completion, low excluded from headline, ai_coverage full/partial/none, M1 rows untouched
  ```
  Re-running reproduces an identical `comparison.csv`.

### T4.9 — Network results gate (FINAL result)
- **Depends on:** T4.8 (hard, with `rl`/`hybrid` runs)
- **Do:** if the dev headline improvement is < 10%: diagnose (per-scenario and per-junction tables, action/phase histograms), then try each remaining lever **once** using **training/validation seeds only** (longer training within budget, reward re-weighting, scenario mix, network term). **Freeze automatically:** commit model + `config.json`; record model sha256, config hash, intended-TLS list hash, git commit and exact command in `docs/experiment_log.md`. **Run the final block once:** `python -m Ai.evaluation.evaluate --family network --controllers fixed rule rl --seed-set final` (crash-resume with identical config allowed and noted). Write `docs/results.md` **Part 2 — M2, final**: the intended-TLS list and exclusions; a line `AI coverage: <n_tls_ai>/<n_tls_controlled> (<full|partial|none>)` copied from `summary.csv`; the **controller level reached** (full shared-PPO / Stage 3 reductions / Stage 4 hybrid); headline Metric N with CI, `target_met`, common-trip beside censored and completion rates, per-scenario rows, `net_low` separate, per-junction congestion table, limitations (simulation only, synthetic demand, cars only, decentralised shared policy, excluded TLS on native program, no real-world validation) and "provisional until P1". Report all attempts, including failed ones. Do not change seeds, scenarios, TLS list or metrics after seeing results. "Full network-wide AI control" may appear only if `ai_coverage = full`.
- **Accept:** every number in `docs/results.md` (both parts) equals `results/summary/comparison.csv`/`summary.csv`; `pytest -q tests/test_results_doc.py` also checks the `AI coverage:` line against `summary.csv` and fails if "full network-wide AI control" appears while `ai_coverage != full`.

### T4.10 — Stage-4 fallback (CONDITIONAL; triggered automatically, never by waiting for a human)
- **Trigger:** T4.6 or T4.7 declares the DEC-14 ladder exhausted (Stages 1–3 and the T4.7 iteration lists done, full coverage not achieved or the gate failed). Otherwise `Not triggered`.
- **Depends on:** T4.5, the best-by-validation network model (if any), T4.4 rule baseline.
- **Do:** the agent writes a short spec in `docs/experiment_log.md` and implements `HybridNetworkController` in `Ai/controllers/network.py`: **per-junction non-regression gate** computed on validation seeds 3000–3002 (`net_medium`, `net_heavy`): PPO may control junction *j* only if its mean queue and mean wait are not worse than fixed-time's by more than 5% and it uses ≥ 2 distinct actions; PPO runs at gate-passing junctions, rule-based elsewhere (all through the safety layer). If no junction passes, the controller is the validated multi-junction rule-based controller with `ai_coverage = none`. The gate is frozen before dev evaluation. Run it through T4.8/T4.9 unchanged. Every report states `ai_coverage = partial` (or `none`) with the coverage fraction and the level reached; it is never described as full network-wide AI control.
- **Accept:** `pytest -q tests/test_hybrid_controller.py` (exactly the gate-passing junctions are PPO-driven, the rest rule-based; `ai_coverage` computed correctly) and the T4.8 acceptance commands.

---

# PHASE 5 — Dashboard (read-only, file-based; required deliverable)
Work branch: `agent/autonomous-build` (checkpoint at phase end, 0.5)

> Owner direction selects the supplied Flutter project instead of the Streamlit default. Keep the dashboard **read-only, local and file-based**: no database/backend/API/authentication, no TraCI, no control/training/evaluation logic, and no fabricated values. It reads saved Section 11 CSV/JSON and live status files. Windows desktop is the supported target; do not claim the generated web target works. Simulated results remain labelled as such.

### T5.1 — Dashboard data layer and live-status files
- **Depends on:** T4.2 (`run_episode` for both families) · **Soft:** T3.2, T4.9 (real files for the real-data check) · **SRS:** FR-DSH-* (data side); NFR-PRF-02/03 where applicable to a local dashboard
- **Do:**
  1. Integrate the owner-supplied Flutter project with the real project folder layout. Do not add a backend or database; document Windows desktop as the supported target.
  2. **Additive, observational-only change to `Ai/common/run_episode.py`** (both families; no change to controller, safety, scenario or metric behaviour): (a) flush `steps.csv` after every logged row; (b) write `results/raw/<run_id>/status.json` (schema in Section 11) at start, every `logging.step_log_every_s`, and at the end, atomically (temporary file in the same folder, then `os.replace`). Normal completion → `state = finished`; exception → `state = failed` with a short `error`. A run killed from outside leaves `state = running` with an old `updated_utc` — shown as **stale**, never as running (`dashboard.stale_after_s`).
  3. Flutter file reader: no TraCI dependency and no writes; load saved raw runs, summaries, comparison, junction and model config files; validate expected columns/version, tolerate a partial trailing CSV record, and show explicit no-data states.
- **Files:** `dashboard_flutter/lib/`, `dashboard_flutter/test/`, `Ai/common/run_episode.py` (additive change), status/data tests.
- **Accept:**
  ```
  cd dashboard_flutter; flutter pub get; flutter analyze; flutter test
  pytest -q tests/test_run_status.py        # atomic status schema, timestamps and failed-state details
  ruff check .
  python scripts/check_zombies.py
  ```
  Re-run one fixed-time `medium` episode (seed 3000) and confirm every `summary.csv` column except `wall_clock_s` (and `run_id`) equals the pre-change run — the change must be observational only. Report the comparison honestly.

### T5.2 — Dashboard views: live monitoring
- **Depends on:** T5.1 · **SRS:** FR-DSH-* (monitoring)
- **Do:** extend the supplied Flutter app and its screens using the same read-only file reader:
  1. **Simulation status** — run selector (default: latest); state (`running` / `finished` / `failed` / `stale` / `no data`), family, controller, scenario, seed, simulated time vs `max_sim_s`, `n_tls_controlled`, last update time.
  2. **Signal states and phases** — per intersection (junction selector for `family=network`): current `phase`, `signal_state`, `phase_elapsed`, last `action` and `action_accepted` from `steps.csv`; table of phase changes over time; for finished network runs, `controlled_by` and `ppo_tick_share` from `junctions.csv`.
  3. **Traffic metrics** — over simulated time: per-approach `halting` (queue length) and `wait_time`, `vehicles`, `mean_speed`, and `congestion` level (Low/Medium/High per `congestion.thresholds`); for network runs also the network total and the worst junction. For finished runs, flow and congestion indicators from `summary.csv` (`throughput_veh_per_min`, `avg_queue`, `frac_time_high_congestion`, `teleports`, `completion_rate`).
  - Launch: `cd dashboard_flutter; flutter run -d windows` (local only). With no data it shows an explicit no-data state and never substitutes sample values.
- **Files:** `dashboard_flutter/lib/main.dart`, `dashboard_flutter/lib/screens/`, `dashboard_flutter/test/widget_test.dart`.
- **Accept:**
  ```
  cd dashboard_flutter; flutter test   # includes no-data and synthetic saved-file integration checks
  ruff check .
  ```
  **Automated live check (report only what is observed):** run the resource-safe demo-seed network rule workflow, then confirm `status.json`/`steps.csv` growth and visible refresh in the Windows app; stop processes and run `check_zombies.py`. Do not claim live UI verification unless observed.

### T5.3 — Dashboard views: comparison, evaluation results and experiment history
- **Depends on:** T5.2 · **Soft:** T3.2, T4.9 (real files) · **SRS:** FR-DSH-* (results)
- **Do:** three more views reading only saved files and showing values exactly as written (formatting only — the dashboard **never recomputes** a headline, improvement %, CI or `target_met`):
  4. **Controller comparison** — fixed-time vs rule-based vs PPO per scenario from `results/summary/comparison.csv` (choose milestone M1/M2 and `seed_set` dev/final): travel time, waiting, time loss, queue, throughput, completion rate, teleports. **Survivorship rule kept (DEC-01/DEC-12):** a common-trip travel time is never shown without the censored travel time, completion rate and common-set size beside it. `low`/`net_low` rows are shown separately and never inside a headline row.
  5. **Evaluation results and performance indicators** — headline and primary rows with CI and `target_met` (`false` shown as "target not met"); M1 labelled "milestone, not the final result"; for M2 the line `AI coverage: <n_tls_ai>/<n_tls_controlled> (<full|partial|none>)` copied from `summary.csv`, the per-junction congestion table from `network_junctions.csv`, and every headline marked "provisional until P1". "Full network-wide AI control" is displayed only when `ai_coverage = full`.
  6. **Experiment history** — table of every run in `results/raw/*/summary.csv` (run_id, controller, scenario, seed, family, key metrics, `git_commit`, `metrics_version`) with simple filters, plus the model records from `Ai/rl/models/*/config.json` (seeds, reward weights, git commit, wall-clock; intended-TLS list hash for network models). `results/raw/` is not committed, so history shows the runs on this machine.
- **Files:** `dashboard_flutter/lib/screens/`, `dashboard_flutter/test/widget_test.dart`, real-artifact integration checks.
- **Accept:**
  ```
  cd dashboard_flutter; flutter test   # local synthetic file fixtures and UI states
  # audit real-results displayed values against saved summary/comparison files
  ruff check .
  ```
  Flutter tests prove the no-data state and real-file parsing using temporary synthetic fixtures only. Add a synthetic view test showing common-trip values beside censored time, completion rate, and common-set size; `low`/`net_low` excluded from headlines; `target_met=false` as not met; partial coverage without full-coverage wording; missing comparison as an explicit prompt. The real-data audit checks at least 10 displayed values against saved `comparison.csv` and `summary.csv`; record those values. A mismatch is a bug to fix.

### T5.4 — Dashboard integration, no-database check and documentation
- **Depends on:** T5.3
- **Do:**
  1. `tests/test_no_database.py`: assert no tracked source or requirements file uses or lists a database or backend package (`sqlite3`, `sqlalchemy`, `psycopg2`, `supabase`, `alembic`, `fastapi`, `uvicorn`, `websockets`), that `git ls-files` has no `*.db` / `*.sqlite*` file, and that nothing under the dashboard imports `traci`.
  2. Run the dashboard against the real `results/` (both families) and a live run (as in T5.2); fix any defect found.
  3. Measure and record (real numbers only): Windows dashboard startup/page-load time on real results and lag between a `status.json` update and its appearance. Compare with SRS NFR-PRF-02/03 only if the approved SRS source is available; otherwise report the missing source.
  4. `docs/dashboard.md`: exact start commands for supported Windows desktop, view/source mapping, freshness/stale behavior, and limitations (local only, read-only, unauthenticated, simulation only, data already on disk, raw results not committed).
- **Files:** `tests/test_no_database.py`, `docs/dashboard.md`, any defect fixes in `dashboard/`.
- **Accept:**
  ```
  pytest -q tests/test_no_database.py
  cd dashboard_flutter; flutter analyze; flutter test; flutter build windows
  ruff check .
  python scripts/check_zombies.py
  ```
  plus the live smoke run and the measured latency table, reported with real output.

---

# PHASE 6 — Demo, quality, documentation (lean)
Work branch: `agent/autonomous-build` (checkpoint at phase end, 0.5)

### T6.1 — One-command demo
- **Depends on:** T4.9 (or T4.10 outputs), T3.2, T5.4
- **Do:** `python -m scripts.run_demo --family {single,network} --controller {fixed,rule,rl} --scenario <medium|net_medium> --seed 8000 [--gui]` (`--family network --gui` shows the whole map) — runs SUMO(-GUI) with the chosen controller, prints live-ish metrics, writes outputs (including `status.json`) to `results/raw/`. Demo seeds are the **8000+ block**, never final-evaluation seeds. Add `scripts/run_all.md` listing the exact command order (scenarios → fixed → rule → train → evaluate → demo → dashboard). If the hybrid (T4.10) is the delivered level, `--controller rl` in the network family runs it and says so.
- **Accept:** the three controllers each run once via this CLI for **both** families (network `rl` demo prints `n_tls_ai` vs `n_tls_controlled` and states the controller level reached, DEC-14); `python scripts/check_zombies.py` clean; a 1-hour simulated session completes without crash (§5.4); the demo run is visible in the dashboard's live views (verified as in T5.2 and reported honestly; `--gui` is exercised only if a display exists, else stated).

### T6.2 — Quality pass and blocker sweep
- **Do:** first **re-test every open blocker** in `docs/decisions.md` once (0.6.4) and complete any `Partial` task whose pending item now exists. Then: `ruff check .` clean over the **whole repo** (exclusions justified per 0.7 and listed in `docs/lint_exclusions.md`); `pytest -q` and the **full** `pytest -m sumo` pass; `git grep -nEi "password|secret|apikey|token"` reviewed; `.gitignore` works (no large files tracked); temp scripts removed/labelled; no database/backend packages or Python web server in requirements; `git grep -nEi "opencv|ultralytics|yolo|sqlalchemy|sqlite|psycopg|fastapi|uvicorn"` finds no use in code or requirements, and no leftover unused dependency remains (e.g. `scikit-learn`/`joblib` from the removed prediction scope; remove them, regenerate `requirements.lock.txt`, remove an unused `"camera"` source value from `Ai/common/traffic_state.py` — no behaviour change); OSM (ODbL) attribution in README.
- **Accept:** command outputs summarised in the tracker note.

### T6.3 — Documentation
- **Do:** `README.md` (overview, mermaid architecture diagram, prerequisites, setup for Windows and Ubuntu with the verified Python version, config, **exact command sequence**, outputs map, limitations, ODbL attribution); `docs/srs_deviations.md` (the Section A table, P1/P2 "pending supervisor sign-off", P3–P6 outcomes as autonomous decisions); `docs/limitations.md` (including any blocked/partial item and why); `docs/report_inputs.md` (checklist of validated tables/figures for the report and PPT, each with its source path; generate figures by script; SUMO-GUI/dashboard screenshots are captured by script if the environment allows, otherwise listed as optional owner items — never a blocker); pointer to `docs/dashboard.md`.
- **Accept:** every README command was executed by you at least once; list those you could not run.

### T6.4 — Release
- **Do:** after the final checkpoint the agent performs the one planned local merge of `agent/autonomous-build` into `main` (0.5, case a) and creates the tag `v1.0-ai-core` **on `main`** (no push unless the owner authorized it); fills `docs/RELEASE_CHECKLIST.md` with real results; lists any task that is not `Done` and why; states which of P1/P2 are pending and **which controller level was reached (full network AI / partial-AI / rule-only, DEC-14)**; writes the final report (0.1.7).

---

# NOT IN SCOPE (do not start unless the human explicitly says so)
- **Backend:** simulation service thread, FastAPI REST + WebSocket, authentication/roles, audit log, `docs/openapi.json`. (The Phase 5 dashboard needs none of them: it reads files, DEC-15.)
- **Database:** any database (PostgreSQL / SQLite / SQLAlchemy / Supabase / other). Persistence is CSV/JSON only (DEC-04).
- **Dashboard extras:** manual override or remote control of signals (FR-OVR-*), login/roles (FR-AUT-*), any page or feature not listed in T5.2–T5.3.
- **Removed entirely (not deferred):** OpenCV/YOLO computer vision and camera-based detection; any separate traffic-prediction model and prediction-as-RL-input.
- **Optional (only if the human asks later):** emergency-vehicle priority, **explicit communication-based inter-junction coordination (green waves, message passing)**.
- **Not excluded:** multi-junction *control itself* is **mandatory** in Phase 4 (M2). Only explicit coordination *between* junctions is out of scope; the shared policy of DEC-14 is the only coordination mechanism in scope.

The only things the optional items need from today's work: JSON-serialisable `IntersectionState`, the `Controller` interface, the safety layer's `Accepted/Rejected(reason)` API, and the CSV/JSON schemas in Section 11.

---

# 10. Requirement → task traceability

| SRS requirement(s) | Task(s) / status |
|---|---|
| FR-SIM-01..07 | T0.3, T0.4 (M1 pilot junction); T4.1, T4.3 (all intended TLS, network scenarios). FR-SIM-01 satisfied by the existing OSM→SUMO map |
| FR-SEN-01..05 | T0.3, T1.1, T1.4 |
| FR-CV-01..07 | **Removed from scope** (deviation logged) |
| FR-STA-01..05 | T1.1 (camera-sourced state removed; deviation logged) |
| FR-PRD-01..05 | **Removed from scope** (deviation logged) |
| FR-CTL-01, 02, 08 | T1.3 (M1), T4.2 (every intended TLS) |
| FR-CTL-03, 04, 05, 09 | T2.1, T2.3 (M1); T4.5, T4.6 (shared policy, all intended TLS) |
| FR-CTL-06 (safety) | T1.2, T2.2 (M1); T4.2, T4.5 (every intended junction) |
| FR-CTL-07 | T1.3, T2.4, T4.7 |
| FR-CTL-10 | T4.1–T4.9 (multi-junction control, M2); T4.10 only if the ladder is exhausted (DEC-14 Stage 4) |
| FR-EMG-* | Deferred (optional) |
| FR-EVL-01..07 | T3.1, T3.2 (M1); T4.4, T4.8, T4.9 (network-wide) |
| FR-DSH-* | T5.1–T5.4 (read-only, file-based; only the views of T5.2–T5.3; exact FR-DSH items checked against SRS §3.1 — ambiguity A-3) |
| FR-OVR-*, FR-AUT-*, FR-DAT-* | **Not implemented** (no backend, authentication, database or manual override; CSV/JSON instead) |
| NFR-PRF-01 | T2.4, T4.7 · NFR-PRF-04 → not applicable · NFR-PRF-05 → T0.1 and T4.2 (measured sim speed, whole network) |
| NFR-PRF-02, 03 | Dashboard latency measured in T5.4 against the SRS threshold; REST latency not applicable |
| NFR-PRF-06 (≥ 10%) | T3.1, T3.2 (M1 milestone); **T4.8, T4.9 (M2 network-wide, final)** — **measured, never asserted; provisional (P1)** |
| §5.2 Safety | T1.2, T1.3 (fallback); T4.2 (all junctions) |
| §5.3 Security | No authentication/backend (deviation logged); dashboard is local-only (`localhost`) and read-only (DEC-15) |
| §5.4 Reliability / Reproducibility / Testability | T0.2, T3.1, T6.1, T6.2 |
| §5.5 Business rule: identical scenarios/seeds | T3.1, T4.8 |
| §6 Delivery (code, model, scenarios, docs, demo script, dashboard) | T0.4, T3.2, T4.3, T4.9, T5.4, T6.1, T6.3 |

---

# 11. Data schemas (CSV and JSON files only — no database; UTF-8; header row for CSV; one schema for every controller)

**`results/raw/<run_id>/steps.csv`** (logged every `logging.step_log_every_s`) — `run_id, controller, scenario, seed, sim_time, intersection_id, approach, vehicles, halting, mean_speed, wait_time, phase, phase_elapsed, signal_state, action, action_accepted, congestion`

**`results/raw/<run_id>/trips.csv`** — `run_id, controller, scenario, seed, vehicle_id, vtype, scheduled_depart, actual_depart, depart_delay, arrival, duration, trip_time, waiting_time, time_loss, route_length, completed, route_through_junction, first_controlled_movement, n_controlled_junctions_on_route, passed_controlled_junction` (unfinished: `trip_time = end_time − scheduled_depart`, `completed=false`)

**`results/raw/<run_id>/summary.csv`** (one row) — `run_id, controller, scenario, seed, git_commit, config_hash, metrics_version, n_trips, n_trips_junction, n_completed, n_unfinished, completion_rate, completion_rate_junction, avg_travel_time_completed, avg_travel_time_censored, avg_travel_time_junction_completed, avg_travel_time_junction_censored, avg_wait, avg_time_loss, avg_depart_delay, avg_queue, avg_speed, throughput_veh_per_min, frac_time_high_congestion, teleports, sim_end_time, wall_clock_s, family(single|network), n_tls_controlled, n_tls_ai, ai_coverage(full|partial|none), avg_junction_queue_mean, worst_junction_avg_queue`
(For `family=network` the "junction" columns mean trips using ≥ 1 controlled movement of any intended TLS; the M2 headline uses the all-trips columns. Network-only columns are documented-blank for `family=single`.)

**`results/raw/<run_id>/junctions.csv`** (network family; one row per controlled TLS) — `run_id, controller, scenario, seed, tls_id, controlled_by(fixed|rule|rl|rl_fallback|native), avg_queue, max_queue, avg_wait, frac_time_high_congestion, throughput_veh_per_min, n_switches, n_forced_max_green, n_illegal_actions, n_hold_overridden, fallback_activations, n_ticks, ppo_tick_share`
(`ppo_tick_share` = decision ticks in which PPO supplied the action passed to the safety layer ÷ `n_ticks`; an illegal or hold-overridden PPO action still counts as a PPO decision, a tick taken over by `FallbackController` does not. `controlled_by = rl` only if `ppo_tick_share ≥ eval.ai_coverage_min_share`, else `rl_fallback`. In `summary.csv`, `n_tls_ai` counts junctions with `controlled_by = rl`, `n_tls_controlled` counts all junctions on the frozen intended list, and `ai_coverage` = `full` if `n_tls_ai == n_tls_controlled == len(network.controlled_tls)`, `partial` if 0 < `n_tls_ai` < that, else `none`. For the T4.10 hybrid, junctions driven by the rule fallback are `controlled_by = rule`. Computed by the evaluation code, never typed by hand.)

**`results/summary/comparison.csv`** — `milestone(M1|M2), scenario, aggregation(scenario|headline|primary|low|pooled), controller, metric, scope(all|junction), trip_basis(common|all), mean, std, ci95_low, ci95_high, n_seeds, n_trips_basis, completion_rate_mean, seed_set(dev|final), improvement_vs_fixed_pct, improvement_vs_rule_pct, target_met`

**`results/summary/network_junctions.csv`** — `scenario, tls_id, controller, avg_queue_mean, avg_wait_mean, ci95_low, ci95_high, n_seeds, seed_set(dev|final)`

**`results/raw/<run_id>/status.json`** (one small JSON object, written atomically and overwritten at each update by `run_episode`, T5.1; read by the dashboard) — `schema_version, run_id, state(running|finished|failed), family(single|network), controller, scenario, seed, sim_time, max_sim_s, n_tls_controlled, started_utc, updated_utc, error(null unless failed)`. A `running` status whose `updated_utc` is older than `dashboard.stale_after_s` is displayed as stale, never as running.

**`results/jobs/<job_id>.json`** (written by `scripts/job_runner.py`, 0.8; not committed) — `job_id, command, resume_command, pid, started_utc, updated_utc, log_path, out_dir, state(running|finished|failed|interrupted)`

`comparison.csv` is rebuilt from **all** runs in `results/raw/` (every milestone and seed set) each time, so evaluating one family never removes or alters rows of another; rows are keyed by `(milestone, seed_set, scenario, aggregation, controller, metric, scope, trip_basis)`. Metric definitions live in `docs/metrics.md` (T1.4). When a definition changes: bump `metrics_version` and re-run evaluation. These files (plus each model's `config.json`) are the only persistence of experimental results; the dashboard reads them and writes nothing.

---

# 12. Progress tracker (the agent updates this after every task)

Status values: `Not started` · `In progress` · `Blocked (reason)` · `Partial (pending: item)` · `Done` · `Done with deviation (what)` · `Not triggered` (T4.10 only). No phase and no task may be silently skipped: Phases 0–6 are all core (T4.10 is the only conditional task). Fill date and commit hash when Done.

**Checkboxes:** change `[ ]` to `[x]` on a task row **only when its status is `Done` / `Done with deviation` and every `Accept` command passed**, in the same commit that updates status, date and hash. T4.10 stays `[ ]` unless triggered. A phase box is ticked (in a normal commit on `agent/autonomous-build`) once every task in it (except a non-triggered T4.10) is `[x]` or recorded as `Blocked`/`Partial` with its blocker in `docs/decisions.md`, **and** the phase checkpoint (0.5) has passed; the agent then continues immediately.

**Resume point:** Phase 0 and the Phase 1 tasks are Done. A0 (once) reconciles `agent/autonomous-build` so it contains all completed work (merging other local branch tips into it if it lacks them, losing no commit or uncommitted change), runs the Phase 1 checkpoint there, ticks the Phase 1 box if it passes, then work continues at **T2.1**. The commit hashes in the table below are what A0 uses to verify that the branch contains all completed work.

**Phase checklist**
- [x] Phase 0 — Foundation and scenarios (T0.1–T0.4)
- [x] Phase 1 — Core: state, safety, controllers, metrics (T1.1–T1.4) — A0 checkpoint passed 2026-10-25
- [x] Phase 2 — RL environment and PPO (T2.1–T2.5) — checkpoint passed 2026-10-27
- [ ] Phase 3 — Fair evaluation → **M1 reached** (T3.1–T3.2)
- [x] Phase 4 — Network-wide control → **M2, final deliverable** (T4.1–T4.9; T4.10 triggered and completed under DEC-14; phase checkpoint passed 2026-11-02)
- [ ] Phase 5 — Dashboard, read-only and file-based (T5.1–T5.4)
- [ ] Phase 6 — Demo, quality, documentation, release (T6.1–T6.4)

| Task | Status | Date | Commit | Note |
|---|---|---|---|---|
| [x] T0.1 Audit | Done | 2026-10-20 | 19d83ad | Repository and environment audit recorded; baseline replay did not reproduce. |
| [x] T0.2 Skeleton, config, tooling | Done | 2026-10-20 | 50bda08 | Setup, config, dependency lock, lint and tests pass. If `scikit-learn`/`joblib`/vision packages were installed or locked, remove them in T6.2. |
| [x] T0.3 SUMO client + TLS + suitability (M1 pilot junction) | Done | 2026-10-24 | e2b189d | Confirmed target; rank 3/13, 5 approaches, 4 green phases, no protected foe conflicts; 8 permissive yielding overlaps documented. |
| [x] T0.4 Scenarios + cached pool | Done with approved deviation | 2026-10-24 | 478daff | 140/140 cached routes verified; native >5% teleport failure preserved and deferred to post-PPO comparison per Section 0.6. |
| [x] T1.1 Traffic State | Done | 2026-10-24 | 133b0c0 | SUMO sensor aggregation, normalized vector, serialization; unit/live SUMO checks pass. If the code still accepts `source = camera`, remove it in T6.2 (no behaviour change). |
| [x] T1.2 Safety layer | Done | 2026-10-24 | eacb7e0 | SUMO safety fuzzer 1200 s; unit/SUMO suites and Ruff pass. |
| [x] T1.3 Controllers + runner | Done | 2026-10-25 | ef1772a | Fixed, rule, fallback controllers and runner complete; 9/9 validation tuning cells run; selected queue=6, wait=30s; unit tests pass. |
| [x] T1.4 Metrics | Done with approved deviation | 2026-10-25 | ef1772a | 33-column Section 11 summary complete (no NaN); all 210 crossing mismatches explained by teleports (0 unexplained); teleport rates preserved per Section 0.6 deviation. |
| [x] T2.1 Env | Done | 2026-10-25 | 9e0508c | Follow-up `3330439`: keep holds safely; default seeds match the prepared cache. |
| [x] T2.2 Env tests (gate) | Done | 2026-10-25 | 8154ed6 | `pytest -m sumo tests/test_env.py -q`: 6 passed; default seed test also passed. |
| [x] T2.3 PPO training (staged) | Done | 2026-10-27 | — (no commit per user instruction) | Main job `20261026-182735_519e7950` finished RC 0 at 200,224 steps; cumulative output clock 30,104.04 s (8.36 h / 10 h), best validation −17.548 (SD 19.647) at 180k. User directed use of the 200k-stage model; later continuation stopped at 232,768 before promoting its artifacts. |
| [x] T2.4 RL controller | Done | 2026-10-27 | — (user requested no commit) | Focused suite: 7 passed; seed-3000 CLI completed with the pinned 200k-stage validation-best model; diagnostics and logs recorded. |
| [x] T2.5 RL sanity gate | Done | 2026-10-27 | — (user requested no commit) | All 18 fixed/rule/RL runs completed on medium/heavy, validation seeds 3000–3002, using the pinned 200k-stage validation-best checkpoint. Aggregate paired common-trip junction travel time: fixed 3028.68 s, RL 2884.04 s (−4.78%); two PPO actions, all four greens used, forced max-green 0/1251. Gate PASS; details and teleports in `docs/rl_diagnostics.md`. Phase 2 checkpoint: Ruff passed; full suite 40 passed/11 deselected; SUMO env 6 passed/1 deselected; zombie check clean. |
| [x] T3.1 Evaluation harness (M1) | Done | 2026-10-28 | - (no commit per user instruction) | Job `20261028-114545_bf75b94d` RC 0; full audit 105/105 valid; pytest 4 passed; Ruff passed; seven simulated figures; identical CSV rerun (SHA-256 `ca11e935c3968ce25eb3fe8bdf98cea3de1dd75d7ed6aa9e981dccc9c41c49a17`). |
| [ ] T3.2 Results gate — M1 milestone | In progress (resumed clean run `20261105-091026_edd94e34`) | 2026-11-05 | — | Earlier job `20261104-062146_46129cd5` had config drift: evaluator metadata SHA-256 `99a432c2912d0320ca0bf61f9435781f2d8cbdb1f282fdeddc391c3da4408e16` conflicted with summary/current YAML SHA-256 `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`; preserve/exclude its artifacts. Clean job `20261104-073704_d0bec4e8` stopped logging on Nov 4 and its PIDs were absent on Nov 5. Fresh lineage audit at 17:18 accepts 29/105 cells (fixed 10/35, rule 10/35, RL 9/35; 76 missing); evaluator and six workers are live and logs advance. Exact resume runs unchanged final model/seeds/metrics under SHA `322293c6c89cfdeba92c08b7ff65b5858095897adb733abc81200da74c5a7668`; pre/post episode hash guards are enabled. Require 105-cell lineage audit, report test and exact comparison acceptance before T3.2 completes. |
| [x] T4.1 Network TLS inventory + intended set (frozen by agent) | Done | 2026-10-31 | — (uncommitted per user direction) | Inspected 13; froze 12 intended, excluded 1 (<20 crossings); foe/yellow checks pass; hash `4fc1323e1885d0763d8ac0598a1ec5e7446c6a835a63b62136f657c735979bcd`; T4.2 probe measured 8.8171 sim-s/real-s under all 12 TLS. |
| [x] T4.2 Multi-junction state, safety, controllers | Done | 2026-10-31 | — (uncommitted per user direction) | Network state/sensors/safety/controllers and runner; 4 unit/config tests passed, 2 SUMO tests passed, Ruff/zombie checks pass; controlled probe reached 7200 s, 816.5936 s wall; 12 junction and 69,120 step rows. |
| [x] T4.3 Network scenarios + cached pool | Done | 2026-10-31 | — (checkpoint work uncommitted) | Eleven seed-1000 attempts logged. Final scenarios pass <1% teleports and ≥0.50 controlled-route share; primary scenarios show measured medium queue-band time. `--all`, byte-identical `--force`, 100/100 pool validation, 6 scenario tests and focused Ruff passed. Demand-design evidence only; T3.2 remains a soft input. |
| [x] T4.4 Network metrics + baselines | Done | 2026-10-31 | — (uncommitted mixed worktree) | Network metric tests 3 passed; focused Ruff passed; exact fixed/rule medium seed-3000 acceptance commands exited 0. Nine tuning cells selected q8/wait45 (q8/q10 exact mean-queue tie resolved by candidate order). All 30 fixed/rule baseline cells valid across five scenarios × seeds 3000–3002; each run has 12/12 frozen TLS rows, finite summaries and 100% completion. Common-trip comparison has 15 paired rows. Fixed teleports exceeded 1% on net_heavy (52/2400=2.167%) and net_medium seed3000 (8/650=1.23%); preserve/report, no demand reduction. Results in experiment log, `docs/rule_tuning.md` and `results/summary/t44_network_common_trips.csv`. |
| [x] T4.5 Network RL env (gate) | Done | 2026-10-31 | — (preserved in mixed worktree; `.git` is read-only in this workspace) | `NetworkVecEnv` contract and all 10 gate behaviors covered; exact `pytest -m sumo tests/test_network_env.py -q` passed 9 tests; `ruff check Ai/rl` clean; no SUMO processes remained. Uses 12 frozen slots, M1 features/reward with selected T2.5 weights, lockouts, deterministic cached episodes and safety ticks every SUMO step. See `docs/rl_design.md` and `docs/experiment_log.md`. |
| [x] T4.6 Shared-policy PPO (staged ladder) | Done — Stage 3 early-stop rule met | 2026-11-01 | - | Owner-authorized retry job `20261101-093754_d4eea1dd` exited 0; stopped after two validation rounds without improvement at 2,200,020/2,300,000 steps (99,980 short), as configured by Stage 3 patience 2. Cumulative training time 36,841.7217 s, within revised 40,000 s cap (original 36,000 s preserved). Best validation remains 940,008 steps / 252.371598 s / 93.2160% completion; final round 253.874 s / 93.10%. Latest durable checkpoint 2,196,480 loads; selected model files match. T4.6 acceptance follows the documented Stage 3 early-stop rule; this is not a T4.7 controller/effectiveness pass. See `docs/experiment_log.md`. |
| [x] T4.7 Network RL controller + sanity gate | Done | 2026-11-01 | — | Rejection-penalty job `20261101-113217_b592e349` exited 0 at exact target 2,296,476; cumulative time 38,893.1046/43,000 s. Selected candidate SHA `758711e7…f5037757`, best validation at 2,240,004 / 253.432630 s. Six-cell gate job `20261101-120825_14a91b7b` exited 0; all 4,350 trips completed with full 12-TLS coverage. Acceptance: 12/12 TLS use ≥2 actions; forced max-green 0/17,323; pooled censored travel 270.136818 s vs fixed 418.114749 s; worst TLS queue regression +15.48%; median inference 1.37985 ms. Required controller test 5 passed. Detailed per-cell/per-TLS evidence and comparison with the prior candidate are in `docs/rl_diagnostics.md` Part 2. At T4.7 completion, T4.8 was the next task; its completed result is in the following row. |
| [x] T4.8 Network evaluation harness | Done | 2026-11-01 | — | Development grid job `20261101-130401_d0dddfe6` exited 0; all 75 cells valid, matching routes, tests and byte-identical aggregation passed. Development Metric N was 23.35% below fixed. Coverage remains none at the 0.95 PPO-owned tick threshold; see `docs/results.md` Part 2. Final-seed work is documented under T4.9/T4.10. |
| [x] T4.9 Network results gate — FINAL | Done (Stage 4 hybrid reported) | 2026-11-02 | — | Frozen PPO-only audit job `20261101-160643_0cb80208` exited 0 with 75/75 valid cells; its coverage failure correctly triggered T4.10. The final unchanged-metric hybrid gate then finished job `20261101-194723_3fa4c619` RC 0 with 75/75 valid cells on seeds 6000–6004. Final Metric N is 277.532 s hybrid vs 375.478 s fixed: 25.84% improvement (paired 95% CI 22.20–29.49%), target MET, 100% completion. Final coverage is 0/12 (none) under the unchanged 0.95 criterion; the Stage-4 fallback result is disclosed without a complete-AI-ownership claim. Full report and per-TLS table: `docs/results.md` Part 3. |
| [x] T4.10 Stage-4 fallback | Done (triggered by T4.9 ownership failure) | 2026-11-02 | — | Reused validation evidence and frozen gate JSON `results/summary/t410_hybrid_gate.json` (SHA-256 `655e36c69382dbbbb39d3ef3144691fd0e635598a519bd63de8499672390ff55`): PPO admitted at 11 TLS, rule at `GS_cluster_11178931802_11178931803_2414626606_6887565739` after +15.48% queue regression. Hybrid dev/final grids each validate 75/75 cells; final completion is 100%, with 25.84% common-trip improvement vs fixed. Final coverage is 0/12 (none); fallback averages 57.52% on PPO-eligible TLS; four hybrid teleports are disclosed in `docs/results.md` Part 3. Reaggregation is byte-identical (comparison SHA-256 `8aefa3c0a2ae2ac13e9528de5da410670a1a74cc95f47adf0d706468f712dcd4`). Focused regression suite: 37 passed; full default suite: 87 passed; Phase 4 SUMO suite: 12 passed; whole-repo Ruff passes after exact-path exclusion of preserved untracked PDF helper; zombie check clean. |
| [ ] T5.1 Dashboard data layer + live-status files | Partial | 2026-11-03 | — | Existing fixed/medium/seed-3000 summaries match in all fields except `run_id`, `wall_clock_s`, and `config_hash`. Current hash is the current YAML SHA; old hash `6b0b87b8…b5bef` is absent from committed config history and its snapshot is not archived. Regression test added for raw-byte provenance hashes versus behavioral equality. Keep Partial until identical config provenance can be verified; details in `docs/PROGRESS.md`. |
| [x] T5.2 Dashboard views: live monitoring | Done | 2026-11-02 | — (uncommitted) | Built/launched the Windows Release app and loaded `D:\smart-traffic-management-system`. Fresh run `20261102-233024_rule_net_medium_s3001` visibly refreshed RUNNING state and active/waiting counts; while running, summary cards showed `—` instead of old values. After finish, dashboard avg_wait `41.206153846153846` and throughput `9.15707912655553` exactly matched this run's `summary.csv`; status was `finished`, 650/650 trips, 0 teleports, sim end 4259 s, exit 0. Fixed selected-run summary binding/cache refresh and added transient `PermissionError` retry for atomic status replacement. Flutter: 9 tests passed, analysis clean, Windows Release build succeeded. Status test: 4 passed; changed-file Ruff clean. See `docs/experiment_log.md` for commands and evidence. T5.1, T5.3 and T5.4 remain Partial; Phase 5 is not complete. |
| [x] T5.3 Dashboard views: comparison, results, history | Done | 2026-11-02 | — (uncommitted) | `flutter test --no-pub --reporter expanded` passed 10 tests, including synthetic censored/common context, low exclusion, `target_met=false`, partial coverage without full-coverage wording, explicit missing-comparison prompt, and a real-project render audit. `ruff check .` passed. Real M2/final hybrid values checked against `comparison.csv`: mean 277.5315164945055, CI 275.35166244368133–279.63375072252745, common mean 277.5315164945055 over 11,500 trips, completion 1.0, 5 seeds, improvements 25.842935394271755% vs fixed and 6.974859123248817% vs rule, `target_met=True`; summary coverage 0/12 (none). |
| [ ] T5.4 Dashboard integration, no-database check, docs | Partial (post-evaluation zombie check pending) | 2026-11-05 | — | Five Windows Release real-results loads measured median 1589.084 ms (492 raw dirs/460 summary rows each). Flutter analysis: no issues (49.2 s); widget tests 19 passed; Windows Release build 32.5 s; no-database test 2 passed; whole-repo Ruff clean. Freshness evidence `docs/evidence/t54_live_freshness_20261105.json`: 30/30 distinct producer timestamps rendered correctly, consecutive 5-s sim-time steps across 45.0 s, median age 661.151 ms, max 1676.448 ms (≤2 s NFR-PRF-02 criterion for this sample; not a universal guarantee). Check zombies after the active M1 grid finishes. NFR-PRF-03 REST latency is not applicable because no REST exists. |
| [ ] T6.1 Demo CLI | In progress | 2026-11-04 | — | Added `scripts.run_demo` with safe seed-block validation, cached-route preparation, live `status.json` progress output, and network `rl` routing to the delivered DEC-14 Stage 4 hybrid. Added `scripts/run_all.md`; focused CLI/controller-routing tests: 3 passed; Ruff clean. Remaining acceptance: six real demo controller/family runs, 1-hour session, clean zombie check, and dashboard live-view verification. |
| [ ] T6.2 Quality pass + blocker sweep | In progress | 2026-11-05 | — | Removed stale vision/prediction placeholders from package discovery, config, setup docs and requirements; `IntersectionState.source` is now SUMO-only. Whole-repository Ruff passes; full default `pytest -q`: 101 passed, 1 skipped, 23 deselected in 20.62 s (cache warning); report test is 1 passed/1 skipped pending M1. `pip check`: no broken requirements. Final static scope search found no removed-scope code/dependency hits; reviewed secret matches were placeholders/code tokens and binary diagram names. Ignore probes confirm `.venv`, `.env`, `results/raw/`, `results/jobs/`. Four >10 MB tracked files are existing SUMO network/backup inputs and `Documents/Untitled document.docx`; none modified. The untracked pre-existing `tmp/pdfs/build_report.py` is documented and has an exact-path lint exclusion. Full SUMO suite, final artifact audit, blocker recheck and zombie check remain pending. |
| [x] T6.3 Documentation | Done with deviation (unrun commands itemized) | 2026-11-05 | — (record task commit hash after local commit) | README, SRS deviations, limitations and report/PPT input inventory are complete. Windows checks and saved M2 evaluation are verified; unrun Ubuntu, fresh-install, T6.1 demo and exact dashboard launch commands are listed in README. Local Markdown-link audit passed 8/8. M1 values remain explicitly pending T3.2; dashboard/live demo evidence remains T6.1. |
| [ ] T6.4 Release | Not started | | | |

| Decision register | Status |
|---|---|
| P1 Supervisor confirms headline metrics (M1 junction trips; M2 network-wide) | Pending — labels only, never blocks |
| P2 Supervisor acknowledges SRS deviations | Pending — labels only, never blocks |
| P3 M1 pilot junction | Resolved (T0.3) |
| P4 Intended TLS list | Autonomous default: agent freezes it at the end of T4.1 |
| P5 Fallback if shared PPO cannot cover all intended TLS | Autonomous default: T4.10 triggers automatically, labelled with coverage fraction |
| P6 Dashboard technology and view list | Owner-directed Flutter Windows desktop app / local files / six views |

**Order:** 0 → 1 → 2 → 3 (**M1 reached**) → **4 (M2, the final AI result)** → 5 (dashboard) → 6 (release). Numeric order is the default; a blocked task never stops independent work (0.11). Each phase ends with a checkpoint on the single branch `agent/autonomous-build` (0.5); `main` is merged only when necessary (T6.4). Backend, database, computer vision, prediction and optional features: not in scope.

---

# 13. Definition of done

**All items 1–11 are required; no phase may be silently omitted.** Anything not achieved must be labelled honestly in Section 12, `docs/results.md`, `docs/limitations.md` and the release checklist. The single-junction milestone (items 3–4) is **necessary but not sufficient**: without items 5–7 the project is not complete.

1. SUMO starts from the documented command with the intended map and no unexplained warnings.
2. Safety tests prove — for the M1 junction (T1.2) **and for every intended junction simultaneously** (T4.2): no conflicting greens, yellow on every change, min/max green enforced, fallback works, excluded TLS never commanded.
3. **M1:** fixed, rule-based and RL controllers run on identical scenarios and seeds (≥ 5 per scenario, all seven single-junction scenarios); results regenerate from documented commands.
4. **M1 results:** `docs/results.md` Part 1 reports the measured reduction from the final seed block (run once on the frozen model) for metric B (headline, provisional) and A, per scenario, `low` separate, common-trip beside censored time and completion rates, with limitations — labelled "milestone, not the final result" (and stating a failed T2.5 gate if one occurred).
5. **M2 scope:** the intended TLS list is documented (`docs/network_tls.md`), frozen by the agent at the end of T4.1 with hash and time (DEC-13) before any evaluation, with every excluded TLS and its reason.
6. **M2 AI control of all intended traffic lights:** in the final-seed `rl` runs, `summary.csv` shows `n_tls_ai == n_tls_controlled == len(network.controlled_tls)` (`ai_coverage = full`), with every junction's `ppo_tick_share ≥ eval.ai_coverage_min_share` in `junctions.csv`. If that was not achieved, the deliverable is explicitly labelled with its DEC-14 level (Stage 4 hybrid / rule-only, AI-coverage fraction stated, the automatic T4.10 trigger recorded) and is **not** described as full AI control.
7. **M2 network-level results:** `docs/results.md` Part 2 reports, from the final network seed block (run once on the frozen model), Metric N, measured reduction, `target_met` yes/no, common-trip beside censored and completion rates, per-scenario rows with `net_low` separate, the per-junction congestion table, and limitations.
8. **Dashboard (Phase 5):** a functioning local, read-only, file-based dashboard (DEC-15) starts from the documented command and displays — from real files produced by the system, never fabricated — simulation status, signal states and phases, queue lengths and waiting times, congestion and vehicle-flow metrics, the fixed-time / rule-based / PPO comparison, evaluation results and performance indicators (including `target_met` and `ai_coverage`; M1 labelled as milestone), and historical experiment results from saved CSV/JSON; the tests of T5.1–T5.4 pass and `docs/dashboard.md` exists.
9. Tests, lint (whole repo, justified exclusions only), README and docs pass; no secrets, no unused dependencies, no large artifacts committed; **no database, backend/API, OpenCV/YOLO or prediction-model code or dependency exists** (`tests/test_no_database.py`, T5.4; T6.2).
10. SRS deviations are documented (`docs/srs_deviations.md`); P1/P2 are listed as pending supervisor items; P3–P6 outcomes are recorded as autonomous decisions in `docs/decisions.md`; every open blocker (if any) is listed with the exact question.
11. Report, PPT and demo use only validated numbers from `results/`; the one-command demo runs for both families, the network `rl` demo shows AI control across the intended TLS (or states the DEC-14 level reached), and the dashboard displays the demo run.

---

# 14. Execution budget, order and cut lines (all applied by the agent, none needs approval)

**Priority order when time or compute is short** (apply in this order, log each in `docs/decisions.md`; if `project.deadline_utc` is set, apply them earlier by estimating remaining time from measured throughput):
1. **No phase is optional.** The former prediction and camera phases are removed from scope, not deferred.
2. **Within Phase 4, reduce cost, never coverage:** fewer training scenarios, shorter episodes, larger decision interval, one PPO seed, early stop on validation (DEC-14 Stage 3). The frozen intended TLS list is not shrunk to save time. Fewer evaluation seeds are **not** an allowed cut once a final block is defined (DEC-09).
3. **If shared PPO cannot cover all intended TLS or pass T4.7 within budget → T4.10 triggers automatically**, with honest labelling of the level reached and the AI-coverage fraction. Single-junction control is never silently reported as the final result.
4. **Keep Phase 5 to exactly the views of T5.2–T5.3** and Phase 6 lean.
5. **Never cut:** Phases 0–3 (M1); Phase 4 with a validated, honestly labelled result in `docs/results.md`; Phase 5 (dashboard at the listed minimal scope); lean Phase 6 (T6.1–T6.4, incl. docs).

**Compute budgets (defaults):** M1 main PPO ≤ `rl.max_train_hours` (10 h); M2 main PPO ≤ `rl_net.max_train_hours` (10 h); evaluation grids run in parallel (`jobs.parallel_runs`); waiting time on long jobs is used for independent tasks (0.11). Long jobs are unattended and resumable (0.8, 0.12).

**Indicative effort (for planning only, not a gate):** Phases 0–1 are done; Phase 2 ≈ one overnight PPO run plus gate iterations; Phase 3 ≈ evaluation grid (105 runs per seed set, parallel); Phase 4 is the longest (network baselines, env gate, staged shared-PPO training, 75-run evaluation grids); Phase 5 and Phase 6 are short and mostly independent of PPO outcomes, so they proceed while a PPO job runs or when a PPO-dependent task is blocked.
