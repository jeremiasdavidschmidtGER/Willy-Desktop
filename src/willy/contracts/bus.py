"""Event bus contract: synchronous, main-thread only, dispatch in
subscription order, raises BusRecursionError beyond re-entrancy depth 3."""

from __future__ import annotations

from typing import Callable, Protocol, TypeVar

from willy.contracts.events import Event

E = TypeVar("E", bound=Event)


class BusRecursionError(RuntimeError):
    """Raised when publish() re-enters deeper than the allowed depth."""


class EventBus(Protocol):
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...

    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...

    def publish(self, event: Event) -> None: ...
