"""
Comprehensive Automated Test Suite for Apple Notes MCP & REST API.
Verifies Bridge, MCP tools, and FastAPI REST endpoints including Swagger UI.
"""

import pytest
import uuid
from starlette.testclient import TestClient
from api import app
from notes_bridge import AppleNotesBridge
from mcp_server import server


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def bridge():
    return AppleNotesBridge()


def test_health_endpoint(client):
    """Verify system health endpoint connects to Apple Notes."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "Notes"


def test_swagger_documentation(client):
    """Verify Swagger UI and OpenAPI specifications are generated and accessible."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger" in docs_resp.text.lower()

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "Apple Notes API & MCP Hub"
    assert "/api/notes" in schema["paths"]


def test_folders_api(client):
    """Verify folder listing."""
    response = client.get("/api/folders")
    assert response.status_code == 200
    folders = response.json()
    assert isinstance(folders, list)
    assert len(folders) >= 1


def test_full_rest_crud_lifecycle(client):
    """Verify creating, reading, updating, searching, and deleting a note via REST."""
    unique_suffix = str(uuid.uuid4())[:8]
    test_title = f"Pytest Note {unique_suffix}"
    initial_body = "This is a test note created during pytest."

    # 1. Create
    create_resp = client.post("/api/notes", json={
        "title": test_title,
        "body": initial_body
    })
    assert create_resp.status_code == 201
    created_note = create_resp.json()
    note_id = created_note["id"]
    assert created_note["name"] == test_title

    try:
        # 2. Read by ID
        get_id_resp = client.get(f"/api/notes/{note_id}")
        assert get_id_resp.status_code == 200
        assert test_title in get_id_resp.json()["plaintext"]

        # 3. Read by Title
        get_title_resp = client.get(f"/api/notes/by-title/{test_title}")
        assert get_title_resp.status_code == 200
        assert get_title_resp.json()["id"] == note_id

        # 4. Search
        search_resp = client.get("/api/notes", params={"search": unique_suffix})
        assert search_resp.status_code == 200
        matches = search_resp.json()
        assert any(n["id"] == note_id for n in matches)

        # 5. Update (append)
        update_resp = client.put(f"/api/notes/{note_id}", json={
            "body": "Appended second test line.",
            "append": True
        })
        assert update_resp.status_code == 200
        assert "Appended second test line" in update_resp.json()["plaintext"]

    finally:
        # 6. Delete
        del_resp = client.delete(f"/api/notes/{note_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_mcp_tools():
    """Verify MCP server exposes all required tools."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    required_tools = {
        "code_mode",
        "list_notes",
        "read_note",
        "create_note",
        "update_note",
        "delete_note",
        "list_folders",
        "create_folder"
    }
    assert required_tools.issubset(tool_names), f"Missing tools: {required_tools - tool_names}"


def test_codemode_python_execution(client):
    """Verify executing Python in Code Mode via REST endpoint."""
    script = """
notes_list = codemode.list_notes(limit=5)
print(f"CodeMode Python: Found {len(notes_list)} notes")
"""
    resp = client.post("/api/codemode", json={"code": script})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "CodeMode Python: Found" in data["output"]


def test_codemode_python_multistep_lifecycle(client):
    """Verify full multi-step lifecycle in a single Python Code Mode execution."""
    script = """
import uuid
uid = str(uuid.uuid4())[:6]
title = f"Pure Python CodeMode {uid}"

# 1. Create note
created = codemode.create_note(title=title, body="Initial line from Code Mode")
print("Created:", created["name"])

# 2. Append content
updated = codemode.update_note(id=created["id"], body="Appended line in same script", append=True)
print("Updated successfully")

# 3. Read it back
read_back = codemode.read_note(id=created["id"])
print("Has appended line:", "Appended line in same script" in read_back["plaintext"])

# 4. Clean up / delete
del_res = codemode.delete_note(id=created["id"])
print("Deleted:", del_res["success"])
"""
    resp = client.post("/api/codemode", json={"code": script})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Created: Pure Python CodeMode" in data["output"]
    assert "Has appended line: True" in data["output"]
    assert "Deleted: True" in data["output"]


