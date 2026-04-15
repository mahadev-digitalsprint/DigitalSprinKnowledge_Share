from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class BusEvent:
    topic: str
    event: str
    data: dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, tuple[set[str], asyncio.Queue[BusEvent]]] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def subscribe(self, topics: set[str]) -> tuple[int, asyncio.Queue[BusEvent]]:
        async with self._lock:
            subscriber_id = self._next_id
            self._next_id += 1
            queue: asyncio.Queue[BusEvent] = asyncio.Queue()
            self._subscribers[subscriber_id] = (topics, queue)
            return subscriber_id, queue

    async def unsubscribe(self, subscriber_id: int) -> None:
        async with self._lock:
            self._subscribers.pop(subscriber_id, None)

    async def publish(self, topic: str, event: str, data: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.values())

        bus_event = BusEvent(topic=topic, event=event, data=data)
        for topics, queue in subscribers:
            if topic in topics:
                await queue.put(bus_event)


event_bus = EventBus()
