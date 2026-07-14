from __future__ import annotations

from datetime import UTC, datetime

import pytest

from willy.contracts import (
    AnimationPriority,
    DragEnded,
    DragStarted,
    Facing,
    ScreenPoint,
)
from willy.core import InteractionController

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
