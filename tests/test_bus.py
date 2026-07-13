from __future__ import annotations

from datetime import datetime, timezone

import pytest

from willy.app.bus import SyncEventBus
from willy.contracts import AppStarted, BusRecursionError, TickElapsed

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_dispatch_in_subscription_order():
    bus = SyncEventBus()
    seen: list[str] = []
    bus.subscribe(AppStarted, lambda e: seen.append("first"))
    bus.subscribe(AppStarted, lambda e: seen.append("second"))
    bus.subscribe(AppStarted, lambda e: seen.append("third"))
    bus.publish(AppStarted(timestamp=NOW))
    assert seen == ["first", "second", "third"]


def test_exact_type_subscription_only():
    bus = SyncEventBus()
    seen: list[object] = []
    bus.subscribe(AppStarted, seen.append)
    bus.publish(TickElapsed(timestamp=NOW, dt_seconds=1.0))
    assert seen == []


def test_unsubscribe_stops_delivery():
    bus = SyncEventBus()
    seen: list[object] = []
    bus.subscribe(AppStarted, seen.append)
    bus.unsubscribe(AppStarted, seen.append)
    bus.publish(AppStarted(timestamp=NOW))
    assert seen == []


def test_reentrancy_guard_raises_beyond_depth_3():
    bus = SyncEventBus()

    def republish(event: AppStarted) -> None:
        bus.publish(AppStarted(timestamp=NOW))

    bus.subscribe(AppStarted, republish)
    with pytest.raises(BusRecursionError):
        bus.publish(AppStarted(timestamp=NOW))


def test_one_level_reentrancy_is_allowed():
    bus = SyncEventBus()
    seen: list[object] = []

    def chain(event: AppStarted) -> None:
        bus.publish(TickElapsed(timestamp=NOW, dt_seconds=1.0))

    bus.subscribe(AppStarted, chain)
    bus.subscribe(TickElapsed, seen.append)
    bus.publish(AppStarted(timestamp=NOW))
    assert len(seen) == 1
