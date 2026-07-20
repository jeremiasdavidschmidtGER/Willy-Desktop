from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from willy.contracts import (
    AnimationFinished,
    AnimationPriority,
    DragEnded,
    DragMoved,
    DragStarted,
    Facing,
    MouseButton,
    ScreenPoint,
    TickElapsed,
    WillyClicked,
)
from willy.core import InteractionController
from willy.core.interaction import (
    ANNOYED_DRAG_ASSET_ID,
    DRAG_HOLD_ANNOYED_SECONDS,
    DRAG_SWING_VELOCITY_PX_S,
    FACING_DRAG_FLIP_THRESHOLD_PX,
    FRONT_ENTER_ASSET_ID,
    FRONT_HOLD_SECONDS,
    FRONT_IDLE_ASSET_ID,
    FRONT_LEAVE_ASSET_ID,
    SWING_ASSET_ID,
)

TS = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def rig():
    commands = []
    dirty_marks = []
    controller = InteractionController(
        dispatch=commands.append, state_dirty=lambda: dirty_marks.append(True)
    )
    return controller, commands, dirty_marks


def drag(controller, grab_x=100, drop_x=100, drop_y=50):
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=grab_x, y=50)))
    controller.on_drag_ended(DragEnded(timestamp=TS, drop_point=ScreenPoint(x=drop_x, y=drop_y)))


def test_drag_started_plays_dragged_pose_at_reaction(rig):
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=10, y=20)))
    assert len(commands) == 1
    assert commands[0].animation_id == "willy_dragged"
    assert commands[0].priority is AnimationPriority.REACTION
    assert commands[0].facing is Facing.RIGHT


def test_drag_ended_plays_landing_and_marks_dirty(rig):
    controller, commands, dirty = rig
    drag(controller)
    assert [command.animation_id for command in commands] == [
        "willy_dragged",
        "willy_drop_landing",
    ]
    assert dirty == [True]


def test_facing_flips_toward_drag_direction(rig):
    controller, commands, _ = rig
    drag(controller, grab_x=100, drop_x=40)  # dragged left
    assert controller.facing is Facing.LEFT
    assert commands[-1].facing is Facing.LEFT
    drag(controller, grab_x=100, drop_x=180)  # dragged right
    assert controller.facing is Facing.RIGHT
    assert commands[-1].facing is Facing.RIGHT


def test_tiny_horizontal_drift_keeps_facing(rig):
    controller, _, _ = rig
    drag(controller, grab_x=100, drop_x=40)
    assert controller.facing is Facing.LEFT
    drag(controller, grab_x=100, drop_x=101)  # 1 px: below threshold
    assert controller.facing is Facing.LEFT


def test_vertical_drag_keeps_facing(rig):
    controller, _, _ = rig
    drag(controller, grab_x=100, drop_x=100, drop_y=400)
    assert controller.facing is Facing.RIGHT


def test_initial_facing_restored_from_persistence(rig):
    commands = []
    controller = InteractionController(
        dispatch=commands.append, state_dirty=lambda: None, initial_facing=Facing.LEFT
    )
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    assert commands[0].facing is Facing.LEFT


def test_drag_ended_without_started_still_lands_safely(rig):
    controller, commands, dirty = rig
    controller.on_drag_ended(DragEnded(timestamp=TS, drop_point=ScreenPoint(x=5, y=5)))
    assert commands[-1].animation_id == "willy_drop_landing"
    assert controller.facing is Facing.RIGHT  # no grab point: facing kept
    assert dirty == [True]


# --- D-18: escalating drag tiers (horizontal swing-intensity + hold-duration) ---


def move(controller, x, y, at_seconds):
    """at_seconds is an absolute offset from TS (drag-clock time), not a
    delta from the previous move — matches how DragMoved.timestamp works."""
    controller.on_drag_moved(
        DragMoved(timestamp=TS + timedelta(seconds=at_seconds), point=ScreenPoint(x=x, y=y))
    )


def sustained_horizontal_move(controller, instantaneous_px_s, dt=0.05, steps=20, start_at=1.0):
    """Simulate steady horizontal dragging at a constant instantaneous
    speed for several samples, letting the velocity EMA converge close to
    `instantaneous_px_s` — matches a real sustained swing, unlike a single
    huge jump (which the EMA deliberately dampens, live-test 2026-07-20)."""
    x = 0.0
    t = start_at
    step_px = instantaneous_px_s * dt
    for _ in range(steps):
        x += step_px
        t += dt
        move(controller, x=x, y=0, at_seconds=t)


def test_fast_horizontal_swing_escalates_to_swing_tier(rig):
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    # Sustained horizontal speed above the swing threshold, given enough
    # samples for the EMA to converge.
    sustained_horizontal_move(controller, DRAG_SWING_VELOCITY_PX_S * 1.5)
    assert commands[-1].animation_id == SWING_ASSET_ID


