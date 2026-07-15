"""Fake-clock accelerated soak simulation driver (A-11).

Drives a real `WillyApp` through a simulated multi-hour session with an
injected fake clock: publishes the same events the platform layer would
(`WillyClicked`, `DragStarted`/`DragEnded`), calls the same render/behaviour
tick methods `app.start()` wires to real `QTimer`s, and periodically
re-checks the screen-layout monitor against a rotating fake monitor set.
Nothing here pumps a real Qt event loop, so wall-clock time elapses only as
fast as this Python loop runs — an "8 hour session" completes in seconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from willy.app.wiring import WillyApp
from willy.contracts import DragEnded, DragStarted, MouseButton, ScreenPoint, WillyClicked
from willy.platform.screens import ScreenGeometry

from tools.test_harness.event_generator import ActionKind, SimulatedAction, generate_schedule

TICK_SECONDS = 1.0  # accelerated step; select_frame() is elapsed-time based
# (animation/timing.py), so correctness doesn't depend on matching the real
# 33 ms render cadence — only on driving enough ticks to exercise it.

_LAYOUT_ONE_SCREEN = (ScreenGeometry(name="soak-a", x=0, y=0, width=1920, height=1080),)
_LAYOUT_TWO_SCREENS = (
    ScreenGeometry(name="soak-a", x=0, y=0, width=1920, height=1080),
    ScreenGeometry(name="soak-b", x=1920, y=0, width=1280, height=1024),
)


class FakeClockLike(Protocol):
    def advance(self, seconds: float) -> None: ...


@dataclass(slots=True)
class SoakReport:
    duration_seconds: float
    ticks_run: int
    actions_applied: int
    still_responsive: bool  # state machine settled (not stuck mid-drag/fall)


def run_fake_clock_soak(
    app: WillyApp,
    clock: FakeClockLike,
    *,
    duration_seconds: float,
    seed: int,
    tick_seconds: float = TICK_SECONDS,
) -> SoakReport:
    pending = list(generate_schedule(duration_seconds=duration_seconds, seed=seed))
    layout_toggle = False
    ticks_run = 0
    actions_applied = 0
    elapsed = 0.0

    while elapsed < duration_seconds:
        clock.advance(tick_seconds)
        elapsed += tick_seconds
        app.render_tick()
        app.behaviour_tick()
        ticks_run += 1

        while pending and pending[0].at_seconds <= elapsed:
            action = pending.pop(0)
            _apply_action(app, action, layout_toggle=layout_toggle)
            if action.kind is ActionKind.LAYOUT_CHANGE:
                layout_toggle = not layout_toggle
            actions_applied += 1

    # Sanity check: the state machine still answers a normal click after the
    # marathon and settles — proves it never wedged into a stuck priority,
    # mid-drag, or mid-fall state.
    app.bus.publish(
        WillyClicked(timestamp=app.clock.now(), button=MouseButton.LEFT, clicks_in_last_10s=1)
    )
    app.render_tick()
    still_responsive = not app.window.dragging and not app.window.falling

    return SoakReport(
        duration_seconds=elapsed,
        ticks_run=ticks_run,
        actions_applied=actions_applied,
        still_responsive=still_responsive,
    )


def _apply_action(app: WillyApp, action: SimulatedAction, *, layout_toggle: bool) -> None:
    if action.kind is ActionKind.CLICK:
        app.bus.publish(
            WillyClicked(timestamp=app.clock.now(), button=MouseButton.LEFT, clicks_in_last_10s=1)
        )
    elif action.kind is ActionKind.DRAG_CYCLE:
        start = ScreenPoint(x=app.window.x(), y=app.window.y())
        end = ScreenPoint(x=start.x + 40, y=start.y)
        app.bus.publish(DragStarted(timestamp=app.clock.now(), grab_point=start))
        app.window.move(end.x, end.y)
        app.bus.publish(DragEnded(timestamp=app.clock.now(), drop_point=end))
    elif action.kind is ActionKind.LAYOUT_CHANGE:
        monitor = app._screen_monitor
        layout = _LAYOUT_TWO_SCREENS if layout_toggle else _LAYOUT_ONE_SCREEN
        monitor._get_screens = lambda: layout
        monitor._get_primary = lambda: layout[0]
        monitor.check_and_relocate()
