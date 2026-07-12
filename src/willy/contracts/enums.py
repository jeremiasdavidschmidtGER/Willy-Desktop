from __future__ import annotations

from enum import Enum, auto


class Facing(Enum):
    LEFT = auto()
    RIGHT = auto()


class AnimationPriority(Enum):  # higher interrupts lower
    IDLE = 0
    AMBIENT = 1
    INTERACTION = 2
    REACTION = 3


class TrayCommandKind(Enum):
    MUTE_TOGGLE = auto()
    PAUSE_TOGGLE = auto()
    HIDE_TOGGLE = auto()
    RESET_POSITION = auto()
    EXIT = auto()


class MouseButton(Enum):
    LEFT = auto()
    RIGHT = auto()
