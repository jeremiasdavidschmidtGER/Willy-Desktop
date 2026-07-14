"""Time-based frame selection (A-06). Qt-free by design.

Frames are chosen from elapsed time since clip start (ARCHITECTURE §1,
D-6): robust to event-loop hiccups, drift-free for loops (modulo), and
deterministic under a fake clock.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrameSelection:
    index: int
    finished: bool  # non-loop clip ran past its last frame


def select_frame(durations_ms: Sequence[int], elapsed_seconds: float, loop: bool) -> FrameSelection:
    if not durations_ms:
        raise ValueError("durations_ms must not be empty")
    total = float(sum(durations_ms))
    elapsed_ms = max(0.0, elapsed_seconds * 1000.0)

    if loop:
        elapsed_ms = math.fmod(elapsed_ms, total)
    elif elapsed_ms >= total:
        return FrameSelection(index=len(durations_ms) - 1, finished=True)

    threshold = 0.0
    for index, duration in enumerate(durations_ms):
        threshold += duration
        if elapsed_ms < threshold:
            return FrameSelection(index=index, finished=False)
    return FrameSelection(index=len(durations_ms) - 1, finished=False)  # fmod edge
