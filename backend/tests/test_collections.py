from __future__ import annotations

import pytest


async def test_list_collections_empty(client):
    resp = await client.get("/api/collections")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_collection_returns_201(client):
    payload = {"name": "Test Collection", "description": "A test", "color": "#ff0000"}
    resp = await client.post("/api/collections", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Collection"
    assert data["description"] == "A test"
    assert data["color"] == "#ff0000"
    assert "id" in data
    assert data["doc_count"] == 0


async def test_list_collections_returns_created(client):
    await client.post("/api/collections", json={"name": "Alpha"})
    await client.post("/api/collections", json={"name": "Beta"})

    resp = await client.get("/api/collections")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Alpha" in names
    assert "Beta" in names


async def test_create_collection_defaults(client):
    resp = await client.post("/api/collections", json={"name": "Minimal"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_public"] is True
    assert data["section"] == "General"
    assert data["color"] == "#10a37f"


async def test_create_collection_custom_section(client):
    payload = {"name": "Engineering", "section": "Tech", "is_public": False}
    resp = await client.post("/api/collections", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["section"] == "Tech"
    assert data["is_public"] is False


async def test_get_collection_summary_not_found(client):
    resp = await client.get("/api/collections/nonexistent-id/summary")
    assert resp.status_code == 404


async def test_get_collection_summary_empty(client):
    create_resp = await client.post(
        "/api/collections", json={"name": "Empty Collection"}
    )
    coll_id = create_resp.json()["id"]

    resp = await client.get(f"/api/collections/{coll_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["collection_id"] == coll_id
    assert data["collection_name"] == "Empty Collection"
    assert data["tool_count"] == 0
    assert data["document_count"] == 0
    assert data["tools"] == []
    assert data["documents"] == []


async def test_get_collection_summary_all(client):
    resp = await client.get("/api/collections/all/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["collection_id"] == "all"
    assert data["collection_name"] == "All Documents"


async def test_delete_collection(client):
    create_resp = await client.post("/api/collections", json={"name": "ToDelete"})
    coll_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/collections/{coll_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/collections")
    ids = [c["id"] for c in list_resp.json()]
    assert coll_id not in ids


async def test_delete_collection_not_found(client):
    resp = await client.delete("/api/collections/does-not-exist")
    assert resp.status_code == 404


async def test_collection_id_is_uuid_format(client):
    resp = await client.post("/api/collections", json={"name": "UUID Check"})
    data = resp.json()
    parts = data["id"].split("-")
    assert len(parts) == 5


async def test_create_multiple_collections_unique_ids(client):
    r1 = await client.post("/api/collections", json={"name": "Col1"})
    r2 = await client.post("/api/collections", json={"name": "Col2"})
    assert r1.json()["id"] != r2.json()["id"]
