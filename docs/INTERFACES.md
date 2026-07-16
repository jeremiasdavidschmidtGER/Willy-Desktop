# Willy Desktop — INTERFACES.md

Status: v1 (Gate A). Owned by Lead Architect. Any change to this file
requires lead review; implementation agents may not edit it.

Everything here lives in `src/willy/contracts/` and imports **stdlib only**
(no Qt, no sqlite3). All DTOs are `@dataclass(frozen=True, slots=True)`.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import PurePath
from typing import Callable, Mapping, Protocol, Sequence, TypeVar
```

---

## 1. Enums

```python
class Facing(Enum):
    LEFT = auto()
    RIGHT = auto()

class AnimationPriority(Enum):     # higher interrupts lower
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
```

```python
@dataclass(frozen=True, slots=True)
class ScreenPoint:
    """Virtual-desktop coordinates (Qt global coords)."""
    x: int
    y: int
```

---

## 2. Events (published on the bus; past tense, facts only)

```python
@dataclass(frozen=True, slots=True)
class Event:
    timestamp: datetime            # injected clock, never datetime.now() in core

# --- lifecycle ---
@dataclass(frozen=True, slots=True)
class AppStarted(Event): ...

@dataclass(frozen=True, slots=True)
class ShutdownRequested(Event): ...

# --- time ---
@dataclass(frozen=True, slots=True)
class TickElapsed(Event):
    dt_seconds: float              # behaviour tick, ~1.0

# --- user interaction (published by platform layer only) ---
@dataclass(frozen=True, slots=True)
class WillyClicked(Event):
    button: MouseButton
    clicks_in_last_10s: int        # platform counts; core interprets

@dataclass(frozen=True, slots=True)
class DragStarted(Event):
    grab_point: ScreenPoint

@dataclass(frozen=True, slots=True)
class DragMoved(Event):
    # D-18: one per real cursor move while dragging; InteractionController
    # derives swing-intensity from consecutive points/timestamps itself —
    # the platform layer stays dumb (same division as WillyClicked).
    point: ScreenPoint

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
```

Rules: events describe what happened, never what should happen. Only the
module that observed the fact may publish it.

---

## 3. Commands (imperatives; consumed by exactly one sink)

```python
@dataclass(frozen=True, slots=True)
class Command: ...

@dataclass(frozen=True, slots=True)
class PlayAnimation(Command):          # sink: animation
    animation_id: str
    facing: Facing
    priority: AnimationPriority
    loop_override: bool | None = None  # None → manifest value

@dataclass(frozen=True, slots=True)
class SetWindowPosition(Command):      # sink: platform
    point: ScreenPoint

@dataclass(frozen=True, slots=True)
class SetVisibility(Command):          # sink: platform
    visible: bool

@dataclass(frozen=True, slots=True)
class SetMuted(Command):               # sink: audio (Gate A: no-op stub)
    muted: bool

@dataclass(frozen=True, slots=True)
class SetPaused(Command):              # sink: animation
    paused: bool
```

Dispatch: `app/` wires a `CommandRouter` mapping command type → single sink
callable. Decision code returns/emits commands; it never calls sinks.

---

## 4. Event bus

```python
E = TypeVar("E", bound=Event)

class EventBus(Protocol):
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...
    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...
    def publish(self, event: Event) -> None: ...
```

Contract: synchronous, main-thread only, dispatch in subscription order,
raises `BusRecursionError` beyond re-entrancy depth 3.

---

## 5. Animation contracts

```python
@dataclass(frozen=True, slots=True)
class FrameSpec:
    image: str                     # file name relative to manifest dir
    duration_ms: int               # > 0

@dataclass(frozen=True, slots=True)
class AnimationManifest:
    asset_id: str                  # e.g. "willy_walk"
    source_direction: Facing       # always RIGHT for canon assets
    mirror_allowed: bool
    loop: bool
    priority: AnimationPriority
    frames: tuple[FrameSpec, ...]  # len >= 1
    anchors: Mapping[str, tuple[int, int]] = field(default_factory=dict)
    # required anchor keys when present on any Willy body asset:
    # "body_pivot", "ground"; optional: "mouth", "eyes", "headset",
    # "front_hoof", "rear_effect", "folder_contact", "click_region_center"

class AnimationController(Protocol):
    def play(self, cmd: PlayAnimation) -> None: ...
    def set_paused(self, paused: bool) -> None: ...
    @property
    def current_animation_id(self) -> str: ...
    @property
    def current_facing(self) -> Facing: ...
```

Mirroring contract (per MVP §28.6): mirrored anchor
`x' = frame_width - 1 - x`; `y` unchanged; performed once per asset load;
both directions cached; `mirror_allowed=False` assets are served as-is for
either facing.

---

## 6. Behaviour proposal (defined now; produced from Gate B on)

```python
@dataclass(frozen=True, slots=True)
class BehaviourProposal:
    behaviour_id: str
    animation_id: str | None
    dialogue_intent: str | None
    audio_id: str | None
    state_changes: Mapping[str, int]   # e.g. {"irritation": 2}

class ProposalValidator(Protocol):
    def validate(self, proposal: BehaviourProposal) -> BehaviourProposal | None:
        """Return possibly-adjusted proposal, or None to reject."""
```

Gate A ships the types and a pass-through validator only. Any future LLM
output must be reduced to a `BehaviourProposal` before entering the pipeline.

---

## 7. Persistence repositories

```python
@dataclass(frozen=True, slots=True)
class WillyStateSnapshot:
    position: ScreenPoint
    screen_name: str
    facing: Facing
    updated_at: datetime

class WillyStateRepository(Protocol):
    def load(self) -> WillyStateSnapshot | None: ...     # None on first run
    def save(self, snapshot: WillyStateSnapshot) -> None: ...

class SettingsRepository(Protocol):
    def get_bool(self, key: str, default: bool) -> bool: ...
    def get_int(self, key: str, default: int) -> int: ...
    def get_str(self, key: str, default: str) -> str: ...
    def set(self, key: str, value: bool | int | str) -> None: ...
```

Reserved settings keys (Gate A): `audio.muted`, `willy.paused`,
`willy.hidden`, `window.always_on_top`. Reserved for later:
`window.click_through`, `behaviour.intensity`, `privacy.*`.

```python
class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...
```

All non-Qt code takes a `Clock`; tests inject a fake.

---

## 8. Forward seams (types only, no Gate A implementation)

```python
class FolderActivity(Enum):
    INSPECTING = auto(); DIGGING = auto(); SLEEPING = auto(); HIDING = auto()

@dataclass(frozen=True, slots=True)
class VirtualFolderLocation:
    """Fictional presence only. Never implies filesystem writes."""
    root_id: str
    relative_path: PurePath
    entered_at: datetime
    activity: FolderActivity
```

---

## 9. Ownership of this file

| Section | May propose changes | Approves |
|---|---|---|
| all | any agent via escalation | Lead Architect (+ human for scope) |

Implementation agents code **against** these protocols and construct these
DTOs; they never redefine them locally or add Qt types to `contracts/`.
