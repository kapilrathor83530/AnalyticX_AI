"""Unified Advanced Forecasting Pipeline for Analyticx AI."""
import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from app.forecasting.evaluator import (
    compute_prediction_intervals,
    evaluate_candidate_models,
)
from app.forecasting.insights_agent import synthesize_forecasting_narrative
from app.forecasting.models import (
    _generate_future_index,
    run_model_by_key,
)
from app.forecasting.preprocessor import (
    detect_time_series_readiness,
    prepare_time_series_series,
)
from app.forecasting.scenarios import generate_forecast_scenarios


def run_advanced_forecast(
    df: pd.DataFrame,
    date_column: str,
    target_column: str,
    horizon: int = 12,
    frequency: str = "M",
    model_type: Optional[str] = None,
    group_dimension: Optional[str] = None,
    group_value: Optional[str] = None,
    fill_strategy: str = "interpolate",
    handle_outliers: bool = True,
    custom_assumptions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the complete advanced forecasting lifecycle:
    1. Inspection & chronological validation.
    2. Resampling & missingness/outlier adjustment.
    3. Chronological holdout backtesting across candidate models.
    4. Model selection (champion vs baselines).
    5. Full-history forecast generation.
    6. Uncertainty estimation (80% and 95% prediction intervals).
    7. Business Decision Simulator scenarios (baseline, optimistic, pessimistic, what-if).
    8. Plain-English narrative synthesis.
    """
    start_time = time.time()

    # 1. Prepare and validate time series
    try:
        series, validation_meta = prepare_time_series_series(
            df=df,
            date_column=date_column,
            target_column=target_column,
            frequency=frequency,
            group_dimension=group_dimension,
            group_value=group_value,
            fill_strategy=fill_strategy,
            handle_outliers=handle_outliers,
        )
    except Exception as e:
        return {"error": f"Data preparation error: {str(e)}"}

    n = len(series)
    if n < 3:
        return {"error": f"Insufficient data points after resampling (found {n}, minimum 3 required)."}

    # 2. Chronological Backtest & Model Evaluation
    evaluation = evaluate_candidate_models(series=series)
    if "error" in evaluation:
        return {"error": evaluation["error"]}

    # Selected model (override or champion)
    chosen_key = model_type if model_type and model_type != "auto" else evaluation["champion_key"]

    # 3. Train on complete series and forecast forward
    try:
        forecast_values, model_meta = run_model_by_key(chosen_key, series, horizon)
    except Exception as e:
        # Fallback to linear trend if chosen model fails
        forecast_values, model_meta = run_model_by_key("linear", series, horizon)
        chosen_key = "linear"

    future_index = _generate_future_index(series, horizon)
    is_non_neg = validation_meta.get("is_non_negative", True)
    if is_non_neg:
        forecast_values = np.maximum(0.0, forecast_values)

    # 4. Uncertainty Intervals (80% and 95%)
    intervals = compute_prediction_intervals(
        forecast_values=forecast_values,
        champion_metrics=evaluation.get("champion_metrics", {}),
        is_non_negative=is_non_neg,
    )

    # 5. Format predictions with interval boundaries
    predictions = []
    for step, (dt, val) in enumerate(zip(future_index, forecast_values)):
        predictions.append({
            "date": dt.isoformat(),
            "value": round(float(val), 2),
            "lower_80": intervals["lower_80"][step],
            "upper_80": intervals["upper_80"][step],
            "lower_95": intervals["lower_95"][step],
            "upper_95": intervals["upper_95"][step],
        })

    # 6. Format historical observations
    history = [
        {"date": idx.isoformat(), "value": round(float(val), 2)}
        for idx, val in series.items()
    ]

    # 7. Business Decision Simulator Scenarios
    scenarios_data = generate_forecast_scenarios(
        forecast_values=[p["value"] for p in predictions],
        intervals=intervals,
        target_metric=target_column,
        custom_assumptions=custom_assumptions,
        is_non_negative=is_non_neg,
    )

    # 8. Forecasting Insights Narrative
    insights = synthesize_forecasting_narrative(
        series=series,
        forecast_points=predictions,
        evaluation=evaluation,
        intervals=intervals,
        target_metric=target_column,
        date_column=date_column,
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "model_type": chosen_key,
        "model_name": model_meta["model_name"],
        "model_description": model_meta["description"],
        "target_column": target_column,
        "date_column": date_column,
        "group_dimension": group_dimension,
        "group_value": group_value,
        "horizon": horizon,
        "frequency": validation_meta["frequency"],
        "history": history,
        "predictions": predictions,
        "confidence_intervals": intervals,
        "metrics": evaluation.get("champion_metrics", {}),
        "naive_baseline_metrics": evaluation.get("naive_baseline_metrics", {}),
        "selection_reason": evaluation.get("selection_reason", ""),
        "candidate_models": evaluation.get("candidate_models", []),
        "backtest_results": evaluation.get("backtest_curves", {}),
        "scenarios": scenarios_data["scenarios"],
        "insights": insights,
        "data_validation": validation_meta,
        "training_time_ms": elapsed_ms,
    }


# Backwards compatibility wrapper for existing tests and routes
def run_forecast(
    df: pd.DataFrame,
    date_column: str,
    target_column: str,
    horizon: int = 12,
    frequency: str = "M",
    model_type: Optional[str] = None,
) -> Dict[str, Any]:
    return run_advanced_forecast(
        df=df,
        date_column=date_column,
        target_column=target_column,
        horizon=horizon,
        frequency=frequency,
        model_type=model_type,
    )
