"""Commands: imperatives; each consumed by exactly one sink (CommandRouter in app)."""

from __future__ import annotations

from dataclasses import dataclass

from willy.contracts.enums import AnimationPriority, Facing
from willy.contracts.primitives import ScreenPoint


@dataclass(frozen=True, slots=True)
class Command: ...


@dataclass(frozen=True, slots=True)
class PlayAnimation(Command):  # sink: animation
    animation_id: str
    facing: Facing
    priority: AnimationPriority
    loop_override: bool | None = None  # None -> manifest value


@dataclass(frozen=True, slots=True)
class SetWindowPosition(Command):  # sink: platform
    point: ScreenPoint


@dataclass(frozen=True, slots=True)
class SetVisibility(Command):  # sink: platform
    visible: bool


@dataclass(frozen=True, slots=True)
class SetMuted(Command):  # sink: audio (Gate A: no-op stub)
    muted: bool


@dataclass(frozen=True, slots=True)
class SetPaused(Command):  # sink: animation
    paused: bool
