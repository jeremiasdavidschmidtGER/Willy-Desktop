"""InteractionController (A-07 + D-16 + A-08): Qt-free event → command
mapping.

Consumes drag and click facts from the platform layer and emits
animation commands; owns Willy's facing (flips toward drag direction)
and his session-only annoyance level (A-08). Decision code: it never
imports Qt and never calls sinks directly — commands go through the
injected dispatch callable (the CommandRouter's).
"""

from __future__ import annotations

import random
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
FALL_ASSET_ID = "willy_fall"
# D-19: two alternate one-shot reactions for the start of a real gravity
# fall, picked at random each time — willy_fall (an existing pose, already
# extracted/animated in the asset factory's raw pipeline but never bridged
# to Gate A until now, same situation D-17 found with the front-facing
# pose) was requested as a second option alongside the existing startle,
# rather than a replacement for it.
FALL_START_REACTIONS: tuple[str, ...] = (STARTLE_ASSET_ID, FALL_ASSET_ID)
LANDING_ASSET_ID = "willy_drop_landing"
FACING_FLIP_THRESHOLD_PX = 2  # tiny horizontal drift keeps current facing (at drop)
# Pull-back from the most extreme x reached in the current facing
# direction needed to flip facing *during* an active drag — much bigger
# than FACING_FLIP_THRESHOLD_PX on purpose: a real swing gesture
# oscillates left-right by design, so a tiny per-event threshold would
# flicker facing on every jitter (live-test 2026-07-20: facing was
# previously only set at drop, so SWING_ASSET_ID's directional pose
# stayed stuck facing one way regardless of drag direction). Tracked
# against a *trailing extremum*, not a fixed reference point — an
# earlier version anchored the reference at the last flip and never
# moved it while travel continued the same direction, so reversing
# after a long swing needed pulling back almost the entire swing
# distance before it would flip (read as major lag).
FACING_DRAG_FLIP_THRESHOLD_PX = 20

