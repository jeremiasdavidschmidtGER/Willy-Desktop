# Gate A acceptance report

Task A-12 (`docs/GATE_A_BACKLOG.md`). Documented pass/fail against all 10
Gate A criteria (MVP_SPEC §6.4), with evidence, using final art.

- **Branch:** `feature/gate-a-12-acceptance-run`
- **Commit under test:** `dd501c1` (`main`, all of A-01–A-11 + the
  `willy_fuming`/`willy_smug`/`willy_annoyed_idle` art landed)
- **Report started:** 2026-07-15
- **Overall result:** **All 10 criteria PASS with evidence.** Awaiting
  only the human's sign-off (and, optionally, a fresh quick manual
  recheck — see "What ran" below) to close out A-12. No deviations
  found.

## What ran (this pass)

- [x] `python -m pytest` — 279 passed, 0 failed
- [x] `python -m ruff check .` — all checks passed
- [x] `python -m ruff format --check .` — 84 files already formatted
- [x] `python -m tools.test_harness.profile_idle --seconds 20` — 1.64%
      idle CPU, 48.5 MB RSS, both PASS
- [x] `python -m tools.test_harness.run_soak_test --minutes 5` —
      supplementary real-Qt-loop check: PASS, 10.5 MB RSS growth, 0
      errors (not a substitute for the 4h run; see criterion 1)
- [x] `python -m tools.test_harness.run_soak_test --minutes 240` — the
      real 4-hour run (criterion 1). Started 2026-07-15 17:56, finished
      ~21:57 (PID 25548, ran detached): **PASS**, 481 RSS samples,
      **-8.5 MB RSS growth** (memory went *down* over the run, nowhere
      near the 20 MB threshold), **0 errors**.
- [ ] Fresh manual pass at this commit (focus theft, monitor
      recovery, tray look-and-feel) — recommended even though most of
      these were already live-tested in earlier sessions (see per-
      criterion notes); optional, not blocking sign-off.

## Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Runs ≥4h without crashing | **PASS** | Real 4-hour run, 2026-07-15 17:56–21:57: 481 RSS samples, -8.5 MB growth, 0 errors. Supplementary: fake-clock 8h sim and 5-min real-Qt mini-soak both also clean (see per-criterion notes). |
| 2 | Animations remain responsive | PASS | `tests/animation/` (timing, controller, render wiring — 51 tests); fake-clock 8h sim asserts the animation state machine is never wedged; live-tested throughout A-06–A-10. |
| 3 | No keyboard focus theft | PASS | `tests/platform/test_window.py` asserts required window flags/attributes (`Qt.WindowDoesNotAcceptFocus` etc.); live-tested and confirmed by the human (recorded in asset factory `HANDOFF.md`, A-03/A-04 sessions). |
| 4 | Position survives restart | PASS | `tests/platform/test_drag_and_persistence.py` (11 tests, incl. `test_position_and_facing_survive_restart`); `tests/platform/test_screens.py` (clamp-on-invalid-screen); live-tested. |
| 5 | Recoverable after monitor changes | PASS | `tests/platform/test_screens.py` (17 tests: `resolve_restore_position`, `ScreenLayoutMonitor`); live-tested dragging to/recovering from a second monitor (PR #12 / A-10, confirmed by the human per asset factory `HANDOFF.md`). |
| 6 | Tray controls work reliably | PASS | `tests/platform/test_tray_controls.py` (16 tests); live-tested — found in the Windows hidden-icons overflow by default (expected OS behaviour), menu toggles confirmed working (PR #11 / A-09, per asset factory `HANDOFF.md`). |
| 7 | Mute and hide act immediately | PASS | `test_tray_controls.py::TestTraySettingsPersistenceWiring::test_hide_toggle_hides_window_immediately`; live-tested immediate effect, confirmed by the human. |
| 8 | Dragging/dropping doesn't break animation state | PASS | `tests/core/test_drag_state_machine.py`, `tests/platform/test_drag_and_persistence.py`, `tests/platform/test_floor_gravity.py`, `tests/platform/test_startle_reaction.py` (26 tests total); fake-clock 8h sim exercises random drag/drop cycles and asserts no wedge; live-tested (drag feel, facing flip, fall+startle sequence). |
| 9 | CPU/memory usage acceptable | PASS (dev machine) | `profile_idle.py`: 1.64% idle CPU (< 2%), 48.5 MB idle RSS (< 150 MB). Real 4h run: -8.5 MB RSS growth (i.e. no growth at all) over 481 samples — the strongest evidence for this criterion. |
| 10 | No optional subsystem required to launch | PASS | Gate A ships no LLM/network subsystem at all (by design — `CLAUDE.md`: "Willy must fully function with no LLM present"); `tests/simulation/test_forbidden_api_check.py` (repo-wide static scan, 9 tests) confirms no forbidden network/input APIs; `test_tray_controls.py::test_no_db_path_tray_still_works_without_crashing` and `test_sprite_only_mode_pause_is_a_safe_no_op` confirm the app degrades gracefully with persistence/animation absent. |

## Per-criterion notes

**Criterion 1 (4h real run) — closed.** MVP_SPEC §6.4 requires Willy to
run ≥4 hours without crashing. Two pieces of automated evidence existed
beforehand but neither was a substitute, per `docs/testing/TESTING.md`'s
own reasoning: the fake-clock 8h simulation proves the *core logic*
survives a long simulated session without driving a real Qt event loop,
and the 5-minute real-time mini-soak only proves the real event loop
survives briefly. The dedicated real 4-hour run closes the gap:

```powershell
python -m tools.test_harness.run_soak_test --minutes 240
```

Launched detached (PID 25548) 2026-07-15 17:56, finished ~21:57.
**4-hour run result:**

```
soak run: 481 RSS samples, growth -8.5 MB, 0 error(s)
PASS
```

Threshold was < 20 MB RSS growth; actual growth was *negative* (memory
usage went down over the 4 hours, likely GC/allocator settling), with
zero unhandled exceptions across 481 samples. No deviation to record.

**Criterion 9, real-world number.** The `profile_idle` figures above are
a clean-idle snapshot; the 4-hour run's -8.5 MB RSS growth over 481
samples is the more meaningful real-world figure for sustained usage,
and it's a clean pass with margin to spare.

**On citing prior live-tests (criteria 3, 5, 6, 7).** These were
confirmed by the human at the screen during the A-03/A-08/A-09/A-10
sessions, recorded in the asset factory's `HANDOFF.md` rather than back
into the willy-desktop PR bodies (PR #11/#12 shipped with these manual
checkboxes still unchecked, then confirmed afterward). The underlying
behaviour hasn't changed since; the only changes since then are art
pixel refreshes (`willy_fuming`, `willy_smug` re-quantization,
`willy_annoyed_idle` added — none wired to behaviour). A fresh quick
re-check at this exact commit is cheap and recommended (can run in
parallel with the 4h background soak) but is not expected to surface
anything new — flagged as a "nice to have" checkbox above, not blocking.

## 5-minute mini-soak result (this pass, supplementary)

```
soak run: 11 RSS samples, growth 10.5 MB, 0 error(s)
PASS
```

(Threshold: < 20 MB growth. Supplementary evidence only — not a
substitute for criterion 1's 4-hour run, see below.)

## Deviations / failures

None found.

## Follow-up

- Optional: a fresh quick manual pass at this commit (focus theft,
  monitor recovery, tray look-and-feel) — not expected to surface
  anything new (see the note above on why), but cheap if you want the
  belt-and-suspenders check.
- Once you're satisfied, check the two boxes below and tag `main` as
  `gate-a` to close out A-12.

## Sign-off

- [x] All 10 criteria green with evidence
- [x] Human sign-off: Jeremias Schmidt, 2026-07-20
- [x] `main` tagged `gate-a`
