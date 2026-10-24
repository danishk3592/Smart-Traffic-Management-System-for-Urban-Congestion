# Rule controller validation tuning (T1.3)

Unchanged `medium` demand; validation seeds 3000-3002. Three candidate threshold pairs are crossed with all three seeds; progress below counts completed cells.
Selection uses the lowest mean approach queue over all nine runs; waiting time and teleports are shown as context.

| Queue threshold | Wait threshold (s) | Seed | Avg queue | Avg wait (s) | Completed / trips | Teleports | Fallback activations | Wall time (s) | Run |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 6 | 30 | 3000 | 12.221 | 197.691 | 1544 / 2600 | 1145 | 0 | 1459.7 | `20261024-202355_rule_medium_s3000` |
| 6 | 30 | 3001 | 10.964 | 163.735 | 1495 / 2600 | 1099 | 0 | 846.8 | `20261024-212011_rule_medium_s3001` |
| 6 | 30 | 3002 | 10.582 | 196.329 | 1540 / 2600 | 1041 | 0 | 929.1 | `20261024-213436_rule_medium_s3002` |
| 8 | 45 | 3000 | 12.203 | 220.470 | 1576 / 2600 | 1096 | 0 | 1216.9 | `20261024-215010_rule_medium_s3000` |
| 8 | 45 | 3001 | 11.482 | 182.541 | 1527 / 2600 | 1070 | 0 | 1004.5 | `20261024-221033_rule_medium_s3001` |
| 8 | 45 | 3002 | 10.266 | 230.668 | 1507 / 2600 | 1050 | 0 | 966.3 | `20261024-222724_rule_medium_s3002` |
| 10 | 60 | 3000 | 12.211 | 210.877 | 1568 / 2600 | 1094 | 0 | 1431.9 | `20261024-231306_rule_medium_s3000` |
| 10 | 60 | 3001 | 11.270 | 198.708 | 1557 / 2600 | 1059 | 0 | 3162.5 | `20261024-233704_rule_medium_s3001` |
| 10 | 60 | 3002 | 10.743 | 170.291 | 1543 / 2600 | 1073 | 0 | 894.3 | `20261025-002952_rule_medium_s3002` |

Completed trials: 9/9.

Selected thresholds: queue `6`, wait `30s`; mean queue/wait = `11.256` / `185.918`.
