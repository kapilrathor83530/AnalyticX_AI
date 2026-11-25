import io
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from app.analytics.cleaning_engine import apply_cleaning_action
from app.analytics.data_quality import inspect_data_quality
from app.analytics.eda_engine import generate_eda_report
from app.services.cleaning_service import apply_cleaning_decision, auto_clean_dataset, undo_last_transformation
from app.models.dataset import Dataset


@pytest.fixture
def messy_df():
    return pd.DataFrame({
        "ID": [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
        "Region": ["North", " South ", "East", "West", "North", np.nan, "South", "East", "West", "West"],
        "Sales": [100.0, 110.0, 120.0, np.nan, 140.0, 150.0, 160.0, 170.0, 10000.0, 10000.0],
        "Quantity": [5, 10, np.nan, 8, 12, 6, 9, 11, 14, 14],
    })


def test_inspect_data_quality(messy_df):
    report = inspect_data_quality(messy_df)
    assert report["dataset_shape"]["rows"] == 10
    assert report["dataset_shape"]["columns"] == 4
    assert report["summary"]["duplicate_rows"] == 1
    assert "Sales" in report["missing_by_column"]
    assert "Region" in report["missing_by_column"]
    assert "Sales" in report["outliers_by_column"]
    assert report["quality_score"] < 100.0
    assert len(report["recommendations"]) >= 3


def test_apply_cleaning_impute_median(messy_df):
    action = {
        "action_type": "impute_missing",
        "column": "Quantity",
        "strategy": "median",
        "parameters": {"column": "Quantity", "strategy": "median"},
    }
    cleaned_df, audit = apply_cleaning_action(messy_df, action)
    assert cleaned_df["Quantity"].isna().sum() == 0
    assert audit["affected_records"] == 1


def test_apply_cleaning_impute_unknown(messy_df):
    action = {
        "action_type": "impute_missing",
        "column": "Region",
        "strategy": "unknown",
        "parameters": {"column": "Region", "strategy": "unknown"},
    }
    cleaned_df, audit = apply_cleaning_action(messy_df, action)
    assert cleaned_df["Region"].isna().sum() == 0
    assert "Unknown" in cleaned_df["Region"].values


def test_apply_cleaning_remove_duplicates(messy_df):
    action = {
        "action_type": "remove_duplicates",
        "strategy": "remove_exact",
        "parameters": {},
    }
    cleaned_df, audit = apply_cleaning_action(messy_df, action)
    assert cleaned_df.shape[0] == 9
    assert audit["affected_records"] == 1


def test_apply_cleaning_winsorize_outliers(messy_df):
    action = {
        "action_type": "handle_outliers",
        "column": "Sales",
        "strategy": "winsorize",
        "parameters": {"column": "Sales", "strategy": "winsorize", "lower": 0, "upper": 350},
    }
    cleaned_df, audit = apply_cleaning_action(messy_df, action)
    assert cleaned_df.shape[0] == 10  # Winsorization preserves rows!
    assert cleaned_df["Sales"].max() <= 350.0


def test_generate_eda_report(messy_df):
    report = generate_eda_report(messy_df, dataset_name="TestMessy")
    assert report["row_count"] == 10
    assert report["column_count"] == 4
    assert len(report["data_dictionary"]) == 4
    assert "Sales" in report["numeric_statistics"]
    assert "insights_report" in report
    insights = report["insights_report"]
    assert len(insights["dataset_summary"]) >= 1
    assert len(insights["column_findings"]) >= 1
    assert len(insights["recommended_next_steps"]) >= 1


def test_api_quality_and_clean_endpoints(client):
    # Upload test CSV
    csv_data = b"Product,Revenue,Units\nA,100,2\nB,200,4\nC,,6\nB,200,4\n"
    res = client.post("/api/v1/datasets/upload", files={"file": ("test_studio.csv", io.BytesIO(csv_data), "text/csv")})
    assert res.status_code == 200
    dataset_id = res.json()["id"]

    # Quality Report
    res_q = client.get(f"/api/v1/datasets/{dataset_id}/quality-report")
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert "quality_score" in q_data
    assert len(q_data["recommendations"]) >= 1

    # Auto-Clean
    res_clean = client.post(f"/api/v1/datasets/{dataset_id}/auto-clean", json={"save_as_new_version": False})
    assert res_clean.status_code == 200
    clean_data = res_clean.json()
    assert clean_data["success"] is True
    assert clean_data["after"]["quality_score"] >= clean_data["before"]["quality_score"]

    # EDA Report
    res_eda = client.get(f"/api/v1/datasets/{dataset_id}/eda-report")
    assert res_eda.status_code == 200
    eda_data = res_eda.json()
    assert len(eda_data["insights_report"]["dataset_summary"]) >= 1

    # Export CSV
    res_exp = client.get(f"/api/v1/datasets/{dataset_id}/export/csv")
    assert res_exp.status_code == 200
    assert "text/csv" in res_exp.headers.get("content-type", "")

    # Analyst Chat
    res_chat = client.post(f"/api/v1/datasets/{dataset_id}/analyst-chat", json={
        "messages": [{"role": "user", "content": "Which columns have missing values?"}],
        "selected_column": "Revenue",
    })
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert "answer" in chat_data
