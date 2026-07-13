"""Single-instance guard via lock file (OPEN_DECISIONS D-11).

A second launch fails to take the lock, reports, and exits — two Willys
must never fight over the database.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from willy.platform import win32


def default_lock_path(env: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if env is None else env
    appdata = environment.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "WillyDesktop" / "willy.lock"


class SingleInstanceGuard:
    def __init__(self, lock_path: Path | str | None = None) -> None:
        self._path = Path(lock_path) if lock_path is not None else default_lock_path()
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def acquire(self) -> bool:
        """True if this process now holds the lock; False if another does."""
        if self._fd is not None:
            return True
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_RDWR)
        if not win32.try_lock_file(fd):
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        win32.unlock_file(self._fd)
        os.close(self._fd)
        self._fd = None
        try:
            self._path.unlink()
        except OSError:
            pass  # another instance may already have reopened it
