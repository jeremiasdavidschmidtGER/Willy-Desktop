"""Multi-monitor recovery and DPI scale selection (A-10, ARCHITECTURE §7).

`ScreenGeometry` + the pure functions below are Qt-free and fully testable
with fake geometries; `ScreenLayoutMonitor` is the thin Qt adapter that
watches real screen add/remove and turns it into the same shape (platform
publishes facts, core/app decide nothing here — ARCHITECTURE §4).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtGui import QGuiApplication, QScreen

from willy.contracts import Clock, EventBus, ScreenLayoutChanged, ScreenPoint

# Sprites use integer scaling only; 1x below this DPI, 2x at/above it
# (D-14's base factor of 2 is multiplied by this — MVP §29 / ARCHITECTURE §7).
HIGH_DPI_THRESHOLD = 1.5
LOW_DPI_SCALE = 1
HIGH_DPI_SCALE = 2


@dataclass(frozen=True, slots=True)
class ScreenGeometry:
    name: str
    x: int
    y: int
    width: int
    height: int
    device_pixel_ratio: float = 1.0

    def contains_rect(self, point: ScreenPoint, width: int, height: int) -> bool:
        return (
            self.x <= point.x
            and self.y <= point.y
            and point.x + width <= self.x + self.width
            and point.y + height <= self.y + self.height
        )

    def clamp(self, point: ScreenPoint, width: int, height: int) -> ScreenPoint:
        max_x = max(self.x + self.width - width, self.x)
        max_y = max(self.y + self.height - height, self.y)
        return ScreenPoint(
            x=min(max(point.x, self.x), max_x),
            y=min(max(point.y, self.y), max_y),
        )


def scale_factor_for_dpi(device_pixel_ratio: float) -> int:
    """Integer sprite scale for a screen's DPI; multiplies D-14's base factor."""
    return HIGH_DPI_SCALE if device_pixel_ratio >= HIGH_DPI_THRESHOLD else LOW_DPI_SCALE


def resolve_restore_position(
    *,
    screen_name: str,
    point: ScreenPoint,
    sprite_width: int,
    sprite_height: int,
    screens: tuple[ScreenGeometry, ...],
    primary: ScreenGeometry,
) -> ScreenPoint:
    """ARCHITECTURE §7: saved screen missing or point off all screens → clamp
    onto the primary screen's available geometry; otherwise unchanged."""
    saved_screen_present = any(screen.name == screen_name for screen in screens)
    fully_on_some_screen = any(
        screen.contains_rect(point, sprite_width, sprite_height) for screen in screens
    )
    if saved_screen_present and fully_on_some_screen:
        return point
    return primary.clamp(point, sprite_width, sprite_height)


def qscreen_to_geometry(screen: QScreen) -> ScreenGeometry:
    rect = screen.availableGeometry()
    return ScreenGeometry(
        name=screen.name(),
        x=rect.x(),
        y=rect.y(),
        width=rect.width(),
        height=rect.height(),
        device_pixel_ratio=screen.devicePixelRatio(),
    )


def current_screens() -> tuple[ScreenGeometry, ...]:
    return tuple(qscreen_to_geometry(screen) for screen in QGuiApplication.screens())


def primary_screen_geometry() -> ScreenGeometry | None:
    screen = QGuiApplication.primaryScreen()
    return qscreen_to_geometry(screen) if screen is not None else None


class ScreenLayoutMonitor:
    """Watches `QGuiApplication` screen add/remove; publishes
    `ScreenLayoutChanged` and relocates the window when its current position
    is no longer valid (screen gone, or off every remaining screen)."""

    def __init__(
        self,
        *,
        bus: EventBus,
        clock: Clock,
        get_screens: Callable[[], tuple[ScreenGeometry, ...]],
        get_primary: Callable[[], ScreenGeometry],
        get_window_state: Callable[[], tuple[str, ScreenPoint, int, int]],
        set_window_position: Callable[[ScreenPoint], None],
        mark_state_dirty: Callable[[], None],
        app: QGuiApplication | None = None,
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._get_screens = get_screens
        self._get_primary = get_primary
        self._get_window_state = get_window_state
        self._set_window_position = set_window_position
        self._mark_state_dirty = mark_state_dirty
        self._app = app if app is not None else QGuiApplication.instance()
        if self._app is not None:
            self._app.screenAdded.connect(self._on_layout_changed)
            self._app.screenRemoved.connect(self._on_layout_changed)

    def close(self) -> None:
        if self._app is not None:
            self._app.screenAdded.disconnect(self._on_layout_changed)
            self._app.screenRemoved.disconnect(self._on_layout_changed)
            self._app = None

    def check_and_relocate(self) -> None:
        """Public so tests can trigger the same logic a real screenAdded/
        Removed signal would, without fabricating a QScreen."""
        screens = self._get_screens()
        self._bus.publish(
            ScreenLayoutChanged(
                timestamp=self._clock.now(),
                screen_names=tuple(screen.name for screen in screens),
            )
        )
        screen_name, point, width, height = self._get_window_state()
        resolved = resolve_restore_position(
            screen_name=screen_name,
            point=point,
            sprite_width=width,
            sprite_height=height,
            screens=screens,
            primary=self._get_primary(),
        )
        if resolved != point:
            self._set_window_position(resolved)
            self._mark_state_dirty()

    def _on_layout_changed(self, _screen: QScreen) -> None:
        self.check_and_relocate()
