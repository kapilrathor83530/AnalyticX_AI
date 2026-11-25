from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _upload(rows: str):
    csv = "date,revenue,cost\n" + rows
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("forecast.csv", csv, "text/csv")},
    )
    return response.json()["id"]


def test_forecast_train_endpoint():
    dataset_id = _upload(
        "\n".join(
            f"2022-{month:02d}-01,{100 + month * 10},{40 + month * 5}" for month in range(1, 13)
        )
    )

    response = client.post(
        "/api/v1/forecasting/train",
        json={
            "dataset_id": dataset_id,
            "date_column": "date",
            "target_column": "revenue",
            "horizon": 3,
            "frequency": "M",
            "model_type": "linear",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["model_type"] == "linear"
    assert len(body["predictions"]) == 3


def test_scenario_endpoint():
    dataset_id = _upload("2022-01-01,1000,400\n2022-02-01,2000,800\n2022-03-01,1500,600\n")

    response = client.post(
        "/api/v1/simulation/scenario",
        json={
            "dataset_id": dataset_id,
            "name": "Price +5%",
            "metric_columns": {"revenue": "revenue", "cost": "cost"},
            "adjustments": [{"field": "revenue", "mode": "percent", "value": 5}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Price +5%"
    assert "results" in body
