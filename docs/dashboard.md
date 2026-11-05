# Local dashboard

The Flutter dashboard is a local, read-only viewer. It reads CSV/JSON already written by STMS, has no backend/API/database, opens no TraCI connection, and sends no signal-control commands. It displays only data from the selected project folder. Missing or invalid data is shown as no data/error; the UI does not substitute sample metrics.

## Windows startup

From the repository root, use the installed Flutter SDK:

```powershell
cd dashboard_flutter
C:\src\flutter\bin\flutter.bat pub get
C:\src\flutter\bin\flutter.bat run -d windows
```

The validated Windows Release executable is `dashboard_flutter\build\windows\x64\runner\Release\dashboard_flutter.exe`. Launch it directly, then use the folder button to select the repository root (or another STMS project folder containing `results/`).

## Ubuntu startup

Linux desktop startup is documented but has not been validated on this machine. After installing Flutter and the Linux desktop toolchain (`clang`, `cmake`, `ninja-build`, `pkg-config`, GTK 3 development headers, and `libstdc++`), enable Linux desktop support and run:

```bash
cd dashboard_flutter
flutter config --enable-linux-desktop
flutter pub get
flutter run -d linux
```

Select the repository root in the folder picker after launch. The generated web target is unsupported; Linux desktop behavior is not part of the verified Windows acceptance evidence.

## Views and data sources

| View | Data source |
|---|---|
| Traffic Operations Overview | Selected run's `results/raw/<run_id>/status.json`, `steps.csv`, and `summary.csv`; status is preferred for run state and live simulation time. |
| Live Signal & Traffic Monitoring | Selected run's `status.json`, `steps.csv`, and `junctions.csv` when present. |
| Performance and controller evaluation | Saved `results/summary/comparison.csv`, summary rows, and junction rows. |
| Experiment History | `results/raw/*/summary.csv` and `Ai/rl/models/*/config.json`. |

Real-data audit (2026-11-03) compared the saved run summary files with dashboard values:

| Family | Run ID | Average waiting time | Throughput (vehicles/min) | Result |
|---|---|---:|---:|---|
| Single | `20261102-211150_fixed_medium_s3000` | 2505.193076923077 s | 2.075 | Displayed values matched `summary.csv`. |
| Network | `20261102-140258_rule_net_medium_s8000` | 41.036923076923074 s | 9.048723897911833 | Saved history/dashboard values matched `summary.csv`. |

The history is local to this machine because `results/raw/` is not committed. The dashboard reads saved metrics and confidence intervals; it does not recompute them. Common-trip comparison values are not presented without censored comparison context. M1 is labelled a milestone, and AI coverage is copied from saved evidence; full network-wide AI control is shown only when the saved coverage field is `full`. All results are simulated.

## Refresh, freshness, and stale data

After a project folder is loaded, the store polls once per second. Filesystem discovery, metadata checks, CSV parsing, and summary reads run in a background isolate. Run directories and summary files are checked in bounded batches; summary fingerprints include modification time and file size, so a summary created after its run directory is first discovered is loaded on a later poll. The run selector refreshes without reloading the project folder. A selected run stays selected while it exists; newly discovered runs appear at the top of the selector and can be selected explicitly.

A `running` status whose `updated_utc` is more than 15 seconds old is classified as stale. An incomplete trailing CSV record is ignored while the simulation writes. A run directory is discoverable before its files are complete, but absent or invalid status/summary files are treated as unavailable and retried on later polls. Changing the selected run clears its run-specific telemetry immediately; run metrics are read only from that selected run, and a status `run_id` mismatch is rejected. Summary metrics stay blank while a live run has no completed summary, so prior-run values are not presented as current.

T5.4 measurements on this Windows machine:

