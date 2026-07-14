"""Real-time mini-soak (A-11): runs a real `WillyApp` under a real Qt event
loop for N minutes of actual wall-clock time, injecting synthetic clicks and
drags on a timer, and asserts no unhandled exception and bounded RSS growth.

This is the complement to `tools/test_harness/soak_runner.py`'s fake-clock
8h simulation: that one proves the *core logic* survives a long simulated
session; this one proves the *real Qt timers and event loop* do too, since
nothing here artificially advances time.

Usage:
    python -m tools.test_harness.run_soak_test [--minutes 30] [--rss-growth-threshold-mb 20]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tools.test_harness.memory_probe import current_rss_bytes  # noqa: E402
from willy.app.clock import SystemClock  # noqa: E402
from willy.app.wiring import WillyApp, default_assets_root  # noqa: E402
from willy.contracts import DragEnded, DragStarted, MouseButton, ScreenPoint, WillyClicked  # noqa: E402

ACTION_INTERVAL_MS = 7_000
RSS_SAMPLE_INTERVAL_MS = 30_000


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    errors: list[BaseException] = []
    rss_samples: list[int] = []

    qapp = QApplication.instance() or QApplication([])
    clock = SystemClock()
    with tempfile.TemporaryDirectory(prefix="willy-soak-") as tmp:
        app = WillyApp(
            assets_root=default_assets_root(),
            clock=clock,
            db_path=Path(tmp) / "soak.db",
        )
        qapp.aboutToQuit.connect(app.shutdown)
        app.start()

        rng = random.Random(args.seed)

        def inject_action() -> None:
            try:
                if rng.random() < 0.5:
                    app.bus.publish(
                        WillyClicked(
                            timestamp=clock.now(), button=MouseButton.LEFT, clicks_in_last_10s=1
                        )
                    )
                else:
                    start = ScreenPoint(x=app.window.x(), y=app.window.y())
                    end = ScreenPoint(x=start.x + 30, y=start.y)
                    app.bus.publish(DragStarted(timestamp=clock.now(), grab_point=start))
                    app.window.move(end.x, end.y)
                    app.bus.publish(DragEnded(timestamp=clock.now(), drop_point=end))
            except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
                errors.append(exc)

        def sample_rss() -> None:
            try:
                rss_samples.append(current_rss_bytes())
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        action_timer = QTimer()
        action_timer.timeout.connect(inject_action)
        action_timer.start(ACTION_INTERVAL_MS)

        rss_timer = QTimer()
        rss_timer.timeout.connect(sample_rss)
        rss_timer.start(RSS_SAMPLE_INTERVAL_MS)

        sample_rss()  # baseline before the run starts accumulating
        QTimer.singleShot(int(args.minutes * 60_000), qapp.quit)

        qapp.exec()
        action_timer.stop()
        rss_timer.stop()
        sample_rss()  # final reading

    return _report(errors, rss_samples, args.rss_growth_threshold_mb)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=float, default=30.0)
    parser.add_argument("--rss-growth-threshold-mb", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=1)
    return parser.parse_args(argv)


def _report(errors: list[BaseException], rss_samples: list[int], threshold_mb: float) -> int:
    growth_mb = (rss_samples[-1] - rss_samples[0]) / (1024 * 1024) if len(rss_samples) >= 2 else 0.0
    print(
        f"soak run: {len(rss_samples)} RSS samples, growth {growth_mb:.1f} MB, "
        f"{len(errors)} error(s)"
    )
    for exc in errors:
        print(f"  error: {exc!r}")
    if errors:
        return 1
    if growth_mb > threshold_mb:
        print(f"  FAIL: RSS growth {growth_mb:.1f} MB exceeds threshold {threshold_mb:.1f} MB")
        return 1
    print("  PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
