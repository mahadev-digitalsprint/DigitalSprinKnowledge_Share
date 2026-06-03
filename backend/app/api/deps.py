from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import parse_access_token
from app.core.rbac import UserContext, normalize_role
from app.db import AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_qdrant(request: Request) -> AsyncQdrantClient:
    return request.app.state.qdrant


def get_current_user(request: Request) -> UserContext:
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        payload = parse_access_token(token)
        return UserContext(
            user_id=str(payload.get("sub", "")).strip() or "unknown",
            role=normalize_role(str(payload.get("role", "employee"))),
            allowed_collections={
                item.strip()
                for item in payload.get("collections", ["*"])
                if isinstance(item, str) and item.strip()
            }
            or {"*"},
        )

    user_id = (
        request.headers.get("x-user-id")
        or request.query_params.get("user_id")
        or ""
    ).strip()
    role = normalize_role(
        request.headers.get("x-user-role")
        or request.query_params.get("user_role")
        or "employee"
    )
    raw_collections = (
        request.headers.get("x-user-collections")
        or request.query_params.get("user_collections")
        or ""
    )
    if not user_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    allowed_collections = {
        item.strip() for item in raw_collections.split(",") if item.strip()
    } or {"*"}
    return UserContext(
        user_id=user_id,
        role=role,
        allowed_collections=allowed_collections,
    )


SessionDep = Annotated[AsyncSession, Depends(get_session)]
QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant)]
CurrentUserDep = Annotated[UserContext, Depends(get_current_user)]
