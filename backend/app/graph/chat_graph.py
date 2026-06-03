from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embedder import embed_query
from app.core.registry import resolve_embedding_profile
from app.db import CollectionDB, DocumentDB
from app.models.schemas import ChatRequest
from app.retrieval.qdrant import SearchRoute, search_routes

_TEMPORAL_PATTERN = re.compile(
    r"\b(recent|recently|latest|newest|new|last\s+added|just\s+added|"
    r"today|this\s+week|this\s+month|added|current|freshly|fresh)\b",
    re.IGNORECASE,
)

_DEPARTMENT_MAP: dict[str, str] = {
    "hr": "HR",
    "human resource": "HR",
    "human resources": "HR",
    "people ops": "HR",
    "marketing": "Marketing",
    "sales": "Sales",
    "crm": "Sales",
    "lead": "Sales",
    "developer": "Developers",
    "developers": "Developers",
    "dev ": "Developers",
    "coding": "Developers",
    "engineer": "Developers",
    "engineering": "Developers",
    "frontend": "Frontend",
    "front-end": "Frontend",
    "front end": "Frontend",
    "ui ": "Frontend",
    "ux ": "Frontend",
    "design": "Frontend",
    "backend": "Backend",
    "back-end": "Backend",
    "back end": "Backend",
    "api ": "Backend",
    "server": "Backend",
    "infrastructure": "Backend",
    "operations": "Operations",
    "ops": "Operations",
    "qa": "QA & Testing",
    "testing": "QA & Testing",
    "tester": "QA & Testing",
    "quality": "QA & Testing",
    "architect": "Architecture",
    "architecture": "Architecture",
    "platform": "Architecture",
}


class ChatGraphState(TypedDict):
    body: ChatRequest
    session: AsyncSession
    qdrant: AsyncQdrantClient
    is_temporal: bool
    detected_dept: str | None
    raw_docs: list[dict[str, Any]]
    recent_rows: list[DocumentDB]
    sources: list[dict[str, Any]]
    user_content: str
    messages: list[dict[str, str]]


@dataclass(frozen=True)
class GraphChatResult:
    sources: list[dict[str, Any]]
    messages: list[dict[str, str]]


def _detect_temporal(query: str) -> bool:
    return bool(_TEMPORAL_PATTERN.search(query))


def _detect_department(query: str) -> str | None:
    q = query.lower()
    for keyword, dept in _DEPARTMENT_MAP.items():
        if keyword in q:
            return dept
    return None


def _format_age(created_at: datetime | None, now: datetime) -> str:
    if created_at is None:
        return "unknown"
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    delta = now - created_at
    days = delta.days
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 31:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


async def _load_search_routes(
    session: AsyncSession,
    collection_id: str,
    department: str | None = None,
) -> list[SearchRoute]:
    if collection_id and collection_id != "all":
        collection = await session.get(CollectionDB, collection_id)
        if collection is None:
            return [
                SearchRoute(
                    embedding_profile=resolve_embedding_profile(None),
                    org_id=settings.default_org_id,
                    collection_id=collection_id,
                    department=department,
                )
            ]
        return [
            SearchRoute(
                embedding_profile=resolve_embedding_profile(collection.embedding_profile),
                org_id=settings.default_org_id,
                collection_id=collection.id,
                department=department,
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
            department=department,
        )
        for profile in profiles
    ]


async def _node_detect(state: ChatGraphState) -> ChatGraphState:
    body = state["body"]
    state["is_temporal"] = _detect_temporal(body.query)
    state["detected_dept"] = _detect_department(body.query)
    return state


async def _node_retrieve(state: ChatGraphState) -> ChatGraphState:
    body = state["body"]
    routes = await _load_search_routes(
        state["session"],
        body.collection_id,
        department=state["detected_dept"],
    )
    profiles = OrderedDict((route.embedding_profile, None) for route in routes)
    vectors = await asyncio.gather(
        *(embed_query(body.query, profile=profile) for profile in profiles.keys())
    )
    query_vectors = dict(zip(profiles.keys(), vectors, strict=True))
    state["raw_docs"] = await search_routes(
        state["qdrant"],
        routes,
        query_vectors,
        limit=8,
    )
    return state


