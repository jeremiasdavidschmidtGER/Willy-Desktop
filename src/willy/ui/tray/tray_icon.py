"""System tray icon and menu (A-09). Dumb shell: publishes
`TrayCommandIssued` on menu interaction, never decides anything — the same
platform-publishes/core-interprets split as the window (ARCHITECTURE §4).
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from willy.contracts import Clock, EventBus, TrayCommandIssued, TrayCommandKind


class WillyTrayIcon:
    def __init__(
        self,
        *,
        icon: QIcon,
        bus: EventBus,
        clock: Clock,
        muted: bool = False,
        paused: bool = False,
        hidden: bool = False,
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._tray = QSystemTrayIcon(icon)
        self._menu = QMenu()

        self.mute_action = self._add_checkable_action("Mute", muted, TrayCommandKind.MUTE_TOGGLE)
        self.pause_action = self._add_checkable_action(
            "Pause", paused, TrayCommandKind.PAUSE_TOGGLE
        )
        self.hide_action = self._add_checkable_action(
            "Hide Willy", hidden, TrayCommandKind.HIDE_TOGGLE
        )
        self._menu.addSeparator()
        self.reset_action = self._add_action("Reset Position", TrayCommandKind.RESET_POSITION)
        self._menu.addSeparator()
        self.exit_action = self._add_action("Exit", TrayCommandKind.EXIT)

        self._tray.setToolTip("Willy")
        self._tray.setContextMenu(self._menu)

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def update_state(self, *, muted: bool, paused: bool, hidden: bool) -> None:
        self.mute_action.setChecked(muted)
        self.pause_action.setChecked(paused)
        self.hide_action.setChecked(hidden)

    def _add_checkable_action(self, text: str, checked: bool, kind: TrayCommandKind) -> QAction:
        action = QAction(text, self._menu)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(lambda _checked=False: self._publish(kind))
        self._menu.addAction(action)
        return action

    def _add_action(self, text: str, kind: TrayCommandKind) -> QAction:
        action = QAction(text, self._menu)
        action.triggered.connect(lambda _checked=False: self._publish(kind))
        self._menu.addAction(action)
        return action

    def _publish(self, kind: TrayCommandKind) -> None:
        self._bus.publish(TrayCommandIssued(timestamp=self._clock.now(), kind=kind))
