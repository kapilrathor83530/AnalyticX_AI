import pandas as pd
import pytest

from app.analytics.cleaning_engine import apply_cleaning_action
from app.analytics.root_cause import analyze_root_cause


def test_mode_1_rename_column_cleaning_action():
    df = pd.DataFrame({"old_col": [1, 2, 3], "value": [10, 20, 30]})
    res_df, audit = apply_cleaning_action(
        df,
        {"action_type": "rename_column", "column": "old_col", "parameters": {"new_name": "renamed_col"}}
    )
    assert "renamed_col" in res_df.columns
    assert "old_col" not in res_df.columns
    assert "renamed_col" in audit["description"]


def test_mode_3_root_cause_variance_decomposition():
    df = pd.DataFrame({
        "region": ["North", "South", "North", "South", "West", "West"],
        "profit": [100, 200, 80, 150, 50, 10], # Declines in second half
    })
    res = analyze_root_cause(df, metric_column="profit", dimension_columns=["region"])
    assert res["metric_column"] == "profit"
    assert res["direction"] == "declined"
    assert "dimensions" in res
    assert "region" in res["dimensions"]
    assert len(res["recommendations"]) > 0
    assert len(res["waterfall_steps"]) > 0


def test_mode_2_sql_query_execution_and_security(client):
    # Upload a sample dataset first
    csv_content = b"region,sales,profit\nNorth,100,20\nSouth,200,45\nNorth,150,30\nWest,300,80\n"
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sales_data.csv", csv_content, "text/csv")},
    )
    assert res.status_code == 200
    dataset_id = res.json()["id"]

    # Test read-only SQL query
    sql_payload = {
        "query": "SELECT region, SUM(sales) as total_sales FROM dataset GROUP BY region ORDER BY total_sales DESC"
    }
    sql_res = client.post(f"/api/v1/analytics/{dataset_id}/sql", json=sql_payload)
    assert sql_res.status_code == 200
    data = sql_res.json()
    assert data["success"] is True
    assert data["row_count"] == 3
    assert data["columns"] == ["region", "total_sales"]
    assert data["rows"][0]["region"] == "West"
    assert data["rows"][0]["total_sales"] == 300

    # Test SQL security rejection for forbidden DDL/DML statements
    bad_res = client.post(f"/api/v1/analytics/{dataset_id}/sql", json={"query": "DROP TABLE dataset"})
    assert bad_res.status_code == 400

    # Test schema inspection
    schema_res = client.get(f"/api/v1/analytics/{dataset_id}/schema")
    assert schema_res.status_code == 200
    assert len(schema_res.json()["columns"]) == 3

    # Test Root Cause API endpoint
    rc_res = client.post(f"/api/v1/analytics/{dataset_id}/root-cause", json={"metric_column": "sales"})
    assert rc_res.status_code == 200
    assert rc_res.json()["metric_column"] == "sales"

    # Test PPTX export endpoint
    pptx_res = client.post(f"/api/v1/reports/dataset/{dataset_id}/pptx", json={})
    assert pptx_res.status_code == 200
    assert pptx_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert len(pptx_res.content) > 1000

    # Test Word DOCX export endpoint
    docx_res = client.post(f"/api/v1/reports/dataset/{dataset_id}/docx", json={})
    assert docx_res.status_code == 200
    assert docx_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert len(docx_res.content) > 1000

    # Test Create & Fetch Sharable Report
    share_payload = {
        "title": "Q3 Sales Performance Review",
        "executive_summary": "Sales grew by +12% driven by West region.",
        "recommendations": ["Expand West inventory", "Audit East margins"],
    }
    share_res = client.post(f"/api/v1/reports/dataset/{dataset_id}/share", json=share_payload)
    assert share_res.status_code == 200
    share_token = share_res.json()["share_token"]
    assert len(share_token) > 10

    # Fetch shared report without auth
    public_res = client.get(f"/api/v1/reports/shared/{share_token}")
    assert public_res.status_code == 200
    assert public_res.json()["title"] == "Q3 Sales Performance Review"
    assert len(public_res.json()["recommendations"]) == 2

    # Test Report Schedules endpoint
    sched_res = client.get(f"/api/v1/reports/dataset/{dataset_id}/schedules")
    assert sched_res.status_code == 200
    assert len(sched_res.json()["schedules"]) >= 1
