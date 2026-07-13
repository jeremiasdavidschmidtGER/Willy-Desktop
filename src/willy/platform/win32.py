"""Windows-specific primitives behind plain-Python interfaces.

Every raw Windows API touch lives here (ARCHITECTURE.md §7); nothing else
in the codebase imports ctypes or Windows-only modules. Qt covers all
Gate A window behaviour, so the only resident is the file-lock primitive
used by the single-instance guard (D-11).
"""

from __future__ import annotations

import msvcrt
import os


def try_lock_file(fd: int) -> bool:
    """Take a non-blocking exclusive lock on the first byte of ``fd``.

    The OS releases the lock automatically when the process dies, so a
    crashed instance can never leave a stale lock behind.
    """
    try:
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def unlock_file(fd: int) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
