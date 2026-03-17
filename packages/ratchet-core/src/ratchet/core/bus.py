"""Simple async pub/sub event bus for inter-module communication."""

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("ratchet.core.bus")

EventHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """
    Lightweight pub/sub bus. Modules communicate through events
    without importing each other.

    Event naming convention: "module_name.event_name"
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if payload is None:
            payload = {}
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *[h(event_type, payload) for h in handlers],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler {handlers[i]} failed on {event_type}: {result}")

    @property
    def event_types(self) -> list[str]:
        return list(self._subscribers.keys())
