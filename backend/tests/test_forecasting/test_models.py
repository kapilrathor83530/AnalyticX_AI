import numpy as np
import pandas as pd
import pytest

from app.forecasting.evaluator import evaluate_model
from app.forecasting.predictor import run_forecast


def make_series():
    dates = pd.date_range("2022-01-01", periods=24, freq="ME")
    values = np.arange(24) * 10 + 100
    return pd.DataFrame({"date": dates, "revenue": values})


def test_run_forecast_linear():
    df = make_series()
    result = run_forecast(df, date_column="date", target_column="revenue", horizon=6, model_type="linear")
    assert "predictions" in result
    assert len(result["predictions"]) == 6
    assert result["model_type"] == "linear"


def test_run_forecast_naive():
    df = make_series()
    result = run_forecast(df, date_column="date", target_column="revenue", horizon=3, model_type="naive")
    assert len(result["predictions"]) == 3


def test_evaluate_model_returns_metrics():
    df = make_series()
    result = evaluate_model(df, date_column="date", target_column="revenue", model_type="linear", test_size=3)
    assert "metrics" in result
    assert "mae" in result["metrics"]


def test_run_forecast_too_little_data():
    df = pd.DataFrame({"date": ["2024-01-01"], "revenue": [100]})
    result = run_forecast(df, date_column="date", target_column="revenue", horizon=6, model_type="linear")
    assert "error" in result
