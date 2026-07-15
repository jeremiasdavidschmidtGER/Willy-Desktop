"""Deterministic synthetic-event schedule for the soak simulation (A-11).

Pure, seeded, no Qt/no I/O: given a duration and a seed, produces the same
schedule every time so a failing soak run is reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto


class ActionKind(Enum):
    CLICK = auto()
    DRAG_CYCLE = auto()
    LAYOUT_CHANGE = auto()


@dataclass(frozen=True, slots=True)
class SimulatedAction:
    at_seconds: float
    kind: ActionKind


# (min, max) seconds between consecutive actions of each kind.
DEFAULT_CLICK_INTERVAL_S = (5.0, 90.0)
DEFAULT_DRAG_INTERVAL_S = (60.0, 600.0)
DEFAULT_LAYOUT_CHANGE_INTERVAL_S = (900.0, 3600.0)


def generate_schedule(
    *,
    duration_seconds: float,
    seed: int,
    click_interval_s: tuple[float, float] = DEFAULT_CLICK_INTERVAL_S,
    drag_interval_s: tuple[float, float] = DEFAULT_DRAG_INTERVAL_S,
    layout_change_interval_s: tuple[float, float] = DEFAULT_LAYOUT_CHANGE_INTERVAL_S,
) -> tuple[SimulatedAction, ...]:
    """A time-sorted schedule of clicks, drag cycles, and layout changes
    spread across `duration_seconds`, reproducible for a given `seed`."""
    if duration_seconds < 0:
        raise ValueError("duration_seconds must be >= 0")
    rng = random.Random(seed)
    actions: list[SimulatedAction] = []
    for kind, interval in (
        (ActionKind.CLICK, click_interval_s),
        (ActionKind.DRAG_CYCLE, drag_interval_s),
        (ActionKind.LAYOUT_CHANGE, layout_change_interval_s),
    ):
        t = rng.uniform(*interval)
        while t < duration_seconds:
            actions.append(SimulatedAction(at_seconds=t, kind=kind))
            t += rng.uniform(*interval)
    return tuple(sorted(actions, key=lambda action: action.at_seconds))
