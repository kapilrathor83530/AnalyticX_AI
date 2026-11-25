import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.analytics.project_insights_engine import (
    calculate_transparent_quality_score,
    build_automated_eda,
    discover_business_insights,
    build_executive_summary,
    compute_dataset_fingerprint,
)
from app.models.dataset import Dataset

client = TestClient(app)


@pytest.fixture
def sample_sales_df():
    return pd.DataFrame({
        "Region": ["North", "North", "South", "South", "East", "East", "West", "West"],
        "Category": ["Electronics", "Furniture", "Electronics", "Furniture", "Electronics", "Furniture", "Electronics", "Furniture"],
        "Sales": [12000.0, 5000.0, 11000.0, 4800.0, 14500.0, 6200.0, 13000.0, 5400.0],
        "Profit": [2800.0, 600.0, 2400.0, 550.0, 3600.0, 850.0, 3100.0, 700.0],
        "Quarter": ["Q1", "Q1", "Q1", "Q1", "Q2", "Q2", "Q2", "Q2"],
    })


def test_quality_score_calculation(sample_sales_df):
    score, methodology = calculate_transparent_quality_score(sample_sales_df)
    assert score == 100.0
    assert methodology["null_cells"] == 0
    assert methodology["duplicate_rows"] == 0

    # Introduce nulls and duplicates
    dirty_df = sample_sales_df.copy()
    dirty_df.loc[0, "Sales"] = np.nan
    dirty_df.loc[1, "Profit"] = np.nan
    dirty_df = pd.concat([dirty_df, dirty_df.iloc[[0]]], ignore_index=True)

    dirty_score, dirty_meta = calculate_transparent_quality_score(dirty_df)
    assert dirty_score < 100.0
    assert dirty_meta["null_cells"] == 3
    assert dirty_meta["duplicate_rows"] == 1


def test_automated_eda_output(sample_sales_df):
    eda = build_automated_eda(sample_sales_df, "Test Sales")
    assert eda["row_count"] == 8
    assert eda["column_count"] == 5
    assert "Sales" in eda["numeric_stats"]
    assert eda["numeric_stats"]["Sales"]["mean"] == 8987.5
    assert len(eda["schema"]) == 5
    assert "Sales" in eda["correlations"]
    # Profit and Sales should have positive correlation
    corr = eda["correlations"]["Sales"]["Profit"]
    assert corr > 0.8


def test_business_insights_generation(sample_sales_df):
    dummy_dataset = Dataset(id=999, name="Test Sales", version=1, size_bytes=1024)
    fingerprint = compute_dataset_fingerprint(dummy_dataset, sample_sales_df)
    eda = build_automated_eda(sample_sales_df, "Test Sales")
    insights = discover_business_insights(sample_sales_df, dummy_dataset, eda, fingerprint)

    assert len(insights) >= 2
    categories = {i["category"] for i in insights}
    assert "performance" in categories or "trend" in categories

    # Verify that every insight has complete mathematical trace
    for ins in insights:
        assert "title" in ins
        assert "explanation" in ins
        assert "supporting_metrics" in ins
        assert "methodology" in ins
        assert ins["confidence_score"] > 0.7


def test_executive_summary_structure(sample_sales_df):
    dummy_dataset = Dataset(id=999, name="Test Sales", version=1, size_bytes=1024)
    fingerprint = compute_dataset_fingerprint(dummy_dataset, sample_sales_df)
    eda = build_automated_eda(sample_sales_df, "Test Sales")
    insights = discover_business_insights(sample_sales_df, dummy_dataset, eda, fingerprint)
    summary = build_executive_summary(sample_sales_df, "Test Sales", eda, insights)

    assert "project_overview" in summary
    assert len(summary["key_metrics"]) >= 3
    assert len(summary["recommended_next_actions"]) >= 1
    assert len(summary["limitations_and_uncertainties"]) >= 1


def test_api_project_insights_flow():
    # 1. Upload temporary dataset
    csv_content = b"Department,Budget,Spend\nSales,100000,95000\nEngineering,250000,240000\nMarketing,80000,78000\nHR,30000,28000\n"
    res_up = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("dept_budget.csv", csv_content, "text/csv")},
    )
    assert res_up.status_code == 200
    dataset_id = res_up.json()["id"]

    # 2. Get Project Insights
    res_ins = client.get(f"/api/v1/project-insights/{dataset_id}")
    assert res_ins.status_code == 200
    data = res_ins.json()
    assert data["dataset_id"] == dataset_id
    assert "executive_summary" in data
    assert "eda" in data
    assert "insights" in data
    assert len(data["insights"]) >= 1

    first_insight_id = data["insights"][0]["id"]

    # 3. Save Insight
    res_save = client.patch(
        f"/api/v1/project-insights/{dataset_id}/insights/{first_insight_id}",
        json={"status": "saved"},
    )
    assert res_save.status_code == 200
    assert res_save.json()["status"] == "saved"

    # 4. Deeper ANOVA Analysis Action
    res_action = client.post(
        f"/api/v1/project-insights/{dataset_id}/action",
        json={
            "action_type": "deeper_analysis",
            "payload": {"group_column": "Department", "value_column": "Spend"},
        },
    )
    assert res_action.status_code == 200
    act_data = res_action.json()
    assert act_data["success"] is True
    assert "interpretation" in act_data

    # 5. Project Chat Q&A
    res_chat = client.post(
        f"/api/v1/project-insights/{dataset_id}/chat",
        json={"question": "What are the top findings and risks?"},
    )
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert "answer" in chat_data
    assert len(chat_data["grounded_sources"]) >= 1
