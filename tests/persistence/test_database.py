from __future__ import annotations

import logging
import sqlite3

import pytest

from willy.persistence import Database
from willy.persistence.database import SCHEMA_VERSION

EXPECTED_TABLES = {
    "schema_version",
    "settings",
    "willy_state",
    "novelty",
    "memories",
    "relationship",
}


def table_names(db: Database) -> set[str]:
    rows = db.connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def stored_version(db: Database) -> int:
    return int(db.connection.execute("SELECT version FROM schema_version").fetchone()["version"])


def test_fresh_file_migrates_to_v1(tmp_path):
    with Database(tmp_path / "willy.db") as db:
        assert EXPECTED_TABLES <= table_names(db)
        assert stored_version(db) == SCHEMA_VERSION


def test_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "nested" / "deeper" / "willy.db"
    with Database(path):
        assert path.exists()


def test_open_is_idempotent(tmp_path):
    db = Database(tmp_path / "willy.db")
    db.open()
    first = db.connection
    db.open()
    assert db.connection is first
    db.close()


def test_reopen_preserves_schema_without_remigrating(tmp_path):
    path = tmp_path / "willy.db"
    with Database(path):
        pass
    with Database(path) as db:
        assert stored_version(db) == SCHEMA_VERSION


def test_connection_before_open_raises(tmp_path):
    db = Database(tmp_path / "willy.db")
    with pytest.raises(RuntimeError):
        _ = db.connection


def test_corrupt_file_is_backed_up_and_recreated(tmp_path, caplog, fake_clock):
    path = tmp_path / "willy.db"
    path.write_bytes(b"this is not a sqlite database, honest")

    with caplog.at_level(logging.WARNING):
        with Database(path, clock=fake_clock) as db:
            assert EXPECTED_TABLES <= table_names(db)

    backups = list(tmp_path.glob("willy.db.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"this is not a sqlite database, honest"
    assert any("Recreating database" in record.message for record in caplog.records)


def test_two_corruptions_get_distinct_backups(tmp_path, fake_clock):
    path = tmp_path / "willy.db"
    for _ in range(2):
        path.write_bytes(b"garbage")
        with Database(path, clock=fake_clock):
            pass
        path.unlink()
    assert len(list(tmp_path.glob("willy.db.corrupt-*"))) == 2


def test_newer_schema_is_backed_up_and_recreated(tmp_path, fake_clock):
    path = tmp_path / "willy.db"
    with Database(path) as db:
        db.connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION + 1,))
        db.connection.commit()

    with Database(path, clock=fake_clock) as db:
        assert stored_version(db) == SCHEMA_VERSION
    assert len(list(tmp_path.glob("willy.db.corrupt-*"))) == 1


def test_wal_mode_and_normal_sync(tmp_path):
    with Database(tmp_path / "willy.db") as db:
        assert db.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.connection.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL


def test_missing_file_error_propagates_if_nothing_to_back_up(tmp_path, monkeypatch):
    # If connecting fails and there is no file to back up, the error must
    # surface rather than loop.
    db = Database(tmp_path / "willy.db")
    monkeypatch.setattr(
        db, "_connect_and_migrate", lambda: (_ for _ in ()).throw(sqlite3.DatabaseError("boom"))
    )
    with pytest.raises(sqlite3.DatabaseError):
        db.open()
