from typing import Any, Dict, List

import pandas as pd

from app.analytics.profiling import to_python


def compute_baseline(
    df: pd.DataFrame,
    metric_columns: Dict[str, str] | None = None,
    price_column: str | None = None,
    cost_column: str | None = None,
    quantity_column: str | None = None,
) -> Dict[str, Any]:
    metric_columns = metric_columns or {}

    baseline: Dict[str, Any] = {
        "row_count": int(df.shape[0]),
        "totals": {},
        "means": {},
        "columns_used": {},
    }

    def _sum(col: str) -> float | None:
        if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            return float(df[col].sum())
        return None

    def _mean(col: str) -> float | None:
        if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            return float(df[col].mean())
        return None

    for key, col in metric_columns.items():
        total = _sum(col)
        if total is not None:
            baseline["totals"][key] = to_python(total)
            baseline["means"][key] = to_python(_mean(col))
            baseline["columns_used"][key] = col

    if price_column:
        baseline["columns_used"]["price"] = price_column
        baseline["means"]["price"] = to_python(_mean(price_column))
    if cost_column:
        baseline["columns_used"]["cost"] = cost_column
        baseline["means"]["cost"] = to_python(_mean(cost_column))
    if quantity_column:
        baseline["columns_used"]["quantity"] = quantity_column
        baseline["totals"]["quantity"] = to_python(_sum(quantity_column))

    revenue = baseline["totals"].get("revenue")
    cost = baseline["totals"].get("cost")
    if revenue is not None and cost is not None:
        baseline["totals"]["profit"] = to_python(revenue - cost)
        baseline["totals"]["margin_percent"] = to_python(((revenue - cost) / revenue * 100) if revenue else None)

    return baseline