def test_slow_moves_do_not_escalate(rig):
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    move(controller, x=1, y=0, at_seconds=1.0)  # 1 px/s: far below any threshold
    assert commands[-1].animation_id == "willy_dragged"


def test_fast_vertical_only_movement_does_not_escalate_swing(rig):
    """SWING_ASSET_ID's art is a left-right pendulum swing — a fast
    *vertical* shake must not trigger it, only real horizontal motion
    (live-test 2026-07-16)."""
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    fast_px = DRAG_SWING_VELOCITY_PX_S * 2
    move(controller, x=0, y=fast_px, at_seconds=1.0)  # same x, big y jump
    assert commands[-1].animation_id == "willy_dragged"


def test_long_motionless_hold_escalates_straight_to_annoyed(rig):
    """A hold alone can only ever reach ANNOYED, never SWING — SWING's art
    depicts real dragging motion, so it must never fire from an idle
    hold (live-test 2026-07-16)."""
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    controller.on_tick_elapsed(TickElapsed(timestamp=TS, dt_seconds=DRAG_HOLD_ANNOYED_SECONDS))
    assert commands[-1].animation_id == ANNOYED_DRAG_ASSET_ID


def test_no_amount_of_velocity_reaches_annoyed(rig):
    """Fully asymmetric by live-test design (2026-07-20): velocity can
    only ever reach SWING, never ANNOYED — an earlier version let
    sustained fast velocity also reach ANNOYED, which converged there
    almost immediately during a real swing. Only a motionless hold
    reaches ANNOYED now."""
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    sustained_horizontal_move(controller, DRAG_SWING_VELOCITY_PX_S * 10, steps=60)
    assert commands[-1].animation_id == SWING_ASSET_ID
    assert ANNOYED_DRAG_ASSET_ID not in [c.animation_id for c in commands]


def test_drag_tier_is_sticky_and_does_not_step_back_down(rig):
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    sustained_horizontal_move(controller, DRAG_SWING_VELOCITY_PX_S * 1.5)
    assert commands[-1].animation_id == SWING_ASSET_ID
    dispatch_count = len(commands)
    # A subsequent slow move must not un-escalate the tier or re-dispatch
    # the same clip, even though the EMA itself will start decaying back
    # down — the tier tracks the *peak* smoothed value, not the current one.
    move(controller, x=1, y=0, at_seconds=10.0)
    assert commands[-1].animation_id == SWING_ASSET_ID
    assert len(commands) == dispatch_count  # no re-dispatch


def test_new_drag_resets_the_tier(rig):
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    controller.on_tick_elapsed(TickElapsed(timestamp=TS, dt_seconds=DRAG_HOLD_ANNOYED_SECONDS))
    assert commands[-1].animation_id == ANNOYED_DRAG_ASSET_ID
    controller.on_drag_ended(DragEnded(timestamp=TS, drop_point=ScreenPoint(x=0, y=0)))
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    assert commands[-1].animation_id == "willy_dragged"  # back to the calm tier


def test_ticks_only_accumulate_hold_time_while_dragging(rig):
    controller, commands, _ = rig
    controller.on_tick_elapsed(TickElapsed(timestamp=TS, dt_seconds=DRAG_HOLD_ANNOYED_SECONDS))
    assert commands == []  # not dragging: no drag-tier state to escalate


# --- D-19: facing updates live during a drag, not just at drop ---


def test_facing_flips_mid_drag_and_redisplays_the_active_tier(rig):
    """SWING_ASSET_ID's art is directional — facing must follow the
    actual swing direction live, not stay stuck at whatever it was
    before the drag started (live-test 2026-07-20)."""
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    assert controller.facing is Facing.RIGHT  # default rig facing
    sustained_horizontal_move(controller, DRAG_SWING_VELOCITY_PX_S * 1.5)
    assert commands[-1].animation_id == SWING_ASSET_ID
    dispatch_count = len(commands)
    # Now swing back past the flip threshold, the opposite direction.
    move(controller, x=-(FACING_DRAG_FLIP_THRESHOLD_PX + 5), y=0, at_seconds=100.0)
    assert controller.facing is Facing.LEFT
    assert commands[-1].animation_id == SWING_ASSET_ID  # re-dispatched, same tier
    assert commands[-1].facing is Facing.LEFT
    assert len(commands) == dispatch_count + 1  # exactly one re-dispatch for the flip


