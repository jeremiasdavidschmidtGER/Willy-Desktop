"""SQLite database lifecycle: path, migrations, corruption recovery.

One database file holds everything (ARCHITECTURE.md §6, D-1). All access
goes through :class:`Database`; no SQL outside this package.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from willy.contracts import Clock

LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# Forward-only numbered migration scripts, applied in order by
# _migrate() whenever the stored version is behind (ARCHITECTURE.md §6).
_MIGRATIONS: dict[int, str] = {
    1: """
        CREATE TABLE schema_version (version INTEGER NOT NULL);

        CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE willy_state (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            pos_x       INTEGER NOT NULL,
            pos_y       INTEGER NOT NULL,
            screen_name TEXT    NOT NULL,
            facing      TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        );

        -- Reserved for Gate B; created empty so migrations stay linear.
        CREATE TABLE novelty (id INTEGER PRIMARY KEY);
        CREATE TABLE memories (id INTEGER PRIMARY KEY);
        CREATE TABLE relationship (id INTEGER PRIMARY KEY);
    """,
}


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


SYSTEM_CLOCK: Clock = _SystemClock()


def default_database_path(env: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if env is None else env
    appdata = environment.get("APPDATA")
    if appdata:
        return Path(appdata) / "WillyDesktop" / "willy.db"
    return Path.home() / "AppData" / "Roaming" / "WillyDesktop" / "willy.db"


class Database:
    """Owns the single SQLite connection (main thread only, per D-2).

    ``open()`` guarantees a usable, migrated database: an unreadable or
    newer-schema file is backed up beside itself and recreated with
    defaults — launch is never blocked (Gate A criterion 10).
    """

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        clock: Clock = SYSTEM_CLOCK,
        logger: logging.Logger | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self._clock = clock
        self._logger = logger or LOGGER
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Database is not open; call open() first")
        return self._connection

    def open(self) -> None:
        if self._connection is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = self._connect_and_migrate()
        except sqlite3.DatabaseError as error:
            self._backup_bad_file(error)
            self._connection = self._connect_and_migrate()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> Database:
        self.open()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _connect_and_migrate(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            self._check_integrity(connection)
            self._migrate(connection)
        except BaseException:
            connection.close()
            raise
        return connection

    def _check_integrity(self, connection: sqlite3.Connection) -> None:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        if row is None or row[0] != "ok":
            detail = row[0] if row else "no result"
            raise sqlite3.DatabaseError(f"integrity_check failed: {detail}")

    def _migrate(self, connection: sqlite3.Connection) -> None:
        version = self._stored_version(connection)
        if version > SCHEMA_VERSION:
            # A downgrade cannot be migrated; treat like corruption so the
            # app still launches. The old file survives as a backup.
            raise sqlite3.DatabaseError(
                f"schema version {version} is newer than supported {SCHEMA_VERSION}"
            )
        for target in range(version + 1, SCHEMA_VERSION + 1):
            connection.executescript(_MIGRATIONS[target])
            connection.execute("DELETE FROM schema_version")
            connection.execute("INSERT INTO schema_version (version) VALUES (?)", (target,))
            connection.commit()
            self._logger.info("Applied schema migration to v%d", target)

    def _stored_version(self, connection: sqlite3.Connection) -> int:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
        ).fetchone()
        if table is None:
            return 0
        row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        return 0 if row is None else int(row["version"])

    def _backup_bad_file(self, error: sqlite3.DatabaseError) -> None:
        if not self.path.exists():
            raise error
        stamp = self._clock.now().strftime("%Y%m%d%H%M%S")
        backup = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
        counter = 1
        while backup.exists():
            backup = self.path.with_name(f"{self.path.name}.corrupt-{stamp}-{counter}")
            counter += 1
        self.path.replace(backup)
        # WAL side files belong to the bad database; move them out of the way
        # so they cannot be replayed into the fresh file.
        for suffix in ("-wal", "-shm"):
            side = self.path.with_name(self.path.name + suffix)
            if side.exists():
                side.replace(backup.with_name(backup.name + suffix))
        self._logger.warning("Recreating database; bad file backed up to %s (%s)", backup, error)
