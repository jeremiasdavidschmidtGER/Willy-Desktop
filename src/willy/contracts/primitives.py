from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreenPoint:
    """Virtual-desktop coordinates (Qt global coords)."""

    x: int
    y: int