| Method / measurement | Observation | Interpretation |
|---|---:|---|
| Earlier executable launch to main-window handle | 4.43 s, one launch | Prior OS-window startup sample; retained as a single observation. |
| Earlier folder selection to real-results page | approximately 5 s, one observation | Prior externally observed sample with a different start/end boundary. |
| Release process launch to measurement-app exit, five processes | 5146.6, 4087.0, 4072.2, 5075.6, 5084.4 ms; median **5075.6 ms** | PowerShell stopwatch around `Start-Process -Wait`; includes app startup, real-data loading, report write, and process exit, so it is not a pure startup or page-load measure. |
| Windows Release real-results load, five separate processes | 1610.269, 1401.459, 1199.841, 1589.084, 1916.659 ms; median **1589.084 ms** | Each app process loaded the repository's real project root and rendered its first post-load Flutter frame after `DashboardStore.loadFolder()` returned. All five discovered 492 run directories, loaded 460 summary rows, selected `20261103-005248_rule_net_medium_s8000`, and confirmed its summary was present. This is an app-internal Flutter frame measurement, not a screenshot timestamp or a cold-cache guarantee. |
| Dart entry to initial Flutter frame, same five processes | 34.432, 33.590, 39.196, 39.632, 55.944 ms; median **39.196 ms** | Startup inside Dart/Flutter only; excludes Windows process creation and native engine startup, so it is not comparable to the prior 4.43 s window-handle sample. |
| Live `status.json` update to Flutter post-frame `Last update`, run `20261105-144059_fixed_balanced_s6002` | 30 samples across 45.0 s; ages min 155.555 ms, median **661.151 ms**, max **1676.448 ms** | All 30 source timestamps were unique and rendered text matched the source in 30/30 samples. Sim-time increments were exactly 5 s for all 29 consecutive pairs. Max observed age was below NFR-PRF-02's 2 s limit. Raw sample evidence: [`t54_live_freshness_20261105.json`](evidence/t54_live_freshness_20261105.json), SHA-256 `de704ecd51e8fbca3e4b4202b2d118bdaee1ed1fdd930b3fb31ec682cc25417b`. |
| Historical screenshot observations, run `20261103-005248_rule_net_medium_s8000` | 4 observations; approximately 0.6, 1.3, 1.5, 1.2 s; max approximately **1.5 s** | Earlier visual observations, retained as historical context; the 30-sample app-frame measurement above is the current numeric acceptance evidence. |

### Measurement procedure and limits

Flutter widget tests and `integration_test`/`pumpAndSettle` can time app code or test frames, but those values are not Windows Release application timings. The selected method added an opt-in Release-only command-line measurement path to the actual dashboard. Launch each process from the Release directory with `--t54-measure-root=<project-root>` and a unique `--t54-measure-output=<json-path>`. Start timing immediately before `DashboardStore.loadFolder(root)` (after the initial no-data frame); stop in the first post-frame callback after loading has completed and real run summaries are present. The output records the selected real run and loaded-data counts, allowing invalid/fixture-only observations to be rejected. For safety, report paths must be new `stms_t54_*.json` files under the OS temporary directory; exclusive creation rejects existing files and paths under project results. With neither measurement flag, normal startup stays on the ordinary no-data/folder-picker path. The five processes ran sequentially against unchanged saved results; Windows filesystem cache state was not cleared or controlled. Process-launch-to-exit is a separate, broader interval that includes data loading, report writing, and app exit.

**Live measurement, 2026-11-05.** The actual Windows Release app used the production `DashboardStore` and selected the currently running M1 producer `20261105-144059_fixed_balanced_s6002`. Across the first dashboard load and 45.0 seconds of continued updates, it captured 30 samples at sim times 5085–5230 s. Every displayed `Last update` string matched its producer `updated_utc`; all 29 inter-sample sim-time deltas were 5 s, so no update was skipped in this sample. The ages were recomputed from the raw UTC pairs and matched the report: minimum 155.555 ms, median 661.151 ms, maximum 1676.448 ms. All 30 were ≤2000 ms. The raw report, including every value and timestamp, is preserved at [`docs/evidence/t54_live_freshness_20261105.json`](evidence/t54_live_freshness_20261105.json). The producer was part of the six-worker final M1 run; this is one measured interval and does not guarantee the same bound under every load.

The opt-in measurement mode is available in the real Flutter app. After a live run's `status.json` exists, launch the Release executable with `--t54-freshness-root=<project-root>`, `--t54-freshness-run-id=<run_id>`, and `--t54-freshness-output=<new stms_t54_*.json path under the OS temp directory>`. It loads the project through the production `DashboardStore`, selects the requested run, and records 30 distinct `updated_utc` values with UTC timestamps in post-frame callbacks while the overview renders the `Last update` value. The report includes raw pairs, run ID, sample count, median age and maximum age; report creation is exclusive and constrained to the OS temp directory. Ordinary startup is unchanged when these flags are absent. The validated raw report was copied unchanged from OS temp into `docs/evidence/` for durable review. The Computer Use helper was unavailable during this run, so no screenshot or separate visual observation is claimed.

