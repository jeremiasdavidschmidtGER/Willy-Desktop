"""Tray command routing (A-09): tray fact in, commands + settings out.

Qt-free decision code (ARCHITECTURE §4). Position writes reuse the app's
single debounced-write path (`mark_state_dirty`) rather than writing state
directly, so there is exactly one place that persists `WillyStateSnapshot`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from willy.contracts import (
    Command,
    ScreenPoint,
    SettingsRepository,
    SetMuted,
    SetPaused,
    SetVisibility,
    SetWindowPosition,
    TrayCommandIssued,
    TrayCommandKind,
)

AUDIO_MUTED_KEY = "audio.muted"
WILLY_PAUSED_KEY = "willy.paused"
WILLY_HIDDEN_KEY = "willy.hidden"


@dataclass(slots=True)
class TrayState:
    muted: bool = False
    paused: bool = False
    hidden: bool = False


class TrayCommandHandler:
    def __init__(
        self,
        *,
        state: TrayState,
        settings_repository: SettingsRepository | None,
        emit_command: Callable[[Command], None],
        reset_position: Callable[[], ScreenPoint],
        mark_state_dirty: Callable[[], None],
        quit_app: Callable[[], None],
    ) -> None:
        self.state = state
        self._settings_repository = settings_repository
        self._emit_command = emit_command
        self._reset_position = reset_position
        self._mark_state_dirty = mark_state_dirty
        self._quit_app = quit_app

    @classmethod
    def load_state(cls, settings_repository: SettingsRepository) -> TrayState:
        return TrayState(
            muted=settings_repository.get_bool(AUDIO_MUTED_KEY, default=False),
            paused=settings_repository.get_bool(WILLY_PAUSED_KEY, default=False),
            hidden=settings_repository.get_bool(WILLY_HIDDEN_KEY, default=False),
        )

    def apply_startup_state(self) -> None:
        self._emit_command(SetMuted(muted=self.state.muted))
        self._emit_command(SetPaused(paused=self.state.paused))
        self._emit_command(SetVisibility(visible=not self.state.hidden))

    def handle(self, event: TrayCommandIssued) -> TrayState:
        if event.kind is TrayCommandKind.MUTE_TOGGLE:
            self.state.muted = not self.state.muted
            self._set_setting(AUDIO_MUTED_KEY, self.state.muted)
            self._emit_command(SetMuted(muted=self.state.muted))
        elif event.kind is TrayCommandKind.PAUSE_TOGGLE:
            self.state.paused = not self.state.paused
            self._set_setting(WILLY_PAUSED_KEY, self.state.paused)
            self._emit_command(SetPaused(paused=self.state.paused))
        elif event.kind is TrayCommandKind.HIDE_TOGGLE:
            self.state.hidden = not self.state.hidden
            self._set_setting(WILLY_HIDDEN_KEY, self.state.hidden)
            self._emit_command(SetVisibility(visible=not self.state.hidden))
        elif event.kind is TrayCommandKind.RESET_POSITION:
            self._emit_command(SetWindowPosition(point=self._reset_position()))
            self._mark_state_dirty()
        elif event.kind is TrayCommandKind.EXIT:
            self._quit_app()
        return self.state

    def _set_setting(self, key: str, value: bool) -> None:
        if self._settings_repository is not None:
            self._settings_repository.set(key, value)
