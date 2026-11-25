from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _upload():
    csv = "region,revenue,cost\nNorth,100,40\nSouth,200,80\nNorth,150,60\n"
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample.csv", csv, "text/csv")},
    )
    return response.json()["id"]


def test_export_dataset_csv():
    dataset_id = _upload()
    response = client.get(f"/api/v1/reports/dataset/{dataset_id}/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "region" in response.text


def test_report_metadata():
    dataset_id = _upload()
    response = client.get(f"/api/v1/reports/metadata/{dataset_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["generator"] == "Analyticx AI"
    assert "generated_at" in body

def test_export_pdf():
    dataset_id = _upload()
    response = client.post(f"/api/v1/reports/dataset/{dataset_id}/pdf", json={})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
