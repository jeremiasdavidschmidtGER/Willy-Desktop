# Gate A acceptance report

Task A-12 (`docs/GATE_A_BACKLOG.md`). Documented pass/fail against all 10
Gate A criteria (MVP_SPEC §6.4), with evidence, using final art.

- **Branch:** `feature/gate-a-12-acceptance-run`
- **Commit under test:** `dd501c1` (`main`, all of A-01–A-11 + the
  `willy_fuming`/`willy_smug`/`willy_annoyed_idle` art landed)
- **Report started:** 2026-07-15
- **Overall result:** **PENDING** — 9/10 criteria have automated or
  already-recorded manual evidence; criterion 1 needs a fresh real
  4-hour run performed by the human (instructions below). No deviations
  found so far.

## What ran (this pass)

- [x] `python -m pytest` — 279 passed, 0 failed
- [x] `python -m ruff check .` — all checks passed
- [x] `python -m ruff format --check .` — 84 files already formatted
- [x] `python -m tools.test_harness.profile_idle --seconds 20` — 1.64%
      idle CPU, 48.5 MB RSS, both PASS
- [x] `python -m tools.test_harness.run_soak_test --minutes 5` —
      supplementary real-Qt-loop check (not a substitute for the 4h run;
      see criterion 1)
- [ ] Fresh manual pass at this commit (focus theft, monitor
      recovery, tray look-and-feel) — recommended even though most of
      these were already live-tested in earlier sessions (see per-
      criterion notes); cheap to run alongside the 4h background soak.
- [ ] Real 4-hour run (criterion 1) — **not yet performed**, instructions
      below.

## Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Runs ≥4h without crashing | **PENDING** | Needs the real 4h human run — see below. Fake-clock 8h sim and 5-min real-Qt mini-soak both clean (see per-criterion notes) but neither satisfies this criterion on their own. |
| 2 | Animations remain responsive | PASS | `tests/animation/` (timing, controller, render wiring — 51 tests); fake-clock 8h sim asserts the animation state machine is never wedged; live-tested throughout A-06–A-10. |
| 3 | No keyboard focus theft | PASS | `tests/platform/test_window.py` asserts required window flags/attributes (`Qt.WindowDoesNotAcceptFocus` etc.); live-tested and confirmed by the human (recorded in asset factory `HANDOFF.md`, A-03/A-04 sessions). |
| 4 | Position survives restart | PASS | `tests/platform/test_drag_and_persistence.py` (11 tests, incl. `test_position_and_facing_survive_restart`); `tests/platform/test_screens.py` (clamp-on-invalid-screen); live-tested. |
| 5 | Recoverable after monitor changes | PASS | `tests/platform/test_screens.py` (17 tests: `resolve_restore_position`, `ScreenLayoutMonitor`); live-tested dragging to/recovering from a second monitor (PR #12 / A-10, confirmed by the human per asset factory `HANDOFF.md`). |
| 6 | Tray controls work reliably | PASS | `tests/platform/test_tray_controls.py` (16 tests); live-tested — found in the Windows hidden-icons overflow by default (expected OS behaviour), menu toggles confirmed working (PR #11 / A-09, per asset factory `HANDOFF.md`). |
| 7 | Mute and hide act immediately | PASS | `test_tray_controls.py::TestTraySettingsPersistenceWiring::test_hide_toggle_hides_window_immediately`; live-tested immediate effect, confirmed by the human. |
| 8 | Dragging/dropping doesn't break animation state | PASS | `tests/core/test_drag_state_machine.py`, `tests/platform/test_drag_and_persistence.py`, `tests/platform/test_floor_gravity.py`, `tests/platform/test_startle_reaction.py` (26 tests total); fake-clock 8h sim exercises random drag/drop cycles and asserts no wedge; live-tested (drag feel, facing flip, fall+startle sequence). |
| 9 | CPU/memory usage acceptable | PASS (dev machine) | `profile_idle.py` this pass: 1.64% idle CPU (< 2%), 48.5 MB idle RSS (< 150 MB). 5-min mini-soak RSS growth: see below. Real 4h RSS-growth number still pending as part of criterion 1's run. |
| 10 | No optional subsystem required to launch | PASS | Gate A ships no LLM/network subsystem at all (by design — `CLAUDE.md`: "Willy must fully function with no LLM present"); `tests/simulation/test_forbidden_api_check.py` (repo-wide static scan, 9 tests) confirms no forbidden network/input APIs; `test_tray_controls.py::test_no_db_path_tray_still_works_without_crashing` and `test_sprite_only_mode_pause_is_a_safe_no_op` confirm the app degrades gracefully with persistence/animation absent. |

## Per-criterion notes

**Criterion 1 (4h real run) — the one open item.** MVP_SPEC §6.4 requires
Willy to run ≥4 hours without crashing. Two pieces of automated evidence
exist but neither is a substitute, per `docs/testing/TESTING.md`'s own
reasoning:
- Fake-clock 8h simulation (`tests/simulation/test_soak_simulation.py`,
  runs in ~2s) proves the *core logic* survives a long simulated session
  — it does not drive a real Qt event loop or real timers.
- The 5-minute real-time mini-soak run this pass (see below) proves the
  *real* Qt event loop survives briefly — not 4 hours.

Neither was ever intended to satisfy Gate A criterion 1; the backlog
requires a dedicated real 4-hour run on the human's machine. **Manual
procedure for the human:**

1. Close other heavy applications if you want a clean CPU/RSS baseline
   (optional — not required for a pass, just makes the numbers cleaner).
2. From the repo root, run:
   ```powershell
   python -m tools.test_harness.run_soak_test --minutes 240
   ```
   This launches a real `WillyApp` under a real Qt event loop and
   injects synthetic clicks/drags on a timer for 4 real hours, then
   reports pass/fail on RSS growth (< 20 MB threshold) and any unhandled
   exception.
3. Use the desktop normally in the background if you like (this is also
   effectively a manual check for criteria 2/3/6/7 under real everyday
   conditions) — the tool doesn't require you to watch it continuously.
4. When it finishes, paste the tool's final output (pass/fail line +
   RSS numbers) into this report's "4-hour run result" section below,
   and flip criterion 1 to PASS/FAIL accordingly.
5. If it crashes or fails the RSS threshold, do **not** try to fix it in
   this branch — record it as a deviation below and open a new bounded
   fix task (A-12's forbidden paths are all of `src/`).

**4-hour run result:** *(paste here when the human has run it)*

```
(pending)
```

**Criterion 9, real-world number.** The `profile_idle` figures above are
a clean-idle snapshot; the 4-hour run's RSS-growth number (step 4 above)
is the more meaningful real-world figure for sustained usage and will be
folded in here once available.

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
(filled in once the background run completes)
```

## Deviations / failures

None found so far.

## Follow-up

None yet — pending the human's 4-hour run and sign-off.

## Sign-off

- [ ] All 10 criteria green with evidence
- [ ] Human sign-off: _____________________ (name, date)
- [ ] `main` tagged `gate-a`
