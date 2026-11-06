# T2.1 reward design

This reward design was explicitly approved by the project owner on 2026-10-25. It is a project decision, not recovered from an earlier authoritative document. The initial weights and scales are starting values and have not been validated as optimal.

For one environment step:

    r_t = -w_q * q_norm - w_w * wait_norm + w_t * throughput_norm

- q_norm = clip((Q_t - Q_(t-1)) / S_q, -1, 1). Q_t is the current total halting-vehicle queue over configured controlled approaches. Q_(t-1) is the previous sample. Reset initializes Q_(t-1) from its first sample, so the first reward uses the queue change during the first decision interval. A queue decrease gives a positive queue contribution.
- wait_norm = clip(W_t / S_w, 0, 1). W_t is mean accumulated waiting time across all vehicles currently present in SUMO. It is zero when no vehicles are present.
- throughput_norm = clip(P_t / S_p, 0, 1). P_t is the number of vehicles passing the controlled junction during the preceding decision interval. The sensor reports vehicles per minute; the environment converts this rate using the measured interval duration.
- w_q, w_w, and w_t are configurable weights. Initial values are queue=1.0, wait=1.0, throughput=0.5.
- S_q, S_w, and S_p are configurable, finite, strictly positive scales in rl.reward_scales. Initial values are queue_change=300 vehicles, mean_wait_s=300 seconds, and throughput_vehicles=5 vehicles per decision interval. The queue value is 60 halting vehicles per each of five configured approaches; the wait value matches the existing state waiting-time normalization. The throughput value is an initial scale choice. These values are not claimed to be optimal.