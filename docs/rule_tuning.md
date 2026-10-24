# Rule controller validation tuning (T1.3)

Unchanged `medium` demand; validation seeds 3000-3002. Three queue/wait threshold pairs were planned.
Selection uses the lowest mean approach queue over all nine runs; waiting time and teleports are shown as context.

| Queue threshold | Wait threshold (s) | Seed | Avg queue | Avg wait (s) | Completed / trips | Teleports | Fallback activations | Wall time (s) | Run |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 6 | 30 | 3000 | 12.221 | 197.691 | 1544 / 2600 | 1145 | 0 | 1459.7 | `20261024-202355_rule_medium_s3000` |

Completed trials: 1/9. No threshold was selected.

The user stopped the batch on 2026-10-24. The active q6/w30/seed-3001 trial is preserved at `results/raw/20261024-204907_rule_medium_s3001/`; its step log ends at simulation time 1,655 s of 7,200 s and it has no trip log or `run.json`. A prior startup attempt is preserved at `results/raw/20261024-204834_rule_medium_s3001/` with a zero-byte step log. The remaining eight complete validation runs were not resumed. Do not treat the partial trial as a completed measurement or change the configured 8/45 thresholds based on 1/9 results.
