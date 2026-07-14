"""Composition root for the Gate A slice built so far (A-03 + A-06 + A-07 +
A-08).

Wires bus, window, command router, animation controller (33 ms render
tick), interaction controller, a ~1 Hz behaviour tick (annoyance decay),
and persistence (restore on launch, debounced save, flush on quit).
Everything is constructed here and only here (ARCHITECTURE.md §2).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

import willy
from willy.animation.controller import WillyAnimationController
from willy.animation.library import AssetLibrary
from willy.app.bus import SyncEventBus
from willy.app.clock import SystemClock
from willy.app.placeholder import build_placeholder_sprite
from willy.app.router import CommandRouter
from willy.app.tray_commands import TrayCommandHandler, TrayState
from willy.assets_runtime.pixmap_cache import PixmapCache
from willy.contracts import (
    AnimationFinished,
    AnimationPriority,
    AppStarted,
    Clock,
    DragEnded,
    DragStarted,
    Facing,
    PlayAnimation,
    ScreenPoint,
    SetMuted,
    SetPaused,
    SetVisibility,
    SetWindowPosition,
    ShutdownRequested,
    TickElapsed,
    TrayCommandIssued,
    WillyClicked,
    WillyStateSnapshot,
)
from willy.core.interaction import InteractionController
from willy.persistence import (
    Database,
    DebouncedWriter,
    SQLiteSettingsRepository,
    SQLiteWillyStateRepository,
    default_database_path,
)
from willy.platform.screens import (
    ScreenGeometry,
    ScreenLayoutMonitor,
    current_screens,
    primary_screen_geometry,
    resolve_restore_position,
    scale_factor_for_dpi,
)
from willy.platform.single_instance import SingleInstanceGuard
from willy.ui.tray.tray_icon import WillyTrayIcon
from willy.ui.window.willy_window import WillyWindow

LOGGER = logging.getLogger(__name__)

RENDER_TICK_MS = 33  # ~30 fps (ARCHITECTURE §1)
BLINK_INTERVAL_MS = 6000
BLINK_ASSET_ID = "willy_idle_blink"
PERSIST_DEBOUNCE_S = 1.0  # ARCHITECTURE §1 timer table
BASE_SPRITE_SCALE = 2  # D-14; A-10 multiplies by per-monitor DPI factor
BEHAVIOUR_TICK_MS = 1000  # ~1 Hz TickElapsed for annoyance decay (A-08)


def default_assets_root() -> Path | None:
    root = Path(willy.__file__).resolve().parents[2] / "assets" / "manifests"
    return root if root.is_dir() else None


class WillyApp:
    """Wires the Gate A slice: window executes commands, bus carries
    events, controller animates when an asset root is provided."""

    def __init__(
        self,
        *,
        clock: Clock,
        sprite: QPixmap | None = None,
        assets_root: Path | None = None,
        db_path: Path | None = None,
        bus: SyncEventBus | None = None,
    ) -> None:
        self.bus = bus or SyncEventBus()
        self.clock = clock
        self.router = CommandRouter()
        self.controller: WillyAnimationController | None = None
        self.interaction: InteractionController | None = None
        self._last_pixmap: QPixmap | None = None
        self._render_timer: QTimer | None = None
        self._blink_timer: QTimer | None = None
        self._behaviour_timer: QTimer | None = None
        self._last_behaviour_tick_mono: float | None = None
        self._restored: WillyStateSnapshot | None = None

        # Persistence (A-07): optional so tests and asset-less modes stay
        # side-effect free. db_path=None disables it entirely.
        self._db: Database | None = None
        self._state_repo: SQLiteWillyStateRepository | None = None
        self._settings_repo: SQLiteSettingsRepository | None = None
        self._state_writer: DebouncedWriter | None = None
        if db_path is not None:
            self._db = Database(db_path, clock=clock)
            self._db.open()
            self._state_repo = SQLiteWillyStateRepository(self._db)
            self._settings_repo = SQLiteSettingsRepository(self._db)
            self._state_writer = DebouncedWriter(self._flush_state, clock, PERSIST_DEBOUNCE_S)
            self._restored = self._state_repo.load()

        if assets_root is not None:
            library = AssetLibrary(assets_root, strict=False)
            library.load()
            self._library = library
            primary = primary_screen_geometry()
            dpi_scale = scale_factor_for_dpi(primary.device_pixel_ratio) if primary else 1
            self.controller = WillyAnimationController(
                cache=PixmapCache(library),
                library=library,
                bus=self.bus,
                clock=clock,
                scale=BASE_SPRITE_SCALE * dpi_scale,
            )
            self.router.register(PlayAnimation, self.controller.play)
            initial_facing = self._restored.facing if self._restored else Facing.RIGHT
            if initial_facing is not Facing.RIGHT:
                self.router.dispatch(
                    PlayAnimation(
                        animation_id=self.controller.current_animation_id,
                        facing=initial_facing,
                        priority=AnimationPriority.IDLE,
                    )
                )
            self._last_pixmap = self.controller.tick()
            self.interaction = InteractionController(
                dispatch=self.router.dispatch,
                state_dirty=self._mark_state_dirty,
                initial_facing=initial_facing,
                is_falling=lambda: self.window.falling,
            )
            self.window = WillyWindow(
                self._last_pixmap,
                bus=self.bus,
                clock=clock,
                on_fall_started=self.interaction.on_fall_started,
            )
            self.bus.subscribe(DragStarted, self.interaction.on_drag_started)
            self.bus.subscribe(DragEnded, self.interaction.on_drag_ended)
            self.bus.subscribe(AnimationFinished, self.interaction.on_animation_finished)
            self.bus.subscribe(WillyClicked, self.interaction.on_willy_clicked)
            self.bus.subscribe(TickElapsed, self.interaction.on_tick_elapsed)
        else:
            if sprite is None:
                raise ValueError("either sprite or assets_root is required")
            self.window = WillyWindow(sprite, bus=self.bus, clock=clock)

        if self._settings_repo is not None:
            self.window.set_always_on_top(
                self._settings_repo.get_bool("window.always_on_top", True)
            )

        self.router.register(SetWindowPosition, self._execute_set_window_position)
        self.router.register(SetVisibility, self._execute_set_visibility)
        self.router.register(SetPaused, self._execute_set_paused)
        self.router.register(SetMuted, self._execute_set_muted)
        self._shutdown_published = False

        # Tray (A-09): built regardless of asset mode so --sprite debug runs
        # still get working controls; SetPaused/SetMuted are safe no-ops
        # above when there is no controller.
        tray_state = (
            TrayCommandHandler.load_state(self._settings_repo)
            if self._settings_repo is not None
            else TrayState()
        )
        self._tray_handler = TrayCommandHandler(
            state=tray_state,
            settings_repository=self._settings_repo,
            emit_command=self.router.dispatch,
            reset_position=self._primary_screen_center,
            mark_state_dirty=self._mark_state_dirty,
            quit_app=self._request_exit,
        )
        self._tray_icon = WillyTrayIcon(
            icon=QIcon(self.window.pixmap),
            bus=self.bus,
            clock=clock,
            muted=tray_state.muted,
            paused=tray_state.paused,
            hidden=tray_state.hidden,
        )
        self.bus.subscribe(TrayCommandIssued, self._on_tray_command)
        self._tray_handler.apply_startup_state()

        # Multi-monitor recovery (A-10): live screenAdded/Removed relocation;
        # the at-launch clamp uses the same resolve_restore_position in
        # _initial_position below.
        self._screen_monitor = ScreenLayoutMonitor(
            bus=self.bus,
            clock=clock,
            get_screens=current_screens,
            get_primary=self._primary_geometry,
            get_window_state=self._current_window_state,
            set_window_position=self.window.set_window_position,
            mark_state_dirty=self._mark_state_dirty,
        )

    def start(self) -> None:
        self.window.set_window_position(self._initial_position())
        self.window.show_without_activating()
        self.window.snap_to_floor()  # Willy lives on the ground line (D-15)
        if self.controller is not None:
            self._render_timer = QTimer(self.window)
            self._render_timer.timeout.connect(self.render_tick)
            self._render_timer.start(RENDER_TICK_MS)
            if BLINK_ASSET_ID in self._library.asset_ids:
                # Provisional idle-blink default so Willy visibly blinks in
                # Gate A; real behaviour selection replaces this (later gates).
                self._blink_timer = QTimer(self.window)
                self._blink_timer.timeout.connect(self._blink)
                self._blink_timer.start(BLINK_INTERVAL_MS)
            self._behaviour_timer = QTimer(self.window)
            self._behaviour_timer.timeout.connect(self.behaviour_tick)
            self._behaviour_timer.start(BEHAVIOUR_TICK_MS)
        self._tray_icon.show()
        self.bus.publish(AppStarted(timestamp=self.clock.now()))

    def render_tick(self) -> None:
        self.window.step_fall()  # gravity physics, no-op unless falling (D-15)
        if self._state_writer is not None:
            self._state_writer.maybe_flush()  # debounce polling (D-6 style)
        if self.controller is None:
            return
        pixmap = self.controller.tick()
        if pixmap is not self._last_pixmap:  # frames are cached: identity works
            self._last_pixmap = pixmap
            self.window.set_pixmap(pixmap)

    def behaviour_tick(self) -> None:
        """Publishes TickElapsed (~1 Hz) so core can decay annoyance (A-08)."""
        now = self.clock.monotonic()
        if self._last_behaviour_tick_mono is None:
            dt = BEHAVIOUR_TICK_MS / 1000
        else:
            dt = now - self._last_behaviour_tick_mono
        self._last_behaviour_tick_mono = now
        self.bus.publish(TickElapsed(timestamp=self.clock.now(), dt_seconds=dt))

    def shutdown(self) -> None:
        if self._shutdown_published:
            return
        self._shutdown_published = True
        for timer in (self._render_timer, self._blink_timer, self._behaviour_timer):
            if timer is not None:
                timer.stop()
        self._tray_icon.hide()
        self._screen_monitor.close()
        if self._state_writer is not None:
            self._state_writer.mark_dirty()  # persist final position even
            self._state_writer.flush()  # without a preceding drag
        if self._db is not None:
            self._db.close()
        self.bus.publish(ShutdownRequested(timestamp=self.clock.now()))

    def _mark_state_dirty(self) -> None:
        if self._state_writer is not None:
            self._state_writer.mark_dirty()

    def _flush_state(self) -> None:
        assert self._state_repo is not None
        facing = self.interaction.facing if self.interaction is not None else Facing.RIGHT
        self._state_repo.save(
            WillyStateSnapshot(
                position=ScreenPoint(x=self.window.x(), y=self.window.y()),
                screen_name=self._current_screen_name(),
                facing=facing,
                updated_at=self.clock.now(),
            )
        )

    def _current_screen_name(self) -> str:
        screen = self.window.screen()
        return screen.name() if screen is not None else ""

    def _current_window_state(self) -> tuple[str, ScreenPoint, int, int]:
        return (
            self._current_screen_name(),
            ScreenPoint(x=self.window.x(), y=self.window.y()),
            self.window.width(),
            self.window.height(),
        )

    def _blink(self) -> None:
        assert self.controller is not None
        self.router.dispatch(
            PlayAnimation(
                animation_id=BLINK_ASSET_ID,
                facing=self.controller.current_facing,
                priority=AnimationPriority.IDLE,
            )
        )

    def _execute_set_paused(self, command: SetPaused) -> None:
        if self.controller is not None:
            self.controller.set_paused(command.paused)

    def _execute_set_muted(self, command: SetMuted) -> None:
        # Gate A: no audio sink exists yet; this is a logged stub (A-09 brief).
        LOGGER.info("mute toggled: muted=%s (no audio sink yet)", command.muted)

    def _execute_set_window_position(self, command: SetWindowPosition) -> None:
        self.window.set_window_position(command.point)

    def _execute_set_visibility(self, command: SetVisibility) -> None:
        self.window.set_visibility(command.visible)

    def _on_tray_command(self, event: TrayCommandIssued) -> None:
        state = self._tray_handler.handle(event)
        self._tray_icon.update_state(muted=state.muted, paused=state.paused, hidden=state.hidden)

    def _request_exit(self) -> None:
        self.shutdown()
        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.quit()

    def _initial_position(self) -> ScreenPoint:
        # Restored position wins (A-07), clamped back onto a live screen if
        # its saved screen is gone or it now falls off every screen (A-10,
        # ARCHITECTURE §7).
        if self._restored is not None:
            primary = primary_screen_geometry()
            if primary is None:
                return self._restored.position
            return resolve_restore_position(
                screen_name=self._restored.screen_name,
                point=self._restored.position,
                sprite_width=self.window.width(),
                sprite_height=self.window.height(),
                screens=current_screens(),
                primary=primary,
            )
        return self._primary_screen_center()

    def _primary_screen_center(self) -> ScreenPoint:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return ScreenPoint(x=100, y=100)
        centre = screen.availableGeometry().center()
        return ScreenPoint(
            x=centre.x() - self.window.width() // 2,
            y=centre.y() - self.window.height() // 2,
        )

    def _primary_geometry(self) -> ScreenGeometry:
        return primary_screen_geometry() or ScreenGeometry(
            name="", x=0, y=0, width=self.window.width(), height=self.window.height()
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
        clock = SystemClock()
        db_path = default_database_path()
        if sprite_path is not None:
            # Explicit --sprite: static single-frame mode.
            app = WillyApp(sprite=load_sprite(sprite_path), clock=clock, db_path=db_path)
        else:
            assets_root = default_assets_root()
            if assets_root is not None:
                app = WillyApp(assets_root=assets_root, clock=clock, db_path=db_path)
            else:
                LOGGER.error("assets/manifests not found; static placeholder Willy")
                app = WillyApp(sprite=build_placeholder_sprite(), clock=clock, db_path=db_path)
        qapp.aboutToQuit.connect(app.shutdown)
        app.start()
        return qapp.exec()
    finally:
        guard.release()
