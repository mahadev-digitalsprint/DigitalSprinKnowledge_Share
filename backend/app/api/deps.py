from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_qdrant(request: Request) -> AsyncQdrantClient:
    return request.app.state.qdrant


SessionDep = Annotated[AsyncSession, Depends(get_session)]
QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant)]
