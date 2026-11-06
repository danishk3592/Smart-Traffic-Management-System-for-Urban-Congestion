# Windows 11 setup

This is the supported fresh-clone path for the current Phase 1 checkpoint. The setup is pinned to the versions verified in the repository's local Windows environment on 2026-11-05. It uses CPU-only PyTorch by default; an NVIDIA GPU and CUDA are optional.

## Prerequisites

Install these before cloning:

1. **64-bit Python 3.14** from [python.org](https://www.python.org/downloads/). The repository metadata permits Python 3.10+, but this dependency set was verified locally on Python 3.14.10 on 2026-11-05. The Windows lock file was originally captured on Python 3.14.2 and rechecked on 3.14.10. PyTorch's Windows support in the verified environment covers this Python version.
2. **Eclipse SUMO 1.27.1 for Windows** from the [official SUMO downloads](https://sumo.dlr.de/userdoc/Downloads.php). This matches the repository's pinned `traci` and `sumolib` packages. The newer SUMO release may need a coordinated package/config update; the setup checker intentionally requires 1.27.1.
3. **Git for Windows**.

The SUMO installer normally adds its executables to `PATH` and sets `SUMO_HOME`. If that did not happen, configure `SUMO_HOME` to the SUMO installation directory and add its `bin` directory to `PATH`, then open a new PowerShell window. The checker requires `sumo`, `sumo-gui`, `duarouter`, and `netconvert`.

## Clone and set up

Open PowerShell in the directory where you keep projects and run:

```powershell
git clone https://github.com/hannanahmedqureshi786-eng/smart-traffic-management-system.git
cd smart-traffic-management-system
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

The script creates `Ai/.venv` with Python 3.14, installs the pinned Windows dependency lock and editable project package, and runs the environment checker. It will not replace an existing `Ai/.venv`; if one already exists, the script checks it and installs into it. If it uses a different Python minor version, the script stops with an error and preserves it.

Then activate the environment and verify again:

```powershell
.\Ai\.venv\Scripts\Activate.ps1
python .\scripts\check_environment.py
```

The environment checker is read-only. A successful result confirms Python package imports and pins, project configuration, the referenced SUMO net/route/additional/GUI files, the required project scripts, SUMO version and executables, and `SUMO_HOME`.

## GPU use is optional

The default setup installs CPU-only PyTorch and works without an NVIDIA GPU, CUDA toolkit, or `nvidia-smi`. The project config also defaults PPO to `cpu`. If you later want CUDA acceleration, use the current [official PyTorch Windows install selector](https://pytorch.org/get-started/locally/) to select a supported CUDA build, then verify with:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

CUDA acceleration is not required for setup or for the environment checker. The target ASUS laptop specifications in this repository's project facts were supplied by the user; that computer has not been tested here.

## Dependency groups

- `requirements.txt`: pinned project runtime, SUMO/TraCI, and PPO stack.
- `requirements-dev.txt`: pinned pytest and Ruff tools.
- `requirements.lock.txt`: pinned transitive dependency set for Windows CPython 3.14.x; it was captured on Python 3.14.2 and rechecked on the installed Python 3.14.10 environment on 2026-11-04. The setup script installs the CPU Torch wheel first, then this lock.
- `Ai/requirements.txt`: compatibility include for the root runtime and development files. Use the root files for new setup work.

## Phase 1 checkpoint

After setup, the repository remains at the Phase 1 checkpoint. To run the current default unit suite and lint check:

```powershell
pytest -q
ruff check .
```

SUMO integration tests are marked separately and require the installed SUMO tools. Setup does not start simulations, train PPO, or alter any SUMO network files.
