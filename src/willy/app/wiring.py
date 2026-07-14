"""Composition root for the Gate A slice built so far (A-03).

Wires bus, window, and command router; publishes lifecycle events.
Everything is constructed here and only here (ARCHITECTURE.md §2).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication

from willy.app.bus import SyncEventBus
from willy.app.clock import SystemClock
from willy.app.placeholder import build_placeholder_sprite
from willy.app.router import CommandRouter
from willy.contracts import (
    AppStarted,
    Clock,
    ScreenPoint,
    SetVisibility,
    SetWindowPosition,
    ShutdownRequested,
)
from willy.platform.single_instance import SingleInstanceGuard
from willy.ui.window.willy_window import WillyWindow

LOGGER = logging.getLogger(__name__)


class WillyApp:
    """Wires the A-03 slice: window executes commands, bus carries events."""

    def __init__(self, *, sprite: QPixmap, clock: Clock, bus: SyncEventBus | None = None) -> None:
        self.bus = bus or SyncEventBus()
        self.clock = clock
        self.window = WillyWindow(sprite)
        self.router = CommandRouter()
        self.router.register(SetWindowPosition, self._execute_set_window_position)
        self.router.register(SetVisibility, self._execute_set_visibility)
        self._shutdown_published = False

    def start(self) -> None:
        self.window.set_window_position(self._initial_position())
        self.window.show_without_activating()
        self.bus.publish(AppStarted(timestamp=self.clock.now()))

    def shutdown(self) -> None:
        if self._shutdown_published:
            return
        self._shutdown_published = True
        self.bus.publish(ShutdownRequested(timestamp=self.clock.now()))

    def _execute_set_window_position(self, command: SetWindowPosition) -> None:
        self.window.set_window_position(command.point)

    def _execute_set_visibility(self, command: SetVisibility) -> None:
        self.window.set_visibility(command.visible)

    def _initial_position(self) -> ScreenPoint:
        # No persistence hookup in A-03 (A-07 restores saved position):
        # centre of the primary screen's available area.
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return ScreenPoint(x=100, y=100)
        centre = screen.availableGeometry().center()
        return ScreenPoint(
            x=centre.x() - self.window.width() // 2,
            y=centre.y() - self.window.height() // 2,
        )


def load_sprite(sprite_path: str | None) -> QPixmap:
    if sprite_path:
        pixmap = QPixmap(str(Path(sprite_path)))
        if not pixmap.isNull():
            return pixmap
        LOGGER.error("Could not load sprite %s; using placeholder", sprite_path)
    return build_placeholder_sprite()


def run_app(sprite_path: str | None = None) -> int:
    guard = SingleInstanceGuard()
    if not guard.acquire():
        print("Willy is already running.")
        return 0
    try:
        qapp = QApplication.instance() or QApplication([])
        app = WillyApp(sprite=load_sprite(sprite_path), clock=SystemClock())
        qapp.aboutToQuit.connect(app.shutdown)
        app.start()
        return qapp.exec()
    finally:
        guard.release()
