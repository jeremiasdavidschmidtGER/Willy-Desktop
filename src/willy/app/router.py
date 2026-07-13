"""Command routing (INTERFACES.md §3): command type → exactly one sink."""

from __future__ import annotations

from collections.abc import Callable

from willy.contracts import Command


class CommandRouter:
    def __init__(self) -> None:
        self._sinks: dict[type[Command], Callable] = {}

    def register(self, command_type: type[Command], sink: Callable) -> None:
        if command_type in self._sinks:
            raise ValueError(f"{command_type.__name__} already has a sink")
        self._sinks[command_type] = sink

    def dispatch(self, command: Command) -> None:
        sink = self._sinks.get(type(command))
        if sink is None:
            raise LookupError(f"no sink registered for {type(command).__name__}")
        sink(command)
