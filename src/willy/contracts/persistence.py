from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from willy.contracts.enums import Facing
from willy.contracts.primitives import ScreenPoint


@dataclass(frozen=True, slots=True)
class WillyStateSnapshot:
    position: ScreenPoint
    screen_name: str
    facing: Facing
    updated_at: datetime


class WillyStateRepository(Protocol):
    def load(self) -> WillyStateSnapshot | None: ...  # None on first run

    def save(self, snapshot: WillyStateSnapshot) -> None: ...


class SettingsRepository(Protocol):
    def get_bool(self, key: str, default: bool) -> bool: ...

    def get_int(self, key: str, default: int) -> int: ...

    def get_str(self, key: str, default: str) -> str: ...

    def set(self, key: str, value: bool | int | str) -> None: ...


class Clock(Protocol):
    """All non-Qt code takes a Clock; tests inject a fake."""

    def now(self) -> datetime: ...

    def monotonic(self) -> float: ...
