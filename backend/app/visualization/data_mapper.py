"""Intelligent Chart Data Preparation & Aggregation Engine for Analyticx AI."""
from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.analytics.data_understanding import understand_dataset
from app.analytics.profiling import to_python
from app.visualization.chart_schemas import ChartConfig

AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count", "nunique"}


def _apply_filters(df: pd.DataFrame, filters: List[Dict[str, Any]]) -> pd.DataFrame:
    result = df
    for f in filters or []:
        column = f.get("column")
        op = f.get("op", "eq")
        value = f.get("value")

        if column not in result.columns:
            continue

        if op == "eq":
            result = result[result[column] == value]
        elif op == "neq":
            result = result[result[column] != value]
        elif op == "gt":
            result = result[pd.to_numeric(result[column], errors="coerce") > float(value)]
        elif op == "gte":
            result = result[pd.to_numeric(result[column], errors="coerce") >= float(value)]
        elif op == "lt":
            result = result[pd.to_numeric(result[column], errors="coerce") < float(value)]
        elif op == "lte":
            result = result[pd.to_numeric(result[column], errors="coerce") <= float(value)]
        elif op == "in":
            result = result[result[column].isin(value or [])]
        elif op == "not_in":
            result = result[~result[column].isin(value or [])]
        elif op == "contains":
            result = result[result[column].astype(str).str.contains(str(value), case=False, na=False)]
        elif op == "not_contains":
            result = result[~result[column].astype(str).str.contains(str(value), case=False, na=False)]
        elif op == "between" and isinstance(value, list) and len(value) == 2:
            result = result[pd.to_numeric(result[column], errors="coerce").between(float(value[0]), float(value[1]))]
        elif op in {"top_n", "bottom_n"}:
            try:
                limit = max(1, min(int(value), 200))
                num_s = pd.to_numeric(result[column], errors="coerce")
                valid_idx = num_s.nlargest(limit).index if op == "top_n" else num_s.nsmallest(limit).index
                result = result.loc[valid_idx]
            except (TypeError, ValueError):
                continue
    return result


def _aggregate(df: pd.DataFrame, group_col: str, value_col: str | None, agg: str) -> pd.DataFrame:
    if agg not in AGGREGATIONS:
        agg = "sum"

    if value_col is None or agg == "count" or value_col not in df.columns:
        if agg == "nunique" and value_col and value_col in df.columns:
            grouped = df.groupby(group_col, dropna=True)[value_col].nunique().reset_index()
            grouped.columns = [group_col, value_col]
            return grouped
        out_col = value_col if (value_col and value_col != group_col) else "count"
        grouped = df.groupby(group_col, dropna=True).size().reset_index(name=out_col)
        return grouped

    if agg == "nunique":
        grouped = df.groupby(group_col, dropna=True)[value_col].nunique().reset_index()
        return grouped

    temp = df[[group_col]].copy()
    temp["__val"] = pd.to_numeric(df[value_col], errors="coerce")
    temp = temp.dropna(subset=[group_col, "__val"])
    if temp.empty:
        return pd.DataFrame(columns=[group_col, value_col])

    grouped = temp.groupby(group_col)["__val"].agg(agg).reset_index()
    grouped.columns = [group_col, value_col]
    return grouped


