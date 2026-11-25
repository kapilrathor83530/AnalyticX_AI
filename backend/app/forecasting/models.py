"""Candidate Forecasting Model Implementations for Analyticx AI."""
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def _generate_future_index(series: pd.Series, horizon: int) -> pd.DatetimeIndex:
    """Generates future DatetimeIndex continuing the series frequency."""
    freq = series.index.freq or "ME"
    start_date = series.index[-1]
    return pd.date_range(start=start_date, periods=horizon + 1, freq=freq)[1:]


def forecast_naive(series: pd.Series, horizon: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Naive Baseline: Extrapolates the final observed value forward."""
    last_val = float(series.iloc[-1])
    preds = np.full(horizon, last_val)
    return preds, {
        "model_name": "Naive Baseline",
        "parameters": {"last_value": last_val},
        "description": "Assumes future values will equal the last observed historical observation.",
    }


def forecast_seasonal_naive(series: pd.Series, horizon: int, season_length: int = 12) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Seasonal Naive Baseline: Projects the observation from the previous seasonal cycle."""
    n = len(series)
    m = season_length if n >= season_length * 2 else (4 if n >= 8 else (7 if n >= 14 else 1))
    if m <= 1:
        return forecast_naive(series, horizon)

    preds = []
    for h in range(horizon):
        idx = -(m - (h % m))
        preds.append(float(series.iloc[idx]))
    preds_arr = np.array(preds)
    return preds_arr, {
        "model_name": "Seasonal Naive",
        "parameters": {"season_length": m},
        "description": f"Repeats observed values from the previous seasonal cycle (period m={m}).",
    }


def forecast_moving_average(series: pd.Series, horizon: int, window: int = 3) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Moving Average: Extrapolates the mean of the most recent k observations."""
    k = min(window, max(2, len(series) // 2))
    ma_val = float(series.iloc[-k:].mean())
    preds = np.full(horizon, ma_val)
    return preds, {
        "model_name": "Moving Average",
        "parameters": {"window": k, "mean_value": round(ma_val, 2)},
        "description": f"Extrapolates the trailing rolling average over the last {k} periods.",
    }


def forecast_linear_trend(series: pd.Series, horizon: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Linear Regression Trend: Fits an OLS trend line across chronological time steps."""
    from sklearn.linear_model import LinearRegression

    n = len(series)
    x = np.arange(n).reshape(-1, 1)
    y = series.values
    model = LinearRegression().fit(x, y)

    future_x = np.arange(n, n + horizon).reshape(-1, 1)
    preds = model.predict(future_x)
    # Clip negative values if historical data is strictly non-negative
    if (y >= 0).all():
        preds = np.maximum(0.0, preds)

    slope = float(model.coef_[0])
    return preds, {
        "model_name": "Linear Trend",
        "parameters": {"slope": round(slope, 3), "intercept": round(float(model.intercept_), 2)},
        "description": f"Fits an ordinary least squares trend (slope = {slope:+,.2f} per period).",
    }


def forecast_exponential_smoothing(series: pd.Series, horizon: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Holt-Winters / Exponential Smoothing using statsmodels."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    n = len(series)
    # Determine appropriate seasonal period
    seasonal_periods = None
    seasonal_type = None
    if n >= 24:
        seasonal_periods = 12
        seasonal_type = "add"
    elif n >= 8:
        seasonal_periods = 4
        seasonal_type = "add"

    try:
        if seasonal_periods:
            hw = ExponentialSmoothing(
                series,
                trend="add",
                seasonal=seasonal_type,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            ).fit()
        else:
            hw = ExponentialSmoothing(
                series,
                trend="add",
                seasonal=None,
                initialization_method="estimated",
            ).fit()
        preds = hw.forecast(horizon).values
        model_desc = f"Holt-Winters with additive trend{' and seasonality (m=' + str(seasonal_periods) + ')' if seasonal_periods else ''}."
    except Exception:
        # Fallback to simple exponential smoothing
        try:
            hw = ExponentialSmoothing(series, trend=None, seasonal=None, initialization_method="estimated").fit()
            preds = hw.forecast(horizon).values
            model_desc = "Simple Exponential Smoothing (level only)."
        except Exception:
            return forecast_linear_trend(series, horizon)

    if (series.values >= 0).all():
        preds = np.maximum(0.0, preds)

    return preds, {
        "model_name": "Holt-Winters (ETS)",
        "parameters": {"seasonal_periods": seasonal_periods},
        "description": model_desc,
    }


def forecast_arima(series: pd.Series, horizon: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Auto-configured ARIMA (p, d, q) via statsmodels."""
    from statsmodels.tsa.arima.model import ARIMA

    n = len(series)
    candidates = [(1, 1, 1), (1, 1, 0), (0, 1, 1), (1, 0, 0)] if n >= 12 else [(1, 0, 0), (0, 1, 0)]
    best_model = None
    best_aic = float("inf")
    chosen_order = (1, 0, 0)

    for order in candidates:
        try:
            fit_res = ARIMA(series, order=order).fit()
            if fit_res.aic < best_aic:
                best_aic = fit_res.aic
                best_model = fit_res
                chosen_order = order
        except Exception:
            continue

    if best_model is None:
        return forecast_linear_trend(series, horizon)

    try:
        preds = best_model.forecast(steps=horizon).values
    except Exception:
        return forecast_linear_trend(series, horizon)

    if (series.values >= 0).all():
        preds = np.maximum(0.0, preds)

    return preds, {
        "model_name": f"ARIMA{chosen_order}",
        "parameters": {"order": chosen_order, "aic": round(best_aic, 2)},
        "description": f"Autoregressive Integrated Moving Average model with order (p,d,q)={chosen_order}.",
    }


def forecast_random_forest(series: pd.Series, horizon: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Feature-based Machine Learning: Random Forest with lag features & cyclical calendar signals."""
    from sklearn.ensemble import RandomForestRegressor

    n = len(series)
    if n < 8:
        return forecast_linear_trend(series, horizon)

    # Build lag features (t-1, t-2, rolling mean)
    df_feat = pd.DataFrame({"y": series.values}, index=series.index)
    df_feat["lag_1"] = df_feat["y"].shift(1)
    df_feat["lag_2"] = df_feat["y"].shift(2)
    df_feat["roll_mean_3"] = df_feat["y"].shift(1).rolling(3).mean()
    df_feat["trend_idx"] = np.arange(n)
    df_feat["month"] = df_feat.index.month
    df_feat["quarter"] = df_feat.index.quarter

    clean_train = df_feat.dropna()
    if len(clean_train) < 4:
        return forecast_linear_trend(series, horizon)

    feature_cols = ["lag_1", "lag_2", "roll_mean_3", "trend_idx", "month", "quarter"]
    X = clean_train[feature_cols]
    y = clean_train["y"]

    rf = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=5)
    rf.fit(X, y)

    # Recursive multi-step forecasting
    future_index = _generate_future_index(series, horizon)
    current_history = list(series.values)
    preds = []

    for step in range(horizon):
        f_date = future_index[step]
        l1 = current_history[-1]
        l2 = current_history[-2] if len(current_history) >= 2 else l1
        r_mean = float(np.mean(current_history[-3:]))
        tr_idx = n + step
        x_step = pd.DataFrame([{
            "lag_1": l1,
            "lag_2": l2,
            "roll_mean_3": r_mean,
            "trend_idx": tr_idx,
            "month": f_date.month,
            "quarter": f_date.quarter,
        }])
        pred_val = float(rf.predict(x_step)[0])
        preds.append(pred_val)
        current_history.append(pred_val)

    preds_arr = np.array(preds)
    if (series.values >= 0).all():
        preds_arr = np.maximum(0.0, preds_arr)

    # Feature importance
    feat_importances = {
        col: round(float(imp), 3) for col, imp in zip(feature_cols, rf.feature_importances_)
    }

    return preds_arr, {
        "model_name": "Random Forest Regressor",
        "parameters": {"n_estimators": 50, "feature_importance": feat_importances},
        "description": "Non-linear ensemble learning leveraging autoregressive lags (t-1, t-2), rolling metrics, and calendar features.",
    }


ALL_CANDIDATE_MODEL_KEYS = ["naive", "seasonal_naive", "moving_average", "linear", "exp_smoothing", "arima", "random_forest"]


def run_model_by_key(key: str, series: pd.Series, horizon: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Dispatches to model implementation by key."""
    if key == "naive":
        return forecast_naive(series, horizon)
    elif key == "seasonal_naive":
        return forecast_seasonal_naive(series, horizon)
    elif key == "moving_average":
        return forecast_moving_average(series, horizon)
    elif key == "linear":
        return forecast_linear_trend(series, horizon)
    elif key == "exp_smoothing":
        return forecast_exponential_smoothing(series, horizon)
    elif key == "arima":
        return forecast_arima(series, horizon)
    elif key == "random_forest":
        return forecast_random_forest(series, horizon)
    else:
        return forecast_linear_trend(series, horizon)
