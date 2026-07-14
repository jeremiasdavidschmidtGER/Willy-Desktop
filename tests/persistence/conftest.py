from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


class FakeClock:
    """Deterministic Clock: advance() moves both now() and monotonic()."""

    def __init__(self) -> None:
        self._now = datetime(2026, 7, 13, 12, 0, 0, tzinfo=UTC)
        self._monotonic = 1000.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
        self._monotonic += seconds


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()
