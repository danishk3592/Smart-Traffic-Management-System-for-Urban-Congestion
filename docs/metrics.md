# Run metrics (version 1)

Each `results/raw/<run_id>/` contains immutable `steps.csv`, `trips.csv`, `run.json`, and a generated one-row `summary.csv`. `Ai.common.metrics.summarize_run` builds the summary from those artifacts. The same cached route file is used for route-based junction membership across controllers.

## Definitions and units

- `n_trips` and `n_trips_junction` count scheduled route-file vehicles. A junction trip has at least one consecutive `from_edge -> to_edge` pair controlled by the selected TLS, as determined by `Ai/common/junction.py`; merely touching an incoming edge does not qualify.
- Completed-trip travel time is `depart_delay + duration` (seconds), equivalently arrival minus scheduled departure. An unfinished trip is censored at `sim_end_time - scheduled_depart`; this includes vehicles still waiting in the SUMO insertion backlog. The four completed/censored averages are shown for all trips and for route-through-junction trips. Completion rates use the corresponding scheduled-trip denominator.
- `avg_wait`, `avg_time_loss`, and `avg_depart_delay` are per scheduled vehicle (seconds). Completed values come from SUMO tripinfo. For unfinished vehicles, waiting is accumulated from TraCI samples at the configured step-log interval and time loss is the latest cumulative TraCI value; these unfinished-vehicle values are approximate because samples are periodic.
- `avg_queue` is the mean total halting count across approaches at each logged simulation time. `avg_speed` is the mean per-trip route length divided by censored trip time, converted to km/h. `throughput_veh_per_min` counts vehicles observed crossing at least one controlled movement, divided by simulated minutes. `frac_time_high_congestion` is the fraction of logged simulation times where at least one configured approach is classified High.
- `teleports` is the count of distinct vehicle IDs observed starting a teleport. `wall_clock_s` is measured elapsed time for the simulation episode, excluding route generation and metric postprocessing. `git_commit`, `config_hash`, and `metrics_version` identify the run inputs.
- For the fixed-time acceptance cross-check, `run.json` lists every completed route-through vehicle missing a recorded controlled-movement crossing, and separates mismatches with a recorded teleport from those without one. The latter must be investigated before accepting T1.4.
- For the single-junction family, exactly one TLS is controlled; `n_tls_ai=0` and `ai_coverage=none` describe the non-PPO fixed/rule controllers. Network-only queue fields are blank. Network-run fields are added by the network milestones.

## Legacy baseline figure

The previously reported “4,408 trips / 3,323 completed / 1,085 unfinished / ~299 s” is retained as a historical result under its original counting and timing definitions. It must not be relabeled as a T1.4 metric: the new definitions count scheduled route-file vehicles, include insertion delay in completed travel time, censor every unfinished trip at the common simulation end, and use actual TLS-controlled consecutive edge pairs for junction membership. The old figure is explained here rather than recalculated or overwritten.

## Aggregation (DEC-01)

For evaluation, compare fixed, rule, and RL on identical scenario/seed routes. Compute per-run Metric A for all scheduled trips and provisional Metric B for trips whose planned route contains a controlled movement. Report completed common-trip travel time and censored all-scheduled-trip time/completion rates together. Average per-seed improvement within each scenario, then take an unweighted mean over the six non-low scenarios; show medium, heavy, and rush-hour separately, and report low separately. Pooled-trip aggregation is a sensitivity check. A reduction target is not a presumed outcome.
