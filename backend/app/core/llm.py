from __future__ import annotations

from functools import lru_cache

from google import genai
from openai import AsyncOpenAI

from app.config import settings
from app.core.http import get_async_http_client
from app.core.registry import get_llm_target


def require_openai_api_key() -> str:
    api_key = settings.openai_api_key.strip()
    if not api_key or api_key == "sk-..." or "your-openai-key" in api_key.lower():
        raise RuntimeError("OPENAI_API_KEY is not configured. Set a real key in .env.")
    return api_key


def require_gemini_api_key() -> str:
    api_key = settings.gemini_api_key.strip()
    if not api_key or "your-gemini-key" in api_key.lower():
        raise RuntimeError("GEMINI_API_KEY is not configured. Set a real key in .env.")
    return api_key


@lru_cache(maxsize=1)
def get_openai() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=require_openai_api_key(),
        http_client=get_async_http_client(),
    )


@lru_cache(maxsize=1)
def get_gemini() -> genai.Client:
    return genai.Client(api_key=require_gemini_api_key())


def resolve_chat_target(
    requested_provider: str,
    requested_model: str,
    *,
    default_target: str = "chat_default",
) -> tuple[str, str]:
    normalized_provider = requested_provider.strip().lower()
    if normalized_provider in {"openai", "gemini"} and requested_model:
        return normalized_provider, requested_model

    target = get_llm_target(default_target)
    return target.provider, target.model


def resolve_chat_model(
    requested_provider: str,
    requested_model: str,
    *,
    default_target: str = "chat_default",
) -> str:
    return resolve_chat_target(
        requested_provider,
        requested_model,
        default_target=default_target,
    )[1]
