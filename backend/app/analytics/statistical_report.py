"""Comprehensive Pandas & NumPy Statistical Analysis Engine for Analyticx AI.

Calculates pure deterministic statistical summaries across:
- Dataset Overview & Schema
- Numerical Descriptive Statistics (Moments, Percentiles, Spread, Kurtosis)
- Categorical Frequencies, Distribution & Cardinality
- Missing-Value Analysis & Patterns
- Duplicate & Quality Assessment
- Outlier Analysis (IQR Fences & Z-Scores)
- Correlation & Associations (Pearson & Spearman)
- Segment Group-By Aggregations
- Time-Series Regularity & Chronological Diagnostics
"""
from datetime import datetime
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from app.analytics.data_understanding import understand_dataset
from app.analytics.profiling import infer_column_type, to_python


def format_bytes(num_bytes: int) -> str:
    """Formats bytes to human-readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def compute_statistical_report(df: pd.DataFrame, dataset_name: str = "Dataset") -> Dict[str, Any]:
    """Generates a complete, verifiable statistical report from a pandas DataFrame."""
    understanding = understand_dataset(df, dataset_name=dataset_name, sanitize=True)
    df = understanding["normalized_df"]
    profile = understanding["profile"]

    total_rows = int(profile["row_count"])
    total_cols = int(profile["column_count"])
    total_cells = total_rows * total_cols
    memory_bytes = int(profile["memory_bytes"])

    numeric_cols = [c for c in profile["numerical_columns"] if c in df.columns]
    datetime_cols = [c for c in profile["datetime_columns"] if c in df.columns]
    categorical_cols = [c for c in profile["categorical_columns"] + profile["boolean_columns"] if c in df.columns]

    # 1. Dataset Overview & Schema
    schema_entries = []
    cols_with_missing_count = 0
    total_missing_cells = 0

    for col in df.columns:
        s = df[col]
        null_count = int(s.isna().sum())
        total_missing_cells += null_count
        if null_count > 0:
            cols_with_missing_count += 1
        null_pct = round((null_count / total_rows * 100), 2) if total_rows else 0.0
        unique_count = int(s.nunique(dropna=True))
        inferred = "numeric" if col in numeric_cols else ("datetime" if col in datetime_cols else "categorical")
        sample_vals = [to_python(v) for v in s.dropna().head(3).tolist()]

        schema_entries.append({
            "column": col,
            "dtype": str(s.dtype),
            "inferred_type": inferred,
            "non_null_count": total_rows - null_count,
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": unique_count,
            "sample_values": sample_vals,
        })

    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / total_rows * 100), 2) if total_rows else 0.0
    complete_rows = int((~df.isna().any(axis=1)).sum())
    complete_rows_pct = round((complete_rows / total_rows * 100), 2) if total_rows else 0.0

    overview = {
        "dataset_name": dataset_name,
        "row_count": total_rows,
        "column_count": total_cols,
        "total_cells": total_cells,
        "memory_bytes": memory_bytes,
        "memory_formatted": format_bytes(memory_bytes),
        "numeric_columns_count": len(numeric_cols),
        "categorical_columns_count": len(categorical_cols),
        "datetime_columns_count": len(datetime_cols),
        "columns_with_missing_count": cols_with_missing_count,
        "duplicate_rows_count": duplicate_rows,
        "duplicate_rows_pct": duplicate_pct,
        "complete_rows_count": complete_rows,
        "complete_rows_pct": complete_rows_pct,
        "generated_at": datetime.utcnow().isoformat(),
        "schema": schema_entries,
    }

    # 2. Numerical Descriptive Statistics
    numeric_stats: Dict[str, Any] = {}
    outlier_stats: Dict[str, Any] = {}

    for col in numeric_cols:
        s = df[col].dropna()
        n = len(s)
        if n == 0:
            continue

        c_mean = float(s.mean())
        c_median = float(s.median())
        c_std = float(s.std(ddof=1)) if n > 1 else 0.0
        c_var = float(s.var(ddof=1)) if n > 1 else 0.0
        c_min = float(s.min())
        c_max = float(s.max())
        c_sum = float(s.sum())
        c_range = c_max - c_min

        # Mode calculation
        mode_series = s.mode()
        c_mode = float(mode_series.iloc[0]) if len(mode_series) > 0 else None

        # Percentiles
        q1 = float(s.quantile(0.25))
        q2 = c_median
        q3 = float(s.quantile(0.75))
        iqr = q3 - q1
        p5 = float(s.quantile(0.05))
        p10 = float(s.quantile(0.10))
        p90 = float(s.quantile(0.90))
        p95 = float(s.quantile(0.95))

        # Skewness & Kurtosis
        c_skew = round(float(s.skew()), 3) if n > 2 and c_std > 0 else 0.0
        c_kurt = round(float(s.kurtosis()), 3) if n > 3 and c_std > 0 else 0.0

        # Coefficient of variation
        cv = round((c_std / abs(c_mean) * 100), 2) if c_mean != 0 else None

        # Counts
        zeros = int((s == 0).sum())
        positives = int((s > 0).sum())
        negatives = int((s < 0).sum())
        null_count = int(df[col].isna().sum())
        null_pct = round((null_count / total_rows * 100), 2) if total_rows else 0.0
        inf_count = int(np.isinf(s).sum())

        numeric_stats[col] = {
            "count": n,
            "mean": round(c_mean, 4),
            "median": round(c_median, 4),
            "mode": round(c_mode, 4) if c_mode is not None else None,
            "min": round(c_min, 4),
            "max": round(c_max, 4),
            "range": round(c_range, 4),
            "sum": round(c_sum, 4),
            "variance": round(c_var, 4),
            "std": round(c_std, 4),
            "q1": round(q1, 4),
            "q2": round(q2, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "p5": round(p5, 4),
            "p10": round(p10, 4),
            "p90": round(p90, 4),
            "p95": round(p95, 4),
            "skewness": c_skew,
            "kurtosis": c_kurt,
            "cv_pct": cv,
            "zeros_count": zeros,
            "positive_count": positives,
            "negative_count": negatives,
            "null_count": null_count,
            "null_pct": null_pct,
            "infinite_count": inf_count,
        }

        # Outlier Fences (IQR and Z-Score)
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        iqr_outliers = int(((s < lower_fence) | (s > upper_fence)).sum())
        iqr_outliers_pct = round((iqr_outliers / n * 100), 2) if n else 0.0

        z_outliers = 0
        if c_std > 0:
            z_scores = np.abs((s - c_mean) / c_std)
            z_outliers = int((z_scores > 3.0).sum())
        z_outliers_pct = round((z_outliers / n * 100), 2) if n else 0.0

        outlier_stats[col] = {
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_fence": round(lower_fence, 4),
            "upper_fence": round(upper_fence, 4),
            "iqr_outlier_count": iqr_outliers,
            "iqr_outlier_pct": iqr_outliers_pct,
            "zscore_outlier_count": z_outliers,
            "zscore_outlier_pct": z_outliers_pct,
        }

    # 3. Categorical Statistics
    categorical_stats: Dict[str, Any] = {}
    for col in categorical_cols:
        s = df[col].dropna().astype(str)
        n = len(s)
        if n == 0:
            continue
        unique_cnt = int(s.nunique())
        null_cnt = int(df[col].isna().sum())
        null_pct = round((null_cnt / total_rows * 100), 2) if total_rows else 0.0

        val_counts = s.value_counts()
        top_cats = []
        cumulative = 0.0
        for cat_name, cnt in val_counts.head(10).items():
            pct = round(float(cnt / n * 100), 2)
            cumulative = round(cumulative + pct, 2)
            top_cats.append({
                "category": str(cat_name),
                "count": int(cnt),
                "pct": pct,
                "cumulative_pct": min(100.0, cumulative),
            })

        rare_count = int((val_counts < (n * 0.01)).sum())
        cardinality = "Low" if unique_cnt <= 10 else ("Medium" if unique_cnt <= 50 else "High")

        categorical_stats[col] = {
            "non_null_count": n,
            "unique_count": unique_cnt,
            "null_count": null_cnt,
            "null_pct": null_pct,
            "cardinality": cardinality,
            "rare_categories_count": rare_count,
            "top_categories": top_cats,
        }

    # 4. Missing-Value Analysis
    missing_cols_detail = []
    high_missingness_warnings = []
    for entry in schema_entries:
        if entry["null_count"] > 0:
            sev = "Critical" if entry["null_pct"] > 40 else ("Moderate" if entry["null_pct"] > 10 else "Low")
            missing_cols_detail.append({
                "column": entry["column"],
                "missing_count": entry["null_count"],
                "missing_pct": entry["null_pct"],
                "severity": sev,
            })
            if entry["null_pct"] > 20:
                high_missingness_warnings.append(
                    f"Column '{entry['column']}' exhibits elevated missingness ({entry['null_pct']}%). Imputation recommended."
                )

    missing_analysis = {
        "total_cells": total_cells,
        "total_missing_cells": total_missing_cells,
        "overall_missing_pct": round((total_missing_cells / total_cells * 100), 2) if total_cells else 0.0,
        "complete_rows_count": complete_rows,
        "complete_rows_pct": complete_rows_pct,
        "rows_with_missing_count": total_rows - complete_rows,
        "columns_no_missing": [e["column"] for e in schema_entries if e["null_count"] == 0],
        "columns_with_missing": missing_cols_detail,
        "warnings": high_missingness_warnings,
    }

    # 5. Data Quality Score & Deductions
    single_val_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    missing_deduction = min(30.0, round((total_missing_cells / max(1, total_cells)) * 100, 1))
    dup_deduction = min(25.0, round((duplicate_rows / max(1, total_rows)) * 100, 1))
    zero_var_deduction = len(single_val_cols) * 5.0
    quality_score = max(10.0, round(100.0 - missing_deduction - dup_deduction - zero_var_deduction, 1))

    quality_analysis = {
        "quality_score": quality_score,
        "single_value_columns": single_val_cols,
        "duplicate_rows": duplicate_rows,
        "duplicate_pct": duplicate_pct,
        "deductions": {
            "missing_cells_penalty": missing_deduction,
            "duplicate_rows_penalty": dup_deduction,
            "single_value_columns_penalty": zero_var_deduction,
        },
    }

    # 6. Correlations (Pearson & Spearman)
    correlations_pearson: Dict[str, Dict[str, float]] = {}
    correlations_spearman: Dict[str, Dict[str, float]] = {}
    notable_correlations: List[Dict[str, Any]] = []

    if len(numeric_cols) >= 2:
        num_sub = df[numeric_cols].dropna()
        if len(num_sub) >= 3:
            p_corr = num_sub.corr(method="pearson").round(4)
            s_corr = num_sub.corr(method="spearman").round(4)

            for c in numeric_cols:
                correlations_pearson[c] = {k: float(v) for k, v in p_corr[c].items()}
                correlations_spearman[c] = {k: float(v) for k, v in s_corr[c].items()}

            # Upper triangle notable pairs
            for i in range(len(numeric_cols)):
                for j in range(i + 1, len(numeric_cols)):
                    c1, c2 = numeric_cols[i], numeric_cols[j]
                    val_p = float(p_corr.loc[c1, c2])
                    val_s = float(s_corr.loc[c1, c2])
                    if not math.isnan(val_p) and abs(val_p) >= 0.35:
                        strength = "Very Strong" if abs(val_p) >= 0.7 else ("Moderate" if abs(val_p) >= 0.5 else "Mild")
                        direction = "Positive" if val_p > 0 else "Negative"
                        notable_correlations.append({
                            "col1": c1,
                            "col2": c2,
                            "pearson": round(val_p, 4),
                            "spearman": round(val_s, 4),
                            "strength": strength,
                            "direction": direction,
                            "sample_size": len(num_sub),
                        })

    # 7. Distribution Histograms
    distributions: Dict[str, Any] = {}
    for col in numeric_cols[:8]:
        s = df[col].dropna()
        if len(s) >= 4 and s.nunique() > 1:
            counts, bins = np.histogram(s, bins=min(10, s.nunique()))
            distributions[col] = {
                "bins": [round(float(b), 2) for b in bins.tolist()],
                "counts": [int(c) for c in counts.tolist()],
            }

    # 8. Segment Group-By Breakdown (if both categorical and numeric exist)
    segment_analysis: Optional[Dict[str, Any]] = None
    if categorical_cols and numeric_cols:
        # Pick best group column: cardinality between 2 and 12
        candidate_cats = [c for c in categorical_cols if 2 <= df[c].nunique(dropna=True) <= 12]
        group_col = candidate_cats[0] if candidate_cats else categorical_cols[0]
        metric_col = numeric_cols[0]

        grp = df.groupby(group_col)[metric_col].agg(["count", "sum", "mean", "std", "min", "median", "max"]).reset_index()
        rows = []
        for _, r in grp.iterrows():
            rows.append({
                "group": str(r[group_col]),
                "count": int(r["count"]),
                "sum": round(float(r["sum"]), 2) if not math.isnan(r["sum"]) else 0.0,
                "mean": round(float(r["mean"]), 2) if not math.isnan(r["mean"]) else 0.0,
                "std": round(float(r["std"]), 2) if not math.isnan(r["std"]) else 0.0,
                "min": round(float(r["min"]), 2) if not math.isnan(r["min"]) else 0.0,
                "median": round(float(r["median"]), 2) if not math.isnan(r["median"]) else 0.0,
                "max": round(float(r["max"]), 2) if not math.isnan(r["max"]) else 0.0,
            })

        segment_analysis = {
            "group_column": group_col,
            "metric_column": metric_col,
            "segments": rows,
        }

    # 9. Time-Series Diagnostics (if datetime column exists)
    time_series_diag: Optional[Dict[str, Any]] = None
    if datetime_cols:
        dcol = datetime_cols[0]
        parsed_dates = pd.to_datetime(df[dcol], errors="coerce").dropna()
        if len(parsed_dates) >= 4:
            min_d = parsed_dates.min()
            max_d = parsed_dates.max()
            span_days = int((max_d - min_d).days)
            time_series_diag = {
                "date_column": dcol,
                "min_date": str(min_d.date()),
                "max_date": str(max_d.date()),
                "span_days": span_days,
                "observation_count": len(parsed_dates),
                "unique_dates": int(parsed_dates.nunique()),
            }

    return {
        "overview": overview,
        "numeric_stats": numeric_stats,
        "outlier_stats": outlier_stats,
        "categorical_stats": categorical_stats,
        "missing_analysis": missing_analysis,
        "quality_analysis": quality_analysis,
        "correlations_pearson": correlations_pearson,
        "correlations_spearman": correlations_spearman,
        "notable_correlations": notable_correlations,
        "distributions": distributions,
        "segment_analysis": segment_analysis,
        "time_series_diagnostics": time_series_diag,
    }
