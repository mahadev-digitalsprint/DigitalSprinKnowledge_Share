from __future__ import annotations

from functools import lru_cache

import httpx


@lru_cache(maxsize=1)
def get_async_http_client() -> httpx.AsyncClient:
    # Ignore broken machine-level proxy variables so local runs can reach model APIs.
    return httpx.AsyncClient(trust_env=False, timeout=60.0)
