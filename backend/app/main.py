"""
FastAPI application entry point.

Startup:
  1. Create local database tables
  2. Initialize embedded Qdrant collections
  3. Ensure local storage is ready
  4. Seed default collections if empty
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select, update

from app.api.chat import router as chat_router
from app.api.collections import router as collections_router
from app.api.events import router as events_router
from app.api.upload import router as upload_router
from app.config import settings
from app.core.registry import resolve_embedding_profile
from app.db import AsyncSessionLocal, CollectionDB, create_tables
from app.retrieval.qdrant import init_collections
from app.storage import ensure_storage_ready

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS = [
    {
        "id": "dept-hr",
        "name": "HR",
        "section": "Business Teams",
        "description": "Hiring, onboarding, policy, and people operations tools.",
        "color": "#ef4444",
    },
    {
        "id": "dept-marketing",
        "name": "Marketing",
        "section": "Business Teams",
        "description": "Campaign, content, SEO, and brand workflow tools.",
        "color": "#f59e0b",
    },
    {
        "id": "dept-sales",
        "name": "Sales",
        "section": "Business Teams",
        "description": "Lead generation, CRM, forecasting, and proposal tools.",
        "color": "#14b8a6",
    },
    {
        "id": "dept-operations",
        "name": "Operations",
        "section": "Business Teams",
        "description": "Operations, support, process, and delivery coordination tools.",
        "color": "#6366f1",
    },
    {
        "id": "dept-developer",
        "name": "Developers",
        "section": "Engineering",
        "description": "General engineering tools for implementation and productivity.",
        "color": "#10a37f",
    },
    {
        "id": "dept-frontend",
        "name": "Frontend",
        "section": "Engineering",
        "description": "UI engineering, component systems, and client-side tooling.",
        "color": "#0ea5e9",
    },
    {
        "id": "dept-backend",
        "name": "Backend",
        "section": "Engineering",
        "description": "APIs, data systems, integrations, and backend services.",
        "color": "#8b5cf6",
    },
    {
        "id": "dept-tester",
        "name": "QA & Testing",
        "section": "Engineering",
        "description": "Test automation, quality workflows, and validation tools.",
        "color": "#e11d48",
    },
    {
        "id": "dept-architect",
        "name": "Architecture",
        "section": "Engineering",
        "description": "Architecture design, platform planning, and systems thinking tools.",
        "color": "#22c55e",
    },
]

LEGACY_COLLECTION_UPDATES = {
    "col-general": {
        "name": "Shared Knowledge",
        "section": "Company Library",
        "description": "General internal references and cross-functional AI tool notes.",
        "color": "#10a37f",
    },
    "col-research": {
        "name": "Research",
        "section": "Company Library",
        "description": "Research papers, benchmarks, and deeper reference material.",
        "color": "#8b5cf6",
    },
    "col-notes": {
        "name": "Meeting Notes",
        "section": "Company Library",
        "description": "Meeting notes, discoveries, and shared team learnings.",
        "color": "#f59e0b",
    },
}


def _create_qdrant_client() -> AsyncQdrantClient:
    if settings.qdrant_url.lower() in {"", "local"}:
        path = Path(settings.qdrant_path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        try:
            return AsyncQdrantClient(path=str(path))
        except RuntimeError as exc:
            message = str(exc)
            if "already accessed by another instance of Qdrant client" not in message:
                raise
            raise RuntimeError(
                f"Embedded Qdrant storage at {path} is already in use. "
                "Stop any other backend process using this repo and restart. "
                "The local Qdrant mode is single-process, so multiple uvicorn instances "
                "or `--reload` against the same data directory can trigger this lock."
            ) from exc
    if settings.qdrant_url == ":memory:":
        return AsyncQdrantClient(location=":memory:")
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.strip() or None,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    logger.info("Database ready")

    qdrant = _create_qdrant_client()
    await init_collections(qdrant)
    app.state.qdrant = qdrant
    logger.info("Vector store ready")

    app.state.storage = ensure_storage_ready()
    logger.info("Local storage ready")

    async with AsyncSessionLocal() as session:
        existing_ids = {row[0] for row in (await session.execute(select(CollectionDB.id))).all()}
        for collection_id, attrs in LEGACY_COLLECTION_UPDATES.items():
            if collection_id not in existing_ids:
                continue
            await session.execute(
                update(CollectionDB).where(CollectionDB.id == collection_id).values(**attrs)
            )

        added = 0
        for collection in DEFAULT_COLLECTIONS:
            if collection["id"] in existing_ids:
                continue
            session.add(
                CollectionDB(
                    id=collection["id"],
                    org_id=settings.default_org_id,
                    name=collection["name"],
                    description=collection["description"],
                    color=collection["color"],
                    section=collection["section"],
                    embedding_profile=resolve_embedding_profile(None),
                )
            )
            added += 1

        if added:
            logger.info("Seeded %d default collections", added)
        await session.commit()

    yield

    await qdrant.close()
    logger.info("Shutdown complete")


app = FastAPI(title="Tool Knowledge RAG API", version="3.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(collections_router)
app.include_router(events_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
