

## 2026-10-20 ? T0.3 SUMO client and TLS inspection

- Seed 1000, initial client smoke: exited at simulation time 0 because the inspection script referenced a not-yet-exposed validated-network property. No traffic was simulated; added the public property.
- Seed 1000, client smoke: stopped at time 70 s because TraCI had already removed an arrived vehicle subscription. Removed the redundant unsubscribe request; client lifecycle tests then passed.
- Seed 1000, 1800 s native-program run: 298 unique crossing vehicles at the configured TLS; rank 6/13, median 243. Initial foe check reported 21 overlaps. Inspection of SUMO request response bits showed 0 protected G/G conflicts and all 21 overlaps have a yielding response from the native program. Kept the existing static program.
- Seed 1000, 1800 s inspection: simulation completed but report generation failed when the warning-time parser included a trailing period. Tightened the time parser and reran.
- Seed 1000, final 1800 s run: rank 6/13, 298 unique crossings; 4 approaches; 3 green phases; 0 protected G/G foe conflicts; 21 permissive overlaps with network yield responses; 1 unique teleport ID in the first 600 s and 38 through 1800 s; 2 warning lines through 600 s and 71 through 1800 s.
- All run outputs and edgeData were directed to temporary storage; no protected source map path was modified.
- Acceptance: inspect_tls.py exited 0; Ruff passed; default pytest 6 passed/3 deselected; SUMO client tests 3 passed; junction tests 4 passed; zombie check found no SUMO processes.
