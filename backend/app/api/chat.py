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
from app.core.llm import get_anthropic, get_openai, resolve_provider_model
from app.core.registry import resolve_embedding_profile
from app.db import CollectionDB, DocumentDB
from app.events import event_bus
from app.models.schemas import ChatRequest
from app.retrieval.qdrant import SearchRoute, search_routes

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful, precise assistant. Answer the user's question
using only the provided source excerpts. Cite sources inline as [1], [2], etc.
If the sources don't contain enough information, say so honestly.
Keep answers concise and direct."""


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
    doc_map: dict[str, str] = {}
    if doc_ids:
        result = await session.execute(
            select(DocumentDB.id, DocumentDB.filename).where(DocumentDB.id.in_(doc_ids))
        )
        doc_map = {row.id: row.filename for row in result}

    sources = [
        {
            "kind": "doc",
            "index": index + 1,
            "title": doc_map.get(doc["document_id"], "Document"),
            "filename": doc_map.get(doc["document_id"], "document"),
            "page": doc["page"],
            "collection_id": doc["collection_id"],
            "excerpt": doc["text"][:300],
            "score": round(doc["score"], 3),
            "document_id": doc["document_id"],
            "quality": doc.get("quality", "fast"),
            "version": doc.get("version", 1),
            "bbox": doc.get("bbox", []),
        }
        for index, doc in enumerate(raw_docs)
    ]
    await event_bus.publish("chat", "chat.sources", {"sources": sources})
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    if raw_docs:
        context_blocks = "\n\n".join(
            f"[{index + 1}] (page {doc['page']}, quality {doc.get('quality', 'fast')})\n{doc['text']}"
            for index, doc in enumerate(raw_docs)
        )
        user_content = f"Sources:\n{context_blocks}\n\nQuestion: {body.query}"
    else:
        user_content = f"Question: {body.query}\n\n(No relevant documents found in this collection.)"

    messages = [{"role": "user", "content": user_content}]
    if body.history:
        messages = [{"role": msg.role, "content": msg.content} for msg in body.history[-6:]] + messages

    provider, model = resolve_provider_model(body.provider, body.model)

    try:
        if provider == "anthropic":
            async for event in _stream_anthropic(model, messages):
                await event_bus.publish("chat", "chat.token", {"delta": event})
                yield f"event: token\ndata: {json.dumps({'delta': event})}\n\n"
        else:
            async for event in _stream_openai(model, messages):
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


async def _stream_anthropic(model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    client = get_anthropic()
    async with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            if text:
                yield text


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
