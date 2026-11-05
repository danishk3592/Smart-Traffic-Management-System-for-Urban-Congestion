# Reproducible command order

Run from the repository root in PowerShell. The verified interpreter is `Ai/.venv/Scripts/python.exe` (Python 3.14.10, rechecked 2026-11-05; 3.14.2 was recorded in an earlier audit). SUMO 1.27.1 must be on PATH.

## Prepare scenarios

```powershell
Ai/.venv/Scripts/python.exe -m scripts.make_scenarios --train-pool
Ai/.venv/Scripts/python.exe -m scripts.make_scenarios --family network --train-pool
```

The route builders validate manifests and reuse matching caches. Demo routes use a separate seed block (8000 and above).

## Run controller smoke episodes

```powershell
Ai/.venv/Scripts/python.exe -m Ai.common.run_episode --family single --controller fixed --scenario medium --seed 8000
Ai/.venv/Scripts/python.exe -m Ai.common.run_episode --family single --controller rule --scenario medium --seed 8000
Ai/.venv/Scripts/python.exe -m Ai.common.run_episode --family network --controller fixed --scenario net_medium --seed 8000
Ai/.venv/Scripts/python.exe -m Ai.common.run_episode --family network --controller rule --scenario net_medium --seed 8000
```

## Train and evaluate

The accepted checkpoints are versioned and pinned in `config/stms.yaml` and model `config.json` files. Do not overwrite them. The historical M1 main-stage command that created the accepted checkpoint is recorded in `docs/experiment_log.md` (T2.3); its output directory already exists, so rerun only into a new versioned directory after selecting the required training budget and seed block under the roadmap.

For command-order traceability, the exact already-executed M1 training command was:

```powershell
Ai/.venv/Scripts/python.exe -m Ai.rl.train_ppo --timesteps 200000 --seed 1000 --reward-weights queue=1,wait=0.5,throughput=0.5 --out Ai/rl/models/ppo_v2_variant_waithalf --resume
```

Its output directory contains the accepted model; do not repeat this command against that path. The network training stages and selected model hashes are recorded in `docs/experiment_log.md` and each model's `config.json`.

```powershell
Ai/.venv/Scripts/python.exe -m Ai.evaluation.evaluate --controllers fixed rule rl --seed-set final --jobs 6
Ai/.venv/Scripts/python.exe -m Ai.evaluation.evaluate --family network --controllers fixed rule hybrid --seed-set final --jobs 6
```

Final-seed evaluation blocks are frozen and must only be run once per frozen model and configuration. The commands above are resume-safe for the existing T3.2 M1 grid and T4.9 M2 grid; do not change model, seeds, scenarios, or metric definitions after inspecting results.

## Run the one-command demos

```powershell
Ai/.venv/Scripts/python.exe -m scripts.run_demo --family single --controller fixed --scenario medium --seed 8000
Ai/.venv/Scripts/python.exe -m scripts.run_demo --family single --controller rule --scenario medium --seed 8000
Ai/.venv/Scripts/python.exe -m scripts.run_demo --family single --controller rl --scenario medium --seed 8000
Ai/.venv/Scripts/python.exe -m scripts.run_demo --family network --controller fixed --scenario net_medium --seed 8000
Ai/.venv/Scripts/python.exe -m scripts.run_demo --family network --controller rule --scenario net_medium --seed 8000
Ai/.venv/Scripts/python.exe -m scripts.run_demo --family network --controller rl --scenario net_medium --seed 8000
```

The network `rl` demo uses the frozen DEC-14 Stage 4 hybrid and prints the measured `n_tls_ai`, `n_tls_controlled`, and coverage label. A partial or absent coverage label is reported exactly; it is never described as full AI control.

## Open the dashboard

```powershell
cd dashboard_flutter
C:\src\flutter\bin\flutter.bat run -d windows
```

Select the repository root. The dashboard reads saved `results/` files and never controls SUMO.
