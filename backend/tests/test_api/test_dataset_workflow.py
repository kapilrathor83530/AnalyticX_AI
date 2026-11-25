from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_csv_preview_profile_and_eda() -> None:
    csv_content = "revenue,region\n100,North\n200,South\n300,North\n"
    upload = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 200
    dataset = upload.json()
    dataset_id = dataset["id"]
    assert dataset["row_count"] == 3
    assert dataset["column_count"] == 2
    assert client.get(f"/api/v1/datasets/{dataset_id}/preview").json()["returned_rows"] == 3
    assert client.get(f"/api/v1/datasets/{dataset_id}/profile").json()["row_count"] == 3
    assert "numeric_summary" in client.get(f"/api/v1/datasets/{dataset_id}/eda").json()
    assert client.delete(f"/api/v1/datasets/{dataset_id}").status_code == 200
