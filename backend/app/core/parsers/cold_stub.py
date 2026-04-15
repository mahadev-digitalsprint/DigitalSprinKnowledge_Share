"""
Cold-path parser stub — LlamaParse integration placeholder.

When LLAMA_CLOUD_API_KEY is set in .env this module will call the real API.
For now it logs intent and returns the fast-parse result unchanged so the
system stays fully functional without the key.

To wire the real API:
  1. pip install llama-parse
  2. Set LLAMA_CLOUD_API_KEY in .env
  3. Replace the body of ColdParser.parse() below.
"""
from __future__ import annotations

import logging

from app.core.parsers.base import ParsedPage
from app.core.parsers.fast import FastParser

logger = logging.getLogger(__name__)


class ColdParser:
    """Upgrades low-quality fast-parse results with LlamaParse (API-based)."""

    @property
    def name(self) -> str:
        return "llamaparse-stub"

    def parse(self, content: bytes, filename: str) -> list[ParsedPage]:
        logger.info(
            "ColdParser: LlamaParse not yet wired — falling back to FastParser for %s. "
            "Set LLAMA_CLOUD_API_KEY and replace this stub to enable premium parsing.",
            filename,
        )
        return FastParser().parse(content, filename)

    # ── future real implementation ────────────────────────────────────────────
    # async def _parse_via_api(self, content: bytes, filename: str) -> list[ParsedPage]:
    #     from llama_parse import LlamaParse
    #     import tempfile, os
    #     parser = LlamaParse(result_type="markdown", api_key=settings.llama_cloud_api_key)
    #     with tempfile.NamedTemporaryFile(suffix=f".{filename.rsplit('.',1)[-1]}", delete=False) as f:
    #         f.write(content); tmp = f.name
    #     try:
    #         docs = await parser.aload_data(tmp)
    #         return [ParsedPage(page=i+1, text=d.text) for i, d in enumerate(docs)]
    #     finally:
    #         os.unlink(tmp)