async def _node_recent(state: ChatGraphState) -> ChatGraphState:
    state["recent_rows"] = []
    if not state["is_temporal"]:
        return state

    body = state["body"]
    stmt = (
        select(DocumentDB)
        .where(DocumentDB.org_id == settings.default_org_id)
        .order_by(DocumentDB.created_at.desc())
        .limit(10)
    )
    if state["detected_dept"]:
        stmt = stmt.where(DocumentDB.department == state["detected_dept"])
    elif body.collection_id and body.collection_id != "all":
        stmt = stmt.where(DocumentDB.collection_id == body.collection_id)
    result = await state["session"].execute(stmt)
    state["recent_rows"] = list(result.scalars().all())
    return state


async def _node_sources_and_messages(state: ChatGraphState) -> ChatGraphState:
    raw_docs = state["raw_docs"]
    session = state["session"]
    body = state["body"]

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
    state["sources"] = sources

    context_parts: list[str] = []
    if state["recent_rows"]:
        now = datetime.now(timezone.utc)
        recent_block = "RECENTLY ADDED TOOLS (newest first):\n" + "\n".join(
            f"- {row.tool_name or row.filename} | "
            f"Department: {row.department or 'General'} | "
            f"Added: {_format_age(row.created_at, now)} | "
            f"Rating: {row.rating}/5 | "
            f"Link: {row.tool_url or 'N/A'} | "
            f"Description: {row.short_description or row.importance_note or ''}"
            for row in state["recent_rows"]
        )
        context_parts.append(recent_block)

    if raw_docs:
        vector_block = "REFERENCE MATERIAL (by relevance):\n\n" + "\n\n".join(
            f"Reference {index + 1} "
            f"(department: {doc.get('department', 'General')}, "
            f"rating: {doc.get('rating', 0)}/5)\n"
            f"Tool: {doc.get('tool_name', 'Unknown')}\n"
            f"Description: {doc.get('short_description', '')}\n"
            f"Link: {doc.get('tool_url', '')}\n"
            f"Why it matters: {doc.get('importance_note', '')}\n"
            f"How it helps: {doc.get('impact_note', '')}\n"
            f"{doc['text']}"
            for index, doc in enumerate(raw_docs)
        )
        context_parts.append(vector_block)

    if context_parts:
        user_content = "\n\n---\n\n".join(context_parts) + f"\n\nQuestion: {body.query}"
    else:
        user_content = f"Question: {body.query}\n\n(No relevant documents found in this collection.)"

    messages = [{"role": "user", "content": user_content}]
    if body.history:
        messages = [{"role": msg.role, "content": msg.content} for msg in body.history[-4:]] + messages

    state["user_content"] = user_content
    state["messages"] = messages
    return state


_graph_builder = StateGraph(ChatGraphState)
_graph_builder.add_node("detect", _node_detect)
_graph_builder.add_node("retrieve", _node_retrieve)
_graph_builder.add_node("recent", _node_recent)
_graph_builder.add_node("assemble", _node_sources_and_messages)
_graph_builder.add_edge(START, "detect")
_graph_builder.add_edge("detect", "retrieve")
_graph_builder.add_edge("retrieve", "recent")
_graph_builder.add_edge("recent", "assemble")
_graph_builder.add_edge("assemble", END)
_chat_graph = _graph_builder.compile()


async def run_chat_graph(
    *,
    body: ChatRequest,
    session: AsyncSession,
    qdrant: AsyncQdrantClient,
) -> GraphChatResult:
    state: ChatGraphState = {
        "body": body,
        "session": session,
        "qdrant": qdrant,
        "is_temporal": False,
        "detected_dept": None,
        "raw_docs": [],
        "recent_rows": [],
        "sources": [],
        "user_content": "",
        "messages": [],
    }
    result = await _chat_graph.ainvoke(state)
    return GraphChatResult(sources=result["sources"], messages=result["messages"])
