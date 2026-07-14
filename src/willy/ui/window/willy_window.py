"""Transparent frameless Willy window (A-03 shell, A-07 dragging).

Dumb shell: it shows a pixmap, executes the window commands it is
handed, and reports facts (`DragStarted`/`DragEnded`) — it never decides
anything (platform publishes, core interprets; ARCHITECTURE §4). Never
steals keyboard focus.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from willy.contracts import Clock, DragEnded, DragStarted, EventBus, ScreenPoint

DRAG_THRESHOLD_PX = 4  # press+move below this stays a click, not a drag


class WillyWindow(QWidget):
    """Per-pixel transparent, frameless, no taskbar entry, no focus theft.

    Hit area is the sprite bounding box (pixel-perfect mask is an A-08
    nicety). Sized to the sprite; resizes when the pixmap changes.
    """

    def __init__(
        self,
        sprite: QPixmap,
        *,
        bus: EventBus | None = None,
        clock: Clock | None = None,
    ) -> None:
        super().__init__(None)
        if sprite.isNull():
            raise ValueError("Willy sprite pixmap is null")
        self._pixmap = sprite
        self._bus = bus
        self._clock = clock
        self._press_global: QPoint | None = None
        self._grab_offset: QPoint | None = None
        self._dragging = False
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

    # --- dragging (A-07): the window reports facts, core decides ---

    @property
    def dragging(self) -> bool:
        return self._dragging

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self._press_global = global_pos
            self._grab_offset = global_pos - self.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press_global is None:
            super().mouseMoveEvent(event)
            return
        global_pos = event.globalPosition().toPoint()
        if not self._dragging:
            delta = global_pos - self._press_global
            if abs(delta.x()) < DRAG_THRESHOLD_PX and abs(delta.y()) < DRAG_THRESHOLD_PX:
                return
            self._dragging = True
            self._publish(
                DragStarted,
                grab_point=ScreenPoint(x=self._press_global.x(), y=self._press_global.y()),
            )
        assert self._grab_offset is not None
        self.move(global_pos - self._grab_offset)  # follow cursor, keep grab offset
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._press_global is not None:
            was_dragging = self._dragging
            self._press_global = None
            self._grab_offset = None
            self._dragging = False
            if was_dragging:
                self._publish(DragEnded, drop_point=ScreenPoint(x=self.x(), y=self.y()))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _publish(self, event_type, **fields) -> None:
        if self._bus is None or self._clock is None:
            return
        self._bus.publish(event_type(timestamp=self._clock.now(), **fields))