The current 30-sample Release measurement is below the approved SRS NFR-PRF-02 threshold of ≤2 seconds. This demonstrates the threshold for one 45-second sample interval on the measured live M1 run; it is not a universal latency guarantee. NFR-PRF-03's REST latency is not applicable because this local file-based app has no REST endpoints. T5.4's post-run zombie check remains pending until the active evaluation finishes.

## Limitations

The application is supported on Windows desktop only. It is local, read-only, unauthenticated, simulation-only, and can show only data already on disk. The generated web target is unsupported because local folder access uses `dart:io`. It does not provide manual overrides, remote control, a backend, REST/WebSocket, or persistence beyond project CSV/JSON files. Large result directories still require a full metadata pass on each poll; scans run off the UI isolate, but timing under substantially larger directories and heavier concurrent load has not been characterized. Raw results are not committed.

## Validation record

On 2026-11-03, Flutter 3.47.9 / Dart 3.13.7 commands from `dashboard_flutter/` passed: `flutter analyze --no-pub` (no issues), `flutter test --no-pub --reporter expanded` (16 tests at the five-load measurement stage), and `flutter build windows --no-pub` (Release executable built). From the repository root, `Ai/.venv/Scripts/python.exe -m pytest -q tests/test_no_database.py` passed 2 tests, `Ai/.venv/Scripts/ruff.exe check .` passed, and `Ai/.venv/Scripts/python.exe scripts/check_zombies.py` found no running SUMO/SUMO-GUI processes after the fresh live run. Both-family saved-run audit passed. Latest run `20261103-005248_rule_net_medium_s8000` was discovered and selected without project-folder reload; after completion, displayed average wait `41.036923076923074 s` and throughput `9.048723897911833 vehicles/min`, matching its `summary.csv`. See [`t54-prior-run-selected.jpg`](evidence/t54-prior-run-selected.jpg), [`t54-new-run-selected.jpg`](evidence/t54-new-run-selected.jpg), and `docs/experiment_log.md`. The five-load page median is now recorded above. T5.4 remains Partial because NFR-PRF-02 live freshness is not established by the four prior observations.

On 2026-11-03, the guarded measurement-mode follow-up passed Flutter analysis, all 18 widget tests, and an explicit Windows Release build. A Release smoke measurement wrote one report to the OS temp directory, exited 0, and loaded the same 492 run directories/460 summary rows. Regression tests verified that ordinary args do not enable measurement mode, an output under `results/raw/` is rejected without changing the file, and an existing temp report cannot be overwritten. The five-sample timing table above remains the acceptance set; this smoke run is not added to it. The focused Python regression suite also passed 11 tests (metrics, status, and episode runner). T5.4 remains Partial because NFR-PRF-02 live producer-to-display freshness has not been established.

**2026-11-04 follow-up:** `pytest -q tests/test_no_database.py` passed (2 tests). The new freshness instrumentation passed direct Dart analysis after a formatting fix (`No issues found!`). Its Flutter widget run was interrupted without test output after about six minutes while the six-worker T3.2 evaluation was active; this is inconclusive and must be retried after the grid releases resources. The Windows Computer Use helper failed twice with `Computer Use native pipe is unavailable` and again after reinitialization; Windows Management Instrumentation process inspection returned `Access denied`. No new window screenshot or visual observation is claimed. A live post-frame measurement remains outstanding; the T5.4 task is Partial.

**2026-11-05 follow-up:** `flutter analyze --no-pub` reported no issues (49.2 s), Flutter widget tests passed 19/19, and `flutter build windows --release --no-pub` succeeded in 32.5 s. `pytest -q tests/test_no_database.py` passed 2 tests, whole-repository Ruff passed, and a fresh Windows Release live-freshness report records 30 consecutive updates with a maximum 1676.448 ms age. The raw sample is in `docs/evidence/t54_live_freshness_20261105.json`. The current M1 evaluation still has six active SUMO workers, so the required clean post-run zombie check is deferred until they finish. Computer Use failed after its prescribed retry/reset; no screenshot is claimed.
