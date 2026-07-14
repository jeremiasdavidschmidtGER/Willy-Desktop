"""InteractionController (A-07): Qt-free event → command mapping.

Consumes drag facts from the platform layer and emits animation
commands; owns Willy's facing (flips toward drag direction). Decision
code: it never imports Qt and never calls sinks directly — commands go
through the injected dispatch callable (the CommandRouter's).
"""

from __future__ import annotations

from collections.abc import Callable

from willy.contracts import (
    AnimationPriority,
    Command,
    DragEnded,
    DragStarted,
    Facing,
    PlayAnimation,
)

DRAGGED_ASSET_ID = "willy_dragged"
LANDING_ASSET_ID = "willy_drop_landing"
FACING_FLIP_THRESHOLD_PX = 2  # tiny horizontal drift keeps current facing


class InteractionController:
    def __init__(
        self,
        *,
        dispatch: Callable[[Command], None],
        state_dirty: Callable[[], None],
        initial_facing: Facing = Facing.RIGHT,
    ) -> None:
        self._dispatch = dispatch
        self._state_dirty = state_dirty
        self._facing = initial_facing
        self._grab_x: int | None = None

    @property
    def facing(self) -> Facing:
        return self._facing

    def on_drag_started(self, event: DragStarted) -> None:
        self._grab_x = event.grab_point.x
        self._dispatch(
            PlayAnimation(
                animation_id=DRAGGED_ASSET_ID,
                facing=self._facing,
                priority=AnimationPriority.REACTION,
            )
        )

    def on_drag_ended(self, event: DragEnded) -> None:
        if self._grab_x is not None:
            delta_x = event.drop_point.x - self._grab_x
            if delta_x > FACING_FLIP_THRESHOLD_PX:
                self._facing = Facing.RIGHT
            elif delta_x < -FACING_FLIP_THRESHOLD_PX:
                self._facing = Facing.LEFT
        self._grab_x = None
        self._dispatch(
            PlayAnimation(
                animation_id=LANDING_ASSET_ID,
                facing=self._facing,
                priority=AnimationPriority.REACTION,
            )
        )
        self._state_dirty()  # position/facing changed → persist (debounced)
