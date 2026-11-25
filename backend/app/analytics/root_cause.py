"""Root-Cause Variance & Driver Decomposition Engine for Analyticx AI."""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def analyze_root_cause(
    df: pd.DataFrame,
    metric_column: str,
    dimension_columns: Optional[List[str]] = None,
    date_column: Optional[str] = None,
    period_split: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs deterministic root-cause analysis on metric changes across dimensions.
    Returns delta decomposition, top detractors, top contributors, waterfall steps, and recommendations.
    """
    if metric_column not in df.columns:
        raise ValueError(f"Metric column '{metric_column}' not found in dataset")

    # Ensure metric is numeric
    work_df = df.copy()
    work_df[metric_column] = pd.to_numeric(work_df[metric_column], errors="coerce").fillna(0)

    # Inferred dimensions if not provided
    if not dimension_columns:
        dimension_columns = [
            c for c in work_df.columns
            if c != metric_column and (work_df[c].dtype == "object" or work_df[c].nunique() < 50)
        ]

    # Time-based or Two-Period Split
    has_date = bool(date_column and date_column in work_df.columns)
    if has_date:
        parsed_dates = pd.to_datetime(work_df[date_column], errors="coerce")
        if parsed_dates.notna().sum() >= len(work_df) * 0.5:
            work_df["__rc_date"] = parsed_dates
            valid_df = work_df.dropna(subset=["__rc_date"]).sort_values("__rc_date")
            n = len(valid_df)
            mid = max(1, n // 2)
            p1 = valid_df.iloc[:mid]
            p2 = valid_df.iloc[mid:]
            p1_label = f"Period 1 ({p1['__rc_date'].iloc[0].strftime('%Y-%m-%d')} to {p1['__rc_date'].iloc[-1].strftime('%Y-%m-%d')})"
            p2_label = f"Period 2 ({p2['__rc_date'].iloc[0].strftime('%Y-%m-%d')} to {p2['__rc_date'].iloc[-1].strftime('%Y-%m-%d')})"
        else:
            # Categorical periods like Q1/Q2, 2023/2024, Jan/Feb
            unique_periods = sorted(work_df[date_column].dropna().unique())
            if len(unique_periods) >= 2:
                mid_idx = len(unique_periods) // 2
                periods_p1 = unique_periods[:mid_idx]
                periods_p2 = unique_periods[mid_idx:]
                p1 = work_df[work_df[date_column].isin(periods_p1)]
                p2 = work_df[work_df[date_column].isin(periods_p2)]
                p1_label = f"{', '.join(map(str, periods_p1))}"
                p2_label = f"{', '.join(map(str, periods_p2))}"
            else:
                n = len(work_df)
                mid = max(1, n // 2)
                p1 = work_df.iloc[:mid]
                p2 = work_df.iloc[mid:]
                p1_label = "Baseline (First Half)"
                p2_label = "Current (Second Half)"
    else:
        n = len(work_df)
        mid = max(1, n // 2)
        p1 = work_df.iloc[:mid]
        p2 = work_df.iloc[mid:]
        p1_label = "Baseline (First Half)"
        p2_label = "Current (Second Half)"

    m1_total = float(p1[metric_column].sum())
    m2_total = float(p2[metric_column].sum())
    delta_total = m2_total - m1_total
    pct_change = round((delta_total / m1_total * 100), 2) if m1_total != 0 else 0.0

    dimension_results = {}
    recommendations = []
    top_driver_dim = None
    max_variance_explained = 0.0

    for dim in dimension_columns:
        if dim not in work_df.columns:
            continue

        g1 = p1.groupby(dim, observed=False)[metric_column].sum()
        g2 = p2.groupby(dim, observed=False)[metric_column].sum()

        all_cats = sorted(list(set(g1.index.dropna()).union(set(g2.index.dropna()))))
        items = []

        for cat in all_cats:
            v1 = float(g1.get(cat, 0.0))
            v2 = float(g2.get(cat, 0.0))
            delta = v2 - v1
            pct = round((delta / v1 * 100), 2) if v1 != 0 else (100.0 if v2 > 0 else 0.0)
            share = round((delta / delta_total * 100), 2) if delta_total != 0 else 0.0

            items.append({
                "segment": str(cat),
                "baseline_value": round(v1, 2),
                "comparison_value": round(v2, 2),
                "delta": round(delta, 2),
                "percent_change": pct,
                "contribution_share": share,
            })

        # Sort items by negative delta first (detractors), then contributors
        detractors = sorted([i for i in items if i["delta"] < 0], key=lambda x: x["delta"])
        contributors = sorted([i for i in items if i["delta"] > 0], key=lambda x: x["delta"], reverse=True)

        # Variance explained
        sum_abs_deltas = sum(abs(i["delta"]) for i in items)
        if sum_abs_deltas > max_variance_explained:
            max_variance_explained = sum_abs_deltas
            top_driver_dim = dim

        dimension_results[dim] = {
            "dimension": dim,
            "unique_segments": len(all_cats),
            "top_detractors": detractors[:5],
            "top_contributors": contributors[:5],
            "all_segments": items,
        }

    # Generate Waterfall Chart Steps for the top driver dimension
    waterfall_steps = []
    if top_driver_dim and top_driver_dim in dimension_results:
        waterfall_steps.append({"name": p1_label, "value": round(m1_total, 2), "type": "total"})
        dim_info = dimension_results[top_driver_dim]
        # Include top 3 detractors and top 3 contributors
        featured = dim_info["top_detractors"][:3] + dim_info["top_contributors"][:3]
        featured_names = {f["segment"] for f in featured}
        for f in featured:
            waterfall_steps.append({
                "name": f"{f['segment']}",
                "value": f["delta"],
                "type": "delta",
                "contribution_share": f["contribution_share"],
            })

        other_delta = delta_total - sum(f["delta"] for f in featured)
        if round(other_delta, 2) != 0:
            waterfall_steps.append({
                "name": "Other Segments",
                "value": round(other_delta, 2),
                "type": "delta",
                "contribution_share": round((other_delta / delta_total * 100), 2) if delta_total != 0 else 0.0,
            })
        waterfall_steps.append({"name": p2_label, "value": round(m2_total, 2), "type": "total"})

    # Actionable Recommendations Engine
    direction = "declined" if delta_total < 0 else "increased"
    if top_driver_dim and top_driver_dim in dimension_results:
        top_info = dimension_results[top_driver_dim]
        if delta_total < 0 and top_info["top_detractors"]:
            det = top_info["top_detractors"][0]
            recommendations.append(
                f"Immediate Root Cause: Primary detractor '{det['segment']}' in dimension '{top_driver_dim}' fell by {abs(det['delta']):,.2f} ({det['contribution_share']}% of total decline). Conduct an immediate operational and pricing review of this segment."
            )
        elif delta_total > 0 and top_info["top_contributors"]:
            con = top_info["top_contributors"][0]
            recommendations.append(
                f"Growth Engine: Primary growth contributor is '{con['segment']}' in dimension '{top_driver_dim}' with +{con['delta']:,.2f} ({con['contribution_share']}% of total gain). Reallocate resources to capitalize on this expansion."
            )

        if len(top_info["top_detractors"]) > 1:
            det2 = top_info["top_detractors"][1]
            recommendations.append(
                f"Secondary Risk Factor: '{det2['segment']}' contributed {abs(det2['delta']):,.2f} to the decline. Audit supply chain and customer retention in this area."
            )

        if top_info["top_contributors"]:
            con = top_info["top_contributors"][0]
            recommendations.append(
                f"Opportunity: Benchmark best practices from '{con['segment']}' across underperforming segments."
            )

    if not recommendations:
        recommendations.append(f"Metric '{metric_column}' remained relatively stable across observed periods.")

    return {
        "metric_column": metric_column,
        "primary_driver_dimension": top_driver_dim,
        "baseline_period": p1_label,
        "comparison_period": p2_label,
        "baseline_value": round(m1_total, 2),
        "comparison_value": round(m2_total, 2),
        "total_delta": round(delta_total, 2),
        "percent_change": pct_change,
        "direction": direction,
        "dimensions": dimension_results,
        "waterfall_steps": waterfall_steps,
        "recommendations": recommendations,
        "executive_summary": (
            f"{metric_column.capitalize()} {direction} by {abs(delta_total):,.2f} ({pct_change}%) between {p1_label} and {p2_label}. "
            f"The primary root-cause driver identified is '{top_driver_dim}'."
        ),
    }
