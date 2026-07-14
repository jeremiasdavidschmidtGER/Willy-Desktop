"""Local idle CPU/RSS profiling script (A-11).

Launches a real `WillyApp`, lets it sit idle under a real Qt event loop
(render/blink/behaviour timers firing normally, no synthetic interaction),
and reports idle CPU% and RSS against the Gate A dev-machine thresholds
(idle CPU < 2%, RSS < 150 MB — ARCHITECTURE.md / MVP_SPEC criterion 9).
Not wired into CI: results are machine-dependent by nature.

Usage:
    python -m tools.test_harness.profile_idle [--seconds 20]
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tools.test_harness.memory_probe import current_rss_bytes  # noqa: E402
from willy.app.clock import SystemClock  # noqa: E402
from willy.app.wiring import WillyApp, default_assets_root  # noqa: E402

IDLE_CPU_THRESHOLD_PERCENT = 2.0
RSS_THRESHOLD_MB = 150.0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    qapp = QApplication.instance() or QApplication([])
    clock = SystemClock()
    with tempfile.TemporaryDirectory(prefix="willy-profile-") as tmp:
        app = WillyApp(
            assets_root=default_assets_root(), clock=clock, db_path=Path(tmp) / "profile.db"
        )
        qapp.aboutToQuit.connect(app.shutdown)
        app.start()

        QTimer.singleShot(int(args.seconds * 1000), qapp.quit)
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        qapp.exec()
        wall_elapsed = time.perf_counter() - wall_start
        cpu_elapsed = time.process_time() - cpu_start
        rss_bytes = current_rss_bytes()

    cpu_percent = (cpu_elapsed / wall_elapsed) * 100 if wall_elapsed > 0 else 0.0
    rss_mb = rss_bytes / (1024 * 1024)
    cpu_ok = cpu_percent < IDLE_CPU_THRESHOLD_PERCENT
    rss_ok = rss_mb < RSS_THRESHOLD_MB

    print(
        f"idle CPU: {cpu_percent:.2f}% (threshold < {IDLE_CPU_THRESHOLD_PERCENT:.1f}%) "
        f"[{'PASS' if cpu_ok else 'WARN'}]"
    )
    print(
        f"RSS:      {rss_mb:.1f} MB (threshold < {RSS_THRESHOLD_MB:.1f} MB) "
        f"[{'PASS' if rss_ok else 'WARN'}]"
    )
    return 0 if (cpu_ok and rss_ok) else 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=20.0)
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
