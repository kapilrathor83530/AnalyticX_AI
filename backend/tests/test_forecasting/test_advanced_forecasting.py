import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.forecasting.preprocessor import (
    detect_time_series_readiness,
    prepare_time_series_series,
)
from app.forecasting.evaluator import (
    compute_prediction_intervals,
    evaluate_candidate_models,
)
from app.forecasting.scenarios import generate_forecast_scenarios
from app.forecasting.predictor import run_advanced_forecast

client = TestClient(app)


@pytest.fixture
def monthly_sales_df():
    """Generates 24 months of synthetic trended sales data."""
    dates = pd.date_range(start="2024-01-01", periods=24, freq="ME")
    # Trend + seasonal effect
    sales = [
        10000 + i * 500 + (2000 if i % 12 in (10, 11) else -1000 if i % 12 == 1 else 0)
        for i in range(24)
    ]
    regions = ["North" if i % 2 == 0 else "South" for i in range(24)]
    return pd.DataFrame({"Date": dates, "Sales": sales, "Region": regions})


def test_readiness_inspection(monthly_sales_df):
    report = detect_time_series_readiness(monthly_sales_df)
    assert report["is_ready"] is True
    assert report["recommended_date_column"] == "Date"
    assert report["recommended_target_column"] == "Sales"
    assert "M" in report["recommended_frequency"]

    # Non-temporal DataFrame
    no_time_df = pd.DataFrame({"Category": ["A", "B", "C"], "Value": [10, 20, 30]})
    no_time_rep = detect_time_series_readiness(no_time_df)
    assert no_time_rep["is_ready"] is False
    assert "supervised prediction" in no_time_rep["reason"].lower()


def test_prepare_time_series_series(monthly_sales_df):
    series, meta = prepare_time_series_series(
        df=monthly_sales_df,
        date_column="Date",
        target_column="Sales",
        frequency="M",
    )
    assert len(series) == 24
    assert meta["raw_points"] == 24
    assert meta["is_non_negative"] is True


def test_chronological_backtesting_and_models(monthly_sales_df):
    series, _ = prepare_time_series_series(
        df=monthly_sales_df,
        date_column="Date",
        target_column="Sales",
        frequency="M",
    )
    evaluation = evaluate_candidate_models(series=series, test_size=4)
    assert "champion_key" in evaluation
    assert len(evaluation["candidate_models"]) >= 3

    # Check metrics existence
    champ_metrics = evaluation["champion_metrics"]
    assert "mae" in champ_metrics
    assert "rmse" in champ_metrics
    assert "wape" in champ_metrics
    assert champ_metrics["wape"] < 100.0


def test_prediction_intervals(monthly_sales_df):
    f_vals = np.array([12000.0, 12500.0, 13000.0, 13500.0])
    metrics = {"rmse": 800.0}
    intervals = compute_prediction_intervals(f_vals, metrics, is_non_negative=True)

    assert len(intervals["lower_80"]) == 4
    assert len(intervals["upper_80"]) == 4
    assert len(intervals["lower_95"]) == 4
    assert len(intervals["upper_95"]) == 4

    # Monotonic uncertainty widening
    spread_0 = intervals["upper_80"][0] - intervals["lower_80"][0]
    spread_3 = intervals["upper_80"][3] - intervals["lower_80"][3]
    assert spread_3 > spread_0


def test_forecast_scenarios():
    f_vals = [10000.0, 11000.0, 12000.0]
    intervals = {
        "lower_80": [9000.0, 9800.0, 10600.0],
        "upper_80": [11000.0, 12200.0, 13400.0],
    }
    scen = generate_forecast_scenarios(
        forecast_values=f_vals,
        intervals=intervals,
        target_metric="Sales",
        custom_assumptions={"growth_rate_pct": 10.0, "price_change_pct": 5.0, "price_elasticity": -1.0},
    )
    scenarios = scen["scenarios"]
    assert "baseline" in scenarios
    assert "optimistic" in scenarios
    assert "pessimistic" in scenarios
    assert "custom" in scenarios
    assert scenarios["optimistic"]["total"] > scenarios["baseline"]["total"]
    assert scenarios["pessimistic"]["total"] < scenarios["baseline"]["total"]


def test_full_forecasting_pipeline_and_api():
    # 1. Upload temporal dataset
    csv_bytes = (
        "Date,Revenue\n"
        "2024-01-01,15000\n"
        "2024-02-01,16200\n"
        "2024-03-01,17500\n"
        "2024-04-01,16800\n"
        "2024-05-01,18000\n"
        "2024-06-01,19200\n"
        "2024-07-01,21000\n"
        "2024-08-01,20500\n"
        "2024-09-01,22000\n"
        "2024-10-01,23400\n"
        "2024-11-01,25000\n"
        "2024-12-01,28000\n"
    ).encode("utf-8")

    res_up = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("revenue_2024.csv", csv_bytes, "text/csv")},
    )
    assert res_up.status_code == 200
    dataset_id = res_up.json()["id"]

    # 2. Inspect Dataset Readiness API
    res_insp = client.post(
        "/api/v1/forecasting/inspect",
        json={"dataset_id": dataset_id},
    )
    assert res_insp.status_code == 200
    insp_data = res_insp.json()
    assert insp_data["is_ready"] is True
    assert insp_data["recommended_target_column"] == "Revenue"

    # 3. Train Advanced Forecast API
    train_payload = {
        "dataset_id": dataset_id,
        "date_column": "Date",
        "target_column": "Revenue",
        "horizon": 6,
        "frequency": "M",
        "model_type": "auto",
        "custom_assumptions": {"growth_rate_pct": 5.0},
    }
    res_train = client.post("/api/v1/forecasting/train", json=train_payload)
    assert res_train.status_code == 200
    run_data = res_train.json()
    run_id = run_data["id"]

    assert len(run_data["predictions"]) == 6
    assert "metrics" in run_data
    assert "candidate_models" in run_data
    assert "scenarios" in run_data
    assert "insights" in run_data

    # 4. Pin to Dashboard API
    res_pin = client.post(f"/api/v1/forecasting/run/{run_id}/pin")
    assert res_pin.status_code == 200
    assert res_pin.json()["success"] is True

    # 5. Grounded Forecast Chat API
    res_chat = client.post(
        f"/api/v1/forecasting/run/{run_id}/chat",
        json={"question": "Compare this forecast with the naive baseline and explain uncertainty."},
    )
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert "answer" in chat_data
    assert "uncertainty" in chat_data["answer"].lower() or "baseline" in chat_data["answer"].lower()

    # 6. Automatic Recommendation API
    res_rec = client.get(f"/api/v1/forecasting/recommendation/{dataset_id}")
    assert res_rec.status_code == 200
    assert res_rec.json()["has_recommendation"] is True
