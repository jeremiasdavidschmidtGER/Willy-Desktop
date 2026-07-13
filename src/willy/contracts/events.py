"""Events: past tense, facts only. Only the observing module publishes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from willy.contracts.enums import MouseButton, TrayCommandKind
from willy.contracts.primitives import ScreenPoint


@dataclass(frozen=True, slots=True)
class Event:
    timestamp: datetime  # injected clock, never datetime.now() in core


# --- lifecycle ---
@dataclass(frozen=True, slots=True)
class AppStarted(Event): ...


@dataclass(frozen=True, slots=True)
class ShutdownRequested(Event): ...


# --- time ---
@dataclass(frozen=True, slots=True)
class TickElapsed(Event):
    dt_seconds: float  # behaviour tick, ~1.0


# --- user interaction (published by platform layer only) ---
@dataclass(frozen=True, slots=True)
class WillyClicked(Event):
    button: MouseButton
    clicks_in_last_10s: int  # platform counts; core interprets


@dataclass(frozen=True, slots=True)
class DragStarted(Event):
    grab_point: ScreenPoint


@dataclass(frozen=True, slots=True)
class DragEnded(Event):
    drop_point: ScreenPoint


# --- platform ---
@dataclass(frozen=True, slots=True)
class ScreenLayoutChanged(Event):
    screen_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TrayCommandIssued(Event):
    kind: TrayCommandKind


# --- animation feedback ---
@dataclass(frozen=True, slots=True)
class AnimationFinished(Event):
    animation_id: str
