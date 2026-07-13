"""Synchronous typed event bus (ARCHITECTURE.md §3).

Main-thread only. Dispatch is immediate and in subscription order. Handlers
must be fast and must not publish re-entrantly beyond depth 3 — the guard
exists to catch feedback loops early, in development.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from willy.contracts.bus import BusRecursionError
from willy.contracts.events import Event

_MAX_DEPTH = 3


class SyncEventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Callable]] = defaultdict(list)
        self._depth = 0

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        if self._depth >= _MAX_DEPTH:
            raise BusRecursionError(
                f"publish depth exceeded {_MAX_DEPTH} at {type(event).__name__}"
            )
        self._depth += 1
        try:
            # copy: handlers may (un)subscribe during dispatch
            for handler in list(self._handlers[type(event)]):
                handler(event)
        finally:
            self._depth -= 1
