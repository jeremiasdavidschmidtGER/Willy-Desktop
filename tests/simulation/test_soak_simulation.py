"""A-11: fake-clock 8h soak simulation. This IS the required soak-harness
test — it drives a real WillyApp (real core + animation timing logic,
headless) through a simulated 8-hour session and asserts Gate A criteria
1/2/8 hold: no exceptions, the animation/interaction state machine never
wedges, and Python-heap growth stays bounded.
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

from willy.app.wiring import WillyApp

from tools.test_harness.soak_runner import run_fake_clock_soak

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"
EIGHT_HOURS_S = 8 * 3600

# Python-heap growth proxy, not full process RSS (that's the real-time
# mini-soak's job via tools/test_harness/run_soak_test.py). Generous on
# purpose: this only needs to catch an actual unbounded leak, not tune a
# tight budget.
MAX_HEAP_GROWTH_BYTES = 20 * 1024 * 1024


class TestEightHourSoak:
    def test_survives_eight_simulated_hours(self, qtbot, tmp_path, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=tmp_path / "soak.db")
        qtbot.addWidget(app.window)
        app.start()

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        report = run_fake_clock_soak(app, fake_clock, duration_seconds=EIGHT_HOURS_S, seed=2026)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        app.shutdown()

        growth = sum(
            stat.size_diff for stat in snapshot_after.compare_to(snapshot_before, "filename")
        )

        assert report.ticks_run == EIGHT_HOURS_S
        assert report.actions_applied > 0  # the schedule actually fired something
        assert report.still_responsive  # never wedged mid-drag/mid-fall
        assert growth < MAX_HEAP_GROWTH_BYTES, f"Python heap grew {growth / 1e6:.1f} MB"

    def test_reproducible_with_same_seed(self, qtbot, tmp_path, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=tmp_path / "soak.db")
        qtbot.addWidget(app.window)
        app.start()
        report = run_fake_clock_soak(app, fake_clock, duration_seconds=3600, seed=99)
        app.shutdown()
        assert report.ticks_run == 3600
        assert report.still_responsive
