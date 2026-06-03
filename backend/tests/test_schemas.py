from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    ChatRequest,
    CollectionCreate,
    DocumentOut,
    UploadAccepted,
)


def test_collection_create_defaults():
    c = CollectionCreate(name="Test")
    assert c.name == "Test"
    assert c.description == ""
    assert c.color == "#10a37f"
    assert c.is_public is True
    assert c.section == "General"
    assert c.embedding_profile is None


def test_collection_create_custom():
    c = CollectionCreate(
        name="HR",
        description="Human resources",
        color="#ff0000",
        is_public=False,
        section="Business",
        embedding_profile="openai-small",
    )
    assert c.name == "HR"
    assert c.color == "#ff0000"
    assert c.is_public is False
    assert c.section == "Business"
    assert c.embedding_profile == "openai-small"


def test_document_out_audience_roles_from_comma_string(sample_doc_dict):
    doc = DocumentOut(**{**sample_doc_dict, "audience_roles": "dev, ops, qa"})
    assert doc.audience_roles == ["dev", "ops", "qa"]


def test_document_out_audience_roles_from_list(sample_doc_dict):
    doc = DocumentOut(**{**sample_doc_dict, "audience_roles": ["dev", "ops"]})
    assert doc.audience_roles == ["dev", "ops"]


def test_document_out_audience_roles_empty_string(sample_doc_dict):
    doc = DocumentOut(**{**sample_doc_dict, "audience_roles": ""})
    assert doc.audience_roles == []


def test_document_out_audience_roles_strips_whitespace(sample_doc_dict):
    doc = DocumentOut(**{**sample_doc_dict, "audience_roles": " dev , ops "})
    assert doc.audience_roles == ["dev", "ops"]


def test_chat_request_defaults():
    req = ChatRequest(query="hello")
    assert req.query == "hello"
    assert req.collection_id == "all"
    assert req.session_id == ""
    assert req.provider == ""
    assert req.model == ""
    assert req.web_search is False
    assert req.history == []


def test_chat_request_custom():
    req = ChatRequest(
        query="test",
        collection_id="dept-hr",
        provider="openai",
        model="gpt-4",
        web_search=True,
    )
    assert req.collection_id == "dept-hr"
    assert req.provider == "openai"
    assert req.model == "gpt-4"
    assert req.web_search is True


def test_upload_accepted_defaults():
    u = UploadAccepted(doc_id="abc", filename="file.pdf", collection_id="col-1")
    assert u.record_kind == "document"
    assert u.tool_name == ""
    assert u.tool_url == ""
    assert u.short_description == ""
    assert u.department == ""


@pytest.fixture
def sample_doc_dict():
    return {
        "id": "doc-1",
        "collection_id": "col-1",
        "filename": "test.pdf",
        "file_size": 1024,
        "status": "searchable",
        "quality": "fast",
        "chunk_count": 5,
        "record_kind": "document",
        "tool_name": "",
        "tool_url": "",
        "short_description": "",
        "department": "",
        "primary_role": "",
        "audience_roles": [],
        "importance_note": "",
        "impact_note": "",
        "rating": 0,
        "created_at": "2024-01-01T00:00:00",
    }
