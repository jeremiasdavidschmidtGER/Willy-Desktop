"""A-07 window drag simulation and position-persistence wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap

from willy.app.bus import SyncEventBus
from willy.app.wiring import WillyApp
from willy.contracts import DragEnded, DragStarted, Facing, MouseButton, ScreenPoint, WillyClicked
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
        bus.subscribe(WillyClicked, events.append)
        window = WillyWindow(sprite(), bus=bus, clock=fake_clock)
        qtbot.addWidget(window)
        window.show_without_activating()
        return window, events

    def test_press_move_release_drags_then_falls_to_floor(self, rig, qtbot, fake_clock):
        window, events = rig
        start_x = window.x()
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseMove(window, QPoint(45, 25))  # well past the 4 px threshold
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(45, 25))
        # Release does not end the interaction: Willy falls first (D-15).
        assert [type(event).__name__ for event in events] == ["DragStarted"]
        assert not window.dragging
        # grab offset kept horizontally: local (5,5) → (45,25) is +40 in x
        assert window.x() - start_x == 40
        for _ in range(400):  # step gravity until impact
            if not window.falling:
                break
            fake_clock.advance(0.033)
            window.step_fall()
        assert not window.falling
        assert [type(event).__name__ for event in events] == ["DragStarted", "DragEnded"]
        assert window.y() == window.floor_y()
        assert events[1].drop_point.x == window.x()
        assert events[1].drop_point.y == window.floor_y()

    def test_click_without_move_is_not_a_drag(self, rig, qtbot):
        window, events = rig
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(6, 5))
        # below threshold: no drag events, but a click is published (A-08)
        assert [type(event).__name__ for event in events] == ["WillyClicked"]
        assert events[0].button is MouseButton.LEFT
        assert events[0].clicks_in_last_10s == 1

    def test_repeated_clicks_roll_up_the_10s_count(self, rig, qtbot):
        window, events = rig
        for _ in range(3):
            qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
            qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        assert [event.clicks_in_last_10s for event in events] == [1, 2, 3]

    def test_click_count_ages_out_after_10s(self, rig, qtbot, fake_clock):
        window, events = rig
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        fake_clock.advance(10.1)
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        assert events[-1].clicks_in_last_10s == 1

    def test_right_click_publishes_reserved_event_without_dragging(self, rig, qtbot):
        window, events = rig
        qtbot.mousePress(window, Qt.MouseButton.RightButton, pos=QPoint(5, 5))
        qtbot.mouseRelease(window, Qt.MouseButton.RightButton, pos=QPoint(5, 5))
        assert [type(event).__name__ for event in events] == ["WillyClicked"]
        assert events[0].button is MouseButton.RIGHT
        assert not window.dragging

    def test_window_without_bus_still_drags(self, qtbot):
        window = WillyWindow(sprite())  # A-03 construction stays valid
        qtbot.addWidget(window)
        window.show_without_activating()
        qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        qtbot.mouseMove(window, QPoint(30, 30))
        qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
        assert not window.dragging  # no crash, no events, movement works
        # no clock to step a fall with → lands instantly on the floor
        assert window.y() == window.floor_y()


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
        # D-15: x restores exactly (within 1 px criterion); y is the floor.
        assert restarted.window.x() == 321
        assert restarted.window.y() == restarted.window.floor_y()
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
        assert restarted.window.x() == 77
        assert restarted.window.y() == restarted.window.floor_y()  # D-15

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
