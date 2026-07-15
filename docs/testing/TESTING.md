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
| Real-time mini-soak | `tools/test_harness/run_soak_test.py` | Manual only — not wired into CI at all (see below) |
| Local idle profiling | `tools/test_harness/profile_idle.py` | Manual, dev machine only |
| Manual checklist (focus, monitor unplug, tray look-and-feel) | `docs/testing/` completion reports | Gate A acceptance run (A-12) |

## Why the mini-soak isn't in CI

The backlog's literal wording is "CI runs simulation + mini-soak on every PR
to main." In practice the mini-soak isn't automated at all — no scheduled
workflow, no per-PR job. Reasoning:

- Its unique value is catching *real Qt-level* bugs the fake-clock
  simulation can't see — a `QTimer` that silently stops firing, a stray
  closure keeping a widget alive, PySide wrapper objects piling up from
  undisconnected signals. The fake-clock simulation drives the same
  core/animation logic directly in a Python loop (no real event loop, no
  real timers) and only tracks Python-heap growth via `tracemalloc`, which
  is blind to all of that.
- It is *not* what proves Gate A's 4-hour stability criterion (MVP_SPEC
  §6.4, criterion 1) — that's a dedicated real 4-hour human-run in A-12.
  The mini-soak was never load-bearing for Gate A acceptance.
- A recurring CI job (nightly or per-PR) has a real, ongoing cost:
  `windows-latest` GitHub Actions runners bill Windows jobs at a 2x minute
  multiplier, so even a nightly 30-minute run is 60 billed minutes/day,
  indefinitely, on a private repo — for a check whose main value is
  "catch Qt-level regressions before they compound," which matters more
  once Gate B/C add real timer/dialogue/den complexity than during Gate A's
  comparatively small surface area.

The tool stays available and useful on demand — run it yourself before a
release, before A-12, or whenever a Qt-level leak is suspected. Automating
it can be revisited later (a nightly schedule is a two-line change to
re-add a workflow file) if it earns its keep.

The fast fake-clock 8h simulation and the forbidden-API scan — both of
which run in seconds — still gate every PR, so regressions in core logic
are still caught immediately regardless of this decision.

## Tools

```powershell
# Fake-clock 8h simulation — this is just `pytest`, already covered above.
python -m pytest tests/simulation/test_soak_simulation.py -v

# Real-time mini-soak (manual only — see "Why the mini-soak isn't in CI").
# 30 min default; override for a quick local check.
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
| Real-time mini-soak: RSS growth over 30 min | < 20 MB | `run_soak_test.py --rss-growth-threshold-mb` (manual) |
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
