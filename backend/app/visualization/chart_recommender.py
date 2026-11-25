"""Rule-Based Intelligent Chart Selection & Recommendation Engine for Analyticx AI.

Selects analytically sound, readable, and dataset-validated charts based on:
- Universal Data Understanding metadata (numeric, categorical, datetime, geographic, ID exclusion)
- Cardinality, distributions, and correlation structure
- Natural-language analytical purpose when provided
- Chart validation & non-empty data verification before returning recommendations
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from app.analytics.data_understanding import understand_dataset
from app.analytics.statistics import calculate_correlation
from app.visualization.chart_schemas import ChartConfig
from app.visualization.chart_validator import validate_chart_config
from app.visualization.data_mapper import build_chart_data


def recommend_charts_for_dataset(
    df: pd.DataFrame,
    query: str = "",
    understanding: Optional[Dict[str, Any]] = None,
    max_recommendations: int = 8,
) -> List[Dict[str, Any]]:
    """
    Recommends validated, non-redundant charts customized to the dataset structure
    and optional user intent. Never recommends IDs as metrics or unreadable pies.
    """
    if df is None or df.empty:
        return []

    if understanding is None:
        understanding = understand_dataset(df, sanitize=True)

    norm_df = understanding["normalized_df"]
    profile = understanding["profile"]

    num_cols = profile.get("numerical_columns", [])
    cat_cols = [
        c for c in profile.get("categorical_columns", []) + profile.get("boolean_columns", [])
        if c not in profile.get("identifier_columns", [])
    ]
    dt_cols = profile.get("datetime_columns", [])
    geo_cols = [c for c in profile.get("geographic_columns", []) if c not in num_cols]
    col_meta = {c["name"]: c for c in profile.get("columns", [])}

    # Eligible categorical dimensions ordered by cleanest cardinality (2..15 first)
    low_card_cats = [c for c in cat_cols if 2 <= (col_meta.get(c, {}).get("unique_count") or 0) <= 7]
    med_card_cats = [c for c in cat_cols if 2 <= (col_meta.get(c, {}).get("unique_count") or 0) <= 15]
    usable_cats = med_card_cats or [c for c in cat_cols if (col_meta.get(c, {}).get("unique_count") or 0) >= 2]

    candidates: List[Dict[str, Any]] = []

    # Rule 1: Date + numeric measure -> Time Series / Line Chart
    if dt_cols and num_cols:
        d_col = dt_cols[0]
        m_col = num_cols[0]
        candidates.append({
            "chart_type": "time_series",
            "title": f"{m_col} Trend Over Time",
            "reason": f"Chronological '{d_col}' pairs naturally with quantitative measure '{m_col}'.",
            "purpose": "trend",
            "priority": 98,
            "data_mapping": {"x": d_col, "y": m_col},
            "aggregation": "sum",
            "source_columns": [d_col, m_col],
        })

    # Rule 2: Category + numeric measure -> Bar / Horizontal Bar
    if usable_cats and num_cols:
        c_col = usable_cats[0]
        m_col = num_cols[0]
        uniq = col_meta.get(c_col, {}).get("unique_count") or 0
        c_type = "horizontal_bar" if uniq > 7 else "bar"
        candidates.append({
            "chart_type": c_type,
            "title": f"{m_col} by {c_col}",
            "reason": f"Compares '{m_col}' across the {uniq} categories of '{c_col}'.",
            "purpose": "comparison",
            "priority": 95,
            "data_mapping": {"x": c_col, "y": m_col},
            "aggregation": "mean" if uniq > 10 else "sum",
            "limit": 15 if uniq > 15 else None,
            "source_columns": [c_col, m_col],
        })

    # Rule 3: Two numerical columns -> Scatter Plot (favor strongest correlation)
    if len(num_cols) >= 2:
        corr_info = calculate_correlation(norm_df, numeric_columns=num_cols[:8])
        top_pairs = corr_info.get("notable_correlations", [])
        if top_pairs:
            p0 = top_pairs[0]
            x_c, y_c = p0["col1"], p0["col2"]
            r_val = p0.get("pearson_r")
            reason = f"Strongest numerical pair (r = {r_val:+.2f}); inspects linear/cluster relationship."
        else:
            x_c, y_c = num_cols[0], num_cols[1]
            reason = f"Visualizes joint distribution and relationship between '{x_c}' and '{y_c}'."
        candidates.append({
            "chart_type": "scatter",
            "title": f"{x_c} vs {y_c}",
            "reason": reason,
            "purpose": "relationship",
            "priority": 90 if top_pairs else 78,
            "data_mapping": {"x": x_c, "y": y_c},
            "source_columns": [x_c, y_c],
        })

    # Rule 4: Numerical distribution by category -> Box Plot
    if low_card_cats and num_cols:
        candidates.append({
            "chart_type": "box",
            "title": f"{num_cols[0]} Spread Across {low_card_cats[0]}",
            "reason": f"Reveals median, IQR quartiles, and tail outliers of '{num_cols[0]}' per '{low_card_cats[0]}'.",
            "purpose": "distribution",
            "priority": 86,
            "data_mapping": {"x": low_card_cats[0], "y": num_cols[0]},
            "source_columns": [low_card_cats[0], num_cols[0]],
        })

    # Rule 5: Single numerical column -> Histogram
    if num_cols:
        candidates.append({
            "chart_type": "histogram",
            "title": f"Distribution of {num_cols[0]}",
            "reason": f"Displays frequency distribution, skewness, and value concentration for '{num_cols[0]}'.",
            "purpose": "distribution",
            "priority": 84,
            "data_mapping": {"x": num_cols[0]},
            "aggregation": "count",
            "source_columns": [num_cols[0]],
        })

    # Rule 6: Small category distribution -> Donut Chart (only when 2..7 categories)
    if low_card_cats:
        c_col = low_card_cats[0]
        m_col = num_cols[0] if num_cols else c_col
        agg_mode = "sum" if num_cols else "count"
        candidates.append({
            "chart_type": "donut",
            "title": f"Share Breakdown by {c_col}",
            "reason": f"Compact proportional composition across {col_meta[c_col]['unique_count']} categories in '{c_col}'.",
            "purpose": "composition",
            "priority": 80,
            "data_mapping": {"labels": c_col, "values": m_col},
            "aggregation": agg_mode,
            "source_columns": list(dict.fromkeys([c_col, m_col])),
        })

    # Rule 7: Multiple numeric columns -> Correlation Heatmap
    if len(num_cols) >= 3:
        cols_subset = num_cols[:10]
        candidates.append({
            "chart_type": "correlation_matrix",
            "title": "Correlation Matrix Across Numeric Measures",
            "reason": f"Summarizes pairwise correlations across {len(cols_subset)} numeric measures.",
            "purpose": "relationship",
            "priority": 82,
            "data_mapping": {"columns": cols_subset},
            "source_columns": cols_subset,
        })

    # Rule 8: Two categories + numeric measure -> Stacked Bar
    if len(low_card_cats) >= 2 and num_cols:
        c1, c2 = low_card_cats[0], low_card_cats[1]
        m_col = num_cols[0]
        candidates.append({
            "chart_type": "stacked_bar",
            "title": f"{m_col} by {c1} Split by {c2}",
            "reason": f"Compares multi-category composition of '{m_col}' across '{c1}' and '{c2}'.",
            "purpose": "comparison",
            "priority": 76,
            "data_mapping": {"x": c1, "y": m_col, "series": c2},
            "aggregation": "sum",
            "source_columns": [c1, c2, m_col],
        })

    # Rule 9: Geographic column + measure -> Geo Map
    if geo_cols and num_cols:
        g_col = geo_cols[0]
        if col_meta.get(g_col, {}).get("semantic_type") in {"geo_country", "geo_state"}:
            candidates.append({
                "chart_type": "geo_map",
                "title": f"Geographic Distribution of {num_cols[0]} by {g_col}",
                "reason": f"Maps '{num_cols[0]}' across geographic locations in '{g_col}'.",
                "purpose": "geographic",
                "priority": 79,
                "data_mapping": {"location": g_col, "value": num_cols[0]},
                "aggregation": "sum",
                "source_columns": [g_col, num_cols[0]],
            })

    # Rule 10: Fallback category frequency bar if dataset is purely categorical
    if not num_cols and cat_cols:
        for idx, c_col in enumerate(cat_cols[:3]):
            uniq = col_meta.get(c_col, {}).get("unique_count") or 0
            c_type = "horizontal_bar" if uniq > 7 else "bar"
            candidates.append({
                "chart_type": c_type,
                "title": f"Frequency Count by {c_col}",
                "reason": f"Shows category counts across {uniq} distinct labels in '{c_col}'.",
                "purpose": "comparison",
                "priority": 88 - idx * 5,
                "data_mapping": {"x": c_col, "y": c_col},
                "aggregation": "count",
                "limit": 15 if uniq > 15 else None,
                "source_columns": [c_col],
            })

    # Validate every candidate and verify non-empty rendered output
    validated_recs: List[Dict[str, Any]] = []
    seen_keys = set()
    for cand in sorted(candidates, key=lambda x: x["priority"], reverse=True):
        cfg = ChartConfig(
            chart_type=cand["chart_type"],
            title=cand["title"],
            data_mapping=cand["data_mapping"],
            aggregation=cand.get("aggregation") or "sum",
            limit=cand.get("limit"),
        )
        val_res = validate_chart_config(norm_df, cfg, understanding=understanding)
        if not val_res.valid:
            continue
        rendered = build_chart_data(norm_df, cfg, normalized_df=norm_df)
        if not rendered:
            continue
        sig = (cand["chart_type"], tuple(sorted(cand.get("source_columns") or [])))
        if sig in seen_keys:
            continue
        seen_keys.add(sig)
        validated_recs.append({
            **cand,
            "valid": True,
            "warnings": val_res.warnings,
            "preview_row_count": len(rendered),
        })
        if len(validated_recs) >= max_recommendations:
            break

    return validated_recs


def select_best_chart_for_query(
    df: pd.DataFrame,
    query: str = "",
    dimension: Optional[str] = None,
    metric: Optional[str] = None,
    understanding: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Selects and validates a single best chart specification for an NL or tool request."""
    if df is None or df.empty:
        return {"error": "Cannot recommend chart on an empty dataset."}

    if understanding is None:
        understanding = understand_dataset(df, sanitize=True)

    norm_df = understanding["normalized_df"]
    profile = understanding["profile"]
    q = str(query or "").lower()

    num_cols = profile.get("numerical_columns", [])
    cat_cols = [c for c in profile.get("categorical_columns", []) + profile.get("boolean_columns", []) if c not in profile.get("identifier_columns", [])]
    dt_cols = profile.get("datetime_columns", [])
    col_meta = {c["name"]: c for c in profile.get("columns", [])}

    # Resolve mentioned dimension / metric if not explicitly supplied
    if not dimension:
        for c in cat_cols + dt_cols:
            if c.lower() in q:
                dimension = c
                break
    if not metric:
        for c in num_cols:
            if c.lower() in q and c != dimension:
                metric = c
                break

    # Intent-driven chart type selection with dataset guardrails
    requested_type = None
    if any(k in q for k in ("correlation matrix", "heatmap")):
        requested_type = "correlation_matrix"
    elif any(k in q for k in ("correlation", "scatter", "relationship", " vs ")):
        requested_type = "scatter"
    elif any(k in q for k in ("histogram", "distribution", "spread")):
        requested_type = "histogram"
    elif any(k in q for k in ("box plot", "boxplot", "outlier")):
        requested_type = "box"
    elif any(k in q for k in ("trend", "over time", "monthly", "daily", "weekly", "yearly", "time series")):
        requested_type = "time_series" if dt_cols else "line"
    elif any(k in q for k in ("pie", "donut", "share", "proportion", "breakdown")):
        requested_type = "donut"
    elif any(k in q for k in ("map", "geographic", "country", "state")):
        requested_type = "geo_map"

    if requested_type == "correlation_matrix" and len(num_cols) >= 2:
        cfg = ChartConfig(chart_type="correlation_matrix", title="Correlation Matrix", data_mapping={"columns": num_cols[:10]})
    elif requested_type == "scatter" and len(num_cols) >= 2:
        x_c = metric or num_cols[0]
        y_c = next((c for c in num_cols if c != x_c), num_cols[1])
        cfg = ChartConfig(chart_type="scatter", title=f"{x_c} vs {y_c}", data_mapping={"x": x_c, "y": y_c})
    elif requested_type == "histogram" and num_cols:
        target = metric or num_cols[0]
        cfg = ChartConfig(chart_type="histogram", title=f"Distribution of {target}", data_mapping={"x": target}, aggregation="count")
    elif requested_type == "box" and num_cols:
        target = metric or num_cols[0]
        grp = dimension or (cat_cols[0] if cat_cols and (col_meta[cat_cols[0]]["unique_count"] <= 12) else None)
        mapping = {"y": target, **({"x": grp} if grp else {})}
        cfg = ChartConfig(chart_type="box", title=f"{target} Box Plot", data_mapping=mapping)
    elif requested_type in {"time_series", "line"} and (dt_cols or dimension) and num_cols:
        d_col = dimension if (dimension and dimension in dt_cols) else (dt_cols[0] if dt_cols else (dimension or num_cols[0]))
        m_col = metric or num_cols[0]
        c_type = "time_series" if d_col in dt_cols else "line"
        cfg = ChartConfig(chart_type=c_type, title=f"{m_col} Over {d_col}", data_mapping={"x": d_col, "y": m_col}, aggregation="sum")
    elif requested_type in {"pie", "donut"} and (dimension or cat_cols):
        c_col = dimension or cat_cols[0]
        uniq = col_meta.get(c_col, {}).get("unique_count") or 0
        m_col = metric or (num_cols[0] if num_cols else c_col)
        agg = "sum" if metric or num_cols else "count"
        # Respect readability guardrail: use bar instead of pie for > 12 categories!
        c_type = "donut" if uniq <= 12 else "horizontal_bar"
        mapping = {"labels": c_col, "values": m_col} if c_type == "donut" else {"x": c_col, "y": m_col}
        cfg = ChartConfig(chart_type=c_type, title=f"{m_col if agg != 'count' else 'Count'} by {c_col}", data_mapping=mapping, aggregation=agg, limit=15 if uniq > 15 else None)
    else:
        recs = recommend_charts_for_dataset(norm_df, query=query, understanding=understanding, max_recommendations=1)
        if recs:
            r0 = recs[0]
            return {
                "chart_type": r0["chart_type"],
                "title": r0["title"],
                "x": r0["data_mapping"].get("x") or r0["data_mapping"].get("labels"),
                "y": r0["data_mapping"].get("y") or r0["data_mapping"].get("values"),
                "data_mapping": r0["data_mapping"],
                "aggregation": r0.get("aggregation", "sum"),
                "reason": r0["reason"],
                "confidence": 0.95,
                "available_columns": [str(c) for c in norm_df.columns],
            }
        # Last-resort count bar on first non-ID column
        cols = [str(c) for c in norm_df.columns]
        c0 = cat_cols[0] if cat_cols else cols[0]
        cfg = ChartConfig(chart_type="bar", title=f"Count by {c0}", data_mapping={"x": c0, "y": c0}, aggregation="count")

    val_res = validate_chart_config(norm_df, cfg, understanding=understanding)
    if not val_res.valid:
        recs = recommend_charts_for_dataset(norm_df, query=query, understanding=understanding, max_recommendations=1)
        if recs:
            r0 = recs[0]
            return {
                "chart_type": r0["chart_type"],
                "title": r0["title"],
                "x": r0["data_mapping"].get("x") or r0["data_mapping"].get("labels"),
                "y": r0["data_mapping"].get("y") or r0["data_mapping"].get("values"),
                "data_mapping": r0["data_mapping"],
                "aggregation": r0.get("aggregation", "sum"),
                "reason": r0["reason"],
                "confidence": 0.9,
                "available_columns": [str(c) for c in norm_df.columns],
            }

    return {
        "chart_type": cfg.chart_type,
        "title": cfg.title,
        "x": cfg.data_mapping.get("x") or cfg.data_mapping.get("labels"),
        "y": cfg.data_mapping.get("y") or cfg.data_mapping.get("values"),
        "data_mapping": cfg.data_mapping,
        "aggregation": cfg.aggregation or "sum",
        "confidence": 0.95,
        "warnings": val_res.warnings,
        "available_columns": [str(c) for c in norm_df.columns],
    }
