# Project facts and environment audit

**Audit date:** 2026-10-25; environment recheck: 2026-11-04. Facts marked verified below came from commands run in this checkout. The target ASUS specifications are user-provided and were not measured.

## Current repository and checkpoint

- Stable checkpoint and current `HEAD` at audit start: `cde577aae0d256d785dbd670caab25db10805f07` (`cde577a`), on branch `agent/phase-2-rl`.
- The repository contains the Phase 1 core, RL scripts, tests, config, SUMO scenario files, a Python environment under `Ai/.venv`, and the setup/development directories. `README.md` is absent; the Windows instructions are in `docs/windows_setup.md`.
- A pre-existing dirty worktree was present at audit start: modified `SUMO/No_Polygon_Map/edgeData.xml`; untracked `Ai/rl/models/`, `Ai/rl/ppo_evaluation.csv`, and `✅ HSR Layout.txt`. These items were preserved without staging or modification.
- The protected SUMO maps were inspected read-only. No setup task writes into either `SUMO/No_Polygon_Map/` or `SUMO/Polygon_Map/`.

## Machine facts

- **Verified local host:** Windows 11, build `10.0.26300` as reported by Python `platform.platform()`.
- **Target computer (provided, not tested):** ASUS ROG Strix G16 G614JU; Intel i7-13650HX; NVIDIA RTX 4050 Laptop GPU with 6 GB VRAM; 16 GB DDR5 RAM; Windows 11.
- Do not treat the target's supplied specifications as local measurements or as proof that CUDA or training performance works.

## Python and package compatibility

- **Verified project interpreter (2026-11-04):** `Ai/.venv/Scripts/python.exe`, Python `3.14.10`. The 2026-10-25 audit recorded Python 3.14.2; both are within the configured 3.14.x setup target.
- **Verified relevant installed versions:** Gymnasium `1.4.0`; NumPy `2.5.4`; PyYAML `6.0.3`; Stable-Baselines3 `2.9.0`; Torch `2.14.1+cpu`; TraCI and sumolib `1.27.1`; psutil `7.2.2`.
- **CUDA status in the verified environment:** Torch reports a CPU build (`torch.version.cuda` is `None`) and `torch.cuda.is_available()` is `False`. CPU is the supported default; this says nothing about the target laptop's CUDA capability.
- `pyproject.toml` declares `requires-python = ">=3.10"`. The full current runtime/dev stack has been checked on Python 3.14.2 historically and Python 3.14.10 on 2026-11-04; the setup script targets Python 3.14.x. Other minor versions have not been verified here.
- The root runtime/dev requirements pin direct dependencies, and `requirements.lock.txt` records the verified Windows environment's pinned dependency closure. Removed-scope vision packages are not project dependencies.
- The existing `Ai/.venv`'s `pip freeze` currently points its editable project install at `C:\Users\empow\AppData\Local\Temp\STMS_phase0_foundation_20261020`; this setup task did not alter that pre-existing environment. The full setup script installs the current checkout as editable after installing the lock.
- The legacy dependency inventory in `Ai/requirements.txt` included packages with no imports in the current source tree (for example Qiskit, PyMuPDF, python-docx, and IPython); it now includes the root runtime and dev files instead of pinning that inventory.

## Dependency audit from current Python imports

| Group | Packages | Evidence / status |
|---|---|---|
| Runtime | `traci`, `sumolib`, `numpy`, `PyYAML`, `gymnasium`, `stable-baselines3`, `torch`, `psutil` | Imported by current code, RL scripts, or `scripts/check_zombies.py`; pinned in `requirements.txt`. |
| Development | `pytest`, `pytest-cov`, `pytest-timeout`, `ruff` | Test/lint tooling; pinned in `requirements-dev.txt`. |
| Not direct project dependencies | `pandas`, `matplotlib`, `scikit-learn`, `joblib`, `tensorboard`, IPython/Jupyter packages, Qiskit, document/PDF packages, and other packages from the supplied inventory | No direct imports found in current project/test Python files. Some packages can still arrive transitively through the pinned RL stack. |
| Deferred web/database | FastAPI, Uvicorn, SQLAlchemy, psycopg2, Supabase, Alembic | No imports found; remain out of scope. |

The import scan covered Python files under `Ai/`, `scripts/`, and `tests/`. Standard-library imports are not listed above.

## SUMO facts

- **Verified installed binary:** Eclipse SUMO `1.27.1`; `SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo\`.
- **Verified PATH commands:** `sumo`, `sumo-gui`, `duarouter`, and `netconvert` all resolve.
- The environment reported `traci` and `sumolib` `1.27.1`, matching the binary version.
- `SUMO/No_Polygon_Map/osm.sumocfg` references `osm.net.xml`, `osm.passenger.rou.xml`, and `output.add.xml`; these and the GUI settings file are checked by `scripts/check_environment.py`.
- For a fresh setup, SUMO 1.27.1 is specified to match the repository package pins. The computer running this audit is not evidence that the target laptop has SUMO installed.

## Setup validation status

- `scripts/setup_windows.ps1` creates/reuses `Ai/.venv`, installs CPU-only PyTorch plus the pinned lock, installs the project editable, and invokes the environment checker. It refuses to replace an existing environment.
- `scripts/check_environment.py` checks Python 3.14, direct package imports and pins, `SUMO_HOME`, SUMO tools/version, configuration references, and required project scripts. It reports NVIDIA availability as informational only.
- **Verified locally:** environment checker passed on Python 3.14.2; all 12 direct runtime/dev package imports and pins passed; SUMO 1.27.1, four commands, SUMO_HOME, config references, and required files passed. It reported CPU-only Torch and no `nvidia-smi` as informational.
- **Verified locally:** `pip check` reported `No broken requirements found.` A no-network `pip install --dry-run --no-index -r requirements.lock.txt` found every locked package already satisfied in the existing environment.
- **Verified locally:** PowerShell parser accepted `setup_windows.ps1`; running it with `-CheckOnly` completed successfully. Ruff passed for the new checker; `py_compile` passed.
- **Not run:** creating a new venv and downloading/installing packages. This checkout already has `Ai/.venv`, and GitHub access from this environment failed, so a fresh network install could not be validated here. No claim is made that the target ASUS laptop has been tested.

## Historical T0.1 audit (retained)

The original T0.1 audit dated 2026-10-20 reported a local Windows 11 host with 4 physical/8 logical cores, 31.78 GiB RAM, and an earlier OS build. At that time Python 3.14.2 and SUMO 1.27.1 were observed; CPU/GPU model details were not fully detected. A 600-step headless SUMO run measured 22.6325531 real seconds (26.51 simulated seconds per real second) with warnings suppressed. A 3,600-step baseline attempt was interrupted, so its historical trip totals were not reproduced. These are historical audit observations, not new measurements from the setup task.
