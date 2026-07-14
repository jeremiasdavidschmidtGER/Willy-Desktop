"""D-15: gravity fall to the ground line after drag release."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap

from willy.app.bus import SyncEventBus
from willy.contracts import DragEnded
from willy.ui.window.willy_window import WillyWindow


def sprite() -> QPixmap:
    pixmap = QPixmap(32, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


@pytest.fixture
def rig(qtbot, fake_clock):
    bus = SyncEventBus()
    drag_ended: list[DragEnded] = []
    bus.subscribe(DragEnded, drag_ended.append)
    window = WillyWindow(sprite(), bus=bus, clock=fake_clock)
    qtbot.addWidget(window)
    window.show_without_activating()
    window.move(50, 0)  # high above the floor
    return window, drag_ended


def drag_and_release(window, qtbot):
    qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    qtbot.mouseMove(window, QPoint(25, 15))
    qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(25, 15))


def settle(window, clock, max_steps=600):
    for _ in range(max_steps):
        if not window.falling:
            return
        clock.advance(0.033)
        window.step_fall()


def test_release_starts_fall_not_drag_ended(rig, qtbot):
    window, drag_ended = rig
    drag_and_release(window, qtbot)
    assert window.falling
    assert drag_ended == []


def test_fall_accelerates_and_lands_on_floor(rig, qtbot, fake_clock):
    window, drag_ended = rig
    drag_and_release(window, qtbot)
    y0 = window.y()
    fake_clock.advance(0.1)
    window.step_fall()
    first_step = window.y() - y0
    fake_clock.advance(0.1)
    window.step_fall()
    second_step = window.y() - y0 - first_step
    assert second_step > first_step > 0  # gravity accelerates
    settle(window, fake_clock)
    assert window.y() == window.floor_y()
    assert len(drag_ended) == 1
    assert drag_ended[0].drop_point.y == window.floor_y()


def test_midair_grab_cancels_fall(rig, qtbot, fake_clock):
    window, drag_ended = rig
    drag_and_release(window, qtbot)
    fake_clock.advance(0.1)
    window.step_fall()
    assert window.falling
    qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    assert not window.falling  # caught mid-air
    assert drag_ended == []
    qtbot.mouseMove(window, QPoint(40, 20))
    qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(40, 20))
    settle(window, fake_clock)
    assert len(drag_ended) == 1  # exactly one landing for the whole episode


def test_release_at_floor_lands_instantly(rig, qtbot, fake_clock):
    window, drag_ended = rig
    window.move(50, window.floor_y())
    qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    qtbot.mouseMove(window, QPoint(25, 5))  # horizontal drag along the floor
    window.move(window.x(), window.floor_y())  # keep him on the line
    qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(25, 5))
    assert not window.falling
    assert len(drag_ended) == 1  # no fall needed: immediate impact


def test_snap_to_floor(rig):
    window, _ = rig
    window.move(123, 7)
    window.snap_to_floor()
    assert window.x() == 123
    assert window.y() == window.floor_y()


def test_step_fall_is_noop_when_not_falling(rig, fake_clock):
    window, drag_ended = rig
    position = window.pos()
    fake_clock.advance(1.0)
    window.step_fall()
    assert window.pos() == position
    assert drag_ended == []
