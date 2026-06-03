from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import QdrantDep, SessionDep
from app.config import settings
from app.core.embedder import embed_query
from app.core.llm import get_gemini, get_openai, resolve_chat_target
from app.core.registry import resolve_embedding_profile
from app.db import CollectionDB, DocumentDB
from app.events import event_bus
from app.models.schemas import ChatRequest
from app.retrieval.qdrant import SearchRoute, search_routes

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are DigitalSprint's internal AI tools advisor.
Use only the provided reference material. Do not invent facts, pricing, integrations, or capabilities.

Output rules:
- Respond in clean GitHub-flavored Markdown.
- Never include source numbers, bracket citations, footnotes, circled citation markers, or a Sources section.
- Use short headings and readable paragraphs.
- Prefer bullets for use cases, fit notes, and implementation advice.
- When comparing multiple tools, use a compact Markdown table.
- If the user asks for one tool, use this structure:
  ## Overview
  One concise paragraph explaining what the tool is.
  ## Best For
  Bullet list of the roles, teams, or workflows where it fits.
  ## Use Cases
  Bullet list of practical use cases.
  ## Similar Tools
  Bullet list or table of related tools from the provided references.
  ## Notes
  Mention limits, missing details, or what to verify if the references are incomplete.
- If the user asks for recommendations, start with a direct recommendation, then explain why.
- If the references do not contain enough information, say exactly what is missing and still summarize what is available."""


@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    session: SessionDep,
    qdrant: QdrantDep,
) -> StreamingResponse:
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
        routes = await _load_search_routes(session, body.collection_id)
        profiles = OrderedDict((route.embedding_profile, None) for route in routes)
        vectors = await asyncio.gather(
            *(embed_query(body.query, profile=profile) for profile in profiles.keys())
        )
        query_vectors = dict(zip(profiles.keys(), vectors, strict=True))

        raw_docs = await search_routes(
            qdrant,
            routes,
            query_vectors,
            limit=8,
        )
    except Exception as exc:
        logger.exception("Retrieval failed")
        payload = {"error": str(exc)}
        await event_bus.publish("chat", "chat.error", payload)
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
        return

    doc_ids = list({doc["document_id"] for doc in raw_docs if doc["document_id"]})
    doc_map: dict[str, dict[str, str]] = {}
    if doc_ids:
        result = await session.execute(
            select(
                DocumentDB.id,
                DocumentDB.filename,
                DocumentDB.record_kind,
                DocumentDB.tool_name,
                DocumentDB.tool_url,
                DocumentDB.short_description,
                DocumentDB.department,
                DocumentDB.primary_role,
            ).where(DocumentDB.id.in_(doc_ids))
        )
        doc_map = {
            row.id: {
                "filename": row.filename,
                "record_kind": row.record_kind,
                "tool_name": row.tool_name,
                "tool_url": row.tool_url,
                "short_description": row.short_description,
                "department": row.department,
                "primary_role": row.primary_role,
            }
            for row in result
        }

    sources = [
        {
            "kind": "doc",
            "index": index + 1,
            "title": doc_map.get(doc["document_id"], {}).get("tool_name")
            or doc_map.get(doc["document_id"], {}).get("filename", "Document"),
            "filename": doc_map.get(doc["document_id"], {}).get("filename", "document"),
            "page": doc["page"],
            "collection_id": doc["collection_id"],
            "excerpt": doc["text"][:300],
            "score": round(doc["score"], 3),
            "document_id": doc["document_id"],
            "quality": doc.get("quality", "fast"),
            "version": doc.get("version", 1),
            "record_kind": doc.get("record_kind", "document"),
            "bbox": doc.get("bbox", []),
            "tool_url": doc.get("tool_url", ""),
            "short_description": doc.get("short_description", ""),
            "department": doc.get("department", ""),
            "primary_role": doc.get("primary_role", ""),
            "rating": doc.get("rating", 0),
        }
        for index, doc in enumerate(raw_docs)
    ]
    await event_bus.publish("chat", "chat.sources", {"sources": sources})
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    if raw_docs:
        context_blocks = "\n\n".join(
            f"Reference {index + 1} (page {doc['page']}, quality {doc.get('quality', 'fast')}, "
            f"department {doc.get('department', 'General')}, "
            f"role {doc.get('primary_role', 'General')}, rating {doc.get('rating', 0)}/5)\n"
            f"Tool: {doc.get('tool_name', 'Unknown')}\n"
            f"Description: {doc.get('short_description', '')}\n"
            f"Tool link: {doc.get('tool_url', '')}\n"
            f"Why it matters: {doc.get('importance_note', '')}\n"
            f"How it helps: {doc.get('impact_note', '')}\n"
            f"{doc['text']}"
            for index, doc in enumerate(raw_docs)
        )
        user_content = f"Reference material:\n{context_blocks}\n\nQuestion: {body.query}"
    else:
        user_content = f"Question: {body.query}\n\n(No relevant documents found in this collection.)"

    messages = [{"role": "user", "content": user_content}]
    if body.history:
        messages = [{"role": msg.role, "content": msg.content} for msg in body.history[-6:]] + messages

    provider, model = resolve_chat_target(body.provider, body.model)

    try:
        stream = _stream_gemini(model, messages) if provider == "gemini" else _stream_openai(model, messages)
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


async def _load_search_routes(session: SessionDep, collection_id: str) -> list[SearchRoute]:
    if collection_id and collection_id != "all":
        collection = await session.get(CollectionDB, collection_id)
        if collection is None:
            return [
                SearchRoute(
                    embedding_profile=resolve_embedding_profile(None),
                    org_id=settings.default_org_id,
                    collection_id=collection_id,
                )
            ]
        return [
            SearchRoute(
                embedding_profile=resolve_embedding_profile(collection.embedding_profile),
                org_id=settings.default_org_id,
                collection_id=collection.id,
            )
        ]

    result = await session.execute(
        select(CollectionDB.embedding_profile).where(CollectionDB.org_id == settings.default_org_id)
    )
    profiles = {
        resolve_embedding_profile(row.embedding_profile)
        for row in result
        if row.embedding_profile
    }
    if not profiles:
        profiles = {resolve_embedding_profile(None)}

    return [
        SearchRoute(
            embedding_profile=profile,
            org_id=settings.default_org_id,
            collection_id=None,
        )
        for profile in profiles
    ]


async def _stream_openai(model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    client = get_openai()
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        max_tokens=1024,
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
