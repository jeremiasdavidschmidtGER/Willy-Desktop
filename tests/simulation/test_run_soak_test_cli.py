"""Smoke test for the real-time mini-soak CLI (A-11): proves the plumbing
(real WillyApp under a real Qt event loop, synthetic-action timer, RSS
sampling, exit-code reporting) works, using a tiny duration so it stays
fast. The real 30-minute run is the nightly `mini-soak.yml` CI job, not
part of the normal `pytest` suite.
"""

from __future__ import annotations

from tools.test_harness.run_soak_test import main


def test_tiny_run_completes_and_passes(qtbot):
    exit_code = main(["--minutes", "0.02", "--seed", "1"])  # ~1.2s real wall-clock
    assert exit_code == 0
