from __future__ import annotations

import pytest

from willy.animation.controller import WillyAnimationController
from willy.animation.library import AssetLibrary
from willy.app.bus import SyncEventBus
from willy.assets_runtime.pixmap_cache import PixmapCache
from willy.contracts import AnimationFinished, AnimationPriority, Facing, PlayAnimation

# All test clips: 2 frames x 100 ms.
CLIPS = [
    ("willy_idle", "IDLE", True),
    ("willy_walk", "AMBIENT", True),
    ("willy_walk_b", "AMBIENT", True),
    ("willy_react", "REACTION", False),
    ("willy_blink", "IDLE", False),
]


@pytest.fixture
def rig(tmp_path, clip_writer, manifest_factory, fake_clock):
    for asset_id, priority, loop in CLIPS:
        clip_writer(
            tmp_path,
            manifest_factory(
                asset_id=asset_id,
                priority=priority,
                loop=loop,
                frames=[
                    {"image": "f0.png", "duration_ms": 100},
                    {"image": "f1.png", "duration_ms": 100},
                ],
            ),
        )
    library = AssetLibrary(tmp_path, strict=True)
    library.load()
    bus = SyncEventBus()
    events: list[AnimationFinished] = []
    bus.subscribe(AnimationFinished, events.append)
    controller = WillyAnimationController(
        cache=PixmapCache(library), library=library, bus=bus, clock=fake_clock
    )
    return controller, fake_clock, events, bus


def play(controller, asset_id, priority, facing=Facing.RIGHT, loop_override=None):
    controller.play(
        PlayAnimation(
            animation_id=asset_id, facing=facing, priority=priority, loop_override=loop_override
        )
    )


def test_starts_on_looping_idle(rig):
    controller, clock, _, _ = rig
    assert controller.current_animation_id == "willy_idle"
    assert controller.current_facing is Facing.RIGHT
    first = controller.tick()
    clock.advance(0.1)
    second = controller.tick()
    assert second is not first  # frame advanced
    clock.advance(0.1)
    assert controller.tick() is first  # looped back, cache identity


def test_higher_priority_interrupts_lower(rig):
    controller, _, _, _ = rig
    play(controller, "willy_walk", AnimationPriority.AMBIENT)
    play(controller, "willy_react", AnimationPriority.REACTION)
    assert controller.current_animation_id == "willy_react"


def test_lower_priority_is_ignored(rig):
    controller, _, _, _ = rig
    play(controller, "willy_react", AnimationPriority.REACTION)
    play(controller, "willy_walk", AnimationPriority.AMBIENT)
    assert controller.current_animation_id == "willy_react"


def test_equal_priority_replaces(rig):
    controller, _, _, _ = rig
    play(controller, "willy_walk", AnimationPriority.AMBIENT)
    play(controller, "willy_walk_b", AnimationPriority.AMBIENT)
    assert controller.current_animation_id == "willy_walk_b"


def test_non_loop_end_publishes_finished_once_and_returns_to_idle(rig):
    controller, clock, events, _ = rig
    play(controller, "willy_react", AnimationPriority.REACTION, facing=Facing.LEFT)
    clock.advance(0.2)  # past the 200 ms clip
    controller.tick()
    assert [event.animation_id for event in events] == ["willy_react"]
    assert controller.current_animation_id == "willy_idle"
    assert controller.current_facing is Facing.LEFT  # facing preserved
    assert controller.current_priority is AnimationPriority.IDLE
    clock.advance(0.05)
    controller.tick()
    assert len(events) == 1  # exactly once


def test_reaction_interrupts_walk_then_idle_resumes(rig):
    controller, clock, events, _ = rig
    play(controller, "willy_walk", AnimationPriority.AMBIENT)
    play(controller, "willy_react", AnimationPriority.REACTION)
    clock.advance(0.2)
    controller.tick()
    assert controller.current_animation_id == "willy_idle"
    assert [event.animation_id for event in events] == ["willy_react"]


def test_finished_handler_play_wins_over_idle(rig):
    controller, clock, events, bus = rig
    bus.subscribe(
        AnimationFinished,
        lambda event: play(controller, "willy_walk", AnimationPriority.AMBIENT),
    )
    play(controller, "willy_react", AnimationPriority.REACTION)
    clock.advance(0.2)
    controller.tick()
    assert controller.current_animation_id == "willy_walk"


def test_pause_freezes_frame_resume_continues_without_jump(rig):
    controller, clock, _, _ = rig
    clock.advance(0.15)  # inside frame 1 of idle
    frozen = controller.tick()
    controller.set_paused(True)
    clock.advance(30.0)
    assert controller.tick() is frozen  # frozen exactly where it paused
    controller.set_paused(False)
    clock.advance(0.049)  # 150+49 = 199 ms → still frame 1
    assert controller.tick() is frozen
    clock.advance(0.002)  # 201 ms → wraps to frame 0
    assert controller.tick() is not frozen


def test_set_paused_is_idempotent(rig):
    controller, clock, _, _ = rig
    controller.set_paused(True)
    controller.set_paused(True)
    controller.set_paused(False)
    controller.set_paused(False)
    assert not controller.paused


def test_loop_override_keeps_non_loop_clip_running(rig):
    controller, clock, events, _ = rig
    play(controller, "willy_react", AnimationPriority.REACTION, loop_override=True)
    clock.advance(0.5)
    controller.tick()
    assert controller.current_animation_id == "willy_react"  # still looping
    assert events == []


def test_loop_override_false_finishes_a_loop_clip(rig):
    controller, clock, events, _ = rig
    play(controller, "willy_walk", AnimationPriority.AMBIENT, loop_override=False)
    clock.advance(0.2)
    controller.tick()
    assert [event.animation_id for event in events] == ["willy_walk"]
    assert controller.current_animation_id == "willy_idle"


def test_facing_is_served_from_cache(rig):
    controller, clock, _, _ = rig
    play(controller, "willy_walk", AnimationPriority.AMBIENT, facing=Facing.LEFT)
    assert controller.current_facing is Facing.LEFT
    assert not controller.tick().isNull()


def test_finished_timestamp_comes_from_clock(rig):
    controller, clock, events, _ = rig
    play(controller, "willy_react", AnimationPriority.REACTION)
    clock.advance(0.2)
    controller.tick()
    assert events[0].timestamp == clock.now()