def test_small_jitter_does_not_flip_facing_mid_drag(rig):
    controller, commands, _ = rig
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    # Flip to LEFT first (default rig facing is RIGHT), so the jitter
    # check below is a real "does it flip back" test, not a no-op.
    move(controller, x=-(FACING_DRAG_FLIP_THRESHOLD_PX + 5), y=0, at_seconds=1.0)
    assert controller.facing is Facing.LEFT
    # Small back-and-forth jitter within the band around the new
    # reference point must not flip facing back to RIGHT.
    move(controller, x=-(FACING_DRAG_FLIP_THRESHOLD_PX + 5) + 5, y=0, at_seconds=1.1)
    assert controller.facing is Facing.LEFT
    move(controller, x=-(FACING_DRAG_FLIP_THRESHOLD_PX + 5) - 5, y=0, at_seconds=1.2)
    assert controller.facing is Facing.LEFT


# --- D-16: startle reaction at the start of a real gravity fall ---


def test_fall_started_plays_startle_pose(rig):
    controller, commands, _ = rig
    controller.on_fall_started()
    assert commands[-1].animation_id == "willy_surprised"
    assert commands[-1].priority is AnimationPriority.REACTION


def test_fall_started_uses_current_facing(rig):
    controller, commands, _ = rig
    drag(controller, grab_x=100, drop_x=40)  # flips to LEFT
    controller.on_fall_started()
    assert commands[-1].facing is Facing.LEFT


def test_startle_finished_while_still_falling_resumes_dragged():
    commands = []
    controller = InteractionController(
        dispatch=commands.append, state_dirty=lambda: None, is_falling=lambda: True
    )
    controller.on_fall_started()
    controller.on_animation_finished(
        AnimationFinished(timestamp=TS, animation_id="willy_surprised")
    )
    assert [command.animation_id for command in commands] == ["willy_surprised", "willy_dragged"]


def test_startle_finished_after_landing_does_not_resume_dragged():
    commands = []
    controller = InteractionController(
        dispatch=commands.append, state_dirty=lambda: None, is_falling=lambda: False
    )
    controller.on_fall_started()
    controller.on_animation_finished(
        AnimationFinished(timestamp=TS, animation_id="willy_surprised")
    )
    assert [command.animation_id for command in commands] == [
        "willy_surprised"
    ]  # no extra dispatch


def test_unrelated_animation_finished_is_ignored(rig):
    controller, commands, _ = rig
    controller.on_animation_finished(AnimationFinished(timestamp=TS, animation_id="willy_walk"))
    assert commands == []


# --- A-08: click reactions and annoyance escalation ---


def click(controller, button=MouseButton.LEFT):
    controller.on_willy_clicked(WillyClicked(timestamp=TS, button=button, clicks_in_last_10s=1))


def tick(controller, dt_seconds):
    controller.on_tick_elapsed(TickElapsed(timestamp=TS, dt_seconds=dt_seconds))


def finish(controller, animation_id):
    controller.on_animation_finished(AnimationFinished(timestamp=TS, animation_id=animation_id))


def reach_annoyed_tier(controller):
    """3 clicks in quick succession: tier 1 (entering) never gets a
    chance to finish before annoyance escalates past it, so it turns
    away and the pending "annoyed" reaction plays once leave finishes.
    Leaves front_state at "none" and annoyance at 3."""
    click(controller)  # 1: tier 1, entering
    click(controller)  # 2: tier 1, still entering (refresh only)
    click(controller)  # 3: annoyed tier -> turns away first
    finish(controller, FRONT_LEAVE_ASSET_ID)  # leave finishes -> annoyed plays


def test_first_click_plays_front_enter_at_interaction_priority(rig):
    controller, commands, _ = rig
    click(controller)
    assert commands[-1].animation_id == FRONT_ENTER_ASSET_ID
    assert commands[-1].priority is AnimationPriority.INTERACTION
    assert commands[-1].facing is Facing.RIGHT
    # Forced one-shot so this stage can always hand off to the next one
    # (here: the enter-finished handler) rather than get stuck looping.
    assert commands[-1].loop_override is False


def test_enter_finishing_starts_the_looping_front_hold(rig):
    controller, commands, _ = rig
    click(controller)
    finish(controller, FRONT_ENTER_ASSET_ID)
    assert commands[-1].animation_id == FRONT_IDLE_ASSET_ID
    assert commands[-1].priority is AnimationPriority.INTERACTION
    assert commands[-1].loop_override is True  # holds until the timer (or an escalation) ends it


def test_repeat_click_while_facing_camera_extends_hold_without_redispatch(rig):
    controller, commands, _ = rig
    click(controller)
    finish(controller, FRONT_ENTER_ASSET_ID)
    dispatched_before = len(commands)
    click(controller)  # still tier 1: refreshes the hold, doesn't replay enter
    assert len(commands) == dispatched_before
    tick(controller, FRONT_HOLD_SECONDS - 0.5)  # would have expired without the refresh
    assert len(commands) == dispatched_before  # still holding: no leave yet


