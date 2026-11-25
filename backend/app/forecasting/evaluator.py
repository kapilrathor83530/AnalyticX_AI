"""Time-Series Chronological Backtesting, Scale-Aware Model Evaluation, and Uncertainty Estimation."""
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.forecasting.models import (
    ALL_CANDIDATE_MODEL_KEYS,
    _generate_future_index,
    run_model_by_key,
)


def _calc_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def _calc_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _calc_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error (Scale-aware, non-zero denominator)."""
    sum_y = float(np.sum(np.abs(y_true)))
    if sum_y == 0:
        return 0.0
    return float((np.sum(np.abs(y_true - y_pred)) / sum_y) * 100)


def _calc_mase(y_true: np.ndarray, y_pred: np.ndarray, in_sample_series: pd.Series) -> float:
    """Mean Absolute Scaled Error (relative to in-sample naive diff)."""
    if len(in_sample_series) < 2:
        return 1.0
    naive_diff = float(np.mean(np.abs(np.diff(in_sample_series.values))))
    if naive_diff == 0:
        return 1.0
    mae = _calc_mae(y_true, y_pred)
    return round(float(mae / naive_diff), 3)


def _calc_mape(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    """Mean Absolute Percentage Error with epsilon smoothing for zero-values."""
    eps = 1e-6
    rel = np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), eps))
    return round(float(np.mean(rel) * 100), 2)


def _calc_r2(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    if ss_tot == 0:
        return None
    return round(float(1.0 - (ss_res / ss_tot)), 3)


def evaluate_candidate_models(
    series: pd.Series,
    test_size: Optional[int] = None,
    candidate_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Executes strict chronological holdout evaluation:
    - Train on [0, T - test_size]
    - Evaluate on [T - test_size, T]
    - Zero data leakage
    - Evaluates all candidate models on identical test data
    - Selects champion model
    """
    n = len(series)
    if n < 4:
        return {
            "error": "Insufficient observations for backtesting (requires at least 4 periods).",
            "candidate_models": [],
            "champion_key": "naive",
        }

    # Determine chronological holdout window size
    if test_size is None:
        if n >= 36:
            test_size = min(12, n // 4)
        elif n >= 12:
            test_size = max(2, min(4, n // 4))
        else:
            test_size = max(1, min(2, n // 3))

    train_series = series.iloc[:-test_size]
    test_series = series.iloc[-test_size:]
    y_true = test_series.values

    # Determine candidate keys appropriate for length
    if not candidate_keys:
        candidate_keys = ["naive", "linear"]
        if n >= 6:
            candidate_keys.append("moving_average")
        if n >= 8:
            candidate_keys.extend(["exp_smoothing", "seasonal_naive"])
        if n >= 12:
            candidate_keys.append("arima")
        if n >= 14:
            candidate_keys.append("random_forest")

    # 1. Run naive baseline on train
    naive_preds, _ = run_model_by_key("naive", train_series, test_size)
    naive_mae = _calc_mae(y_true, naive_preds)
    naive_rmse = _calc_rmse(y_true, naive_preds)
    naive_wape = _calc_wape(y_true, naive_preds)

    evaluated_models = []
    backtest_curves = {
        "dates": [d.isoformat() for d in test_series.index],
        "actual": [round(float(v), 2) for v in y_true],
        "models": {},
    }

    for key in candidate_keys:
        try:
            preds, model_meta = run_model_by_key(key, train_series, test_size)
            mae = _calc_mae(y_true, preds)
            rmse = _calc_rmse(y_true, preds)
            wape = _calc_wape(y_true, preds)
            mase = _calc_mase(y_true, preds, train_series)
            mape = _calc_mape(y_true, preds)
            r2 = _calc_r2(y_true, preds)

            # Improvement vs naive baseline (%)
            wape_improvement_pct = round(((naive_wape - wape) / max(naive_wape, 1e-4)) * 100, 1)

            evaluated_models.append({
                "key": key,
                "name": model_meta["model_name"],
                "description": model_meta["description"],
                "parameters": model_meta.get("parameters", {}),
                "metrics": {
                    "mae": round(mae, 2),
                    "rmse": round(rmse, 2),
                    "wape": round(wape, 2),
                    "mase": mase,
                    "mape": mape,
                    "r2": r2,
                    "wape_improvement_vs_naive_pct": wape_improvement_pct,
                },
                "status": "evaluated",
            })
            backtest_curves["models"][key] = [round(float(v), 2) for v in preds]
        except Exception as e:
            evaluated_models.append({
                "key": key,
                "name": key.replace("_", " ").title(),
                "description": f"Evaluation error: {str(e)}",
                "metrics": {"wape": 999.0, "mae": 999.0, "rmse": 999.0},
                "status": "failed",
            })

    # Sort models by lowest WAPE, then lowest RMSE
    valid_models = [m for m in evaluated_models if m["status"] == "evaluated"]
    valid_models.sort(key=lambda x: (x["metrics"]["wape"], x["metrics"]["rmse"]))

    # Select champion model
    champion = valid_models[0] if valid_models else evaluated_models[0]
    champion_key = champion["key"]

    # Champion selection rationale
    champ_wape = champion["metrics"]["wape"]
    champ_name = champion["name"]
    impr = champion["metrics"].get("wape_improvement_vs_naive_pct", 0.0)

    if champion_key == "naive":
        selection_reason = (
            f"Naive Baseline selected: More complex models did not statistically outperform the naive benchmark on historical holdout testing."
        )
    else:
        selection_reason = (
            f"{champ_name} selected as champion model: Achieved the lowest chronological holdout WAPE ({champ_wape}%), "
            f"outperforming the naive benchmark by {abs(impr):.1f}%."
        )

    return {
        "test_size": test_size,
        "holdout_start": test_series.index[0].isoformat(),
        "holdout_end": test_series.index[-1].isoformat(),
        "candidate_models": evaluated_models,
        "champion_key": champion_key,
        "champion_name": champ_name,
        "selection_reason": selection_reason,
        "champion_metrics": champion["metrics"],
        "naive_baseline_metrics": {
            "mae": round(naive_mae, 2),
            "rmse": round(naive_rmse, 2),
            "wape": round(naive_wape, 2),
        },
        "backtest_curves": backtest_curves,
    }


def compute_prediction_intervals(
    forecast_values: np.ndarray,
    champion_metrics: Dict[str, Any],
    is_non_negative: bool = True,
) -> Dict[str, List[float]]:
    """
    Computes 80% and 95% prediction intervals that widen realistically as horizon increases.
    z_80 = 1.282, z_95 = 1.960.
    """
    rmse = champion_metrics.get("rmse", 1.0)
    if rmse <= 0:
        rmse = float(np.std(forecast_values)) if len(forecast_values) > 1 else 1.0

    horizon = len(forecast_values)
    lower_80 = []
    upper_80 = []
    lower_95 = []
    upper_95 = []

    for step, val in enumerate(forecast_values):
        # Uncertainty expansion factor over time horizon
        time_factor = math.sqrt(1.0 + (step / max(1, horizon)))
        sigma_step = rmse * time_factor

        l80 = val - 1.282 * sigma_step
        u80 = val + 1.282 * sigma_step
        l95 = val - 1.960 * sigma_step
        u95 = val + 1.960 * sigma_step

        if is_non_negative:
            l80 = max(0.0, l80)
            l95 = max(0.0, l95)

        lower_80.append(round(float(l80), 2))
        upper_80.append(round(float(u80), 2))
        lower_95.append(round(float(l95), 2))
        upper_95.append(round(float(u95), 2))

    return {
        "lower_80": lower_80,
        "upper_80": upper_80,
        "lower_95": lower_95,
        "upper_95": upper_95,
    }


def evaluate_model(
    df: pd.DataFrame,
    date_column: str,
    target_column: str,
    frequency: str = "M",
    model_type: Optional[str] = None,
    test_size: int = 3,
) -> Dict[str, Any]:
    """Backwards compatibility wrapper for legacy evaluation signature."""
    from app.forecasting.preprocessor import prepare_time_series_series

    try:
        series, _ = prepare_time_series_series(df, date_column, target_column, frequency)
    except Exception as e:
        return {"error": str(e)}

    keys = [model_type] if model_type and model_type in ALL_CANDIDATE_MODEL_KEYS else None
    res = evaluate_candidate_models(series, test_size=test_size, candidate_keys=keys)
    if "error" in res:
        return res

    champ = next((m for m in res["candidate_models"] if m["key"] == model_type), res["candidate_models"][0])
    return {
        "model_type": champ["key"],
        "test_size": test_size,
        "metrics": champ["metrics"],
    }
