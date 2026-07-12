from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from willy.contracts.commands import PlayAnimation
from willy.contracts.enums import AnimationPriority, Facing


@dataclass(frozen=True, slots=True)
class FrameSpec:
    image: str  # file name relative to manifest dir
    duration_ms: int  # > 0


@dataclass(frozen=True, slots=True)
class AnimationManifest:
    asset_id: str  # e.g. "willy_walk"
    source_direction: Facing  # always RIGHT for canon assets
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
