"""A-07 acceptance: rapid drag-drop-drag never wedges the animation
state machine — real InteractionController driving the real
WillyAnimationController over the real repo assets."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from willy.animation.controller import WillyAnimationController
from willy.animation.library import AssetLibrary
from willy.app.bus import SyncEventBus
from willy.assets_runtime.pixmap_cache import PixmapCache
from willy.contracts import AnimationFinished, DragEnded, DragStarted, ScreenPoint
from willy.core import InteractionController

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"
TS = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def rig(qapp, fake_clock):
    library = AssetLibrary(REPO_ASSETS, strict=True)
    library.load()
    bus = SyncEventBus()
    animation = WillyAnimationController(
        cache=PixmapCache(library), library=library, bus=bus, clock=fake_clock
    )
    interaction = InteractionController(
        dispatch=lambda command: animation.play(command), state_dirty=lambda: None
    )
    bus.subscribe(DragStarted, interaction.on_drag_started)
    bus.subscribe(DragEnded, interaction.on_drag_ended)
    return bus, animation, fake_clock


def test_drag_shows_dragged_pose_immediately(rig):
    bus, animation, clock = rig
    bus.publish(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    assert animation.current_animation_id == "willy_dragged"
    assert not animation.tick().isNull()  # within one render tick


def test_drop_plays_landing_then_idle(rig):
    bus, animation, clock = rig
    bus.publish(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=0, y=0)))
    bus.publish(DragEnded(timestamp=TS, drop_point=ScreenPoint(x=50, y=0)))
    assert animation.current_animation_id == "willy_drop_landing"
    clock.advance(1.0)  # landing clip is 781 ms, non-loop
    animation.tick()
    assert animation.current_animation_id == "willy_idle"


def test_twenty_rapid_drag_drop_cycles_end_in_idle(rig):
    bus, animation, clock = rig
    finished_events = []
    bus.subscribe(AnimationFinished, finished_events.append)
    x = 0
    for cycle in range(20):
        bus.publish(DragStarted(timestamp=TS, grab_point=ScreenPoint(x=x, y=0)))
        assert animation.current_animation_id == "willy_dragged"
        clock.advance(0.05)  # drop long before the landing clip could end
        animation.tick()
        x += 30 if cycle % 2 == 0 else -30
        bus.publish(DragEnded(timestamp=TS, drop_point=ScreenPoint(x=x, y=0)))
        assert animation.current_animation_id == "willy_drop_landing"
        clock.advance(0.05)
        animation.tick()
    clock.advance(2.0)  # let the final landing finish
    animation.tick()
    assert animation.current_animation_id == "willy_idle"
    assert not animation.tick().isNull()
    # Only the last landing ran to its natural end; interrupted clips
    # must not have produced AnimationFinished noise.
    assert [event.animation_id for event in finished_events] == ["willy_drop_landing"]
