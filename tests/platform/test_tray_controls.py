"""A-09 system tray: command routing, settings persistence, tray menu smoke,
and shutdown flush ordering."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from willy.app.tray_commands import (
    AUDIO_MUTED_KEY,
    WILLY_HIDDEN_KEY,
    WILLY_PAUSED_KEY,
    TrayCommandHandler,
    TrayState,
)
from willy.app.wiring import WillyApp
from willy.contracts import (
    ScreenPoint,
    SetMuted,
    SetPaused,
    SetVisibility,
    SetWindowPosition,
    TrayCommandIssued,
    TrayCommandKind,
)

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"
_POINT = ScreenPoint(x=42, y=7)


class FakeSettingsRepository:
    def __init__(self) -> None:
        self._values: dict[str, bool | int | str] = {}

    def get_bool(self, key: str, default: bool) -> bool:
        return bool(self._values.get(key, default))

    def get_int(self, key: str, default: int) -> int:
        return int(self._values.get(key, default))

    def get_str(self, key: str, default: str) -> str:
        return str(self._values.get(key, default))

    def set(self, key: str, value: bool | int | str) -> None:
        self._values[key] = value


class TestTrayCommandHandler:
    """Pure command-routing table: no Qt, fake bus/settings."""

    @pytest.fixture
    def rig(self):
        settings = FakeSettingsRepository()
        commands: list = []
        dirty_calls = []
        quit_calls = []
        handler = TrayCommandHandler(
            state=TrayState(),
            settings_repository=settings,
            emit_command=commands.append,
            reset_position=lambda: _POINT,
            mark_state_dirty=lambda: dirty_calls.append(True),
            quit_app=lambda: quit_calls.append(True),
        )
        return handler, settings, commands, dirty_calls, quit_calls

    def test_mute_toggle_flips_state_persists_and_emits(self, rig):
        handler, settings, commands, _dirty, _quit = rig
        state = handler.handle(_event(TrayCommandKind.MUTE_TOGGLE))
        assert state.muted is True
        assert settings.get_bool(AUDIO_MUTED_KEY, False) is True
        assert commands == [SetMuted(muted=True)]
        state = handler.handle(_event(TrayCommandKind.MUTE_TOGGLE))
        assert state.muted is False
        assert settings.get_bool(AUDIO_MUTED_KEY, True) is False

    def test_pause_toggle_flips_state_persists_and_emits(self, rig):
        handler, settings, commands, _dirty, _quit = rig
        state = handler.handle(_event(TrayCommandKind.PAUSE_TOGGLE))
        assert state.paused is True
        assert settings.get_bool(WILLY_PAUSED_KEY, False) is True
        assert commands == [SetPaused(paused=True)]

    def test_hide_toggle_flips_state_persists_and_emits_inverse_visibility(self, rig):
        handler, settings, commands, _dirty, _quit = rig
        state = handler.handle(_event(TrayCommandKind.HIDE_TOGGLE))
        assert state.hidden is True
        assert settings.get_bool(WILLY_HIDDEN_KEY, False) is True
        assert commands == [SetVisibility(visible=False)]

    def test_reset_position_emits_point_and_marks_dirty(self, rig):
        handler, _settings, commands, dirty_calls, _quit = rig
        handler.handle(_event(TrayCommandKind.RESET_POSITION))
        assert commands == [SetWindowPosition(point=_POINT)]
        assert dirty_calls == [True]

    def test_exit_calls_quit_app(self, rig):
        handler, _settings, _commands, _dirty, quit_calls = rig
        handler.handle(_event(TrayCommandKind.EXIT))
        assert quit_calls == [True]

    def test_settings_repository_is_optional(self):
        commands: list = []
        handler = TrayCommandHandler(
            state=TrayState(),
            settings_repository=None,
            emit_command=commands.append,
            reset_position=lambda: _POINT,
            mark_state_dirty=lambda: None,
            quit_app=lambda: None,
        )
        state = handler.handle(_event(TrayCommandKind.MUTE_TOGGLE))
        assert state.muted is True  # no repo → no persistence, no crash
        assert commands == [SetMuted(muted=True)]

    def test_load_state_reads_persisted_values(self):
        settings = FakeSettingsRepository()
        settings.set(AUDIO_MUTED_KEY, True)
        settings.set(WILLY_PAUSED_KEY, True)
        settings.set(WILLY_HIDDEN_KEY, False)
        state = TrayCommandHandler.load_state(settings)
        assert state == TrayState(muted=True, paused=True, hidden=False)

    def test_apply_startup_state_emits_all_three(self):
        commands: list = []
        handler = TrayCommandHandler(
            state=TrayState(muted=True, paused=False, hidden=True),
            settings_repository=None,
            emit_command=commands.append,
            reset_position=lambda: _POINT,
            mark_state_dirty=lambda: None,
            quit_app=lambda: None,
        )
        handler.apply_startup_state()
        assert commands == [
            SetMuted(muted=True),
            SetPaused(paused=False),
            SetVisibility(visible=False),
        ]


class TestTraySettingsPersistenceWiring:
    def make_app(self, tmp_path, clock, qtbot) -> WillyApp:
        app = WillyApp(assets_root=REPO_ASSETS, clock=clock, db_path=tmp_path / "willy.db")
        qtbot.addWidget(app.window)
        return app

    def test_toggles_survive_restart(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock, qtbot)
        app.start()
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.MUTE_TOGGLE)
        )
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.HIDE_TOGGLE)
        )
        app.shutdown()

        restarted = self.make_app(tmp_path, fake_clock, qtbot)
        assert restarted._tray_handler.state.muted is True
        assert restarted._tray_handler.state.hidden is True
        assert restarted._tray_icon.mute_action.isChecked() is True
        assert restarted._tray_icon.hide_action.isChecked() is True

    def test_hide_toggle_hides_window_immediately(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock, qtbot)
        app.start()
        assert app.window.isVisible()
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.HIDE_TOGGLE)
        )
        assert not app.window.isVisible()

    def test_pause_toggle_pauses_animation_controller(self, qtbot, tmp_path, fake_clock):
        app = self.make_app(tmp_path, fake_clock, qtbot)
        app.start()
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.PAUSE_TOGGLE)
        )
        assert app.controller.paused

    def test_reset_position_moves_window_to_primary_screen_center(
        self, qtbot, tmp_path, fake_clock
    ):
        app = self.make_app(tmp_path, fake_clock, qtbot)
        app.start()
        app.window.move(9999, 9999)
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.RESET_POSITION)
        )
        expected = app._primary_screen_center()
        assert app.window.x() == expected.x
        assert app.window.y() == expected.y

    def test_no_db_path_tray_still_works_without_crashing(self, qtbot, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.MUTE_TOGGLE)
        )
        assert app._tray_handler.state.muted is True
        app.shutdown()

    def test_sprite_only_mode_pause_is_a_safe_no_op(self, qtbot, fake_clock):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap

        sprite = QPixmap(16, 16)
        sprite.fill(Qt.GlobalColor.transparent)
        app = WillyApp(sprite=sprite, clock=fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app.bus.publish(
            TrayCommandIssued(timestamp=fake_clock.now(), kind=TrayCommandKind.PAUSE_TOGGLE)
        )  # must not raise: no controller to pause in sprite-only mode
        assert app._tray_handler.state.paused is True


class TestTrayIconMenuSmoke:
    def test_mute_action_trigger_publishes_and_checks(self, qtbot, tmp_path, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=tmp_path / "willy.db")
        qtbot.addWidget(app.window)
        app.start()
        assert not app._tray_icon.mute_action.isChecked()
        app._tray_icon.mute_action.trigger()
        assert app._tray_icon.mute_action.isChecked()
        assert app._tray_handler.state.muted is True

    def test_exit_action_flushes_state_before_quitting(self, qtbot, tmp_path, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=tmp_path / "willy.db")
        qtbot.addWidget(app.window)
        app.start()
        app.window.move(55, 44)
        assert not app._shutdown_published
        app._tray_icon.exit_action.trigger()
        assert app._shutdown_published  # shutdown() ran: state flushed, timers stopped

        restarted = WillyApp(
            assets_root=REPO_ASSETS, clock=fake_clock, db_path=tmp_path / "willy.db"
        )
        qtbot.addWidget(restarted.window)
        restarted.start()
        assert restarted.window.x() == 55


def _event(kind: TrayCommandKind) -> TrayCommandIssued:
    return TrayCommandIssued(timestamp=datetime(2026, 7, 14, tzinfo=UTC), kind=kind)
