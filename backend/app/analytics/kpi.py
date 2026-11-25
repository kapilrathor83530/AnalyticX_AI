from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.analytics.profiling import to_python


def compute_kpis(
    df: pd.DataFrame,
    metrics: List[str],
    dimensions: Optional[List[str]] = None,
    date_column: Optional[str] = None,
) -> Dict[str, Any]:
    numeric_metrics = [
        m for m in metrics if m in df.columns and pd.api.types.is_numeric_dtype(df[m])
    ]
    if not numeric_metrics:
        return {"error": "No numeric metric columns available"}

    totals = {m: to_python(float(df[m].sum())) for m in numeric_metrics}
    averages = {m: to_python(float(df[m].mean())) for m in numeric_metrics}

    result: Dict[str, Any] = {
        "row_count": int(df.shape[0]),
        "totals": totals,
        "averages": averages,
    }

    if dimensions:
        by_dimension: Dict[str, Any] = {}
        for dim in dimensions:
            if dim not in df.columns:
                continue
            grouped = df.groupby(dim)[numeric_metrics].sum().reset_index()
            by_dimension[dim] = [
                {k: to_python(v) for k, v in row.items()}
                for row in grouped.to_dict(orient="records")
            ]
        result["by_dimension"] = by_dimension

    if date_column and date_column in df.columns:
        series = df.copy()
        series[date_column] = pd.to_datetime(series[date_column], errors="coerce")
        series = series.dropna(subset=[date_column])
        if not series.empty:
            monthly = (
                series.set_index(date_column)[numeric_metrics]
                .resample("M")
                .sum()
                .reset_index()
            )
            result["monthly_trend"] = [
                {k: to_python(v) for k, v in row.items()}
                for row in monthly.to_dict(orient="records")
            ]

    return result


def compute_trend(df: pd.DataFrame, date_column: str, metric_column: str, freq: str = "M") -> Dict[str, Any]:
    if date_column not in df.columns or metric_column not in df.columns:
        return {"error": "Column not found"}

    series = df[[date_column, metric_column]].copy()
    series[date_column] = pd.to_datetime(series[date_column], errors="coerce")
    series = series.dropna().sort_values(date_column)

    if series.empty:
        return {"error": "No valid date-value pairs"}

    grouped = series.set_index(date_column)[metric_column].resample(freq).sum().dropna()

    if len(grouped) < 2:
        return {
            "date_column": date_column,
            "metric_column": metric_column,
            "points": [
                {"date": to_python(idx), "value": to_python(val)} for idx, val in grouped.items()
            ],
            "trend_direction": "unknown",
        }

    first = float(grouped.iloc[0])
    last = float(grouped.iloc[-1])
    change = last - first
    pct = (change / first * 100) if first != 0 else None

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "points": [
            {"date": to_python(idx), "value": to_python(val)} for idx, val in grouped.items()
        ],
        "first": first,
        "last": last,
        "change": change,
        "change_percent": pct,
        "trend_direction": "up" if change > 0 else "down" if change < 0 else "flat",
    }
