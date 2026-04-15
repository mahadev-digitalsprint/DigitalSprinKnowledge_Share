from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import settings
from app.core.registry import get_llm_target


@lru_cache(maxsize=1)
def get_anthropic() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


@lru_cache(maxsize=1)
def get_openai() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


def resolve_provider_model(
    provider: str,
    model: str,
    *,
    default_target: str = "chat_default",
) -> tuple[str, str]:
    if provider and model:
        return provider, model

    target = get_llm_target(default_target)
    return provider or target.provider, model or target.model
