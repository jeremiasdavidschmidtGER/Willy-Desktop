"""SQLite persistence: database lifecycle, repositories, debounced writes.

No SQL outside this package (ARCHITECTURE.md §6). No Qt imports.
"""

from willy.persistence.database import SYSTEM_CLOCK, Database, default_database_path
from willy.persistence.debounce import DebouncedWriter
from willy.persistence.repositories import SQLiteSettingsRepository, SQLiteWillyStateRepository

__all__ = [
    "SYSTEM_CLOCK",
    "Database",
    "default_database_path",
    "DebouncedWriter",
    "SQLiteSettingsRepository",
    "SQLiteWillyStateRepository",
]
