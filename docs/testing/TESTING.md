# Testing architecture

Referenced from `ARCHITECTURE.md` §9. This is the detail behind that
summary, focused on the soak/performance harness added in A-11.

## Layers

| Layer | Location | Runs |
|---|---|---|
| Unit (`contracts`, `core`) | `tests/core/`, etc. | Every PR, `pytest` |
| Animation (golden-image, manifest, transitions) | `tests/animation/` | Every PR |
| Platform smoke (`pytest-qt`, offscreen) | `tests/platform/` | Every PR |
| Fake-clock soak simulation | `tests/simulation/test_soak_simulation.py` | Every PR (fast: ~2s for a simulated 8h session) |
| Forbidden-API static scan | `tests/simulation/test_forbidden_api_check.py` | Every PR (it's a normal pytest test) |
| Real-time mini-soak (30 min wall-clock) | `.github/workflows/mini-soak.yml` | Nightly (scheduled) + manual dispatch — **not** on every PR (see below) |
| Local idle profiling | `tools/test_harness/profile_idle.py` | Manual, dev machine only |
| Manual checklist (focus, monitor unplug, tray look-and-feel) | `docs/testing/` completion reports | Gate A acceptance run (A-12) |

## Why the mini-soak isn't on every PR

The backlog's literal wording is "CI runs simulation + mini-soak on every PR
to main." The 30-minute real-time mini-soak was moved to a nightly schedule
(+ manual dispatch) instead: on `windows-latest` GitHub Actions runners,
Windows jobs are billed at a 2x minute multiplier, so a 30-minute job costs
60 billed minutes *per PR*, indefinitely, on a private repo with a limited
monthly minutes budget. The fast fake-clock 8h simulation and the
forbidden-API scan — both of which run in seconds — still gate every PR, so
regressions in core logic are still caught immediately; the mini-soak adds
a slower, real-Qt-event-loop check on a schedule instead of a per-PR one.

## Tools

```powershell
# Fake-clock 8h simulation — this is just `pytest`, already covered above.
python -m pytest tests/simulation/test_soak_simulation.py -v

# Real-time mini-soak (30 min default; override for a quick local check).
python -m tools.test_harness.run_soak_test --minutes 30
python -m tools.test_harness.run_soak_test --minutes 1   # quick local sanity check

# Local idle CPU/RSS profile (thresholds: idle CPU < 2%, RSS < 150 MB —
# MVP_SPEC §6.4 criterion 9). Machine-dependent; not wired into CI.
python -m tools.test_harness.profile_idle --seconds 20
```

## Thresholds

| Metric | Threshold | Where enforced |
|---|---|---|
| Fake-clock 8h simulation: exceptions | zero | `test_soak_simulation.py` (any exception fails the test) |
| Fake-clock 8h simulation: state machine | never wedged mid-drag/mid-fall | `SoakReport.still_responsive` |
| Fake-clock 8h simulation: Python-heap growth | < 20 MB (`tracemalloc`, a proxy, not full RSS) | `test_soak_simulation.py` |
| Real-time mini-soak: RSS growth over 30 min | < 20 MB | `run_soak_test.py --rss-growth-threshold-mb` |
| Idle CPU (dev machine) | < 2% | `profile_idle.py` |
| Idle RSS | < 150 MB | `profile_idle.py` |

## Forbidden-API scan

`tools/test_harness/forbidden_api_check.py` greps `src/willy/` for
`pyautogui`/`keyboard` imports, raw `SendInput` calls, and file writes
outside the two vetted call sites (`persistence/`, and
`platform/single_instance.py`'s lock file). It's a normal pytest test
(`tests/simulation/test_forbidden_api_check.py`), so it runs on every PR
without any separate CI wiring.

## What A-11 does not cover

Per ARCHITECTURE.md §9: real monitor unplug, real focus-stealing checks,
and tray look-and-feel are manual — a human at the screen, recorded in
completion reports. This tier's job is CPU/memory/stability evidence for
Gate A criteria 1, 2, 8, 9, not a substitute for the manual checklist.
