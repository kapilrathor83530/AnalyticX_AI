from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_llm_health_returns_status():
    response = client.get("/api/v1/llm/health")
    assert response.status_code == 200
    body = response.json()
    assert "available" in body
    assert "active_model" in body


def test_agent_query_endpoint_works_without_llm():
    csv_content = "region,revenue\nNorth,100\nSouth,200\nNorth,150\n"
    upload = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    dataset_id = upload.json()["id"]

    response = client.post(
        "/api/v1/agents/query",
        json={"dataset_id": dataset_id, "question": "Which region has the highest revenue?", "use_llm": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert isinstance(body["tools_used"], list)
