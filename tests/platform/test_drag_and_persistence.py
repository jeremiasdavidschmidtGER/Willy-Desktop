"""A-07 window drag simulation and position-persistence wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap

from willy.app.bus import SyncEventBus
from willy.app.wiring import WillyApp
from willy.contracts import DragEnded, DragStarted, Facing, ScreenPoint
from willy.ui.window.willy_window import WillyWindow

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"


def sprite() -> QPixmap:
    pixmap = QPixmap(32, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


class TestWindowDrag:
    @pytest.fixture
    def rig(self, qtbot, fake_clock):
        bus = SyncEventBus()
        events = []
        bus.subscribe(DragStarted, events.append)
        bus.subscribe(DragEnded, events.append)
        window = WillyWindow(sprite(), bus=bus, clock=fake_clock)
        qtbot.addWidget(window)
        window.show_without_activating()
        return window, events

    def test_press_move_release_drags_window_and_publishes(self, rig, qtbot):
        window, events = rig
        start_pos = window.pos()
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseMove(window, QPoint(45, 25))  # well past the 4 px threshold
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(45, 25))
        assert [type(event).__name__ for event in events] == ["DragStarted", "DragEnded"]
        assert window.pos() != start_pos
        # grab offset kept: cursor at widget-local (5,5) grabbed, released at
        # local (45,25) → window moved by the same delta
        delta = window.pos() - start_pos
        assert (delta.x(), delta.y()) == (40, 20)
        assert events[1].drop_point.x == window.x()
        assert not window.dragging

    def test_click_without_move_is_not_a_drag(self, rig, qtbot):
        window, events = rig
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(6, 5))
        assert events == []  # below threshold: no drag events

    def test_window_without_bus_still_drags(self, qtbot):
        window = WillyWindow(sprite())  # A-03 construction stays valid
        qtbot.addWidget(window)
        window.show_without_activating()
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseMove(window, QPoint(30, 30))
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
        assert not window.dragging  # no crash, no events, movement works


class TestPositionPersistenceWiring:
    def make_app(self, tmp_path, clock) -> WillyApp:
        return WillyApp(assets_root=REPO_ASSETS, clock=clock, db_path=tmp_path / "willy.db")

    def test_position_and_facing_survive_restart(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app.window.move(321, 111)
        # drag left so facing flips, then the debounced write fires
        app.bus.publish(
            DragStarted(timestamp=fake_clock.now(), grab_point=ScreenPoint(x=400, y=100))
        )
        app.bus.publish(DragEnded(timestamp=fake_clock.now(), drop_point=ScreenPoint(x=321, y=111)))
        fake_clock.advance(1.5)
        app.render_tick()  # debounce elapsed → flush
        app.shutdown()

        restarted = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(restarted.window)
        restarted.start()
        assert (restarted.window.x(), restarted.window.y()) == (321, 111)  # within 1 px
        assert restarted.interaction.facing is Facing.LEFT
        assert restarted.controller.current_facing is Facing.LEFT

    def test_shutdown_flushes_even_without_drag(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app.window.move(77, 66)
        app.shutdown()  # no debounce wait: forced flush on quit

        restarted = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(restarted.window)
        restarted.start()
        assert (restarted.window.x(), restarted.window.y()) == (77, 66)

    def test_debounce_does_not_write_before_interval(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app._mark_state_dirty()
        fake_clock.advance(0.5)
        app.render_tick()
        assert app._state_writer.dirty  # not yet flushed
        fake_clock.advance(0.6)
        app.render_tick()
        assert not app._state_writer.dirty

    def test_always_on_top_settings_key_is_honoured(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(app.window)
        app._settings_repo.set("window.always_on_top", False)
        app.shutdown()

        restarted = self.make_app(tmp_path, fake_clock)
        qtbot.addWidget(restarted.window)
        assert not restarted.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint

    def test_no_db_path_means_no_persistence(self, qtbot, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app.shutdown()  # must not raise, nothing written anywhere
        assert app._state_writer is None
