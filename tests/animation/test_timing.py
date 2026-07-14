from __future__ import annotations

import pytest

from willy.animation.timing import FrameSelection, select_frame

DURATIONS = [100, 120, 80]  # total 300 ms


@pytest.mark.parametrize(
    ("elapsed_s", "expected_index"),
    [
        (0.0, 0),
        (0.099, 0),
        (0.100, 1),
        (0.219, 1),
        (0.220, 2),
        (0.299, 2),
        (0.300, 0),  # loop wraps
        (0.350, 0),
        (0.420, 1),
        (0.900, 0),  # three full loops
    ],
)
def test_loop_frame_selection_table(elapsed_s, expected_index):
    assert select_frame(DURATIONS, elapsed_s, loop=True) == FrameSelection(expected_index, False)


def test_non_loop_clamps_to_last_frame_and_finishes():
    assert select_frame(DURATIONS, 0.299, loop=False) == FrameSelection(2, False)
    assert select_frame(DURATIONS, 0.300, loop=False) == FrameSelection(2, True)
    assert select_frame(DURATIONS, 99.0, loop=False) == FrameSelection(2, True)


def test_hiccup_jump_lands_on_correct_frame():
    # 500 ms event-loop stall: selection is purely time-based, no crash,
    # no per-frame stepping to catch up.
    assert select_frame(DURATIONS, 0.1 + 0.5, loop=True) == FrameSelection(0, False)


def test_hours_long_loop_has_no_drift():
    # 8 h soak: index depends only on (elapsed mod total) — drift-free by
    # construction.
    eight_hours = 8 * 3600.0
    assert select_frame(DURATIONS, eight_hours + 0.150, loop=True) == select_frame(
        DURATIONS, 0.150, loop=True
    )


def test_negative_elapsed_clamps_to_first_frame():
    assert select_frame(DURATIONS, -0.5, loop=True) == FrameSelection(0, False)


def test_single_frame_clip():
    assert select_frame([50], 10.0, loop=True) == FrameSelection(0, False)
    assert select_frame([50], 10.0, loop=False) == FrameSelection(0, True)


def test_empty_durations_rejected():
    with pytest.raises(ValueError):
        select_frame([], 0.0, loop=True)
