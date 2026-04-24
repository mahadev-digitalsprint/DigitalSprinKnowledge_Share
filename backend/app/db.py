from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return

    database = url.database or ""
    if not database or database == ":memory:":
        return

    if len(database) >= 4 and database[0] == "/" and database[2] == ":" and database[3] in "\\/":
        database = database[1:]

    db_path = Path(database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)

engine_kwargs = {"echo": False}
if not settings.database_url.startswith("sqlite"):
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.database_url, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CollectionDB(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_profile: Mapped[str] = mapped_column(String, default="openai-small")
    section: Mapped[str] = mapped_column(String, default="General")
    color: Mapped[str] = mapped_column(String, default="#10a37f")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class DocumentDB(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, index=True)
    collection_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collections.id", ondelete="CASCADE"),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="queued")
    quality: Mapped[str] = mapped_column(String, default="fast")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    record_kind: Mapped[str] = mapped_column(String, default="document")
    tool_name: Mapped[str] = mapped_column(String, default="")
    tool_url: Mapped[str] = mapped_column(String, default="")
    short_description: Mapped[str] = mapped_column(String, default="")
    department: Mapped[str] = mapped_column(String, default="")
    primary_role: Mapped[str] = mapped_column(String, default="")
    audience_roles: Mapped[str] = mapped_column(String, default="")
    importance_note: Mapped[str] = mapped_column(String, default="")
    impact_note: Mapped[str] = mapped_column(String, default="")
    rating: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def _ensure_column(sync_conn, table_name: str, column_name: str, definition: str) -> None:
    existing = {column["name"] for column in inspect(sync_conn).get_columns(table_name)}
    if column_name in existing:
        return
    sync_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


def _run_schema_updates(sync_conn) -> None:
    _ensure_column(sync_conn, "collections", "section", "VARCHAR DEFAULT 'General'")
    _ensure_column(sync_conn, "documents", "record_kind", "VARCHAR DEFAULT 'document'")
    _ensure_column(sync_conn, "documents", "tool_name", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "tool_url", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "short_description", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "department", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "primary_role", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "audience_roles", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "importance_note", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "impact_note", "VARCHAR DEFAULT ''")
    _ensure_column(sync_conn, "documents", "rating", "INTEGER DEFAULT 0")


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_schema_updates)
        await conn.execute(
            text(
                "UPDATE documents SET record_kind = 'document' "
                "WHERE record_kind IS NULL OR record_kind = ''"
            )
        )
        await conn.execute(text("UPDATE documents SET tool_name = '' WHERE tool_name IS NULL"))
        await conn.execute(text("UPDATE documents SET tool_url = '' WHERE tool_url IS NULL"))
        await conn.execute(
            text("UPDATE documents SET short_description = '' WHERE short_description IS NULL")
        )
        await conn.execute(text("UPDATE documents SET department = '' WHERE department IS NULL"))
        await conn.execute(
            text("UPDATE documents SET primary_role = '' WHERE primary_role IS NULL")
        )
        await conn.execute(
            text("UPDATE documents SET audience_roles = '' WHERE audience_roles IS NULL")
        )
        await conn.execute(
            text("UPDATE documents SET importance_note = '' WHERE importance_note IS NULL")
        )
        await conn.execute(
            text("UPDATE documents SET impact_note = '' WHERE impact_note IS NULL")
        )
        await conn.execute(text("UPDATE documents SET rating = 0 WHERE rating IS NULL"))
