"""InteractionController (A-07 + D-16 + A-08): Qt-free event → command
mapping.

Consumes drag and click facts from the platform layer and emits
animation commands; owns Willy's facing (flips toward drag direction)
and his session-only annoyance level (A-08). Decision code: it never
imports Qt and never calls sinks directly — commands go through the
injected dispatch callable (the CommandRouter's).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from datetime import datetime

from willy.contracts import (
    AnimationFinished,
    AnimationPriority,
    Command,
    DragEnded,
    DragMoved,
    DragStarted,
    Facing,
    MouseButton,
    PlayAnimation,
    TickElapsed,
    WillyClicked,
)

DRAGGED_ASSET_ID = "willy_dragged"
STARTLE_ASSET_ID = "willy_surprised"
LANDING_ASSET_ID = "willy_drop_landing"
FACING_FLIP_THRESHOLD_PX = 2  # tiny horizontal drift keeps current facing

# D-18: escalating drag tiers, same "hanging" pose family as DRAGGED_ASSET_ID
# but reads as more agitated. Two independent signals — accumulated hold
# duration and peak swing velocity — either one can push the tier up;
# escalation is sticky for the rest of the drag (never steps back down
# until DragEnded), mirroring how REACTION_TIERS never needs a decay step
# mid-drag. Art doesn't exist yet as of D-18's scoping — see
# OPEN_DECISIONS.md; release-mode asset fallback keeps this safe to merge
# ahead of the art landing, but don't ship to users until it has.
SWING_ASSET_ID = "willy_dragged_swing"
ANNOYED_DRAG_ASSET_ID = "willy_dragged_annoyed"
DRAG_TIER_ASSETS: tuple[str, ...] = (DRAGGED_ASSET_ID, SWING_ASSET_ID, ANNOYED_DRAG_ASSET_ID)
# first-pass tuning; retune after live-watching, same as every other threshold here
DRAG_HOLD_TIER_SECONDS: tuple[float, ...] = (3.0, 8.0)
DRAG_VELOCITY_TIER_PX_S: tuple[float, ...] = (600.0, 1400.0)

# A-08: the tier-1 click reaction is a three-stage front-facing sequence
# (turn to face the camera, hold, turn back) rather than a flat one-shot
# clip like the other tiers — see the _front_* state machine below.
FRONT_ENTER_ASSET_ID = "willy_front_enter"
FRONT_IDLE_ASSET_ID = "willy_front_idle"
FRONT_LEAVE_ASSET_ID = "willy_front_leave"
FRONT_HOLD_SECONDS = 3.0  # how long the front-facing hold lasts; first-pass tuning

# A-08: click count → reaction asset, ascending by threshold. Data-driven so
# tuning (or adding tiers) never touches the dispatch logic below.
REACTION_TIERS: tuple[tuple[int, str], ...] = (
    (1, FRONT_ENTER_ASSET_ID),  # 1-2 clicks: turns to look at you, expecting interaction
    (3, "willy_annoyed"),  # 3-5 clicks: annoyed
    (6, "willy_smug"),  # 6+ clicks: smug refusal
)
ANNOYANCE_DECAY_PER_SECOND = 0.3  # first-pass tuning; retune after live-watching


class InteractionController:
    def __init__(
        self,
        *,
        dispatch: Callable[[Command], None],
        state_dirty: Callable[[], None],
        initial_facing: Facing = Facing.RIGHT,
        is_falling: Callable[[], bool] = lambda: False,
        reaction_tiers: Sequence[tuple[int, str]] = REACTION_TIERS,
        annoyance_decay_per_second: float = ANNOYANCE_DECAY_PER_SECOND,
    ) -> None:
        self._dispatch = dispatch
        self._state_dirty = state_dirty
        self._facing = initial_facing
        self._is_falling = is_falling
        self._grab_x: int | None = None
        self._drag_hold_seconds = 0.0
        self._drag_max_velocity_px_s = 0.0
        self._drag_tier_rank = 0
        self._last_drag_x: int | None = None
        self._last_drag_y: int | None = None
        self._last_drag_timestamp: datetime | None = None
        self._reaction_tiers = tuple(sorted(reaction_tiers, key=lambda tier: tier[0]))
        self._annoyance_decay_per_second = annoyance_decay_per_second
        self._annoyance_cap = self._reaction_tiers[-1][0] * 2.0
        self._annoyance = 0.0
        # "none" | "entering" | "holding" | "leaving" — see _enter_or_refresh_front.
        self._front_state = "none"
        self._front_hold_remaining = 0.0
        self._pending_tier_asset: str | None = None

    @property
    def facing(self) -> Facing:
        return self._facing

    @property
    def annoyance(self) -> float:
        return self._annoyance

    def on_drag_started(self, event: DragStarted) -> None:
        self._reset_front_sequence()
        self._grab_x = event.grab_point.x
        self._drag_hold_seconds = 0.0
        self._drag_max_velocity_px_s = 0.0
        self._drag_tier_rank = 0
        self._last_drag_x = event.grab_point.x
        self._last_drag_y = event.grab_point.y
        self._last_drag_timestamp = event.timestamp
        self._play(DRAGGED_ASSET_ID)

    def on_drag_moved(self, event: DragMoved) -> None:
        """D-18: swing-intensity signal — peak cursor speed since the drag
        started. The platform sends a fact per real move; this derives
        velocity from consecutive points/timestamps itself."""
        if self._last_drag_timestamp is not None:
            dt = (event.timestamp - self._last_drag_timestamp).total_seconds()
            if dt > 0 and self._last_drag_x is not None and self._last_drag_y is not None:
                distance = math.hypot(
                    event.point.x - self._last_drag_x, event.point.y - self._last_drag_y
                )
                velocity = distance / dt
                self._drag_max_velocity_px_s = max(self._drag_max_velocity_px_s, velocity)
        self._last_drag_x = event.point.x
        self._last_drag_y = event.point.y
        self._last_drag_timestamp = event.timestamp
        self._update_drag_tier()

    def on_fall_started(self) -> None:
        """Real gravity drop begins (D-15/D-16): startle once, then the
        dangle loop resumes for the rest of the fall via
        on_animation_finished."""
        self._reset_front_sequence()
        self._play(STARTLE_ASSET_ID)

    def on_animation_finished(self, event: AnimationFinished) -> None:
        if event.animation_id == STARTLE_ASSET_ID and self._is_falling():
            # Still airborne: resume dangling instead of A-06's idle
            # default (dispatched here, it wins over idle — see A-06).
            self._play(DRAGGED_ASSET_ID)
        elif event.animation_id == FRONT_ENTER_ASSET_ID and self._front_state == "entering":
            self._front_state = "holding"
            self._front_hold_remaining = FRONT_HOLD_SECONDS
            self._play(
                FRONT_IDLE_ASSET_ID, priority=AnimationPriority.INTERACTION, loop_override=True
            )
        elif event.animation_id == FRONT_LEAVE_ASSET_ID and self._front_state == "leaving":
            self._front_state = "none"
            pending, self._pending_tier_asset = self._pending_tier_asset, None
            if pending is not None:
                self._play(pending, priority=AnimationPriority.INTERACTION, loop_override=False)

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

    def on_willy_clicked(self, event: WillyClicked) -> None:
        """Left click → tiered reaction (A-08); right click is reserved for
        a future context menu (Gate B) and never reacts here."""
        if event.button is not MouseButton.LEFT:
            return
        self._annoyance = min(self._annoyance + 1.0, self._annoyance_cap)
        asset_id = self._tier_asset()
        if asset_id is None:
            return
        if asset_id == FRONT_ENTER_ASSET_ID:
            self._enter_or_refresh_front()
        elif self._front_state == "none":
            # Forced one-shot: some tier clips loop in their manifest (a
            # lingering demeanor is fine while clicks keep coming), but a
            # click reaction must always be able to hand control back to
            # idle on its own — never wait on TickElapsed to un-stick it.
            self._play(asset_id, priority=AnimationPriority.INTERACTION, loop_override=False)
        else:
            # Currently mid front-facing sequence: turn away first, then
            # play the side-view reaction, instead of jump-cutting from
            # facing the camera straight to a side-view pose.
            self._pending_tier_asset = asset_id
            self._begin_front_leave()

    def on_tick_elapsed(self, event: TickElapsed) -> None:
        """Decays annoyance over time — session-only (A-08): a click after
        a long-enough quiet period starts back at the lowest tier. Also
        counts down how long the front-facing hold lasts, and (D-18)
        accumulates how long the current drag has been held."""
        if self._front_state == "holding":
            self._front_hold_remaining -= event.dt_seconds
            if self._front_hold_remaining <= 0.0:
                self._begin_front_leave()
        if self._grab_x is not None:
            self._drag_hold_seconds += event.dt_seconds
            self._update_drag_tier()
        if self._annoyance <= 0.0:
            return
        self._annoyance = max(
            0.0, self._annoyance - self._annoyance_decay_per_second * event.dt_seconds
        )

    def _tier_asset(self) -> str | None:
        asset_id = None
        for threshold, tier_asset_id in self._reaction_tiers:
            if self._annoyance >= threshold:
                asset_id = tier_asset_id
        return asset_id

    def _update_drag_tier(self) -> None:
        """D-18: recompute the drag tier from both signals and, if it just
        escalated, switch the dangle loop. Sticky for the rest of the
        drag — never steps back down until DragEnded starts a fresh one."""
        rank = max(
            self._rank_for(self._drag_hold_seconds, DRAG_HOLD_TIER_SECONDS),
            self._rank_for(self._drag_max_velocity_px_s, DRAG_VELOCITY_TIER_PX_S),
        )
        if rank > self._drag_tier_rank:
            self._drag_tier_rank = rank
            self._play(DRAG_TIER_ASSETS[rank])

    @staticmethod
    def _rank_for(value: float, thresholds: Sequence[float]) -> int:
        rank = 0
        for index, threshold in enumerate(thresholds, start=1):
            if value >= threshold:
                rank = index
        return rank

    def _enter_or_refresh_front(self) -> None:
        if self._front_state in ("entering", "holding"):
            self._front_hold_remaining = FRONT_HOLD_SECONDS  # already facing: extend the hold
            return
        self._front_state = "entering"
        self._play(
            FRONT_ENTER_ASSET_ID, priority=AnimationPriority.INTERACTION, loop_override=False
        )

    def _begin_front_leave(self) -> None:
        self._front_state = "leaving"
        self._play(
            FRONT_LEAVE_ASSET_ID, priority=AnimationPriority.INTERACTION, loop_override=False
        )

    def _reset_front_sequence(self) -> None:
        self._front_state = "none"
        self._front_hold_remaining = 0.0
        self._pending_tier_asset = None

    def _play(
        self,
        asset_id: str,
        *,
        priority: AnimationPriority = AnimationPriority.REACTION,
        loop_override: bool | None = None,
    ) -> None:
        self._dispatch(
            PlayAnimation(
                animation_id=asset_id,
                facing=self._facing,
                priority=priority,
                loop_override=loop_override,
            )
        )
