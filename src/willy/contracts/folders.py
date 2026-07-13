"""Forward seams (types only; no Gate A implementation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import PurePath


class FolderActivity(Enum):
    INSPECTING = auto()
    DIGGING = auto()
    SLEEPING = auto()
    HIDING = auto()


@dataclass(frozen=True, slots=True)
class VirtualFolderLocation:
    """Fictional presence only. Never implies filesystem writes."""

    root_id: str
    relative_path: PurePath
    entered_at: datetime
    activity: FolderActivity
