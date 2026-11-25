"""Forecasting Data Preparation, Chronological Inspection & Validation Module."""
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.analytics.profiling import infer_column_type, to_python


def _normalize_freq(freq: str) -> str:
    """Normalizes pandas frequency aliases across versions."""
    freq = freq.upper() if freq else "ME"
    if freq in ("M", "MONTH", "MONTHLY"):
        return "ME"
    if freq in ("Y", "YEAR", "YEARLY"):
        return "YE"
    if freq in ("Q", "QUARTER", "QUARTERLY"):
        return "QE"
    if freq in ("W", "WEEK", "WEEKLY"):
        return "W"
    if freq in ("D", "DAY", "DAILY"):
        return "D"
    if freq in ("H", "HOUR", "HOURLY"):
        return "h"
    return freq


def detect_time_series_readiness(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Deeply inspects a DataFrame to evaluate readiness for time-series forecasting.
    Detects date candidates, numeric targets, potential grouping dimensions,
    and reports sampling frequency, missing intervals, and anomalies.
    """
    total_rows = len(df)
    if total_rows == 0:
        return {
            "is_ready": False,
            "reason": "Dataset is empty.",
            "date_candidates": [],
            "target_candidates": [],
            "group_candidates": [],
        }

    date_candidates = []
    for col in df.columns:
        s = df[col]
        # Skip purely numeric columns unless formatted like year (e.g. 2020)
        ctype = infer_column_type(s)
        if ctype == "datetime" or "date" in col.lower() or "time" in col.lower() or "quarter" in col.lower():
            parsed = pd.to_datetime(s, errors="coerce")
            valid_pct = parsed.notna().sum() / total_rows
            if valid_pct >= 0.5:
                date_candidates.append({
                    "column": col,
                    "valid_percent": round(float(valid_pct * 100), 1),
                    "min_date": str(parsed.dropna().min())[:10] if not parsed.dropna().empty else None,
                    "max_date": str(parsed.dropna().max())[:10] if not parsed.dropna().empty else None,
                    "unique_dates": int(parsed.nunique(dropna=True)),
                })

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    target_candidates = []
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) > 0 and s.nunique() > 1:
            target_candidates.append({
                "column": col,
                "mean": round(float(s.mean()), 2),
                "std": round(float(s.std()), 2) if len(s) > 1 else 0.0,
                "is_non_negative": bool((s >= 0).all()),
                "missing_count": int(df[col].isna().sum()),
            })

    group_candidates = []
    for col in df.columns:
        if col not in numeric_cols and not any(c["column"] == col for c in date_candidates):
            n_unique = int(df[col].nunique(dropna=True))
            if 1 < n_unique <= 50:
                group_candidates.append({
                    "column": col,
                    "unique_count": n_unique,
                    "top_values": [str(x) for x in df[col].dropna().value_counts().head(5).index],
                })

    is_ready = bool(date_candidates and target_candidates and total_rows >= 4)
    reason = "Dataset contains suitable chronological timestamps and numeric metrics." if is_ready else (
        "No chronological date/time column detected. Consider using supervised prediction instead."
        if not date_candidates
        else "Insufficient numeric metrics or observations for forecasting."
    )

    # Inferred frequency from first date candidate
    recommended_freq = "ME"
    if date_candidates:
        d_col = date_candidates[0]["column"]
        parsed = pd.to_datetime(df[d_col], errors="coerce").dropna().sort_values()
        if len(parsed) >= 3:
            diffs = parsed.diff().dropna()
            median_days = diffs.dt.total_seconds().median() / 86400
            if median_days <= 1.5:
                recommended_freq = "D"
            elif median_days <= 8:
                recommended_freq = "W"
            elif median_days <= 35:
                recommended_freq = "ME"
            elif median_days <= 100:
                recommended_freq = "QE"
            else:
                recommended_freq = "YE"

    return {
        "is_ready": is_ready,
        "reason": reason,
        "row_count": total_rows,
        "date_candidates": date_candidates,
        "target_candidates": target_candidates,
        "group_candidates": group_candidates,
        "recommended_date_column": date_candidates[0]["column"] if date_candidates else None,
        "recommended_target_column": target_candidates[0]["column"] if target_candidates else None,
        "recommended_frequency": recommended_freq,
    }


def prepare_time_series_series(
    df: pd.DataFrame,
    date_column: str,
    target_column: str,
    frequency: str = "M",
    group_dimension: Optional[str] = None,
    group_value: Optional[str] = None,
    fill_strategy: str = "interpolate",
    handle_outliers: bool = True,
) -> Tuple[pd.Series, Dict[str, Any]]:
    """
    Parses dates, handles duplicate timestamps, resamples to regular frequency,
    imputes missing intervals, and applies outlier clipping. Never modifies original DataFrame.
    """
    norm_freq = _normalize_freq(frequency)
    work_df = df.copy()

    # Optional segment filtering
    if group_dimension and group_value and group_dimension in work_df.columns:
        work_df = work_df[work_df[group_dimension].astype(str) == str(group_value)]

    if date_column not in work_df.columns:
        raise ValueError(f"Date column '{date_column}' not found.")
    if target_column not in work_df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")

    # 1. Parse dates & numeric target
    work_df["__parsed_date"] = pd.to_datetime(work_df[date_column], errors="coerce")
    work_df["__parsed_target"] = pd.to_numeric(work_df[target_column], errors="coerce")
    valid_df = work_df.dropna(subset=["__parsed_date", "__parsed_target"]).sort_values("__parsed_date")

    if len(valid_df) < 3:
        raise ValueError("Insufficient valid data points (need at least 3 chronological observations).")

    # 2. Check for duplicate timestamps & aggregate
    dup_count = int(valid_df.duplicated(subset=["__parsed_date"]).sum())
    aggregated = valid_df.groupby("__parsed_date")["__parsed_target"].sum()

    # 3. Resample to standard frequency grid
    resampled = aggregated.resample(norm_freq).sum()
    missing_intervals = int(resampled.isna().sum())

    # 4. Missing value imputation
    if fill_strategy == "interpolate":
        clean_series = resampled.interpolate(method="linear").bfill().ffill()
    elif fill_strategy == "ffill":
        clean_series = resampled.ffill().bfill()
    elif fill_strategy == "zero":
        clean_series = resampled.fillna(0.0)
    else:
        clean_series = resampled.fillna(resampled.mean())

    # 5. Outlier handling (IQR winsorization)
    outlier_count = 0
    if handle_outliers and len(clean_series) >= 6:
        q1 = float(clean_series.quantile(0.25))
        q3 = float(clean_series.quantile(0.75))
        iqr = q3 - q1
        if iqr > 0:
            low_bound = q1 - 2.5 * iqr
            high_bound = q3 + 2.5 * iqr
            outlier_mask = (clean_series < low_bound) | (clean_series > high_bound)
            outlier_count = int(outlier_mask.sum())
            clean_series = clean_series.clip(lower=max(0.0, low_bound), upper=high_bound)

    clean_series = clean_series.astype(float)
    clean_series.name = target_column

    validation_summary = {
        "raw_points": len(valid_df),
        "aggregated_points": len(clean_series),
        "frequency": norm_freq,
        "duplicate_timestamps_merged": dup_count,
        "missing_intervals_imputed": missing_intervals,
        "outliers_adjusted": outlier_count,
        "start_date": clean_series.index[0].isoformat(),
        "end_date": clean_series.index[-1].isoformat(),
        "is_non_negative": bool((clean_series >= 0).all()),
    }

    return clean_series, validation_summary
