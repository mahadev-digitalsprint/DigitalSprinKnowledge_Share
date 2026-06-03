from __future__ import annotations

import pytest

from app.core.parsers.base import ParsedPage
from app.ingestion.chunker import Chunk, chunk_pages


def make_page(text: str, page: int = 1) -> ParsedPage:
    return ParsedPage(page=page, text=text)


def test_empty_pages_returns_empty():
    result = chunk_pages([], doc_id="d1", collection_id="c1", org_id="org1")
    assert result == []


def test_whitespace_only_page_skipped():
    pages = [make_page("   \n\t  ")]
    result = chunk_pages(pages, doc_id="d1", collection_id="c1", org_id="org1")
    assert result == []


def test_single_short_text_one_chunk():
    pages = [make_page("hello world")]
    result = chunk_pages(pages, doc_id="d1", collection_id="c1", org_id="org1")
    assert len(result) == 1
    assert result[0].text == "hello world"
    assert result[0].chunk_index == 0
    assert result[0].page == 1


def test_long_text_creates_multiple_chunks():
    # fast budget=512 tokens; use 600 words to guarantee multiple chunks
    words = " ".join(f"word{i}" for i in range(600))
    pages = [make_page(words)]
    result = chunk_pages(
        pages,
        doc_id="d1",
        collection_id="c1",
        org_id="org1",
        quality="fast",
    )
    assert len(result) > 1


def test_chunks_have_unique_ids():
    words = " ".join(f"w{i}" for i in range(300))
    pages = [make_page(words)]
    result = chunk_pages(pages, doc_id="d1", collection_id="c1", org_id="org1")
    ids = [c.id for c in result]
    assert len(ids) == len(set(ids))


def test_chunk_indices_are_sequential():
    words = " ".join(f"w{i}" for i in range(300))
    pages = [make_page(words)]
    result = chunk_pages(pages, doc_id="d1", collection_id="c1", org_id="org1")
    for i, chunk in enumerate(result):
        assert chunk.chunk_index == i


def test_metadata_propagated_to_chunks():
    pages = [make_page("some text")]
    result = chunk_pages(
        pages,
        doc_id="doc-42",
        collection_id="col-7",
        org_id="org-1",
        quality="high",
        record_kind="tool",
        tool_name="MyTool",
        tool_url="https://example.com",
        department="Engineering",
        primary_role="developer",
        audience_roles=["dev", "qa"],
        importance_note="critical",
        impact_note="saves hours",
        rating=5,
    )
    assert len(result) == 1
    c = result[0]
    assert c.doc_id == "doc-42"
    assert c.collection_id == "col-7"
    assert c.org_id == "org-1"
    assert c.quality == "high"
    assert c.record_kind == "tool"
    assert c.tool_name == "MyTool"
    assert c.tool_url == "https://example.com"
    assert c.department == "Engineering"
    assert c.primary_role == "developer"
    assert c.audience_roles == ["dev", "qa"]
    assert c.importance_note == "critical"
    assert c.impact_note == "saves hours"
    assert c.rating == 5


def test_custom_token_budget_respected():
    # 6 tokens, budget=2 overlap=0 → 3 chunks
    pages = [make_page("a b c d e f")]
    result = chunk_pages(
        pages,
        doc_id="d1",
        collection_id="c1",
        org_id="o1",
        max_tokens=2,
        overlap=0,
    )
    assert len(result) == 3


def test_overlap_produces_repeated_tokens():
    # 4 tokens, budget=3, overlap=1 → chunk1: tok[0:3], chunk2: tok[2:5] but only 4 tokens so tok[2:4]
    pages = [make_page("a b c d")]
    result = chunk_pages(
        pages,
        doc_id="d1",
        collection_id="c1",
        org_id="o1",
        max_tokens=3,
        overlap=1,
    )
    # chunk1 ends with "c", chunk2 starts with "c" (overlap)
    assert len(result) == 2
    assert "c" in result[0].text
    assert "c" in result[1].text


def test_multiple_pages_tracked():
    pages = [make_page("page one text", page=1), make_page("page two text", page=2)]
    result = chunk_pages(pages, doc_id="d1", collection_id="c1", org_id="o1")
    pages_seen = {c.page for c in result}
    assert 1 in pages_seen
    assert 2 in pages_seen


def test_quality_fast_uses_smaller_budget():
    words = " ".join(f"w{i}" for i in range(700))
    pages = [make_page(words)]
    fast_chunks = chunk_pages(
        pages, doc_id="d", collection_id="c", org_id="o", quality="fast"
    )
    high_chunks = chunk_pages(
        pages, doc_id="d", collection_id="c", org_id="o", quality="high"
    )
    # fast has smaller budget → more chunks
    assert len(fast_chunks) >= len(high_chunks)


def test_chunk_is_dataclass_instance():
    pages = [make_page("hello")]
    result = chunk_pages(pages, doc_id="d", collection_id="c", org_id="o")
    assert isinstance(result[0], Chunk)


def test_bbox_from_page():
    page = ParsedPage(page=1, text="text", bbox=[0.0, 1.0, 2.0, 3.0])
    result = chunk_pages([page], doc_id="d", collection_id="c", org_id="o")
    assert result[0].bbox == [0.0, 1.0, 2.0, 3.0]


def test_tags_from_page_metadata():
    page = ParsedPage(page=1, text="text", metadata={"tags": ["ai", "tool"]})
    result = chunk_pages([page], doc_id="d", collection_id="c", org_id="o")
    assert result[0].tags == ["ai", "tool"]


def test_audience_roles_default_empty():
    pages = [make_page("text")]
    result = chunk_pages(pages, doc_id="d", collection_id="c", org_id="o")
    assert result[0].audience_roles == []


def test_source_path_propagated():
    pages = [make_page("text")]
    result = chunk_pages(
        pages, doc_id="d", collection_id="c", org_id="o", source_path="/tmp/file.pdf"
    )
    assert result[0].source_path == "/tmp/file.pdf"