# D-18: escalating drag tiers, same "hanging" pose family as DRAGGED_ASSET_ID
# but reads as more agitated. Art landed 2026-07-16 (Python-Test
# codex/drag-expansion) — see OPEN_DECISIONS.md.
#
# Only ANNOYED is sticky for the rest of the drag (never steps back down
# until DragEnded) — it's reached via DRAG_HOLD_ANNOYED_SECONDS of *total*
# time spent dragging, whether that's a long motionless hold or a long
# bout of active swinging (both just accumulate the same clock; see
# on_tick_elapsed), so once Willy's genuinely fed up he stays that way.
# SWING is deliberately NOT sticky (live-test 2026-07-20, reversing the
# original design): it tracks *current* swing velocity and reverts to
# DRAGGED_ASSET_ID the moment real motion stops, rather than staying
# locked in once reached — a quick swing that stops should just go back
# to hanging calmly, not linger in the swing pose.
SWING_ASSET_ID = "willy_dragged_swing"
ANNOYED_DRAG_ASSET_ID = "willy_dragged_annoyed"
DRAG_TIER_ASSETS: tuple[str, ...] = (DRAGGED_ASSET_ID, SWING_ASSET_ID, ANNOYED_DRAG_ASSET_ID)
# first-pass tuning; retune after live-watching, same as every other threshold here
DRAG_HOLD_ANNOYED_SECONDS = 8.0  # total time dragging (held still or swung) before ANNOYED
# Live-test 2026-07-20: 600 triggered SWING too easily during ordinary
# dragging — it's meant to be reserved for genuinely fast/rapid cursor
# movement, with plain DRAGGED_ASSET_ID as the default the rest of the time.
DRAG_SWING_VELOCITY_PX_S = 1100.0
# Raw per-event instantaneous velocity was too noisy to use directly — two
# DragMoved events a couple ms apart (a perfectly normal small jump at
# real mouse-report rates) could spike to an unrealistic px/s reading
# from a tiny dt alone. An EMA smooths that out; DRAG_VELOCITY_EMA_ALPHA
# is the smoothing weight given to each new sample. DRAG_VELOCITY_MIN_DT_S
# additionally *ignores* samples closer together than this (live-test
# 2026-07-20: SWING was firing the instant Willy was picked up — the
# very first DragMoved can land only fractions of a ms after
# DragStarted's own timestamp, and dividing by that near-zero dt spikes
# even the EMA's first, most-diluted sample past the threshold).
DRAG_VELOCITY_EMA_ALPHA = 0.25
DRAG_VELOCITY_MIN_DT_S = 0.01

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
        reaction_tiers: Sequence[tuple[int, str]] = REACTION_TIERS,
        annoyance_decay_per_second: float = ANNOYANCE_DECAY_PER_SECOND,
        random_choice: Callable[[Sequence[str]], str] = random.choice,
    ) -> None:
        self._dispatch = dispatch
        self._state_dirty = state_dirty
        self._facing = initial_facing
        self._random_choice = random_choice
        self._current_fall_reaction: str | None = None
        self._grab_x: int | None = None
        self._drag_hold_seconds = 0.0
        self._drag_velocity_ema_px_s = 0.0
        self._drag_moved_since_last_tick = False
        self._drag_tier_rank = 0
        self._last_drag_x: int | None = None
        self._last_drag_timestamp: datetime | None = None
        self._facing_extreme_x: int | None = None
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
        self._drag_velocity_ema_px_s = 0.0
        self._drag_moved_since_last_tick = False
        self._drag_tier_rank = 0
        self._last_drag_x = event.grab_point.x
        self._last_drag_timestamp = event.timestamp
        self._facing_extreme_x = event.grab_point.x
        self._play(DRAGGED_ASSET_ID)

    def on_drag_moved(self, event: DragMoved) -> None:
        """D-18: swing-intensity signal — *current* horizontal cursor speed
        (D-19: no longer a sticky peak, see the module-level comment on
        SWING_ASSET_ID). Horizontal-only, not total displacement:
        SWING_ASSET_ID's art is a left-right pendulum swing, so only real
        left-right motion should be able to trigger it (live-test
        2026-07-16). The raw per-event speed is smoothed via an EMA
        before feeding the tier threshold — see DRAG_VELOCITY_EMA_ALPHA
        (live-test 2026-07-20: an unsmoothed single-sample spike made
        SWING nearly unreachable). Also updates facing live (tracked
        against a trailing extremum with hysteresis, see
        FACING_DRAG_FLIP_THRESHOLD_PX) rather than only at drop, so a
        directional pose actually follows the current swing direction."""
        self._drag_moved_since_last_tick = True
        if self._facing_extreme_x is not None:
            if self._facing is Facing.RIGHT:
                self._facing_extreme_x = max(self._facing_extreme_x, event.point.x)
                pullback = self._facing_extreme_x - event.point.x
                flip_to = Facing.LEFT
            else:
                self._facing_extreme_x = min(self._facing_extreme_x, event.point.x)
                pullback = event.point.x - self._facing_extreme_x
                flip_to = Facing.RIGHT
            if pullback > FACING_DRAG_FLIP_THRESHOLD_PX:
                self._facing = flip_to
                self._facing_extreme_x = event.point.x
                if self._drag_tier_rank > 0:
                    self._play(DRAG_TIER_ASSETS[self._drag_tier_rank])
        if self._last_drag_timestamp is not None and self._last_drag_x is not None:
            dt = (event.timestamp - self._last_drag_timestamp).total_seconds()
            if dt > DRAG_VELOCITY_MIN_DT_S:
                instantaneous = abs(event.point.x - self._last_drag_x) / dt
                self._drag_velocity_ema_px_s = (
                    DRAG_VELOCITY_EMA_ALPHA * instantaneous
                    + (1 - DRAG_VELOCITY_EMA_ALPHA) * self._drag_velocity_ema_px_s
                )
                # Only advance the reference once it's actually been used —
                # otherwise a burst of sub-threshold-dt events would keep
                # resetting it and never accumulate enough real time.
                self._last_drag_x = event.point.x
                self._last_drag_timestamp = event.timestamp
        self._update_drag_tier()

    def on_fall_started(self) -> None:
        """Real gravity drop begins (D-15/D-16): one of FALL_START_REACTIONS
        (D-19: picked at random each time), looped for the rest of the
        fall — live-test 2026-07-20: playing it once and then reverting
        to DRAGGED_ASSET_ID mid-air (the original D-16 behaviour) read as
        randomly switching poses partway down, especially with
        FALL_ASSET_ID's much shorter runtime than STARTLE_ASSET_ID's.
        Ends only at DragEnded, which plays LANDING_ASSET_ID regardless
        of what's currently looping."""
        self._reset_front_sequence()
        self._current_fall_reaction = self._random_choice(FALL_START_REACTIONS)
        self._play(self._current_fall_reaction, loop_override=True)

    def on_animation_finished(self, event: AnimationFinished) -> None:
        if event.animation_id == FRONT_ENTER_ASSET_ID and self._front_state == "entering":
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
        accumulates how long the current drag has been held.

        D-19: also the only place SWING's velocity signal can go back
        down. No DragMoved fires while the cursor is genuinely
        stationary, so on_drag_moved alone can never detect "stopped" —
        if a tick sees no movement since the *previous* tick, the
        velocity reading is cleared outright (live-test wanted SWING to
        end "immediately" once motion stops; with only a ~1 Hz heartbeat
        to check on, detection lands within one full silent tick, i.e.
        up to ~2 ticks after the last real movement in the worst case —
        as fast as this mechanism can go)."""
        if self._front_state == "holding":
            self._front_hold_remaining -= event.dt_seconds
            if self._front_hold_remaining <= 0.0:
                self._begin_front_leave()
        if self._grab_x is not None:
            self._drag_hold_seconds += event.dt_seconds
            if not self._drag_moved_since_last_tick:
                self._drag_velocity_ema_px_s = 0.0
            self._drag_moved_since_last_tick = False
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
        """D-18/D-19: recompute the drag tier and switch the dangle loop
        if it changed. ANNOYED (rank 2) is a ceiling — once
        DRAG_HOLD_ANNOYED_SECONDS of total drag time has passed, it's
        sticky for the rest of the drag. Below that ceiling, SWING
        (rank 1) vs. DRAGGED (rank 0) is fully reactive to *current*
        velocity — it can step back down as freely as it steps up,
        by design (live-test 2026-07-20)."""
        if self._drag_hold_seconds >= DRAG_HOLD_ANNOYED_SECONDS:
            rank = 2
        else:
            rank = 1 if self._drag_velocity_ema_px_s >= DRAG_SWING_VELOCITY_PX_S else 0
        if rank != self._drag_tier_rank:
            self._drag_tier_rank = rank
            self._play(DRAG_TIER_ASSETS[rank])

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
