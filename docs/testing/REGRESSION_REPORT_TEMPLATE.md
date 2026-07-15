# Regression report template

Copy this into a new file (e.g. `docs/testing/reports/2026-07-15-soak.md`)
whenever a soak run, mini-soak, or manual Gate A check surfaces a problem —
or to record a clean run before a release/acceptance milestone.

---

## Summary

- **Date:**
- **Trigger:** (manual mini-soak run / manual profiling / A-12 acceptance run / bug report)
- **Branch + commit:**
- **Result:** PASS / FAIL

## What ran

- [ ] `python -m pytest` (unit + fake-clock 8h simulation + forbidden-API scan)
- [ ] `python -m tools.test_harness.run_soak_test --minutes <N>`
- [ ] `python -m tools.test_harness.profile_idle --seconds <N>`
- [ ] Manual checklist (focus theft, monitor unplug, tray look-and-feel — list which)

## Metrics observed

| Metric | Threshold | Observed | Pass? |
|---|---|---|---|
| Real-time RSS growth | < 20 MB | | |
| Idle CPU | < 2% | | |
| Idle RSS | < 150 MB | | |
| Exceptions raised | 0 | | |
| Animation state machine wedged? | no | | |

## Deviations / failures

(One entry per issue. Include: what broke, reproduction steps or seed,
suspected cause, whether it's a new bounded fix task or a known limitation.)

## Follow-up

(Links to new fix-task branches/issues opened as a result of this report.)
