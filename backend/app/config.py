from __future__ import annotations

import json
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _resolve_path(value: str, *, prefer_backend: bool = False) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)

    project_candidate = (PROJECT_ROOT / path).resolve()
    backend_candidate = (BACKEND_ROOT / path).resolve()

    if project_candidate.exists():
        return str(project_candidate)
    if backend_candidate.exists():
        return str(backend_candidate)
    return str(backend_candidate if prefer_backend else project_candidate)


def _normalize_sqlite_url(value: str) -> str:
    url = make_url(value)
    if not url.drivername.startswith("sqlite"):
        return value

    database = url.database or ""
    if not database or database == ":memory:":
        return value

    if len(database) >= 4 and database[0] == "/" and database[2] == ":" and database[3] in "\\/":
        database = database[1:]

    database_path = Path(database)
    if not database_path.is_absolute():
        database_path = (PROJECT_ROOT / database_path).resolve()

    return str(url.set(database=database_path.as_posix()))


class Settings(BaseSettings):
    openai_api_key: str = ""
    gemini_api_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    qdrant_url: str = "local"
    qdrant_api_key: str = ""
    qdrant_path: str = "./data/qdrant"
    local_storage_path: str = "./data/storage"

    cors_origins: str | list[str] = ["http://localhost:3000"]
    default_org_id: str = "default-org"

    registry_path: str = "config/registry.yaml"
    max_inline_upload_mb: int = 10
    sse_heartbeat_seconds: int = 15

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("registry_path", mode="before")
    @classmethod
    def normalize_registry_path(cls, value: str) -> str:
        return _resolve_path(value, prefer_backend=True)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _normalize_sqlite_url(value)

    @field_validator("qdrant_path", "local_storage_path", mode="before")
    @classmethod
    def normalize_local_paths(cls, value: str) -> str:
        return _resolve_path(value)

    model_config = {"env_file": str(PROJECT_ROOT / ".env"), "extra": "ignore"}


settings = Settings()