def _resample_temporal_axis(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    agg: str,
    granularity: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """Parses datetime axis, groups/resamples chronologically, and formats clean sorted dates."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            dt = pd.to_datetime(df[x_col], format="mixed", errors="coerce")
        except TypeError:
            dt = pd.to_datetime(df[x_col], errors="coerce")

    if dt.notna().sum() < 2 or dt.notna().mean() < 0.7:
        return None

    work = df.copy()
    work["__dt"] = dt
    work = work.dropna(subset=["__dt"]).sort_values("__dt")
    if work.empty:
        return None

    freq_map = {"day": "D", "daily": "D", "week": "W", "weekly": "W", "month": "ME", "monthly": "ME", "quarter": "Q", "quarterly": "Q", "year": "YE", "yearly": "YE"}
    freq = freq_map.get(str(granularity or "").lower())

    agg_fn = agg if agg in {"sum", "mean", "median", "min", "max", "count"} else "sum"
    frames: List[pd.DataFrame] = []
    for y_col in y_cols:
        sub = work[["__dt"]].copy()
        if agg_fn == "count" or y_col == x_col:
            sub["__val"] = 1
        else:
            sub["__val"] = pd.to_numeric(work[y_col], errors="coerce")
        sub = sub.dropna()
        if sub.empty:
            continue
        if freq:
            grp = sub.set_index("__dt")["__val"].resample(freq).agg(agg_fn)
            cnt = sub.set_index("__dt")["__val"].resample(freq).count()
            grp = grp[cnt > 0].reset_index()
        else:
            grp = sub.groupby("__dt")["__val"].agg(agg_fn).reset_index()
        grp = grp.sort_values("__dt")
        grp[x_col] = grp["__dt"].apply(lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d))
        out_name = "count" if (agg_fn == "count" and y_col == x_col) else y_col
        grp = grp[[x_col, "__val"]].rename(columns={"__val": out_name})
        frames.append(grp)

    if not frames:
        return None
    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on=x_col, how="outer")
    return merged


def _rows_to_python(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return [{str(k): to_python(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def build_chart_data(
    df: pd.DataFrame,
    config: ChartConfig,
    normalized_df: Optional[pd.DataFrame] = None,
) -> List[Dict[str, Any]]:
    chart_type = config.chart_type
    mapping = dict(config.data_mapping or {})
    agg = (config.aggregation or "sum").lower()
    appearance = config.appearance or {}

    base_df = normalized_df if normalized_df is not None else understand_dataset(df, sanitize=True)["normalized_df"]
    working = _apply_filters(base_df, config.filters)
    if working.empty:
        return []

    if chart_type in {
        "bar", "horizontal_bar", "column", "grouped_bar", "clustered_bar",
        "stacked_bar", "hundred_percent_stacked_bar", "line", "area",
        "stacked_area", "pie", "donut", "funnel", "treemap",
    }:
        x = mapping.get("x") or mapping.get("labels")
        y = mapping.get("y") or mapping.get("values")
        series = mapping.get("series")

        if not x:
            return []
        if not y and agg == "count":
            y = x
        if not y:
            return []
        if x not in working.columns:
            return []

        # Temporal ordering & granularity for line / area charts
        if chart_type in {"line", "area", "stacked_area"} and not series:
            y_list = [c for c in (y if isinstance(y, list) else [y]) if c in working.columns]
            if y_list:
                temporal_df = _resample_temporal_axis(
                    working, x, y_list, agg, granularity=appearance.get("date_granularity")
                )
                if temporal_df is not None:
                    if config.limit:
                        temporal_df = temporal_df.head(config.limit)
                    return _rows_to_python(temporal_df)

        # Multi-measure bars/lines (no series dimension)
        if isinstance(y, list):
            y_columns = [column for column in y if column in working.columns]
            if not y_columns or series:
                return []
            grouped_frames = [_aggregate(working, x, column, agg) for column in y_columns]
            merged = grouped_frames[0]
            for frame in grouped_frames[1:]:
                merged = merged.merge(frame, on=x, how="outer")
            if config.limit:
                merged = merged.head(config.limit)
            return _rows_to_python(merged)

        # Multi-series long format (compatible with Plotly grouped/stacked BarChart & LineChart)
        if series and series in working.columns:
            val_col = y if (y in working.columns and agg != "count") else None
            sub = working[[x, series] + ([val_col] if val_col and val_col not in {x, series} else [])].dropna(subset=[x, series])
            if sub.empty:
                return []

            if val_col is None or agg == "count":
                grouped = sub.groupby([x, series]).size().reset_index(name="__val")
                target_y_key = y if (isinstance(y, str) and y != x and y != series) else "count"
            else:
                sub["__num"] = pd.to_numeric(sub[val_col], errors="coerce")
                sub = sub.dropna(subset=["__num"])
                grouped = sub.groupby([x, series])["__num"].agg(agg if agg in AGGREGATIONS else "sum").reset_index(name="__val")
                target_y_key = val_col

            if chart_type == "hundred_percent_stacked_bar":
                totals = grouped.groupby(x)["__val"].transform("sum")
                grouped["__val"] = np.where(totals != 0, (grouped["__val"] / totals) * 100.0, 0.0).round(2)

            grouped = grouped.rename(columns={"__val": target_y_key})
            return _rows_to_python(grouped)

        # Single x, single y
        if y not in working.columns and agg != "count":
            return []

        grouped = _aggregate(working, x, y, agg)
        if grouped.empty:
            return []
        metric_col_out = [c for c in grouped.columns if c != x][0]

        if config.sort:
            sort_col = config.sort.get("column", metric_col_out)
            ascending = config.sort.get("ascending", False)
            if sort_col in grouped.columns:
                grouped = grouped.sort_values(sort_col, ascending=ascending)
        elif chart_type in {"pie", "donut", "funnel", "treemap", "bar", "horizontal_bar", "column"}:
            grouped = grouped.sort_values(metric_col_out, ascending=False)

        # Keep pie / donut clean by consolidating > 10 tiny categories into 'Other'
        if chart_type in {"pie", "donut"} and len(grouped) > 10:
            top_slice = grouped.head(9).copy()
            other_sum = float(grouped.iloc[9:][metric_col_out].sum())
            if other_sum > 0:
                other_row = pd.DataFrame([{x: "Other", metric_col_out: other_sum}])
                grouped = pd.concat([top_slice, other_row], ignore_index=True)
            else:
                grouped = top_slice

        if config.limit:
            grouped = grouped.head(config.limit)

        # Ensure mapped key name matches frontend expectation when y == x (count mode)
        if y == x and metric_col_out == "count":
            pass
        return _rows_to_python(grouped)

    if chart_type == "histogram":
        x = mapping.get("x")
        if not x or x not in working.columns:
            return []
        clean = pd.to_numeric(working[x], errors="coerce").dropna()
        if clean.empty:
            return []
        if clean.nunique() <= 1:
            val = float(clean.iloc[0])
            return [{"bin_start": to_python(val), "bin_end": to_python(val), "count": int(len(clean))}]
        bins_n = min(int(config.limit or 15), int(clean.nunique()))
        counts, bin_edges = np.histogram(clean, bins=max(2, bins_n))
        return [
            {
                "bin_start": to_python(round(float(bin_edges[i]), 4)),
                "bin_end": to_python(round(float(bin_edges[i + 1]), 4)),
                "count": int(counts[i]),
            }
            for i in range(len(counts))
        ]

    if chart_type == "scatter":
        x = mapping.get("x")
        y = mapping.get("y")
        color = mapping.get("color")
        if not x or not y or x not in working.columns or y not in working.columns:
            return []
        cols = list(dict.fromkeys([x, y] + ([color] if color and color in working.columns else [])))
        subset = working[cols].copy()
        subset[x] = pd.to_numeric(subset[x], errors="coerce")
        if y != x:
            subset[y] = pd.to_numeric(subset[y], errors="coerce")
        subset = subset.dropna().head(2000)
        rows = _rows_to_python(subset)
        if x == y:
            # Ensure payload explicitly keeps single unambiguous key without duplicate column warnings
            pass
        return rows

    if chart_type == "bubble":
        x = mapping.get("x")
        y = mapping.get("y")
        size = mapping.get("size")
        color = mapping.get("color")
        if not x or not y or not size or any(c not in working.columns for c in (x, y, size)):
            return []
        cols = list(dict.fromkeys([x, y, size] + ([color] if color and color in working.columns else [])))
        subset = working[cols].copy()
        for num_c in list(dict.fromkeys([x, y, size])):
            subset[num_c] = pd.to_numeric(subset[num_c], errors="coerce")
        subset = subset.dropna().head(2000)
        return _rows_to_python(subset)

    if chart_type in {"box", "violin"}:
        y = mapping.get("y")
        x = mapping.get("x")
        if not y or y not in working.columns:
            return []
        sub = working[[y] + ([x] if x and x in working.columns and x != y else [])].copy()
        sub[y] = pd.to_numeric(sub[y], errors="coerce")
        sub = sub.dropna(subset=[y])
        if sub.empty:
            return []
        if x and x in sub.columns:
            top_cats = sub[x].value_counts().head(12).index.tolist()
            sub = sub[sub[x].isin(top_cats)]
            groups = sub.groupby(x)[y].apply(list).reset_index()
            return [
                {"group": to_python(row[x]), "values": [to_python(v) for v in row[y][:500]]}
                for _, row in groups.iterrows()
            ]
        return [{"group": y, "values": [to_python(v) for v in sub[y].head(1000).tolist()]}]

    if chart_type in {"heatmap", "correlation_matrix"}:
        columns = mapping.get("columns") or []
        valid_cols = [c for c in columns if c in working.columns]
        if len(valid_cols) < 2:
            valid_cols = working.select_dtypes(include=[np.number]).columns.tolist()
        if len(valid_cols) < 2:
            return []
        method = appearance.get("method", "pearson")
        if method not in {"pearson", "spearman"}:
            method = "pearson"
        num_sub = working[valid_cols].apply(pd.to_numeric, errors="coerce")
        corr = num_sub.corr(method=method).round(4)
        return [
            {"x": str(col_x), "y": str(col_y), "value": to_python(corr.loc[col_y, col_x]) or 0.0}
            for col_y in corr.index
            for col_x in corr.columns
        ]

    if chart_type == "geo_map":
        loc_col = mapping.get("location") or mapping.get("x")
        val_col = mapping.get("value") or mapping.get("y")
        if not loc_col or loc_col not in working.columns:
            return []
        grouped = _aggregate(working, loc_col, val_col if val_col in working.columns else None, agg)
        metric_out = [c for c in grouped.columns if c != loc_col][0]
        return [
            {"location": to_python(row[loc_col]), "value": to_python(row[metric_out])}
            for _, row in grouped.iterrows()
        ]

    if chart_type == "kpi":
        value_col = mapping.get("value")
        if not value_col or value_col not in working.columns:
            return []
        series = pd.to_numeric(working[value_col], errors="coerce").dropna()
        if series.empty:
            return []
        value = series.agg(agg) if agg in AGGREGATIONS and agg != "nunique" else (
            series.nunique() if agg == "nunique" else series.sum()
        )
        comparison_col = mapping.get("comparison")
        comparison = None
        if comparison_col and comparison_col in working.columns:
            comp_s = pd.to_numeric(working[comparison_col], errors="coerce").dropna()
            if not comp_s.empty:
                comparison = comp_s.agg(agg) if agg in AGGREGATIONS and agg != "nunique" else comp_s.sum()
        return [{"value": to_python(value), "comparison": to_python(comparison), "label": value_col}]

    if chart_type == "table":
        cols = [c for c in (mapping.get("columns") or []) if c in working.columns]
        if not cols:
            cols = list(working.columns[:10])
        subset = working[cols].head(config.limit or 100)
        return _rows_to_python(subset)

    if chart_type == "matrix":
        rows = mapping.get("rows") or []
        columns = mapping.get("columns") or []
        value = mapping.get("values")
        row_col = rows[0] if rows else None
        column_col = columns[0] if columns else None
        if not row_col or not column_col or not value or any(c not in working.columns for c in (row_col, column_col, value)):
            return []
        sub = working[[row_col, column_col]].copy()
        sub[value] = pd.to_numeric(working[value], errors="coerce").fillna(0)
        matrix = sub.pivot_table(index=row_col, columns=column_col, values=value, aggfunc=agg if agg in AGGREGATIONS else "sum", fill_value=0).reset_index()
        return _rows_to_python(matrix)

    if chart_type == "waterfall":
        labels = mapping.get("labels") or mapping.get("x")
        values = mapping.get("values") or mapping.get("y")
        if not labels or not values or labels not in working.columns or values not in working.columns:
            return []
        grouped = _aggregate(working, labels, values, agg)
        return _rows_to_python(grouped)

    if chart_type == "gauge":
        value_col = mapping.get("value")
        if not value_col or value_col not in working.columns:
            return []
        series = pd.to_numeric(working[value_col], errors="coerce").dropna()
        if series.empty:
            return []
        value = series.agg(agg) if agg in AGGREGATIONS and agg != "nunique" else series.sum()
        return [{"value": to_python(value), "label": value_col}]

    if chart_type == "time_series":
        date_col = mapping.get("x") or mapping.get("date")
        value_col = mapping.get("y") or mapping.get("value")
        if not date_col or not value_col or date_col not in working.columns or value_col not in working.columns:
            return []
        temporal_df = _resample_temporal_axis(
            working, date_col, [value_col], agg, granularity=appearance.get("date_granularity")
        )
        if temporal_df is None:
            return []
        return [
            {date_col: to_python(row[date_col]), value_col: to_python(row[value_col])}
            for _, row in temporal_df.iterrows()
        ]

    if chart_type == "forecast":
        date_col = mapping.get("date") or mapping.get("x")
        value_col = mapping.get("value") or mapping.get("y")
        if not date_col or not value_col or date_col not in working.columns or value_col not in working.columns:
            return []
        temporal_df = _resample_temporal_axis(
            working, date_col, [value_col], agg, granularity=appearance.get("date_granularity")
        )
        if temporal_df is None:
            return []
        return [
            {"date": to_python(row[date_col]), "value": to_python(row[value_col])}
            for _, row in temporal_df.iterrows()
        ]

    return []
