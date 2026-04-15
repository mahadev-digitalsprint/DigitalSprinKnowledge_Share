from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.config import settings
from app.events import event_bus

router = APIRouter(tags=["events"])


@router.get("/api/events")
async def multiplex_events(
    topics: str = Query("uploads,chat"),
    doc_id: str | None = Query(None),
) -> StreamingResponse:
    topic_set = {item.strip() for item in topics.split(",") if item.strip()}

    async def generate() -> AsyncGenerator[str, None]:
        subscriber_id, queue = await event_bus.subscribe(topic_set)
        try:
            while True:
                try:
                    bus_event = await asyncio.wait_for(
                        queue.get(),
                        timeout=settings.sse_heartbeat_seconds,
                    )
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
                    continue

                if doc_id and bus_event.data.get("doc_id") != doc_id:
                    continue

                yield f"event: {bus_event.event}\ndata: {json.dumps(bus_event.data)}\n\n"
        finally:
            await event_bus.unsubscribe(subscriber_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