def test_hold_expires_and_turns_away(rig):
    controller, commands, _ = rig
    click(controller)
    finish(controller, FRONT_ENTER_ASSET_ID)
    tick(controller, FRONT_HOLD_SECONDS + 0.1)
    assert commands[-1].animation_id == FRONT_LEAVE_ASSET_ID
    assert commands[-1].loop_override is False


def test_leave_finishing_with_nothing_pending_dispatches_nothing_more(rig):
    controller, commands, _ = rig
    click(controller)
    finish(controller, FRONT_ENTER_ASSET_ID)
    tick(controller, FRONT_HOLD_SECONDS + 0.1)
    dispatched_before = len(commands)
    finish(controller, FRONT_LEAVE_ASSET_ID)
    assert len(commands) == dispatched_before  # nothing queued: the clip just ends


def test_escalation_while_facing_camera_turns_away_before_reacting(rig):
    """The user-reported "out of perspective" case: annoyance escalating
    past tier 1 while still mid front-facing sequence must not jump-cut
    straight to the side-view reaction."""
    controller, commands, _ = rig
    click(controller)  # tier 1: entering, never finished
    for _ in range(2):
        click(controller)  # annoyance -> 3: tier is now "annoyed"
    assert commands[-1].animation_id == FRONT_LEAVE_ASSET_ID
    finish(controller, FRONT_LEAVE_ASSET_ID)
    assert commands[-1].animation_id == "willy_annoyed"


def test_direct_dispatch_once_annoyed_tier_reached_and_not_facing_camera(rig):
    controller, commands, _ = rig
    reach_annoyed_tier(controller)
    assert commands[-1].animation_id == "willy_annoyed"
    assert controller.annoyance == 3.0
    click(controller)  # 4: still "annoyed" tier, front_state is "none" -> direct dispatch
    assert commands[-1].animation_id == "willy_annoyed"


def test_sixth_click_escalates_to_smug(rig):
    controller, commands, _ = rig
    reach_annoyed_tier(controller)  # clicks 1-3
    click(controller)  # 4: still "annoyed" tier, direct dispatch
    click(controller)  # 5: still "annoyed" tier, direct dispatch
    click(controller)  # 6: "smug" tier, direct dispatch
    assert commands[-1].animation_id == "willy_smug"


def test_right_click_never_reacts(rig):
    controller, commands, _ = rig
    click(controller, button=MouseButton.RIGHT)
    assert commands == []
    assert controller.annoyance == 0.0


def test_annoyance_decays_with_fake_clock(rig):
    controller, _, _ = rig
    click(controller)
    assert controller.annoyance == 1.0
    tick(controller, 1.0)
    assert controller.annoyance == pytest.approx(0.7)  # 0.3/s default decay
    tick(controller, 10.0)
    assert controller.annoyance == 0.0


def test_annoyance_resets_after_quiet_period(rig):
    controller, commands, _ = rig
    reach_annoyed_tier(controller)
    assert commands[-1].animation_id == "willy_annoyed"
    tick(controller, 100.0)  # long quiet period: fully decayed
    assert controller.annoyance == 0.0
    click(controller)
    assert commands[-1].animation_id == FRONT_ENTER_ASSET_ID  # back to tier 1, freshly dispatched


def test_click_spam_causes_no_crash_and_annoyance_stays_bounded(rig):
    controller, _, _ = rig
    for _ in range(300):  # 10/s for 30s, per acceptance criteria
        click(controller)
    assert controller.annoyance > 0.0  # capped, but bounded — no unbounded growth
    tick(controller, 1000.0)  # eventually settles regardless of spam size
    assert controller.annoyance == 0.0


def test_click_reaction_dispatched_below_drag_priority(rig):
    """Reactions use INTERACTION priority so a real drag (REACTION,
    dispatched separately by the animation controller) always outranks
    them — this control only proves the priority contract at the command
    level; the animation controller enforces the actual arbitration."""
    controller, commands, _ = rig
    click(controller)
    assert commands[-1].priority.value < AnimationPriority.REACTION.value


def test_drag_started_resets_front_sequence(rig):
    controller, commands, _ = rig
    click(controller)  # tier 1: entering, never finished
    controller.on_drag_started(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=10, y=20)))
    assert commands[-1].animation_id == "willy_dragged"
    # A tick that would have expired the (now-abandoned) hold must not
    # spuriously play the turn-away clip on top of the drag. Also below
    # DRAG_HOLD_ANNOYED_SECONDS, so no D-18 drag-tier escalation either.
    tick(controller, FRONT_HOLD_SECONDS + 0.1)
    assert commands[-1].animation_id == "willy_dragged"


def test_fall_started_resets_front_sequence(rig):
    controller, commands, _ = rig
    click(controller)  # tier 1: entering, never finished
    controller.on_fall_started()
    assert commands[-1].animation_id == "willy_surprised"
    tick(controller, FRONT_HOLD_SECONDS + 0.1)
    assert commands[-1].animation_id == "willy_surprised"
