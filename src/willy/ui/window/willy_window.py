"""Transparent frameless Willy window (A-03 shell, A-07 dragging, A-08 clicks).

Dumb shell: it shows a pixmap, executes the window commands it is
handed, and reports facts (`DragStarted`/`DragEnded`/`WillyClicked`) — it
never decides anything (platform publishes, core interprets; ARCHITECTURE
§4). Never steals keyboard focus.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from willy.contracts import (
    Clock,
    DragEnded,
    DragStarted,
    EventBus,
    MouseButton,
    ScreenPoint,
    WillyClicked,
)

DRAG_THRESHOLD_PX = 4  # press+move below this stays a click, not a drag
GRAVITY_PX_S2 = 900.0  # D-15, tuned value from the retired lab
CLICK_WINDOW_S = 10.0  # A-08: rolling window for WillyClicked.clicks_in_last_10s


class WillyWindow(QWidget):
    """Per-pixel transparent, frameless, no taskbar entry, no focus theft.

    Hit area is the sprite bounding box (a pixel-perfect mask is a later
    nicety, not a Gate A criterion). Sized to the sprite; resizes when the
    pixmap changes.
    """

    def __init__(
        self,
        sprite: QPixmap,
        *,
        bus: EventBus | None = None,
        clock: Clock | None = None,
        on_fall_started: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(None)
        if sprite.isNull():
            raise ValueError("Willy sprite pixmap is null")
        self._pixmap = sprite
        self._bus = bus
        self._clock = clock
        self._on_fall_started = on_fall_started
        self._press_global: QPoint | None = None
        self._grab_offset: QPoint | None = None
        self._right_press_global: QPoint | None = None
        self._left_click_times: deque[float] = deque()
        self._right_click_times: deque[float] = deque()
        self._dragging = False
        self._falling = False
        self._fall_velocity = 0.0
        self._fall_y = 0.0
        self._fall_last_mono = 0.0
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # Right click is reserved (A-08): publishes WillyClicked only, no
        # context menu in Gate A.
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setFixedSize(self._pixmap.size())

    @property
    def pixmap(self) -> QPixmap:
        return self._pixmap

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            raise ValueError("Willy sprite pixmap is null")
        self._pixmap = pixmap
        self.setFixedSize(self._pixmap.size())
        if not self._dragging and not self._falling:
            # Different clips can have different frame heights (e.g. the
            # sprawled landing pose vs. standing idle); re-anchor so his
            # feet stay on the ground line (D-15) instead of drifting with
            # whichever clip just switched in. Never snap mid-air/mid-drag.
            self.move(self.x(), self.floor_y())
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

    # --- dragging (A-07) + floor gravity (D-15): facts out, core decides ---

    @property
    def dragging(self) -> bool:
        return self._dragging

    @property
    def falling(self) -> bool:
        return self._falling

    def floor_y(self) -> int:
        """Window y so that Willy stands on the screen's available bottom."""
        screen = self.screen()
        if screen is None:
            return self.y()
        return screen.availableGeometry().bottom() - self.height() + 1

    def snap_to_floor(self) -> None:
        self.move(self.x(), self.floor_y())

    def step_fall(self) -> None:
        """Advance the gravity fall; driven by the render tick (D-15)."""
        if not self._falling or self._clock is None:
            return
        now = self._clock.monotonic()
        dt = max(0.0, now - self._fall_last_mono)
        self._fall_last_mono = now
        self._fall_velocity += GRAVITY_PX_S2 * dt
        self._fall_y += self._fall_velocity * dt
        floor = self.floor_y()
        if self._fall_y >= floor:
            self._falling = False
            self._fall_velocity = 0.0
            self.move(self.x(), floor)
            # Impact is when the drag interaction truly ends: landing clip
            # and position save key off this event (D-15).
            self._publish(DragEnded, drop_point=ScreenPoint(x=self.x(), y=floor))
            return
        self.move(self.x(), round(self._fall_y))

    def _begin_fall(self) -> None:
        if self._clock is None or self.y() >= self.floor_y():
            # No clock to step with, or already grounded: land instantly.
            self.move(self.x(), self.floor_y())
            self._publish(DragEnded, drop_point=ScreenPoint(x=self.x(), y=self.y()))
            return
        self._falling = True
        self._fall_velocity = 0.0
        self._fall_y = float(self.y())
        self._fall_last_mono = self._clock.monotonic()
        if self._on_fall_started is not None:
            self._on_fall_started()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._falling = False  # mid-air grab cancels the fall
            global_pos = event.globalPosition().toPoint()
            self._press_global = global_pos
            self._grab_offset = global_pos - self.pos()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._right_press_global = event.globalPosition().toPoint()
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
                self._begin_fall()  # DragEnded is published at impact (D-15)
            else:
                self._publish_click(MouseButton.LEFT)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton and self._right_press_global is not None:
            self._right_press_global = None
            self._publish_click(MouseButton.RIGHT)  # reserved: no menu yet (Gate B)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _publish_click(self, button: MouseButton) -> None:
        if self._clock is None:
            return
        times = self._left_click_times if button is MouseButton.LEFT else self._right_click_times
        now = self._clock.monotonic()
        times.append(now)
        while times and now - times[0] > CLICK_WINDOW_S:
            times.popleft()
        self._publish(WillyClicked, button=button, clicks_in_last_10s=len(times))

    def _publish(self, event_type, **fields) -> None:
        if self._bus is None or self._clock is None:
            return
        self._bus.publish(event_type(timestamp=self._clock.now(), **fields))
