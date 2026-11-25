import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _upload_test_dataset():
    csv_content = (
        "Order_ID,Category,Product,Sales,Profit,Discount,Order_Date\n"
        "101,Tech,Laptop,1200,300,0.1,2024-01-15\n"
        "102,Office,Binder,45,15,0.0,2024-01-20\n"
        "103,Tech,Smartphone,800,200,0.25,2024-02-10\n"
        "104,Furniture,Desk,450,80,0.15,2024-02-18\n"
        "105,Tech,Monitor,350,90,0.05,2024-03-01\n"
        "106,Furniture,Chair,150,30,0.0,2024-03-12\n"
        "107,Office,Paper,30,10,0.0,2024-03-22\n"
        "108,Tech,Tablet,500,120,0.2,2024-04-05\n"
    )
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("ecommerce_test.csv", csv_content, "text/csv")},
    )
    assert res.status_code == 200
    return res.json()["id"]


def test_natural_language_to_sql_top_n():
    dataset_id = _upload_test_dataset()

    res = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/generate",
        json={"prompt": "show top 5 products by sales"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "SELECT" in data["sql"]
    assert "LIMIT 5" in data["sql"]
    assert "Product" in data["sql"] or "Sales" in data["sql"]
    assert data["query_type"] == "ranking"
    assert len(data["explanation"]) > 10


def test_natural_language_to_sql_aggregations_and_quality():
    dataset_id = _upload_test_dataset()

    # Total count
    res_count = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/generate",
        json={"prompt": "count total records"},
    )
    assert res_count.status_code == 200
    assert "COUNT(*)" in res_count.json()["sql"]

    # Missing values
    res_missing = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/generate",
        json={"prompt": "find missing values in Product"},
    )
    assert res_missing.status_code == 200
    assert "IS NULL" in res_missing.json()["sql"]

    # Duplicates
    res_dup = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/generate",
        json={"prompt": "find duplicates in Category"},
    )
    assert res_dup.status_code == 200
    assert "HAVING COUNT(*) > 1" in res_dup.json()["sql"]


def test_explain_sql_statement_endpoint():
    dataset_id = _upload_test_dataset()
    sql = 'SELECT "Category", SUM("Sales") as total_sales FROM dataset GROUP BY "Category" ORDER BY total_sales DESC LIMIT 10;'

    res = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/explain",
        json={"query": sql},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Category" in data["columns_referenced"]
    assert data["has_group_by"] is True
    assert data["has_order_by"] is True
    assert data["limit"] == 10
    assert len(data["explanation"]) > 20


def test_validate_sql_query_plan_endpoint():
    dataset_id = _upload_test_dataset()

    # Valid read-only query
    res_valid = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/validate",
        json={"query": 'SELECT "Category", COUNT(*) FROM dataset GROUP BY 1;'},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["valid"] is True
    assert res_valid.json()["read_only"] is True

    # Forbidden statement blocked
    res_forbidden = client.post(
        f"/api/v1/analytics/{dataset_id}/sql/validate",
        json={"query": "DROP TABLE dataset;"},
    )
    assert res_forbidden.status_code == 200
    assert res_forbidden.json()["valid"] is False
    assert res_forbidden.json()["read_only"] is False


def test_sql_suggestions_endpoint():
    dataset_id = _upload_test_dataset()

    res = client.get(f"/api/v1/analytics/{dataset_id}/sql/suggestions")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["suggestions"]) >= 3
    first = data["suggestions"][0]
    assert "title" in first
    assert "sql" in first
    assert "prompt" in first
