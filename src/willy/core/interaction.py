"""InteractionController (A-07 + D-16): Qt-free event → command mapping.

Consumes drag facts from the platform layer and emits animation
commands; owns Willy's facing (flips toward drag direction). Decision
code: it never imports Qt and never calls sinks directly — commands go
through the injected dispatch callable (the CommandRouter's).
"""

from __future__ import annotations

from collections.abc import Callable

from willy.contracts import (
    AnimationFinished,
    AnimationPriority,
    Command,
    DragEnded,
    DragStarted,
    Facing,
    PlayAnimation,
)

DRAGGED_ASSET_ID = "willy_dragged"
STARTLE_ASSET_ID = "willy_surprised"
LANDING_ASSET_ID = "willy_drop_landing"
FACING_FLIP_THRESHOLD_PX = 2  # tiny horizontal drift keeps current facing


class InteractionController:
    def __init__(
        self,
        *,
        dispatch: Callable[[Command], None],
        state_dirty: Callable[[], None],
        initial_facing: Facing = Facing.RIGHT,
        is_falling: Callable[[], bool] = lambda: False,
    ) -> None:
        self._dispatch = dispatch
        self._state_dirty = state_dirty
        self._facing = initial_facing
        self._is_falling = is_falling
        self._grab_x: int | None = None

    @property
    def facing(self) -> Facing:
        return self._facing

    def on_drag_started(self, event: DragStarted) -> None:
        self._grab_x = event.grab_point.x
        self._play(DRAGGED_ASSET_ID)

    def on_fall_started(self) -> None:
        """Real gravity drop begins (D-15/D-16): startle once, then the
        dangle loop resumes for the rest of the fall via
        on_animation_finished."""
        self._play(STARTLE_ASSET_ID)

    def on_animation_finished(self, event: AnimationFinished) -> None:
        if event.animation_id == STARTLE_ASSET_ID and self._is_falling():
            # Still airborne: resume dangling instead of A-06's idle
            # default (dispatched here, it wins over idle — see A-06).
            self._play(DRAGGED_ASSET_ID)

    def on_drag_ended(self, event: DragEnded) -> None:
        if self._grab_x is not None:
            delta_x = event.drop_point.x - self._grab_x
            if delta_x > FACING_FLIP_THRESHOLD_PX:
                self._facing = Facing.RIGHT
            elif delta_x < -FACING_FLIP_THRESHOLD_PX:
                self._facing = Facing.LEFT
        self._grab_x = None
        self._play(LANDING_ASSET_ID)
        self._state_dirty()  # position/facing changed → persist (debounced)

    def _play(self, asset_id: str) -> None:
        self._dispatch(
            PlayAnimation(
                animation_id=asset_id,
                facing=self._facing,
                priority=AnimationPriority.REACTION,
            )
        )
