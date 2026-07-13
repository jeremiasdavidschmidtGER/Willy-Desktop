from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from willy.app.placeholder import build_placeholder_sprite
from willy.app.router import CommandRouter
from willy.app.wiring import WillyApp, load_sprite
from willy.contracts import (
    AppStarted,
    ScreenPoint,
    SetMuted,
    SetVisibility,
    SetWindowPosition,
    ShutdownRequested,
)


def sprite() -> QPixmap:
    pixmap = QPixmap(32, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


class TestCommandRouter:
    def test_routes_to_registered_sink(self):
        router = CommandRouter()
        received = []
        router.register(SetVisibility, received.append)
        command = SetVisibility(visible=False)
        router.dispatch(command)
        assert received == [command]

    def test_duplicate_registration_rejected(self):
        router = CommandRouter()
        router.register(SetVisibility, lambda c: None)
        with pytest.raises(ValueError):
            router.register(SetVisibility, lambda c: None)

    def test_unrouted_command_raises(self):
        router = CommandRouter()
        with pytest.raises(LookupError):
            router.dispatch(SetMuted(muted=True))


class TestWillyApp:
    @pytest.fixture
    def app(self, qtbot, fake_clock):
        willy_app = WillyApp(sprite=sprite(), clock=fake_clock)
        qtbot.addWidget(willy_app.window)
        return willy_app

    def test_start_shows_window_and_publishes_app_started(self, app, fake_clock):
        events = []
        app.bus.subscribe(AppStarted, events.append)
        app.start()
        assert app.window.isVisible()
        assert events == [AppStarted(timestamp=fake_clock.now())]

    def test_start_places_window_on_a_screen(self, app):
        app.start()
        assert app.window.x() >= 0 or app.window.y() >= 0

    def test_visibility_command_takes_effect(self, app):
        app.start()
        app.router.dispatch(SetVisibility(visible=False))
        assert not app.window.isVisible()
        app.router.dispatch(SetVisibility(visible=True))
        assert app.window.isVisible()

    def test_position_command_takes_effect(self, app):
        app.start()
        app.router.dispatch(SetWindowPosition(point=ScreenPoint(x=77, y=88)))
        assert (app.window.x(), app.window.y()) == (77, 88)

    def test_shutdown_publishes_once(self, app, fake_clock):
        events = []
        app.bus.subscribe(ShutdownRequested, events.append)
        app.shutdown()
        app.shutdown()  # aboutToQuit + explicit call must not double-publish
        assert events == [ShutdownRequested(timestamp=fake_clock.now())]


class TestSprites:
    def test_placeholder_sprite_has_size_and_alpha(self, qtbot):
        pixmap = build_placeholder_sprite()
        assert not pixmap.isNull()
        assert pixmap.width() == 128 and pixmap.height() == 96
        assert pixmap.hasAlphaChannel()

    def test_load_sprite_falls_back_to_placeholder(self, qtbot, tmp_path):
        assert not load_sprite(str(tmp_path / "missing.png")).isNull()
        assert not load_sprite(None).isNull()

    def test_load_sprite_reads_real_png(self, qtbot, tmp_path):
        path = tmp_path / "willy.png"
        build_placeholder_sprite().save(str(path), "PNG")
        loaded = load_sprite(str(path))
        assert (loaded.width(), loaded.height()) == (128, 96)
