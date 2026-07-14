"""A-08: click reactions and annoyance escalation, driven end-to-end
through WillyApp with real art, the real AnimationController, and the
real InteractionController."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt

from willy.app.wiring import WillyApp
from willy.contracts import MouseButton, TickElapsed, WillyClicked
from willy.core.interaction import FRONT_HOLD_SECONDS

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"


@pytest.fixture
def app(qtbot, fake_clock):
    willy_app = WillyApp(assets_root=REPO_ASSETS, clock=fake_clock)
    qtbot.addWidget(willy_app.window)
    willy_app.start()
    return willy_app


def click(app, qtbot):
    qtbot.mousePress(app.window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    qtbot.mouseRelease(app.window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))


def advance_render(app, fake_clock, seconds, step=0.033):
    for _ in range(int(seconds / step) + 1):
        fake_clock.advance(step)
        app.render_tick()


def quiet_period(app, fake_clock, seconds):
    """Simulates a gap with no clicks: publishes one big TickElapsed
    (decays annoyance, counts down any active front-facing hold), exactly
    as the ~1 Hz behaviour timer would over many small ticks."""
    fake_clock.advance(seconds)
    app.bus.publish(TickElapsed(timestamp=fake_clock.now(), dt_seconds=seconds))
    app.render_tick()


def escalate_to_smug(app, qtbot, fake_clock):
    """Drives 6 clicks through the real tier sequence: front enter -> hold
    -> (escalation) turn away -> annoyed -> smug."""
    click(app, qtbot)  # 1: tier 1, entering
    advance_render(app, fake_clock, 0.5)  # enter finishes -> holding
    click(app, qtbot)  # 2: still tier 1, refreshes the hold
    click(app, qtbot)  # 3: tier now "annoyed" -> turns away first
    advance_render(app, fake_clock, 0.5)  # leave finishes -> annoyed plays
    click(app, qtbot)  # 4
    click(app, qtbot)  # 5
    click(app, qtbot)  # 6: tier now "smug"


def test_single_click_shows_front_enter(app, qtbot):
    click(app, qtbot)
    assert app.controller.current_animation_id == "willy_front_enter"


def test_front_hold_lasts_a_few_seconds_then_returns_to_idle(app, qtbot, fake_clock):
    click(app, qtbot)
    assert app.controller.current_animation_id == "willy_front_enter"
    advance_render(app, fake_clock, 0.5)
    assert app.controller.current_animation_id == "willy_front_idle"
    advance_render(app, fake_clock, 1.0)  # plain rendering never erodes the hold
    assert app.controller.current_animation_id == "willy_front_idle"
    quiet_period(app, fake_clock, seconds=FRONT_HOLD_SECONDS + 0.1)  # expires the hold
    advance_render(app, fake_clock, 0.5)  # lets the leave clip play out
    assert app.controller.current_animation_id == "willy_idle"


def test_repeated_clicks_escalate_through_distinct_tiers(app, qtbot, fake_clock):
    click(app, qtbot)  # 1: tier 1, entering
    assert app.controller.current_animation_id == "willy_front_enter"
    advance_render(app, fake_clock, 0.5)  # enter finishes -> holding
    assert app.controller.current_animation_id == "willy_front_idle"
    click(app, qtbot)  # 2: still tier 1, refreshes the hold only
    assert app.controller.current_animation_id == "willy_front_idle"
    click(app, qtbot)  # 3: tier now "annoyed" -> turn away first
    assert app.controller.current_animation_id == "willy_front_leave"
    advance_render(app, fake_clock, 0.5)  # leave finishes -> annoyed plays
    assert app.controller.current_animation_id == "willy_annoyed"
    click(app, qtbot)  # 4: still "annoyed" tier
    click(app, qtbot)  # 5: still "annoyed" tier
    click(app, qtbot)  # 6: tier now "smug"
    assert app.controller.current_animation_id == "willy_smug"


def test_smug_reaction_returns_to_idle_on_its_own(app, qtbot, fake_clock):
    """willy_smug loops in its manifest, but click reactions force a
    one-shot playback (loop_override) so it can never get stuck."""
    escalate_to_smug(app, qtbot, fake_clock)
    assert app.controller.current_animation_id == "willy_smug"
    for _ in range(200):  # step the render tick well past the clip's length
        fake_clock.advance(0.033)
        app.render_tick()
        if app.controller.current_animation_id == "willy_idle":
            break
    assert app.controller.current_animation_id == "willy_idle"


def test_annoyance_resets_after_quiet_period(app, qtbot, fake_clock):
    escalate_to_smug(app, qtbot, fake_clock)
    assert app.controller.current_animation_id == "willy_smug"
    quiet_period(app, fake_clock, seconds=60.0)  # fully decays annoyance
    advance_render(app, fake_clock, 1.5)  # lets the one-shot smug clip finish
    # Proof of reset: the next click starts back at tier 1, not smug again.
    click(app, qtbot)
    assert app.controller.current_animation_id == "willy_front_enter"


def test_dragging_still_wins_over_click_reaction(app, qtbot, fake_clock):
    qtbot.mousePress(app.window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    qtbot.mouseMove(app.window, QPoint(45, 25))  # past drag threshold
    assert app.controller.current_animation_id == "willy_dragged"
    # A click reaction dispatched at INTERACTION priority must not
    # interrupt the REACTION-priority dragged pose (still mid-drag). The
    # window itself never publishes WillyClicked mid-drag, but a stray
    # click-derived command must still lose priority arbitration.
    app.interaction.on_willy_clicked(
        WillyClicked(timestamp=fake_clock.now(), button=MouseButton.LEFT, clicks_in_last_10s=1)
    )
    assert app.controller.current_animation_id == "willy_dragged"
    qtbot.mouseRelease(app.window, Qt.MouseButton.LeftButton, pos=QPoint(45, 25))


def test_click_spam_does_not_crash_or_get_stuck(app, qtbot, fake_clock):
    for _ in range(300):  # 10/s for 30s, per A-08 acceptance criteria
        click(app, qtbot)
        fake_clock.advance(0.1)
        app.render_tick()
    assert app.interaction.annoyance > 0.0  # bounded, but real clicks did register

    # No crash, and nothing left stuck: two settle passes (one to resolve
    # whatever the spam left mid-sequence, one for anything that chained
    # off of it) bring everything back to idle.
    for _ in range(2):
        quiet_period(app, fake_clock, seconds=120.0)
        advance_render(app, fake_clock, 2.0)
    assert app.controller.current_animation_id == "willy_idle"
    assert app.interaction.annoyance == 0.0


def test_behaviour_tick_decays_annoyance_using_real_elapsed_time(app, qtbot, fake_clock):
    """Smoke-tests the actual QTimer-driven method (not a synthetic
    TickElapsed): repeated calls must each decay annoyance a little,
    computing dt from the real elapsed monotonic time between calls."""
    click(app, qtbot)
    assert app.interaction.annoyance > 0.0
    for _ in range(20):
        fake_clock.advance(1.0)
        app.behaviour_tick()
    assert app.interaction.annoyance == 0.0
