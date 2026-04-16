from __future__ import annotations

import json
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cohere_api_key: str = ""
    llama_cloud_api_key: str = ""

    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379"
    qdrant_url: str = "http://localhost:6333"
    qdrant_path: str = "./data/qdrant"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "documents"
    minio_use_ssl: bool = False
    storage_provider: str = "minio"
    local_storage_path: str = "./data/storage"

    cors_origins: list[str] = ["http://localhost:3000"]
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
        path = Path(value)
        if not path.is_absolute():
            return str(path)
        return value

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
