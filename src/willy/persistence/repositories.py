"""SQLite implementations of the persistence repository protocols."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from willy.contracts import Facing, ScreenPoint, WillyStateSnapshot

from willy.persistence.database import Database

LOGGER = logging.getLogger(__name__)


class SQLiteSettingsRepository:
    """Typed key/value settings; values stored as JSON-encoded scalars.

    A missing key, a type mismatch, or an unreadable value yields the
    caller's default — settings can never block launch.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def get_bool(self, key: str, default: bool) -> bool:
        value = self._get(key)
        return value if isinstance(value, bool) else default

    def get_int(self, key: str, default: int) -> int:
        # bool is a subclass of int; a stored bool must not leak out as int.
        value = self._get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def get_str(self, key: str, default: str) -> str:
        value = self._get(key)
        return value if isinstance(value, str) else default

    def set(self, key: str, value: bool | int | str) -> None:
        connection = self._database.connection
        connection.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, json.dumps(value)),
        )
        connection.commit()

    def _get(self, key: str) -> Any:
        row = self._database.connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            LOGGER.warning("Unreadable settings value for %r; using default", key)
            return None


class SQLiteWillyStateRepository:
    """Singleton willy_state row (id = 1); None on first run.

    An unparseable row is logged and treated as first run rather than
    raised — a damaged value must not block launch.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def load(self) -> WillyStateSnapshot | None:
        row = self._database.connection.execute(
            "SELECT pos_x, pos_y, screen_name, facing, updated_at FROM willy_state WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        try:
            return WillyStateSnapshot(
                position=ScreenPoint(x=int(row["pos_x"]), y=int(row["pos_y"])),
                screen_name=str(row["screen_name"]),
                facing=Facing[str(row["facing"]).upper()],
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )
        except (KeyError, ValueError) as error:
            LOGGER.warning("Unreadable willy_state row (%s); treating as first run", error)
            return None

    def save(self, snapshot: WillyStateSnapshot) -> None:
        connection = self._database.connection
        connection.execute(
            """
            INSERT INTO willy_state (id, pos_x, pos_y, screen_name, facing, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                pos_x = excluded.pos_x,
                pos_y = excluded.pos_y,
                screen_name = excluded.screen_name,
                facing = excluded.facing,
                updated_at = excluded.updated_at
            """,
            (
                snapshot.position.x,
                snapshot.position.y,
                snapshot.screen_name,
                snapshot.facing.name.lower(),
                snapshot.updated_at.isoformat(),
            ),
        )
        connection.commit()
