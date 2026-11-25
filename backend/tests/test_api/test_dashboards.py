from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _upload_sample():
    csv_content = "region,revenue\nNorth,100\nSouth,200\nNorth,150\n"
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    return response.json()["id"]


def test_create_list_update_delete_dashboard():
    dataset_id = _upload_sample()

    create = client.post(
        "/api/v1/dashboards",
        json={"dataset_id": dataset_id, "name": "Sales Overview"},
    )
    assert create.status_code == 200
    dashboard = create.json()
    dashboard_id = dashboard["id"]

    list_response = client.get("/api/v1/dashboards", params={"dataset_id": dataset_id})
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    update = client.put(f"/api/v1/dashboards/{dashboard_id}", json={"name": "Renamed"})
    assert update.status_code == 200
    assert update.json()["name"] == "Renamed"

    delete = client.delete(f"/api/v1/dashboards/{dashboard_id}")
    assert delete.status_code == 200


def test_widget_crud_and_layout():
    dataset_id = _upload_sample()
    dashboard_id = client.post(
        "/api/v1/dashboards",
        json={"dataset_id": dataset_id, "name": "Test Dashboard"},
    ).json()["id"]

    widget = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "chart_type": "bar",
            "title": "Revenue by Region",
            "config": {},
            "data_mapping": {"x": "region", "y": "revenue"},
            "position": {"x": 0, "y": 0},
            "size": {"w": 6, "h": 4},
        },
    )
    assert widget.status_code == 200
    widget_id = widget.json()["id"]

    widgets = client.get(f"/api/v1/dashboards/{dashboard_id}/widgets")
    assert widgets.status_code == 200
    assert len(widgets.json()) == 1

    update = client.put(
        f"/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}",
        json={"title": "Updated Title"},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "Updated Title"

    layout = client.put(
        f"/api/v1/dashboards/{dashboard_id}/layout",
        json={"layout_config": {"cols": 12, "rowHeight": 40}},
    )
    assert layout.status_code == 200
    assert layout.json()["layout_config"]["cols"] == 12

    delete = client.delete(f"/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}")
    assert delete.status_code == 200


def test_visualization_endpoints():
    dataset_id = _upload_sample()

    charts = client.get("/api/v1/visualizations/charts")
    assert charts.status_code == 200
    assert any(c["id"] == "bar" for c in charts.json())

    validate = client.post(
        "/api/v1/visualizations/validate",
        json={
            "dataset_id": dataset_id,
            "config": {
                "chart_type": "bar",
                "data_mapping": {"x": "region", "y": "revenue"},
                "aggregation": "sum",
            },
        },
    )
    assert validate.status_code == 200
    assert validate.json()["valid"] is True

    render = client.post(
        "/api/v1/visualizations/render",
        json={
            "dataset_id": dataset_id,
            "config": {
                "chart_type": "bar",
                "data_mapping": {"x": "region", "y": "revenue"},
                "aggregation": "sum",
            },
        },
    )
    assert render.status_code == 200
    assert len(render.json()["data"]) >= 1
