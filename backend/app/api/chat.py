from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUserDep, QdrantDep, SessionDep
from app.core.llm import get_gemini, get_openai, resolve_chat_target
from app.core.rbac import ensure_collection_access, require_permission
from app.events import event_bus
from app.graph import run_chat_graph
from app.models.schemas import ChatRequest

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the DigitalSprint AI Knowledge Base - an internal advisor helping teams discover, evaluate, and adopt the best AI tools and software across the organisation.

## Your role
Help employees find the right tools for their department and workflow. Be direct, specific, and practical. Always include tool links when available.

## Output rules
- Respond in clean GitHub-flavored Markdown only.
- Never add bracket citations [1], footnotes, or a "Sources" section.
- Keep answers concise - no padding, no repetition.
- When a rating is available, show it as ★ symbols (e.g. ★★★★☆ for 4/5).
- When a tool link is available, always show it.

## Format by query type

**Single tool lookup:**
### [Tool Name]
One paragraph - what it is and who made it.
**Best for:** comma-separated list of roles/teams
**Use cases:** bullet list of 3-5 practical use cases
**Rating:** ★★★★☆ (if available)
**Link:** [URL](URL) (if available)
**Similar tools:** related tools from the knowledge base

**Department/team query** - list all relevant tools found:
**[Tool Name]** - one-sentence description. Best for: [roles]. [Link](URL)

**Comparison query** - use a Markdown table:
| Tool | Best For | Rating | Link |
|------|----------|--------|------|

**Recommendation query** - top pick first with one sentence of justification, then alternatives.

**Recent/latest tools query** - list tools ordered newest-first, showing the addition date if available:
**[Tool Name]** (added [date]) - description. [Link](URL)

**No matching data** - clearly state what is missing. If partially covered, summarise what is available.

## Department context
Collections: HR · Marketing · Sales · Operations · Developers · Frontend · Backend · QA & Testing · Architecture.
When the user mentions a department or team, focus on tools tagged to that collection."""


@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    session: SessionDep,
    qdrant: QdrantDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    require_permission(current_user, "chat:read")
    ensure_collection_access(current_user, body.collection_id)
    return StreamingResponse(
        _stream(body, session, qdrant),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream(
    body: ChatRequest,
    session: SessionDep,
    qdrant: QdrantDep,
) -> AsyncGenerator[str, None]:
    try:
        graph_result = await run_chat_graph(body=body, session=session, qdrant=qdrant)
    except Exception as exc:
        logger.exception("Retrieval graph failed")
        payload = {"error": str(exc)}
        await event_bus.publish("chat", "chat.error", payload)
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
        return

    await event_bus.publish("chat", "chat.sources", {"sources": graph_result.sources})
    yield f"event: sources\ndata: {json.dumps(graph_result.sources)}\n\n"

    provider, model = resolve_chat_target(body.provider, body.model)
    try:
        stream = (
            _stream_gemini(model, graph_result.messages)
            if provider == "gemini"
            else _stream_openai(model, graph_result.messages)
        )
        async for event in stream:
            await event_bus.publish("chat", "chat.token", {"delta": event})
            yield f"event: token\ndata: {json.dumps({'delta': event})}\n\n"
    except Exception as exc:
        logger.exception("LLM streaming failed")
        payload = {"error": str(exc)}
        await event_bus.publish("chat", "chat.error", payload)
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
        return

    await event_bus.publish("chat", "chat.done", {"turn_id": body.session_id or ""})
    yield "event: done\ndata: {}\n\n"


async def _stream_openai(model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    client = get_openai()
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        max_tokens=1500,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


async def _stream_gemini(model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    client = get_gemini()
    prompt = "\n\n".join(
        f"{message['role'].upper()}:\n{message['content']}"
        for message in messages
        if message.get("content")
    )
    contents = f"{SYSTEM_PROMPT}\n\n{prompt}"
    stream = await client.aio.models.generate_content_stream(
        model=model,
        contents=contents,
    )
    async for chunk in stream:
        text = getattr(chunk, "text", None)
        if text:
            yield text
