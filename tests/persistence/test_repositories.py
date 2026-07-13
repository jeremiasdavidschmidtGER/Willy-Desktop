from __future__ import annotations

from datetime import UTC, datetime

import pytest

from willy.contracts import Facing, ScreenPoint, WillyStateSnapshot
from willy.persistence import Database, SQLiteSettingsRepository, SQLiteWillyStateRepository

UPDATED_AT = datetime(2026, 7, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def db(tmp_path):
    with Database(tmp_path / "willy.db") as database:
        yield database


def snapshot(x: int = 10, y: int = 20, facing: Facing = Facing.RIGHT) -> WillyStateSnapshot:
    return WillyStateSnapshot(
        position=ScreenPoint(x=x, y=y),
        screen_name="\\\\.\\DISPLAY1",
        facing=facing,
        updated_at=UPDATED_AT,
    )


class TestSettingsRepository:
    def test_round_trip_all_types(self, db):
        repo = SQLiteSettingsRepository(db)
        repo.set("audio.muted", True)
        repo.set("behaviour.intensity", 2)
        repo.set("window.screen", "DISPLAY1")
        assert repo.get_bool("audio.muted", False) is True
        assert repo.get_int("behaviour.intensity", 0) == 2
        assert repo.get_str("window.screen", "") == "DISPLAY1"

    def test_missing_key_returns_default(self, db):
        repo = SQLiteSettingsRepository(db)
        assert repo.get_bool("nope", True) is True
        assert repo.get_int("nope", 7) == 7
        assert repo.get_str("nope", "fallback") == "fallback"

    def test_type_mismatch_returns_default(self, db):
        repo = SQLiteSettingsRepository(db)
        repo.set("key", "a string")
        assert repo.get_bool("key", False) is False
        assert repo.get_int("key", 3) == 3

    def test_stored_bool_does_not_leak_as_int(self, db):
        repo = SQLiteSettingsRepository(db)
        repo.set("audio.muted", True)
        assert repo.get_int("audio.muted", 9) == 9

    def test_overwrite_updates_value(self, db):
        repo = SQLiteSettingsRepository(db)
        repo.set("willy.paused", False)
        repo.set("willy.paused", True)
        assert repo.get_bool("willy.paused", False) is True

    def test_unreadable_json_returns_default(self, db):
        repo = SQLiteSettingsRepository(db)
        db.connection.execute("INSERT INTO settings (key, value) VALUES ('bad', 'not json{')")
        db.connection.commit()
        assert repo.get_str("bad", "default") == "default"

    def test_values_survive_reopen(self, tmp_path):
        path = tmp_path / "willy.db"
        with Database(path) as db:
            SQLiteSettingsRepository(db).set("willy.hidden", True)
        with Database(path) as db:
            assert SQLiteSettingsRepository(db).get_bool("willy.hidden", False) is True


class TestWillyStateRepository:
    def test_first_run_returns_none(self, db):
        assert SQLiteWillyStateRepository(db).load() is None

    def test_round_trip_both_facings(self, db):
        repo = SQLiteWillyStateRepository(db)
        for facing in (Facing.LEFT, Facing.RIGHT):
            repo.save(snapshot(facing=facing))
            assert repo.load() == snapshot(facing=facing)

    def test_save_overwrites_singleton_row(self, db):
        repo = SQLiteWillyStateRepository(db)
        repo.save(snapshot(x=1, y=2))
        repo.save(snapshot(x=300, y=400))
        assert repo.load() == snapshot(x=300, y=400)
        count = db.connection.execute("SELECT COUNT(*) FROM willy_state").fetchone()[0]
        assert count == 1

    def test_state_survives_reopen(self, tmp_path):
        path = tmp_path / "willy.db"
        with Database(path) as db:
            SQLiteWillyStateRepository(db).save(snapshot(x=42, y=7, facing=Facing.LEFT))
        with Database(path) as db:
            assert SQLiteWillyStateRepository(db).load() == snapshot(x=42, y=7, facing=Facing.LEFT)

    def test_unreadable_row_is_treated_as_first_run(self, db, caplog):
        db.connection.execute(
            """
            INSERT INTO willy_state (id, pos_x, pos_y, screen_name, facing, updated_at)
            VALUES (1, 0, 0, 'DISPLAY1', 'sideways', 'not-a-date')
            """
        )
        db.connection.commit()
        assert SQLiteWillyStateRepository(db).load() is None


def test_second_instance_read_does_not_deadlock(tmp_path):
    # Two open Database handles on the same file: instance 1 writes,
    # instance 2 (a second app launch checking state) reads. WAL mode
    # must let both proceed.
    path = tmp_path / "willy.db"
    with Database(path) as first, Database(path) as second:
        SQLiteWillyStateRepository(first).save(snapshot(x=5, y=6))
        assert SQLiteWillyStateRepository(second).load() == snapshot(x=5, y=6)
        SQLiteSettingsRepository(first).set("audio.muted", True)
        assert SQLiteSettingsRepository(second).get_bool("audio.muted", False) is True
