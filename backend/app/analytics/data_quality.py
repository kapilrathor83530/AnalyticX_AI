"""Comprehensive Data Quality Inspection & Recommendation Engine for Analyticx AI."""
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from app.analytics.profiling import infer_column_type, to_python


def inspect_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    total_rows = int(df.shape[0])
    total_cols = int(df.shape[1])
    total_cells = total_rows * total_cols if total_rows and total_cols else 1

    # 1. Missing Values
    missing_by_col = {}
    total_missing_cells = 0
    high_missing_cols = []

    for col in df.columns:
        s = df[col]
        missing_count = int(s.isna().sum())
        total_missing_cells += missing_count
        missing_pct = round((missing_count / total_rows * 100), 2) if total_rows else 0.0
        
        if missing_count > 0:
            severity = "high" if missing_pct > 25 else ("medium" if missing_pct > 5 else "low")
            missing_by_col[col] = {
                "count": missing_count,
                "percent": missing_pct,
                "severity": severity,
                "dtype": str(s.dtype),
                "inferred_type": infer_column_type(s),
            }
            if missing_pct > 50:
                high_missing_cols.append(col)

    # 2. Duplicate Rows
    exact_duplicates = int(df.duplicated().sum())
    duplicate_pct = round((exact_duplicates / total_rows * 100), 2) if total_rows else 0.0

    # 3. Outlier Analysis (Numerical Columns)
    outliers_by_col = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        q1 = float(s.quantile(0.25))
        q3 = float(s.quantile(0.75))
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower_bound = round(q1 - 1.5 * iqr, 4)
        upper_bound = round(q3 + 1.5 * iqr, 4)

        outlier_mask = (s < lower_bound) | (s > upper_bound)
        outlier_count = int(outlier_mask.sum())
        
        if outlier_count > 0:
            outlier_pct = round((outlier_count / total_rows * 100), 2)
            sample_outliers = [to_python(v) for v in s[outlier_mask].head(6).tolist()]
            # Z-Score comparison
            mean_val = float(s.mean())
            std_val = float(s.std()) if s.std() > 0 else 1.0
            z_outliers = int((np.abs((s - mean_val) / std_val) > 3.0).sum())

            outliers_by_col[col] = {
                "outlier_count": outlier_count,
                "percent": outlier_pct,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "q1": q1,
                "q3": q3,
                "iqr": round(iqr, 4),
                "sample_values": sample_outliers,
                "zscore_outliers_count": z_outliers,
                "severity": "high" if outlier_pct > 10 else ("medium" if outlier_pct > 2 else "low"),
            }

    # 4. Text & Category Inconsistencies
    formatting_issues = {}
    string_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()

    for col in string_cols:
        s = df[col].dropna().astype(str)
        if len(s) == 0:
            continue
        
        # Leading / trailing spaces
        has_whitespace = s.str.startswith(" ") | s.str.endswith(" ")
        ws_count = int(has_whitespace.sum())

        # Mixed casing detection: e.g. "Male", "male"
        unique_vals = s.unique()
        lowered_map = {}
        has_mixed_case = False
        for u in unique_vals:
            low = u.strip().lower()
            if low in lowered_map and lowered_map[low] != u:
                has_mixed_case = True
                break
            lowered_map[low] = u

        if ws_count > 0 or has_mixed_case:
            formatting_issues[col] = {
                "whitespace_count": ws_count,
                "mixed_casing": has_mixed_case,
                "sample_values": [u for u in unique_vals[:4]],
            }

    # 5. Constant / Zero-Variance Columns
    constant_cols = []
    id_candidate_cols = []
    for col in df.columns:
        s = df[col].dropna()
        n_unique = int(s.nunique())
        if n_unique <= 1:
            constant_cols.append(col)
        elif n_unique == total_rows and total_rows > 10:
            id_candidate_cols.append(col)

    # 6. Overall Quality Score Calculation
    # Formula: 100 - penalties
    missing_ratio = total_missing_cells / total_cells
    missing_penalty = min(35.0, missing_ratio * 120.0)
    duplicate_penalty = min(25.0, (exact_duplicates / total_rows * 60.0)) if total_rows else 0.0
    
    total_outliers = sum(v["outlier_count"] for v in outliers_by_col.values())
    outlier_penalty = min(20.0, (total_outliers / total_cells * 100.0))
    constant_penalty = min(20.0, len(constant_cols) * 8.0)

    quality_score = max(5.0, round(100.0 - (missing_penalty + duplicate_penalty + outlier_penalty + constant_penalty), 1))

    # 7. Actionable Cleaning Recommendations
    recommendations = []
    rec_counter = 1

    # Exact duplicates recommendation
    if exact_duplicates > 0:
        recommendations.append({
            "id": f"rec_{rec_counter}",
            "issue_type": "duplicates",
            "column": None,
            "title": f"Remove {exact_duplicates} Exact Duplicate Rows",
            "severity": "high" if duplicate_pct > 5 else "medium",
            "affected_count": exact_duplicates,
            "affected_percent": duplicate_pct,
            "example_values": [],
            "why_it_matters": "Identical rows duplicate observations, artificially skew statistics, and inflate business aggregates.",
            "recommended_action": "remove_exact",
            "available_alternatives": [
                {"strategy": "remove_exact", "label": "Remove Exact Duplicates", "description": "Deletes duplicate rows keeping the first occurrence"},
                {"strategy": "keep", "label": "Keep Duplicates", "description": "Preserve all records without alteration"},
            ],
            "expected_effect": f"Deletes {exact_duplicates} duplicate row(s); preserves one unique record per duplicate set.",
            "safe_for_auto": True,
            "config": {},
        })
        rec_counter += 1

    # Missing value recommendations
    for col, m_info in missing_by_col.items():
        is_num = m_info["inferred_type"] == "numeric"
        skewed = False
        default_strat = "median" if is_num else "mode"
        if is_num and col in df.columns:
            s_clean = df[col].dropna()
            if len(s_clean) > 2 and s_clean.std() > 0:
                skew = abs(float(s_clean.skew()))
                if skew > 0.8:
                    skewed = True
                    default_strat = "median"
                else:
                    default_strat = "mean"

        alternatives = []
        if is_num:
            alternatives = [
                {"strategy": "median", "label": "Median Imputation", "description": "Robust against outliers and skewed values (Recommended)" if skewed else "Fills with median value"},
                {"strategy": "mean", "label": "Mean Imputation", "description": "Standard average replacement for symmetric numerical data"},
                {"strategy": "constant", "label": "Custom Constant", "description": "Replace missing values with a user-specified number (e.g. 0)"},
                {"strategy": "ffill", "label": "Forward Fill", "description": "Propagates previous valid value (best for time-ordered data)"},
                {"strategy": "drop_rows", "label": "Drop Affected Rows", "description": f"Removes {m_info['count']} rows containing missing values in this column"},
                {"strategy": "keep", "label": "Keep Missing", "description": "Do not modify missing values"},
            ]
        else:
            default_strat = "unknown" if m_info["percent"] > 10 else "mode"
            alternatives = [
                {"strategy": "unknown", "label": "Replace with 'Unknown'", "description": "Clear, explicit categorical placeholder without inventing categories"},
                {"strategy": "mode", "label": "Mode Imputation (Most Frequent)", "description": "Replaces missing values with the most common category"},
                {"strategy": "constant", "label": "Custom Category", "description": "Specify a custom string placeholder"},
                {"strategy": "drop_rows", "label": "Drop Affected Rows", "description": f"Removes {m_info['count']} rows"},
                {"strategy": "keep", "label": "Keep Missing", "description": "Do not modify missing values"},
            ]

        sample_vals = [to_python(v) for v in df[col].dropna().head(3).tolist()]
        recommendations.append({
            "id": f"rec_{rec_counter}",
            "issue_type": "missing_values",
            "column": col,
            "title": f"Handle Missing Values in '{col}' ({m_info['count']} rows, {m_info['percent']}%)",
            "severity": m_info["severity"],
            "affected_count": m_info["count"],
            "affected_percent": m_info["percent"],
            "example_values": sample_vals,
            "why_it_matters": f"Missing values in '{col}' can distort aggregate summaries, break downstream machine learning models, or exclude valuable rows from charts.",
            "recommended_action": default_strat,
            "available_alternatives": alternatives,
            "expected_effect": f"Fills {m_info['count']} missing cell(s) in '{col}' using {default_strat.upper()}.",
            "safe_for_auto": default_strat in ["median", "mean", "mode", "unknown"],
            "config": {"column": col, "strategy": default_strat},
        })
        rec_counter += 1

    # Outlier recommendations
    for col, o_info in outliers_by_col.items():
        recommendations.append({
            "id": f"rec_{rec_counter}",
            "issue_type": "outliers",
            "column": col,
            "title": f"Handle {o_info['outlier_count']} Outliers in '{col}' ({o_info['percent']}%)",
            "severity": o_info["severity"],
            "affected_count": o_info["outlier_count"],
            "affected_percent": o_info["percent"],
            "example_values": o_info["sample_values"],
            "why_it_matters": f"Values outside [{o_info['lower_bound']}, {o_info['upper_bound']}] may represent extreme transaction amounts or data anomalies that heavily distort mean calculations.",
            "recommended_action": "winsorize",
            "available_alternatives": [
                {"strategy": "winsorize", "label": "Cap / Winsorize to Bounds", "description": f"Clips extremes to lower ({o_info['lower_bound']}) and upper ({o_info['upper_bound']}) bounds without losing rows (Recommended)"},
                {"strategy": "flag", "label": "Flag as Outliers (Add Indicator Column)", "description": f"Creates a boolean 'is_outlier_{col}' column preserving all raw numbers"},
                {"strategy": "drop_rows", "label": "Drop Outlier Rows", "description": f"Removes {o_info['outlier_count']} rows containing extreme values"},
                {"strategy": "keep", "label": "Keep Outliers (Skip)", "description": "Retains all extreme numbers unchanged"},
            ],
            "expected_effect": f"Caps values below {o_info['lower_bound']} and above {o_info['upper_bound']} to statistical bounds, preserving row count.",
            "safe_for_auto": True,
            "config": {"column": col, "strategy": "winsorize", "lower": o_info["lower_bound"], "upper": o_info["upper_bound"]},
        })
        rec_counter += 1

    # Text formatting recommendations
    for col, f_info in formatting_issues.items():
        if f_info["whitespace_count"] > 0:
            recommendations.append({
                "id": f"rec_{rec_counter}",
                "issue_type": "formatting",
                "column": col,
                "title": f"Trim Whitespace in '{col}' ({f_info['whitespace_count']} cells)",
                "severity": "low",
                "affected_count": f_info["whitespace_count"],
                "affected_percent": round(f_info["whitespace_count"] / total_rows * 100, 2) if total_rows else 0.0,
                "example_values": f_info["sample_values"],
                "why_it_matters": "Leading or trailing whitespace creates duplicate categories in groupby operations (e.g. ' London' vs 'London').",
                "recommended_action": "strip_whitespace",
                "available_alternatives": [
                    {"strategy": "strip_whitespace", "label": "Strip Whitespace", "description": "Removes leading and trailing spaces from all values"},
                    {"strategy": "lowercase", "label": "Strip & Lowercase", "description": "Strips spaces and converts to standard lowercase"},
                    {"strategy": "titlecase", "label": "Strip & Title Case", "description": "Strips spaces and formats each word with capital first letter"},
                ],
                "expected_effect": f"Trims invisible spaces from {f_info['whitespace_count']} text value(s) in '{col}'.",
                "safe_for_auto": True,
                "config": {"column": col, "strategy": "strip_whitespace"},
            })
            rec_counter += 1

    return {
        "dataset_shape": {"rows": total_rows, "columns": total_cols},
        "quality_score": quality_score,
        "score_breakdown": {
            "initial_score": 100.0,
            "missing_penalty": round(missing_penalty, 1),
            "duplicate_penalty": round(duplicate_penalty, 1),
            "outlier_penalty": round(outlier_penalty, 1),
            "constant_penalty": round(constant_penalty, 1),
        },
        "summary": {
            "total_missing_cells": total_missing_cells,
            "missing_cells_pct": round(missing_ratio * 100, 2),
            "columns_with_missing": len(missing_by_col),
            "duplicate_rows": exact_duplicates,
            "duplicate_pct": duplicate_pct,
            "columns_with_outliers": len(outliers_by_col),
            "constant_columns": constant_cols,
            "id_candidate_columns": id_candidate_cols,
        },
        "missing_by_column": missing_by_col,
        "outliers_by_column": outliers_by_col,
        "formatting_issues": formatting_issues,
        "recommendations": recommendations,
    }
