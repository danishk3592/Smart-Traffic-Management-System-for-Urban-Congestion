# T2.1 reward design

This reward design was explicitly approved by the project owner on 2026-10-25. It is a project decision, not recovered from an earlier authoritative document. The initial weights and scales are starting values and have not been validated as optimal.

For one environment step:

    r_t = -w_q * q_norm - w_w * wait_norm + w_t * throughput_norm

- q_norm = clip((Q_t - Q_(t-1)) / S_q, -1, 1). Q_t is the current total halting-vehicle queue over configured controlled approaches. Q_(t-1) is the previous sample. Reset initializes Q_(t-1) from its first sample, so the first reward uses the queue change during the first decision interval. A queue decrease gives a positive queue contribution.
- wait_norm = clip(W_t / S_w, 0, 1). W_t is mean accumulated waiting time across all vehicles currently present in SUMO. It is zero when no vehicles are present.
- throughput_norm = clip(P_t / S_p, 0, 1). P_t is the number of vehicles passing the controlled junction during the preceding decision interval. The sensor reports vehicles per minute; the environment converts this rate using the measured interval duration.
- w_q, w_w, and w_t are configurable weights. Initial values are queue=1.0, wait=1.0, throughput=0.5.
- S_q, S_w, and S_p are configurable, finite, strictly positive scales in rl.reward_scales. Initial values are queue_change=300 vehicles, mean_wait_s=300 seconds, and throughput_vehicles=5 vehicles per decision interval. The queue value is 60 halting vehicles per each of five configured approaches; the wait value matches the existing state waiting-time normalization. The throughput value is an initial scale choice. These values are not claimed to be optimal.

## T4.5 network PPO environment

`NetworkVecEnv` presents one slot per frozen intended TLS in the exact sorted order recorded in `config/stms.yaml`. All slots share one SUMO process and one clock; each vector step samples one whole-network state, applies the action vector, advances the configured decision interval with the safety manager ticking after every SUMO step, and returns one row/reward/info per TLS.

### Observation layout

Each slot has `8 * network.max_approaches + network.max_phases + 2` float32 values clipped to `[0, 1]`. Approach slots follow that TLS's configured approach order and reuse the M1 `to_vector` feature encoding (four normalized measurements followed by four availability masks). Unused approach slots are zero. The phase one-hot occupies the first `len(green_phases)` entries of the fixed phase block; unused phase entries are zero. The last two entries are normalized elapsed green and its availability mask. This preserves the existing M1 feature normalization while making all slot shapes identical.

### Actions, lockouts, and safety

The shared action space is `Discrete(4)`: 0 extends/keeps for one interval; 1 requests the next verified green through `NetworkSafetyManager`; 2 and 3 keep and begin lockouts of `ceil(5 / decision_interval_s)` and `ceil(10 / decision_interval_s)` following decision ticks. A blocked switch or rejected request falls back to a safe keep request and increments that slot's illegal counter; rejected actions during a lockout also increment its hold-overridden counter. The environment never calls a TraCI TLS phase setter.

Every SUMO simulation step calls `NetworkSafetyManager.tick_all()`. A rejection or TraCI failure raises; it is not converted into a synthetic sample. Episodes end only at `rl_net.episode_s` with VecEnv `done=True`, `TimeLimit.truncated`, and a copy of the terminal observation in each slot's info. SUMO is then closed and a seeded RNG selects a cached network scenario/seed pair; the selected route is checked before the next episode starts. SB3 receives the conventional per-slot seed list (`seed + slot`); because slots share one simulation, the first slot seed initializes the shared episode chooser, and actual simulation seeds remain selected only from the configured cached pool.

### Reward

Each slot applies the M1 weighted reward to its own approaches: normalized local queue change, mean waiting time over vehicles currently on those approaches, and arrivals observed in the preceding interval. T4.5 uses the T2.5-selected weights (`queue=1.0, wait=0.5, throughput=0.5`) in `rl_net.reward_weights`; an optional scalar `rl_net.network_term_weight` adds that weight times the mean local reward to every slot reward (default zero). Validation/testing uses separate environment instances and seeds 3000–3009; training routes remain in the configured 1000–1999 pool. The shared clock makes simultaneous slot samples correlated and other junction policies non-stationary; parameter sharing assumes the padded junction observations are sufficiently comparable. This design is not evidence of PPO convergence or network-wide effectiveness.

## T4.6 shared-policy training and validation

`Ai/rl/train_ppo_network.py` trains one `MlpPolicy` over the 12 shared-clock TLS slots. A vector step contributes 12 SB3 timesteps; the rollout uses 512 vector steps (6,144 samples, divisible by batch size 128). Training episodes draw from the configured cached network training pool, while deterministic validation runs the three reserved pairs in `rl_net.validation_pairs` through a separate environment. Validation computes censored average travel time over all scheduled trips and completion rate from SUMO tripinfo plus the exact cached route catalog. The callback logs pair-level measurements and selects the checkpoint with the lowest mean censored travel time, independent of training return.

Training metadata includes the frozen TLS-list hash and slot order, training/validation seeds, reward settings, hyperparameters, library versions, git revision, timestep counts and active wall-clock. Numbered PPO checkpoints, TensorBoard events, `training_log.csv`, and validation history support inspection and resumption. Training time is capped by `rl_net.max_train_hours`; smoke and pilot measurements determine the staged target. No validation seed is sampled from the training pool, and no 5000+/6000+ seeds are used for tuning. Censored validation counts only tripinfo rows with non-negative arrival as completed; unfinished trips use the roadmap's `max(0, sim_end - scheduled_depart)` censor value.

When the remaining budget cannot fit 150,000 more steps, `--stage3-cost-reductions` resumes the existing policy on the three primary training scenarios (`net_medium`, `net_heavy`, `net_rush_hour`), with 1,800 s episodes, 10 s decision intervals, one PPO seed, and validation early-stop patience of two checks without improvement. Only a strict subset of the recorded training scenarios is accepted by this explicit resume mode. Deterministic validation continues with the original 3,600 s episodes and 5 s interval on the same reserved pairs, so checkpoints remain comparable to prior validation rows. Stage settings and validation-selected metadata are recorded in `config.json`.
