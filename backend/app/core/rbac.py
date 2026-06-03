from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class UserContext:
    user_id: str
    role: str
    allowed_collections: set[str]


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "employee": {
        "chat:read",
        "collections:read",
        "documents:read",
        "events:read",
    },
    "admin": {
        "chat:read",
        "chat:write",
        "collections:read",
        "collections:write",
        "documents:read",
        "documents:write",
        "documents:delete",
        "events:read",
        "admin:*",
    },
}


def normalize_role(raw_role: str) -> str:
    role = (raw_role or "").strip().lower()
    if role in {"viewer", "editor", "user"}:
        role = "employee"
    if role in ROLE_PERMISSIONS:
        return role
    return "employee"


def has_permission(user: UserContext, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(user.role, set())
    return permission in permissions or "admin:*" in permissions


def require_permission(user: UserContext, permission: str) -> None:
    if has_permission(user, permission):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied: {permission}",
    )


def ensure_collection_access(user: UserContext, collection_id: str) -> None:
    if collection_id == "all":
        if "*" in user.allowed_collections:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collection access denied: all",
        )
    if user.role == "admin":
        return
    if "*" in user.allowed_collections or collection_id in user.allowed_collections:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Collection access denied: {collection_id}",
    )
