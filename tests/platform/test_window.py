from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from willy.contracts import ScreenPoint
from willy.ui.window.willy_window import WillyWindow


def sprite(width: int = 32, height: int = 24) -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


@pytest.fixture
def window(qtbot):
    w = WillyWindow(sprite())
    qtbot.addWidget(w)
    return w


def test_required_window_flags(window):
    flags = window.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.Tool  # no taskbar entry
    assert flags & Qt.WindowType.WindowStaysOnTopHint


def test_required_attributes(window):
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)


def test_sized_to_sprite(window):
    assert (window.width(), window.height()) == (32, 24)
    assert window.minimumSize() == window.maximumSize()  # fixed


def test_null_sprite_rejected(qtbot):
    with pytest.raises(ValueError):
        WillyWindow(QPixmap())


def test_set_pixmap_resizes_window(window):
    window.set_pixmap(sprite(64, 48))
    assert (window.width(), window.height()) == (64, 48)


def test_set_pixmap_rejects_null(window):
    with pytest.raises(ValueError):
        window.set_pixmap(QPixmap())


def test_set_window_position_moves(window):
    window.set_window_position(ScreenPoint(x=123, y=45))
    assert (window.x(), window.y()) == (123, 45)


def test_set_visibility_toggles(window):
    window.show_without_activating()
    assert window.isVisible()
    window.set_visibility(False)
    assert not window.isVisible()
    window.set_visibility(True)
    assert window.isVisible()


def test_always_on_top_toggle_preserves_visibility(window):
    window.show_without_activating()
    window.set_always_on_top(False)
    assert not window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert window.isVisible()  # flag change must not leave Willy hidden
    window.set_always_on_top(True)
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert window.isVisible()
