"""D-16: startle reaction (willy_surprised) at the start of a real fall,
driven end-to-end through WillyApp with real art and real gravity."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt

from willy.app.wiring import WillyApp

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"


@pytest.fixture
def app(qtbot, fake_clock):
    willy_app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
    qtbot.addWidget(willy_app.window)
    willy_app.start()
    # Far above the screen: guarantees a fall long enough to observe the
    # mid-air startle-to-dangle transition, regardless of virtual screen size.
    willy_app.window.move(200, -5000)
    return willy_app


def drag_release(app, qtbot):
    qtbot.mousePress(app.window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    qtbot.mouseMove(app.window, QPoint(25, 15))
    qtbot.mouseRelease(app.window, Qt.MouseButton.LeftButton, pos=QPoint(25, 15))


def settle(app, fake_clock, max_steps=2000):
    for _ in range(max_steps):
        if not app.window.falling:
            return
        fake_clock.advance(0.033)
        app.render_tick()


def test_release_plays_startle_not_dragged(app, qtbot):
    drag_release(app, qtbot)
    assert app.window.falling
    assert app.controller.current_animation_id == "willy_surprised"


def test_long_fall_resumes_dangling_after_startle_finishes(app, qtbot, fake_clock):
    drag_release(app, qtbot)
    fake_clock.advance(1.3)  # past willy_surprised's 1232 ms, still falling
    app.render_tick()
    assert app.window.falling  # confirm the fall is genuinely still ongoing
    assert app.controller.current_animation_id == "willy_dragged"


def test_eventually_lands_after_startle_and_dangle(app, qtbot, fake_clock):
    drag_release(app, qtbot)
    settle(app, fake_clock)
    assert not app.window.falling
    assert app.window.y() == app.window.floor_y()
    fake_clock.advance(1.0)
    app.render_tick()
    assert app.controller.current_animation_id in ("willy_drop_landing", "willy_idle")


def test_short_drop_near_floor_skips_straight_to_landing(qtbot, fake_clock):
    # Released right at the floor: _begin_fall() lands instantly, so the
    # startle reaction never gets a chance to play (nothing to interrupt).
    willy_app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
    qtbot.addWidget(willy_app.window)
    willy_app.start()
    willy_app.window.move(200, willy_app.window.floor_y())
    drag_release(willy_app, qtbot)
    assert not willy_app.window.falling
    assert willy_app.controller.current_animation_id == "willy_drop_landing"
