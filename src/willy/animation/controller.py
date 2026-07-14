"""Animation controller (A-06): a small state machine over the cache.

Implements the AnimationController protocol: consumes PlayAnimation /
SetPaused, publishes AnimationFinished, interrupts by priority
(REACTION > INTERACTION > AMBIENT > IDLE; equal replaces, lower is
ignored), auto-returns to idle when a non-loop clip ends. It never
decides *why* — it plays what it is told (ARCHITECTURE §4).
"""

from __future__ import annotations

from PySide6.QtGui import QPixmap

from willy.animation.library import FALLBACK_ASSET_ID, AssetLibrary
from willy.animation.timing import select_frame
from willy.assets_runtime.pixmap_cache import PixmapCache
from willy.contracts import (
    AnimationFinished,
    AnimationManifest,
    AnimationPriority,
    Clock,
    EventBus,
    Facing,
    PlayAnimation,
)


class WillyAnimationController:
    def __init__(
        self,
        *,
        cache: PixmapCache,
        library: AssetLibrary,
        bus: EventBus,
        clock: Clock,
        idle_asset_id: str = FALLBACK_ASSET_ID,
    ) -> None:
        self._cache = cache
        self._library = library
        self._bus = bus
        self._clock = clock
        self._idle_asset_id = idle_asset_id
        self._paused = False
        self._pause_started = 0.0
        # populated by _play_idle:
        self._manifest: AnimationManifest
        self._facing: Facing
        self._priority: AnimationPriority
        self._loop: bool
        self._start: float
        self._finished_handled: bool
        self._play_idle(Facing.RIGHT)

    @property
    def current_animation_id(self) -> str:
        return self._manifest.asset_id

    @property
    def current_facing(self) -> Facing:
        return self._facing

    @property
    def current_priority(self) -> AnimationPriority:
        return self._priority

    @property
    def paused(self) -> bool:
        return self._paused

    def play(self, cmd: PlayAnimation) -> None:
        if cmd.priority.value < self._priority.value:
            return  # lower priority never interrupts; equal replaces
        manifest = self._library.manifest(cmd.animation_id)
        loop = manifest.loop if cmd.loop_override is None else cmd.loop_override
        self._apply(manifest, cmd.facing, cmd.priority, loop)

    def set_paused(self, paused: bool) -> None:
        if paused == self._paused:
            return
        now = self._clock.monotonic()
        if paused:
            self._pause_started = now
        else:
            # Shift the clip's start by the pause length: playback resumes
            # exactly where it froze, no jump.
            self._start += now - self._pause_started
        self._paused = paused

    def tick(self) -> QPixmap:
        """Current frame for the render tick; handles non-loop clip end."""
        durations = [frame.duration_ms for frame in self._manifest.frames]
        selection = select_frame(durations, self._elapsed(), self._loop)
        if selection.finished and not self._finished_handled:
            self._finished_handled = True
            finished_id = self._manifest.asset_id
            # Return to idle *before* publishing: a handler reacting to
            # AnimationFinished with its own play() must win over idle.
            self._play_idle(self._facing)
            self._bus.publish(
                AnimationFinished(timestamp=self._clock.now(), animation_id=finished_id)
            )
            durations = [frame.duration_ms for frame in self._manifest.frames]
            selection = select_frame(durations, self._elapsed(), self._loop)
        return self._cache.frames(self._manifest.asset_id, self._facing)[selection.index]

    def _play_idle(self, facing: Facing) -> None:
        manifest = self._library.manifest(self._idle_asset_id)
        self._apply(manifest, facing, AnimationPriority.IDLE, manifest.loop)

    def _apply(
        self,
        manifest: AnimationManifest,
        facing: Facing,
        priority: AnimationPriority,
        loop: bool,
    ) -> None:
        self._manifest = manifest
        self._facing = facing
        self._priority = priority
        self._loop = loop
        self._start = self._clock.monotonic()
        self._finished_handled = False
        if self._paused:
            self._pause_started = self._start  # frozen at frame 0 until resume

    def _elapsed(self) -> float:
        now = self._pause_started if self._paused else self._clock.monotonic()
        return now - self._start
