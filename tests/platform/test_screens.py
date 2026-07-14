"""A-10: multi-monitor recovery (clamp/restore) and DPI scale selection.

Pure logic (ScreenGeometry, resolve_restore_position, scale_factor_for_dpi)
is tested with fake geometries, no Qt. ScreenLayoutMonitor is tested with
injected fake providers via its public check_and_relocate(), so no real
QScreen needs to be fabricated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from willy.app.wiring import WillyApp
from willy.contracts import ScreenLayoutChanged, ScreenPoint
from willy.platform.screens import (
    ScreenGeometry,
    ScreenLayoutMonitor,
    resolve_restore_position,
    scale_factor_for_dpi,
)

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"

PRIMARY = ScreenGeometry(name="primary", x=0, y=0, width=1920, height=1080)
SECONDARY = ScreenGeometry(name="secondary", x=1920, y=0, width=1280, height=1024)


class TestScaleFactorForDpi:
    @pytest.mark.parametrize(
        ("dpi", "expected"),
        [(1.0, 1), (1.25, 1), (1.49, 1), (1.5, 2), (1.75, 2), (2.0, 2)],
    )
    def test_threshold_table(self, dpi, expected):
        assert scale_factor_for_dpi(dpi) == expected


class TestResolveRestorePosition:
    def test_point_fully_on_saved_screen_is_unchanged(self):
        point = ScreenPoint(x=100, y=100)
        resolved = resolve_restore_position(
            screen_name="primary",
            point=point,
            sprite_width=64,
            sprite_height=64,
            screens=(PRIMARY, SECONDARY),
            primary=PRIMARY,
        )
        assert resolved == point

    def test_point_on_a_different_still_connected_screen_is_unchanged(self):
        point = ScreenPoint(x=2000, y=100)  # inside SECONDARY, not PRIMARY
        resolved = resolve_restore_position(
            screen_name="secondary",
            point=point,
            sprite_width=64,
            sprite_height=64,
            screens=(PRIMARY, SECONDARY),
            primary=PRIMARY,
        )
        assert resolved == point

    def test_saved_screen_missing_clamps_to_primary(self):
        point = ScreenPoint(x=2000, y=100)  # was on the now-removed secondary
        resolved = resolve_restore_position(
            screen_name="secondary",
            point=point,
            sprite_width=64,
            sprite_height=64,
            screens=(PRIMARY,),  # secondary unplugged
            primary=PRIMARY,
        )
        assert resolved == PRIMARY.clamp(point, 64, 64)
        assert 0 <= resolved.x <= PRIMARY.width - 64
        assert 0 <= resolved.y <= PRIMARY.height - 64

    def test_point_off_all_screens_clamps_even_if_screen_name_matches(self):
        # Same screen name, but its geometry shrank (e.g. resolution change)
        # so the saved point no longer fits.
        shrunk = ScreenGeometry(name="primary", x=0, y=0, width=800, height=600)
        point = ScreenPoint(x=1800, y=900)
        resolved = resolve_restore_position(
            screen_name="primary",
            point=point,
            sprite_width=64,
            sprite_height=64,
            screens=(shrunk,),
            primary=shrunk,
        )
        assert resolved != point
        assert resolved.x <= shrunk.width - 64
        assert resolved.y <= shrunk.height - 64

    def test_fully_off_screen_negative_point_clamps_into_view(self):
        point = ScreenPoint(x=-500, y=-500)
        resolved = resolve_restore_position(
            screen_name="primary",
            point=point,
            sprite_width=64,
            sprite_height=64,
            screens=(PRIMARY,),
            primary=PRIMARY,
        )
        assert resolved.x == 0
        assert resolved.y == 0


class TestScreenLayoutMonitor:
    @pytest.fixture
    def rig(self, fake_clock):
        from willy.app.bus import SyncEventBus

        bus = SyncEventBus()
        events: list = []
        bus.subscribe(ScreenLayoutChanged, events.append)
        state = {"screen_name": "secondary", "point": ScreenPoint(x=2000, y=100)}
        dirty_calls = []
        set_calls = []
        monitor = ScreenLayoutMonitor(
            bus=bus,
            clock=fake_clock,
            get_screens=lambda: (PRIMARY,),  # secondary is gone
            get_primary=lambda: PRIMARY,
            get_window_state=lambda: (state["screen_name"], state["point"], 64, 64),
            set_window_position=lambda point: set_calls.append(point),
            mark_state_dirty=lambda: dirty_calls.append(True),
            app=None,  # no real QGuiApplication signal hookup needed for this test
        )
        return monitor, bus, events, state, dirty_calls, set_calls

    def test_relocates_when_saved_screen_is_gone(self, rig):
        monitor, _bus, events, _state, dirty_calls, set_calls = rig
        monitor.check_and_relocate()
        assert len(events) == 1
        assert events[0].screen_names == ("primary",)
        assert len(set_calls) == 1
        assert set_calls[0] == PRIMARY.clamp(ScreenPoint(x=2000, y=100), 64, 64)
        assert dirty_calls == [True]

    def test_no_relocation_when_still_valid(self, fake_clock):
        from willy.app.bus import SyncEventBus

        bus = SyncEventBus()
        dirty_calls = []
        set_calls = []
        monitor = ScreenLayoutMonitor(
            bus=bus,
            clock=fake_clock,
            get_screens=lambda: (PRIMARY, SECONDARY),
            get_primary=lambda: PRIMARY,
            get_window_state=lambda: ("primary", ScreenPoint(x=100, y=100), 64, 64),
            set_window_position=lambda point: set_calls.append(point),
            mark_state_dirty=lambda: dirty_calls.append(True),
            app=None,
        )
        monitor.check_and_relocate()
        assert set_calls == []
        assert dirty_calls == []


class TestWiringIntegration:
    def test_startup_clamps_restored_position_off_a_removed_screen(
        self, qtbot, tmp_path, fake_clock, monkeypatch
    ):
        db_path = tmp_path / "willy.db"
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=db_path)
        qtbot.addWidget(app.window)
        app.start()
        app.window.move(500, 400)
        app.shutdown()

        # Simulate the saved screen being gone at next launch: only a
        # smaller primary remains (comfortably bigger than the sprite so the
        # clamp has room to place it fully on-screen).
        new_primary = ScreenGeometry(name="only-screen", x=0, y=0, width=400, height=400)
        monkeypatch.setattr("willy.app.wiring.current_screens", lambda: (new_primary,))
        monkeypatch.setattr("willy.app.wiring.primary_screen_geometry", lambda: new_primary)

        restarted = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=db_path)
        qtbot.addWidget(restarted.window)
        # _initial_position() is the A-10 clamp result; start() then also
        # runs the (unrelated, D-15) floor-snap against the *real* offscreen
        # screen, so assert on the clamp itself rather than the post-start
        # window position.
        resolved = restarted._initial_position()
        assert 0 <= resolved.x <= new_primary.width - restarted.window.width()
        assert 0 <= resolved.y <= new_primary.height - restarted.window.height()

    def test_live_screen_removal_relocates_running_window(self, qtbot, tmp_path, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock, db_path=tmp_path / "willy.db")
        qtbot.addWidget(app.window)
        app.start()
        app.window.move(9000, 9000)  # simulate: was on a monitor far to the right

        shrunk_primary = ScreenGeometry(name="only-screen", x=0, y=0, width=300, height=200)
        app._screen_monitor._get_screens = lambda: (shrunk_primary,)
        app._screen_monitor._get_primary = lambda: shrunk_primary

        app._screen_monitor.check_and_relocate()
        assert app.window.x() <= shrunk_primary.width - app.window.width()
        assert app.window.y() <= shrunk_primary.height - app.window.height()

    def test_high_dpi_primary_multiplies_base_sprite_scale(self, qtbot, fake_clock, monkeypatch):
        from willy.app import wiring as wiring_module

        normal = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
        qtbot.addWidget(normal.window)
        normal_scale = normal.controller._scale

        high_dpi = ScreenGeometry(
            name="hidpi", x=0, y=0, width=1920, height=1080, device_pixel_ratio=2.0
        )
        monkeypatch.setattr(wiring_module, "primary_screen_geometry", lambda: high_dpi)
        scaled = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
        qtbot.addWidget(scaled.window)

        assert scaled.controller._scale == normal_scale * 2

    def test_shutdown_disconnects_screen_monitor_without_raising(self, qtbot, fake_clock):
        app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
        qtbot.addWidget(app.window)
        app.start()
        app.shutdown()  # must not raise; monitor.close() runs
        app.shutdown()  # idempotent, close() already ran once
