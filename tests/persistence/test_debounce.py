from __future__ import annotations

import pytest

from willy.persistence import DebouncedWriter


@pytest.fixture
def recorder():
    calls = []
    return calls


def make_writer(calls, clock, interval=1.0):
    return DebouncedWriter(lambda: calls.append(clock.monotonic()), clock, interval)


def test_clean_writer_never_flushes(fake_clock, recorder):
    writer = make_writer(recorder, fake_clock)
    fake_clock.advance(10)
    assert writer.maybe_flush() is False
    assert writer.flush() is False
    assert recorder == []


def test_no_flush_before_interval(fake_clock, recorder):
    writer = make_writer(recorder, fake_clock)
    writer.mark_dirty()
    fake_clock.advance(0.5)
    assert writer.maybe_flush() is False
    assert recorder == []
    assert writer.dirty


def test_flush_after_interval(fake_clock, recorder):
    writer = make_writer(recorder, fake_clock)
    writer.mark_dirty()
    fake_clock.advance(1.0)
    assert writer.maybe_flush() is True
    assert len(recorder) == 1
    assert not writer.dirty


def test_mark_dirty_restarts_interval(fake_clock, recorder):
    writer = make_writer(recorder, fake_clock)
    writer.mark_dirty()
    fake_clock.advance(0.9)
    writer.mark_dirty()  # restartable debounce (ARCHITECTURE §1)
    fake_clock.advance(0.9)
    assert writer.maybe_flush() is False
    fake_clock.advance(0.1)
    assert writer.maybe_flush() is True
    assert len(recorder) == 1


def test_forced_flush_ignores_deadline(fake_clock, recorder):
    writer = make_writer(recorder, fake_clock)
    writer.mark_dirty()
    assert writer.flush() is True  # shutdown path: flush on aboutToQuit
    assert recorder == [fake_clock.monotonic()]
    assert writer.maybe_flush() is False


def test_interval_is_injectable(fake_clock, recorder):
    writer = make_writer(recorder, fake_clock, interval=5.0)
    writer.mark_dirty()
    fake_clock.advance(4.9)
    assert writer.maybe_flush() is False
    fake_clock.advance(0.1)
    assert writer.maybe_flush() is True


def test_non_positive_interval_rejected(fake_clock):
    with pytest.raises(ValueError):
        DebouncedWriter(lambda: None, fake_clock, 0)
