"""Crash-safety: a process killed between debounced writes must leave a
readable database containing every committed write (A-02 acceptance)."""

from __future__ import annotations

import subprocess
import sys
import textwrap

from willy.contracts import Facing
from willy.persistence import Database, SQLiteWillyStateRepository

CHILD = textwrap.dedent(
    """
    import os, sys
    from datetime import UTC, datetime
    from willy.contracts import Facing, ScreenPoint, WillyStateSnapshot
    from willy.persistence import Database, SQLiteWillyStateRepository

    db = Database(sys.argv[1])
    db.open()
    repo = SQLiteWillyStateRepository(db)
    for step in range(3):
        repo.save(
            WillyStateSnapshot(
                position=ScreenPoint(x=step, y=step),
                screen_name="DISPLAY1",
                facing=Facing.LEFT,
                updated_at=datetime(2026, 7, 13, tzinfo=UTC),
            )
        )
    os._exit(1)  # die without close/commit/atexit — simulates kill -9
    """
)


def test_killed_process_leaves_valid_database_with_last_commit(tmp_path):
    path = tmp_path / "willy.db"
    result = subprocess.run(
        [sys.executable, "-c", CHILD, str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1, result.stderr

    with Database(path) as db:
        assert db.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        loaded = SQLiteWillyStateRepository(db).load()
    assert loaded is not None
    assert loaded.position.x == 2  # last committed write survived
    assert loaded.facing is Facing.LEFT
    assert not list(tmp_path.glob("*.corrupt-*"))  # no recovery was needed
