"""Shared contracts (INTERFACES.md v1). Stdlib only — no Qt, no sqlite3.

Read-only for implementation agents; changes go through lead review.
"""

from willy.contracts.animation import AnimationController, AnimationManifest, FrameSpec
from willy.contracts.bus import BusRecursionError, EventBus
from willy.contracts.commands import (
    Command,
    PlayAnimation,
    SetMuted,
    SetPaused,
    SetVisibility,
    SetWindowPosition,
)
from willy.contracts.enums import AnimationPriority, Facing, MouseButton, TrayCommandKind
from willy.contracts.events import (
    AnimationFinished,
    AppStarted,
    DragEnded,
    DragStarted,
    Event,
    ScreenLayoutChanged,
    ShutdownRequested,
    TickElapsed,
    TrayCommandIssued,
    WillyClicked,
)
from willy.contracts.folders import FolderActivity, VirtualFolderLocation
from willy.contracts.persistence import (
    Clock,
    SettingsRepository,
    WillyStateRepository,
    WillyStateSnapshot,
)
from willy.contracts.primitives import ScreenPoint
from willy.contracts.proposals import BehaviourProposal, ProposalValidator

__all__ = [
    "AnimationController",
    "AnimationManifest",
    "FrameSpec",
    "BusRecursionError",
    "EventBus",
    "Command",
    "PlayAnimation",
    "SetMuted",
    "SetPaused",
    "SetVisibility",
    "SetWindowPosition",
    "AnimationPriority",
    "Facing",
    "MouseButton",
    "TrayCommandKind",
    "AnimationFinished",
    "AppStarted",
    "DragEnded",
    "DragStarted",
    "Event",
    "ScreenLayoutChanged",
    "ShutdownRequested",
    "TickElapsed",
    "TrayCommandIssued",
    "WillyClicked",
    "FolderActivity",
    "VirtualFolderLocation",
    "Clock",
    "SettingsRepository",
    "WillyStateRepository",
    "WillyStateSnapshot",
    "ScreenPoint",
    "BehaviourProposal",
    "ProposalValidator",
]
