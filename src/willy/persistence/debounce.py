"""Restartable write debouncer (ARCHITECTURE.md §1/§6 write policy).

Qt-free: the caller drives it (a QTimer in app/ later, a fake clock in
tests). Each ``mark_dirty()`` restarts the interval; ``flush()`` forces
an immediate write (used on shutdown).
"""

from __future__ import annotations

from collections.abc import Callable

from willy.contracts import Clock


class DebouncedWriter:
    def __init__(
        self,
        flush_callback: Callable[[], None],
        clock: Clock,
        interval_seconds: float = 1.0,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._flush_callback = flush_callback
        self._clock = clock
        self._interval_seconds = interval_seconds
        self._deadline: float | None = None
        self._dirty = False

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True
        self._deadline = self._clock.monotonic() + self._interval_seconds

    def maybe_flush(self) -> bool:
        """Flush if the debounce interval has elapsed; return whether it did."""
        if not self._dirty or self._deadline is None:
            return False
        if self._clock.monotonic() < self._deadline:
            return False
        return self.flush()

    def flush(self) -> bool:
        """Write immediately if dirty; return whether a write happened."""
        if not self._dirty:
            return False
        self._flush_callback()
        self._dirty = False
        self._deadline = None
        return True
