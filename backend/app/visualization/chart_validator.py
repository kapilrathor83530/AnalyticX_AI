"""Semantic and Structural Chart Configuration Validator for Analyticx AI."""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from app.analytics.data_understanding import understand_dataset
from app.visualization.chart_registry import get_chart
from app.visualization.chart_schemas import ChartConfig, ChartValidationResult


def validate_chart_config(
    df: pd.DataFrame,
    config: ChartConfig,
    understanding: Optional[dict] = None,
) -> ChartValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    suggested_alternative: Optional[str] = None

    definition = get_chart(config.chart_type)
    if not definition:
        return ChartValidationResult(
            valid=False,
            errors=[f"Unknown chart type: '{config.chart_type}'"],
            suggested_alternative="bar",
        )

    if df is None or df.empty:
        return ChartValidationResult(valid=False, errors=["Dataset is empty; cannot render chart."])

    if understanding is None:
        understanding = understand_dataset(df, sanitize=True)

    norm_df = understanding["normalized_df"]
    profile = understanding["profile"]
    col_meta = {c["name"]: c for c in profile.get("columns", [])}
    columns = set(str(c) for c in norm_df.columns)
    agg = (config.aggregation or "sum").lower()
    mapping = config.data_mapping or {}

    # Normalize pie/donut/funnel/treemap alias keys transparently (x->labels, y->values)
    effective_mapping = dict(mapping)
    if config.chart_type in {"pie", "donut", "treemap", "funnel", "waterfall"}:
        if not effective_mapping.get("labels") and effective_mapping.get("x"):
            effective_mapping["labels"] = effective_mapping["x"]
        if not effective_mapping.get("values") and effective_mapping.get("y"):
            effective_mapping["values"] = effective_mapping["y"]
        # Count aggregation on labels doesn't strictly require separate measure
        if agg == "count" and effective_mapping.get("labels") and not effective_mapping.get("values"):
            effective_mapping["values"] = effective_mapping["labels"]

    # 1. Required roles & column existence
    for role in definition.data_roles:
        if not role.required:
            continue
        mapped = effective_mapping.get(role.name)
        if role.multiple:
            if not mapped:
                errors.append(f"Missing required data role: {role.label}")
            else:
                mapped_values = mapped if isinstance(mapped, list) else [mapped]
                for col in mapped_values:
                    if col not in columns:
                        errors.append(f"Column '{col}' not found for {role.label}")
        else:
            if not mapped:
                errors.append(f"Missing required data role: {role.label}")
            elif mapped not in columns:
                errors.append(f"Column '{mapped}' not found for {role.label}")

    if errors:
        return ChartValidationResult(valid=False, errors=errors, warnings=warnings, suggested_alternative=suggested_alternative)

    # 2. Measure compatibility & ID protection
    is_count_agg = agg in {"count", "nunique"}
    for role in definition.data_roles:
        col_val = effective_mapping.get(role.name)
        if not col_val:
            continue
        mapped_cols = col_val if isinstance(col_val, list) else [col_val]
        for mapped_column in mapped_cols:
            if mapped_column not in norm_df.columns:
                continue
            meta = col_meta.get(mapped_column, {})
            if role.type == "measure":
                if meta.get("is_identifier") and not is_count_agg:
                    errors.append(
                        f"Column '{mapped_column}' is detected as an identifier/key and should not be summed or averaged as a numeric measure."
                    )
                    suggested_alternative = suggested_alternative or "bar"
                elif not is_count_agg and not pd.api.types.is_numeric_dtype(norm_df[mapped_column]):
                    errors.append(
                        f"Measure '{mapped_column}' is non-numeric ({meta.get('detected_type', 'categorical')}). Choose a numeric column or set aggregation to 'count'."
                    )
                    suggested_alternative = suggested_alternative or "bar"
                elif pd.api.types.is_numeric_dtype(norm_df[mapped_column]) and norm_df[mapped_column].dropna().empty:
                    errors.append(f"Measure '{mapped_column}' contains only missing values.")

            if role.type == "date" or (config.chart_type == "time_series" and role.name == "x"):
                if meta.get("detected_type") != "datetime" and not pd.api.types.is_datetime64_any_dtype(norm_df[mapped_column]):
                    parsed_test = pd.to_datetime(norm_df[mapped_column], errors="coerce")
                    if parsed_test.notna().sum() < 2:
                        errors.append(
                            f"Column '{mapped_column}' does not contain valid chronological dates for a {config.chart_type} chart."
                        )
                        suggested_alternative = "bar"

    # 3. Chart-specific analytical readability & semantic rules
    if config.chart_type in {"pie", "donut"}:
        cat_col = effective_mapping.get("labels") or effective_mapping.get("x")
        if cat_col and cat_col in norm_df.columns:
            nunique = int(norm_df[cat_col].nunique(dropna=True))
            if nunique > 15:
                errors.append(
                    f"{config.chart_type.capitalize()} charts become unreadable with {nunique} categories (limit: 15). Use a Horizontal Bar or Bar chart instead."
                )
                suggested_alternative = "horizontal_bar"
            elif nunique > 8:
                warnings.append(f"'{cat_col}' has {nunique} categories; smaller categories will be grouped into 'Other'.")
        val_col = effective_mapping.get("values") or effective_mapping.get("y")
        if val_col and val_col in norm_df.columns and not is_count_agg:
            neg_series = pd.to_numeric(norm_df[val_col], errors="coerce").dropna()
            if (neg_series < 0).any():
                warnings.append(
                    f"Column '{val_col}' contains negative values, which cannot be meaningfully represented in a {config.chart_type} chart."
                )

    if config.chart_type in {"line", "area", "stacked_area"}:
        x_col = effective_mapping.get("x")
        if x_col and x_col in norm_df.columns:
            meta = col_meta.get(x_col, {})
            if meta.get("detected_type") not in {"datetime", "numeric"} and meta.get("semantic_type") != "temporal_year":
                warnings.append(
                    f"X-axis '{x_col}' appears to be an unordered category rather than dates or numeric steps; a Bar chart is usually more appropriate."
                )
                suggested_alternative = suggested_alternative or "bar"

    if config.chart_type == "correlation_matrix":
        cols = effective_mapping.get("columns") or profile.get("numerical_columns", [])
        if len(cols) < 2:
            errors.append("Correlation matrix requires at least 2 numerical columns.")

    return ChartValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        suggested_alternative=suggested_alternative,
    )
