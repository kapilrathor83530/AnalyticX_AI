from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_workspace_crud():
    create = client.post("/api/v1/workspaces", json={"name": "Test Workspace"})
    assert create.status_code == 200
    workspace = create.json()
    workspace_id = workspace["id"]
    assert workspace["name"] == "Test Workspace"

    list_response = client.get("/api/v1/workspaces")
    assert list_response.status_code == 200
    assert any(w["id"] == workspace_id for w in list_response.json())

    update = client.put(f"/api/v1/workspaces/{workspace_id}", json={"name": "Renamed"})
    assert update.status_code == 200
    assert update.json()["name"] == "Renamed"

    delete = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert delete.status_code == 200

    missing = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert missing.status_code == 404
