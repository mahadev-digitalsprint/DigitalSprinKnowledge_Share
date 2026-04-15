"""
FastAPI application entry point.

Startup:
  1. Create Postgres tables
  2. Init Qdrant collection + indexes
  3. Ensure MinIO bucket exists
  4. Seed default collections if empty
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from qdrant_client import AsyncQdrantClient
from sqlalchemy import func, select

from app.api.chat import router as chat_router
from app.api.collections import router as collections_router
from app.api.events import router as events_router
from app.api.upload import router as upload_router
from app.config import settings
from app.core.registry import resolve_embedding_profile
from app.db import AsyncSessionLocal, CollectionDB, create_tables
from app.retrieval.qdrant import init_collections

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS = [
    {"id": "col-general", "name": "General", "color": "#10a37f"},
    {"id": "col-research", "name": "Research Papers", "color": "#8b5cf6"},
    {"id": "col-notes", "name": "Meeting Notes", "color": "#f59e0b"},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Postgres ──────────────────────────────────────────────────────────────
    await create_tables()
    logger.info("Postgres tables ready")

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    await init_collections(qdrant)
    app.state.qdrant = qdrant
    logger.info("Qdrant ready")

    # ── MinIO ─────────────────────────────────────────────────────────────────
    minio = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )
    if not minio.bucket_exists(settings.minio_bucket):
        minio.make_bucket(settings.minio_bucket)
        logger.info("MinIO bucket '%s' created", settings.minio_bucket)
    app.state.minio = minio
    logger.info("MinIO ready")

    # ── Seed default collections ──────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            select(func.count()).select_from(CollectionDB)
        )
        if count_result.scalar() == 0:
            for c in DEFAULT_COLLECTIONS:
                session.add(
                    CollectionDB(
                        id=c["id"],
                        org_id=settings.default_org_id,
                        name=c["name"],
                        color=c["color"],
                        embedding_profile=resolve_embedding_profile(None),
                    )
                )
            await session.commit()
            logger.info("Seeded %d default collections", len(DEFAULT_COLLECTIONS))

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await qdrant.close()
    logger.info("Shutdown complete")


app = FastAPI(title="digitalsprint.ai RAG API", version="3.0.0", lifespan=lifespan)

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
