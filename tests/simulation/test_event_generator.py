"""Unit tests for the pure, seeded soak-simulation event generator (A-11)."""

from __future__ import annotations

import pytest

from tools.test_harness.event_generator import ActionKind, generate_schedule


class TestGenerateSchedule:
    def test_same_seed_is_reproducible(self):
        first = generate_schedule(duration_seconds=3600, seed=42)
        second = generate_schedule(duration_seconds=3600, seed=42)
        assert first == second

    def test_different_seed_differs(self):
        first = generate_schedule(duration_seconds=3600, seed=1)
        second = generate_schedule(duration_seconds=3600, seed=2)
        assert first != second

    def test_all_actions_within_duration(self):
        schedule = generate_schedule(duration_seconds=7200, seed=7)
        assert schedule  # non-trivial duration should produce at least one action
        assert all(0 <= action.at_seconds < 7200 for action in schedule)

    def test_schedule_is_time_sorted(self):
        schedule = generate_schedule(duration_seconds=7200, seed=7)
        timestamps = [action.at_seconds for action in schedule]
        assert timestamps == sorted(timestamps)

    def test_zero_duration_is_empty(self):
        assert generate_schedule(duration_seconds=0, seed=1) == ()

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError):
            generate_schedule(duration_seconds=-1, seed=1)

    def test_all_three_action_kinds_appear_over_a_long_duration(self):
        schedule = generate_schedule(duration_seconds=8 * 3600, seed=7)
        kinds = {action.kind for action in schedule}
        assert kinds == {ActionKind.CLICK, ActionKind.DRAG_CYCLE, ActionKind.LAYOUT_CHANGE}

    def test_tighter_interval_produces_more_actions_of_that_kind(self):
        schedule = generate_schedule(
            duration_seconds=3600,
            seed=1,
            click_interval_s=(1.0, 2.0),
        )
        clicks = [a for a in schedule if a.kind is ActionKind.CLICK]
        assert len(clicks) > 1000  # ~1800 expected at a 1-2s cadence over 1h
