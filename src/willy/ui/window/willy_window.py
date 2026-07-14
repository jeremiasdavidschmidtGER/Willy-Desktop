"""Transparent frameless Willy window (GATE_A_BACKLOG A-03).

Dumb shell only: it shows a pixmap and executes the window commands it is
handed. It never decides anything — no drag, no clicks, no animation yet
(A-06/A-07 add those). Never steals keyboard focus.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from willy.contracts import ScreenPoint


class WillyWindow(QWidget):
    """Per-pixel transparent, frameless, no taskbar entry, no focus theft.

    Hit area is the sprite bounding box (pixel-perfect mask is an A-08
    nicety). Sized to the sprite; resizes when the pixmap changes.
    """

    def __init__(self, sprite: QPixmap) -> None:
        super().__init__(None)
        if sprite.isNull():
            raise ValueError("Willy sprite pixmap is null")
        self._pixmap = sprite
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(self._pixmap.size())

    @property
    def pixmap(self) -> QPixmap:
        return self._pixmap

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            raise ValueError("Willy sprite pixmap is null")
        self._pixmap = pixmap
        self.setFixedSize(self._pixmap.size())
        self.update()

    def show_without_activating(self) -> None:
        # WA_ShowWithoutActivating makes plain show() safe: the window
        # appears without taking keyboard focus from the active app.
        self.show()

    def set_window_position(self, point: ScreenPoint) -> None:
        self.move(QPoint(point.x, point.y))

    def set_visibility(self, visible: bool) -> None:
        self.setVisible(visible)

    def set_always_on_top(self, on: bool) -> None:
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        if was_visible:
            # Qt hides the window when top-level flags change.
            self.show_without_activating()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        # Pixel art: nearest-neighbour only, never smoothed.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.end()
