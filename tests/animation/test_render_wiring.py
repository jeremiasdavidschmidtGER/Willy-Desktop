"""A-06 paint integration: WillyApp in animated mode over the real assets."""

from __future__ import annotations

import pytest

from willy.app.wiring import WillyApp, default_assets_root
from willy.contracts import AnimationPriority, PlayAnimation, SetPaused


@pytest.fixture
def app(qtbot, fake_clock, repo_assets):
    willy_app = WillyApp(assets_root=repo_assets, clock=fake_clock)
    qtbot.addWidget(willy_app.window)
    return willy_app


def test_default_assets_root_points_at_repo():
    root = default_assets_root()
    assert root is not None
    assert (root / "willy_idle" / "manifest.json").is_file()


def test_animated_mode_starts_on_idle_sized_to_art(app):
    assert app.controller is not None
    assert app.controller.current_animation_id == "willy_idle"
    assert (app.window.width(), app.window.height()) == (90, 84)  # native art size


def test_render_tick_updates_window_pixmap_only_on_change(app, fake_clock):
    first = app.window.pixmap
    app.render_tick()
    assert app.window.pixmap is first  # same frame: no repaint churn
    fake_clock.advance(0.1)  # idle frames are 83 ms
    app.render_tick()
    assert app.window.pixmap is not first


def test_play_animation_routed_to_controller(app):
    app.router.dispatch(
        PlayAnimation(
            animation_id="willy_annoyed",
            facing=app.controller.current_facing,
            priority=AnimationPriority.REACTION,
        )
    )
    assert app.controller.current_animation_id == "willy_annoyed"


def test_set_paused_routed_to_controller(app):
    app.router.dispatch(SetPaused(paused=True))
    assert app.controller.paused
    app.router.dispatch(SetPaused(paused=False))
    assert not app.controller.paused


def test_blink_dispatch_plays_blink_then_idle_resumes(app, fake_clock):
    app._blink()
    assert app.controller.current_animation_id == "willy_idle_blink"
    fake_clock.advance(1.0)  # blink is 166 ms, non-loop
    app.render_tick()
    assert app.controller.current_animation_id == "willy_idle"


def test_static_mode_still_works(qtbot, fake_clock):
    from willy.app.placeholder import build_placeholder_sprite

    willy_app = WillyApp(sprite=build_placeholder_sprite(), clock=fake_clock)
    qtbot.addWidget(willy_app.window)
    assert willy_app.controller is None
    willy_app.render_tick()  # no-op, must not raise


def test_neither_sprite_nor_assets_rejected(fake_clock):
    with pytest.raises(ValueError):
        WillyApp(clock=fake_clock)
