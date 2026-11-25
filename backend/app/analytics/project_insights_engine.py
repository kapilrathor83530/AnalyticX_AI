"""Universal Data Insight Engine for Analyticx AI.

Generates domain-independent, statistically grounded, evidence-backed insights across
any valid uploaded dataset by combining:
- Universal Data Understanding (semantic & type normalization, ID/constant protection)
- Deterministic Statistical Analysis (numerical, categorical, temporal, correlation,
  Cramér's V, ANOVA, IQR/MAD/Z-score/Isolation Forest anomalies)
- Chart-Insight Linkage (verified chart_spec compatible with Visualization Engine)
- Deduplication, Ranking, Insufficient-Evidence Handling, and Version Fingerprinting
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.data_understanding import understand_dataset
from app.analytics.profiling import to_python
from app.analytics.statistics import (
    analyze_categorical_column,
    analyze_datetime_column,
    analyze_numerical_column,
    calculate_correlation,
    compare_groups,
    detect_outliers,
)
from app.models.dataset import Dataset
from app.models.project_insight import ProjectAnalysisRun, ProjectInsight

INSIGHT_CATEGORIES = [
    ("overview", "Dataset Overview"),
    ("quality", "Data Quality"),
    ("statistical", "Statistical Insights"),
    ("distribution", "Distribution Insights"),
    ("trend", "Trend Insights"),
    ("correlation", "Correlation Insights"),
    ("categorical", "Categorical Insights"),
    ("comparative", "Comparative Insights"),
    ("anomaly", "Anomaly Insights"),
    ("performance", "Domain & Performance Insights"),
    ("predictive", "Predictive Insights"),
    ("opportunity", "Recommendations"),
]


def compute_dataset_fingerprint(dataset: Dataset, df: pd.DataFrame) -> str:
    """Computes a deterministic SHA256 fingerprint reflecting dataset version, schema, and content."""
    mtime_ns = 0
    stored_path = getattr(dataset, "stored_path", None)
    if stored_path:
        try:
            p = Path(stored_path)
            if p.exists():
                mtime_ns = p.stat().st_mtime_ns
        except OSError:
            pass
    sample_hash = ""
    if not df.empty:
        try:
            head_str = df.head(5).to_csv(index=False)
            tail_str = df.tail(5).to_csv(index=False)
            sample_hash = hashlib.md5(f"{head_str}|{tail_str}".encode("utf-8", errors="ignore")).hexdigest()[:12]
        except Exception:
            sample_hash = ""
    raw = (
        f"{getattr(dataset, 'id', 0)}_{getattr(dataset, 'version', 1)}_"
        f"{len(df)}_{len(df.columns)}_{'_'.join(sorted(str(c) for c in df.columns))}_"
        f"{getattr(dataset, 'size_bytes', 0)}_{mtime_ns}_{sample_hash}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def calculate_transparent_quality_score(df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
    """
    Transparent scoring methodology:
    - Base: 100 points
    - Missingness deduction: up to -35 points (proportion of null cells)
    - Duplicate row deduction: up to -25 points (proportion of exact duplicates)
    - Outlier deduction: up to -20 points (proportion of extreme IQR outliers on numeric metrics)
    - Single-value column deduction: up to -10 points (columns with 0 variance)
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    if total_rows == 0 or total_cols == 0:
        return 0.0, {"reason": "Empty dataset"}

    total_cells = total_rows * total_cols
    total_nulls = int(df.isna().sum().sum())
    null_ratio = total_nulls / total_cells
    missing_deduction = round(min(35.0, null_ratio * 100 * 0.7), 2)

    total_duplicates = int(df.duplicated().sum())
    dup_ratio = total_duplicates / total_rows
    dup_deduction = round(min(25.0, dup_ratio * 100 * 0.8), 2)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outlier_count = 0
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) >= 4:
            q1 = float(s.quantile(0.25))
            q3 = float(s.quantile(0.75))
            iqr = q3 - q1
            if iqr > 0:
                low = q1 - 1.5 * iqr
                high = q3 + 1.5 * iqr
                outlier_count += int(((s < low) | (s > high)).sum())

    total_num_cells = total_rows * max(1, len(numeric_cols))
    outlier_ratio = outlier_count / total_num_cells
    outlier_deduction = round(min(20.0, outlier_ratio * 100 * 0.6), 2)

    single_val_cols = [str(c) for c in df.columns if df[c].nunique(dropna=False) <= 1]
    single_val_deduction = round(min(10.0, len(single_val_cols) * 3.0), 2)

    score = max(0.0, min(100.0, 100.0 - (missing_deduction + dup_deduction + outlier_deduction + single_val_deduction)))
    methodology = {
        "base_score": 100.0,
        "missing_deduction": missing_deduction,
        "duplicate_deduction": dup_deduction,
        "outlier_deduction": outlier_deduction,
        "zero_variance_deduction": single_val_deduction,
        "null_cells": total_nulls,
        "duplicate_rows": total_duplicates,
        "outlier_points": outlier_count,
        "single_value_columns": single_val_cols,
    }
    return round(score, 1), methodology


def build_automated_eda(
    df: pd.DataFrame,
    dataset_name: str,
    understanding: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates comprehensive Exploratory Data Analysis using Universal Data Understanding."""
    if understanding is None:
        understanding = understand_dataset(df, dataset_name=dataset_name, sanitize=True)

    norm_df = understanding["normalized_df"]
    profile = understanding["profile"]
    total_rows = int(profile["row_count"])
    total_cols = int(profile["column_count"])

    num_cols = profile.get("numerical_columns", [])
    cat_cols = [c for c in profile.get("categorical_columns", []) + profile.get("boolean_columns", []) if c not in profile.get("identifier_columns", [])]
    dt_cols = profile.get("datetime_columns", [])

    # 1. Schema & Data Dictionary
    schema = profile.get("columns", [])

    # 2. Descriptive Statistics across ALL eligible numerical columns
    num_stats: Dict[str, Dict[str, Any]] = {}
    for col in num_cols:
        st = analyze_numerical_column(norm_df, col)
        if st.get("count", 0) > 0:
            num_stats[col] = st

    # 3. Numeric Distributions (Histograms)
    distributions: Dict[str, Dict[str, Any]] = {}
    for col in num_cols[:10]:
        s = pd.to_numeric(norm_df[col], errors="coerce").dropna()
        if len(s) >= 4 and s.nunique() > 1:
            counts, bins = np.histogram(s, bins=min(10, int(s.nunique())))
            distributions[col] = {
                "bins": [round(float(b), 4) for b in bins.tolist()],
                "counts": [int(c) for c in counts.tolist()],
            }

    # 4. Categorical Breakdowns & Metrics
    categorical_stats: Dict[str, Dict[str, Any]] = {}
    categorical_breakdowns: Dict[str, List[Dict[str, Any]]] = {}
    for col in cat_cols[:10]:
        c_info = analyze_categorical_column(norm_df, col)
        if not c_info.get("insufficient_data"):
            categorical_stats[col] = c_info
            categorical_breakdowns[col] = c_info["distribution"][:8]

    # 5. Correlation Matrix (Pearson + Spearman + Cramér's V + Multicollinearity)
    corr_res = calculate_correlation(norm_df, numeric_columns=num_cols, categorical_columns=cat_cols)
    correlations = corr_res.get("pearson_matrix", {})
    notable_correlations = corr_res.get("notable_correlations", [])
    categorical_associations = corr_res.get("categorical_associations", [])
    multicollinear_pairs = corr_res.get("multicollinear_pairs", [])

    # 6. Temporal Trends (properly parsed & chronologically ordered)
    datetime_diagnostics: List[Dict[str, Any]] = []
    time_trend = None
    for d_col in dt_cols[:2]:
        dt_info = analyze_datetime_column(norm_df, d_col, numeric_columns=num_cols)
        if not dt_info.get("insufficient_data"):
            datetime_diagnostics.append(dt_info)
            if time_trend is None and dt_info.get("metric_trends"):
                t0 = dt_info["metric_trends"][0]
                time_trend = {
                    "date_column": d_col,
                    "target_column": t0["metric_column"],
                    "granularity": t0["granularity"],
                    "labels": t0["labels"],
                    "values": t0["values"],
                    "percent_change": t0["percent_change"],
                    "net_delta": t0["net_delta"],
                    "trend_spearman_rho": t0["trend_spearman_rho"],
                    "peak_period": t0["peak_period"],
                    "peak_value": t0["peak_value"],
                    "trough_period": t0["trough_period"],
                    "trough_value": t0["trough_value"],
                }

    # 7. Outlier & Anomaly Scan
    outlier_summary = detect_outliers(norm_df, numeric_columns=num_cols)

    score, quality_meta = calculate_transparent_quality_score(norm_df)

    return {
        "dataset_name": dataset_name,
        "row_count": total_rows,
        "column_count": total_cols,
        "total_cells": total_rows * total_cols,
        "quality_score": score,
        "quality_methodology": quality_meta,
        "validation": understanding.get("validation", {}),
        "numerical_columns": num_cols,
        "categorical_columns": cat_cols,
        "datetime_columns": dt_cols,
        "identifier_columns": profile.get("identifier_columns", []),
        "constant_columns": profile.get("constant_columns", []),
        "schema": schema,
        "numeric_stats": num_stats,
        "distributions": distributions,
        "categorical_stats": categorical_stats,
        "categorical_breakdowns": categorical_breakdowns,
        "correlations": correlations,
        "spearman_correlations": corr_res.get("spearman_matrix", {}),
        "notable_correlations": notable_correlations,
        "categorical_associations": categorical_associations,
        "multicollinear_pairs": multicollinear_pairs,
        "time_trend": time_trend,
        "datetime_diagnostics": datetime_diagnostics,
        "outlier_summary": outlier_summary,
    }


def _make_insight(
    *,
    category: str,
    priority: str,
    title: str,
    finding: str,
    explanation: str,
    supporting_metrics: Dict[str, Any],
    evidence_data: Dict[str, Any],
    methodology: str,
    confidence_score: float,
    confidence_justification: str,
    recommended_action: str,
    action_type: Optional[str],
    action_payload: Optional[Dict[str, Any]],
    source_columns: List[str],
    rank_score: float,
    limitations: str = "Derived from observed records in the active dataset version.",
    chart_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "category": category,
        "priority": priority,
        "title": title,
        "finding": finding,
        "explanation": explanation,
        "practical_interpretation": explanation,
        "limitations": limitations,
        "supporting_metrics": supporting_metrics,
        "evidence_data": evidence_data,
        "chart_spec": chart_spec,
        "methodology": methodology,
        "confidence_score": round(confidence_score, 3),
        "confidence_justification": confidence_justification,
        "recommended_action": recommended_action,
        "action_type": action_type,
        "action_payload": action_payload,
        "source_columns": source_columns,
        "rank_score": round(rank_score, 2),
        "status": "new",
    }


def _deduplicate_and_rank(insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_sigs = set()
    unique: List[Dict[str, Any]] = []
    for item in sorted(insights, key=lambda x: x.get("rank_score", 0.0), reverse=True):
        sig = (item["category"], tuple(sorted(item.get("source_columns") or [])), item["title"][:48].lower())
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        unique.append(item)
    return unique


def discover_business_insights(
    df: pd.DataFrame,
    dataset: Dataset,
    eda: Dict[str, Any],
    fingerprint: str,
) -> List[Dict[str, Any]]:
    """
    Discovers domain-independent, statistically grounded insights across ALL 12 analytical categories.
    Every numerical statement comes directly from deterministic computations on the active dataset.
    """
    # Use normalized working df so string currency / percentages / dates work seamlessly
    understanding = understand_dataset(df, dataset_name=getattr(dataset, "name", "Dataset"), sanitize=True)
    work_df = understanding["normalized_df"]
    profile = understanding["profile"]

    total_rows = int(profile["row_count"])
    total_cols = int(profile["column_count"])
    if total_rows == 0 or total_cols == 0:
        return []

    insights: List[Dict[str, Any]] = []
    num_cols = profile.get("numerical_columns", [])
    cat_cols = [c for c in profile.get("categorical_columns", []) + profile.get("boolean_columns", []) if c not in profile.get("identifier_columns", [])]
    dt_cols = profile.get("datetime_columns", [])
    id_cols = profile.get("identifier_columns", [])
    const_cols = profile.get("constant_columns", [])

    # 1. Dataset Overview Insight
    num_count = len(num_cols)
    cat_count = len(cat_cols)
    dt_count = len(dt_cols)
    insights.append(_make_insight(
        category="overview",
        priority="low",
        title=f"Dataset Profile: {total_rows:,} Records × {total_cols} Attributes",
        finding=f"Evaluated {total_rows:,} rows and {total_cols} columns ({num_count} numeric measures, {cat_count} categorical dimensions, {dt_count} temporal fields).",
        explanation=(
            f"The dataset contains {num_count} analysis-eligible quantitative column(s), {cat_count} discrete grouping dimension(s), "
            f"{dt_count} date/time axis field(s), and excluded {len(id_cols)} identifier(s) and {len(const_cols)} constant column(s) from metric distortion."
        ),
        supporting_metrics={
            "row_count": total_rows,
            "column_count": total_cols,
            "numeric_columns": num_cols,
            "categorical_columns": cat_cols,
            "datetime_columns": dt_cols,
            "excluded_identifiers": id_cols,
            "constant_columns": const_cols,
            "calculation_formula": "Schema classification & semantic type scan",
        },
        evidence_data={
            "type": "table",
            "rows": [
                {"Attribute Type": "Numerical Measures", "Count": num_count, "Columns": ", ".join(num_cols[:5]) or "None"},
                {"Attribute Type": "Categorical Dimensions", "Count": cat_count, "Columns": ", ".join(cat_cols[:5]) or "None"},
                {"Attribute Type": "Date / Time Columns", "Count": dt_count, "Columns": ", ".join(dt_cols[:3]) or "None"},
                {"Attribute Type": "Excluded IDs / Constants", "Count": len(id_cols) + len(const_cols), "Columns": ", ".join((id_cols + const_cols)[:5]) or "None"},
            ],
        },
        methodology="Universal Schema & Semantic Type Classification Engine.",
        confidence_score=0.99,
        confidence_justification=f"Complete deterministic inspection of {total_rows:,} rows.",
        recommended_action="Inspect individual column distributions and relationships in Automated EDA.",
        action_type=None,
        action_payload=None,
        source_columns=list(work_df.columns)[:8],
        rank_score=40.0,
    ))

    # 2. Data Quality & Hygiene Warnings
    q_score = eda.get("quality_score", 100.0)
    q_meta = eda.get("quality_methodology", {})
    null_cells = q_meta.get("null_cells", int(work_df.isna().sum().sum()))
    dup_rows = q_meta.get("duplicate_rows", int(work_df.duplicated().sum()))
    val_warnings = understanding.get("validation", {}).get("warnings", [])
    missing_cols_meta = [c for c in profile["columns"] if c["missing_count"] > 0]

    if null_cells > 0 or dup_rows > 0 or const_cols or val_warnings or q_score < 90.0:
        pct_null = round((null_cells / max(1, total_rows * total_cols) * 100), 2)
        worst_missing = sorted(missing_cols_meta, key=lambda x: x["missing_percent"], reverse=True)
        worst_note = (
            f" Highest missingness in '{worst_missing[0]['name']}' ({worst_missing[0]['missing_percent']}%)."
            if worst_missing else ""
        )
        insights.append(_make_insight(
            category="quality",
            priority="high" if (q_score < 75.0 or pct_null >= 5.0 or dup_rows > 0) else "medium",
            title=f"Data Hygiene Audit: Quality Score {q_score}% ({null_cells:,} Missing Cells, {dup_rows:,} Duplicates)",
            finding=f"{null_cells:,} missing cells ({pct_null}% of cells), {dup_rows:,} duplicate rows, and {len(const_cols)} zero-variance column(s).{worst_note}",
            explanation=(
                f"Detected {null_cells:,} missing cells ({pct_null}%) across {len(missing_cols_meta)} column(s) and "
                f"{dup_rows:,} exact duplicate row(s). Leaving missing values or duplicates unresolved can distort averages and segment totals."
            ),
            supporting_metrics={
                "quality_score": q_score,
                "null_cells": null_cells,
                "missing_percentage": pct_null,
                "duplicate_rows": dup_rows,
                "constant_columns": const_cols,
                "validation_warnings": val_warnings,
                "calculation_formula": "100 - (Missing_Deduction + Duplicate_Deduction + Outlier_Deduction + ZeroVar_Deduction)",
            },
            evidence_data={
                "type": "table",
                "rows": [
                    {"Column": c["name"], "Missing Count": c["missing_count"], "Missing %": f"{c['missing_percent']}%"}
                    for c in worst_missing[:6]
                ] or [
                    {"Metric": "Quality Score", "Value": f"{q_score}%"},
                    {"Metric": "Duplicate Records", "Value": str(dup_rows)},
                    {"Metric": "Constant Columns", "Value": ", ".join(const_cols) or "None"},
                ],
            },
            methodology="Full-scan completeness, duplicate-row, constant-column, and schema integrity audit.",
            confidence_score=0.98,
            confidence_justification=f"Deterministic scan of all {total_rows:,} records across {total_cols} columns.",
            recommended_action="Review imputation, deduplication, and formatting recommendations in Data Prep Studio.",
            action_type="remediate_data",
            action_payload={"route": f"/data-prep/{dataset.id}"},
            source_columns=[c["name"] for c in worst_missing] or const_cols,
            rank_score=92.0 if q_score < 80 else 72.0,
        ))

    # 3. Numerical Statistical & Distribution Insights (scan ALL eligible numeric columns)
    num_stats = eda.get("numeric_stats", {})
    for col, st in num_stats.items():
        if st.get("insufficient_data"):
            continue
        n_obs = st["count"]
        mean_v = st["mean"]
        med_v = st["median"]
        std_v = st["std"]
        min_v = st["min"]
        max_v = st["max"]
        skew_v = st.get("skewness") or 0.0
        cv_v = st.get("cv_pct")
        neg_cnt = st.get("negative_count", 0)
        zero_cnt = st.get("zero_count", 0)
        iqr_out = st.get("iqr_outlier_count", 0)

        # Distribution asymmetry / high dispersion insight
        has_skew = abs(skew_v) >= 1.0
        high_cv = cv_v is not None and cv_v >= 60.0
        has_neg = neg_cnt > 0
        gap_pct = st.get("mean_median_gap_pct") or 0.0

        chart_spec = {
            "chart_type": "histogram",
            "title": f"Distribution of {col}",
            "data_mapping": {"x": col},
            "aggregation": "count",
        }
        dist_info = eda.get("distributions", {}).get(col)
        chart_rows = (
            [
                {"Bin": f"{round(dist_info['bins'][i], 2)} - {round(dist_info['bins'][i + 1], 2)}", "Count": dist_info["counts"][i]}
                for i in range(len(dist_info["counts"]))
            ]
            if dist_info else [{"Statistic": "Min", "Value": min_v}, {"Statistic": "Median", "Value": med_v}, {"Statistic": "Mean", "Value": mean_v}, {"Statistic": "Max", "Value": max_v}]
        )

        if has_skew or high_cv or gap_pct >= 20.0:
            skew_dir = "right-skewed (high upper tail)" if skew_v > 0 else "left-skewed (low lower tail)"
            insights.append(_make_insight(
                category="distribution",
                priority="high" if abs(skew_v) >= 2.0 or (cv_v or 0) >= 100 else "medium",
                title=f"Distribution Shape: '{col}' is {skew_dir if has_skew else 'Widely Dispersed'} (Mean={mean_v:,}, Median={med_v:,})",
                finding=f"'{col}' spans [{min_v:,}, {max_v:,}] with Mean {mean_v:,} vs Median {med_v:,} (Skew={skew_v}, CV={cv_v or 'N/A'}%).",
                explanation=(
                    f"Across {n_obs:,} valid observations, '{col}' shows a {gap_pct:.1f}% difference between mean ({mean_v:,}) and median ({med_v:,}) "
                    f"with standard deviation {std_v:,} and IQR {st['iqr']:,}. "
                    + (f"Contains {neg_cnt} negative and {zero_cnt} zero values. " if (neg_cnt or zero_cnt) else "")
                    + "The median and IQR provide a more outlier-resistant typical benchmark than the arithmetic mean."
                ),
                supporting_metrics={
                    "column": col,
                    "count": n_obs,
                    "mean": mean_v,
                    "median": med_v,
                    "std": std_v,
                    "min": min_v,
                    "max": max_v,
                    "q1": st["q1"],
                    "q3": st["q3"],
                    "iqr": st["iqr"],
                    "skewness": skew_v,
                    "cv_pct": cv_v,
                    "zero_count": zero_cnt,
                    "negative_count": neg_cnt,
                    "calculation_formula": f"Mean={mean_v:,}, Median={med_v:,}, Skewness={skew_v}",
                },
                evidence_data={"type": "chart", "chart_type": "histogram", "x_axis": col, "rows": chart_rows},
                chart_spec=chart_spec,
                methodology="Parametric & non-parametric distribution moments (Skewness, IQR, Coefficient of Variation).",
                confidence_score=0.95,
                confidence_justification=f"Computed directly from all {n_obs:,} non-null observations in '{col}'.",
                recommended_action=f"Visualize '{col}' with a Histogram or Box Plot to inspect tail concentration.",
                action_type="create_chart",
                action_payload={"title": f"{col} Distribution", "chart_type": "histogram", "x": col},
                source_columns=[col],
                rank_score=76.0 if has_skew else 64.0,
            ))
        else:
            # Balanced statistical profile insight for numeric measures
            insights.append(_make_insight(
                category="statistical",
                priority="low",
                title=f"Statistical Summary: '{col}' Averages {mean_v:,} (Range {min_v:,} to {max_v:,})",
                finding=f"'{col}' has Mean={mean_v:,}, Median={med_v:,}, Std Dev={std_v:,}, across {n_obs:,} valid values.",
                explanation=(
                    f"Values in '{col}' are relatively balanced around the center (Mean={mean_v:,}, Median={med_v:,}, Q1={st['q1']:,}, Q3={st['q3']:,}). "
                    + (f"Includes {zero_cnt} zero-value and {neg_cnt} negative-value records." if (zero_cnt or neg_cnt) else "")
                ),
                supporting_metrics={
                    "column": col,
                    "count": n_obs,
                    "mean": mean_v,
                    "median": med_v,
                    "std": std_v,
                    "min": min_v,
                    "max": max_v,
                    "iqr": st["iqr"],
                    "calculation_formula": f"Range=[{min_v:,}, {max_v:,}], Mean={mean_v:,}, Std={std_v:,}",
                },
                evidence_data={"type": "chart", "chart_type": "histogram", "x_axis": col, "rows": chart_rows},
                chart_spec=chart_spec,
                methodology="5-number summary & sample standard deviation.",
                confidence_score=0.95,
                confidence_justification=f"Exact statistics over N={n_obs:,} valid observations.",
                recommended_action=f"Inspect distribution of '{col}' or test group differences across categories.",
                action_type="create_chart",
                action_payload={"title": f"{col} Distribution", "chart_type": "histogram", "x": col},
                source_columns=[col],
                rank_score=48.0 + (4.0 if iqr_out > 0 else 0.0) + (3.0 if has_neg else 0.0),
            ))

    # 4. Categorical Dominance, Imbalance, Rare & Hygiene Insights
    cat_stats = eda.get("categorical_stats", {})
    for col, c_info in cat_stats.items():
        if c_info.get("insufficient_data"):
            continue
        dom_cat = c_info["dominant_category"]
        dom_pct = c_info["dominant_pct"]
        dom_cnt = c_info["dominant_count"]
        least_cat = c_info["least_frequent_category"]
        least_cnt = c_info["least_frequent_count"]
        uniq = c_info["unique_count"]
        imb = c_info["imbalance_ratio"]
        incons = c_info.get("inconsistent_labels", [])
        rare_cnt = c_info.get("rare_categories_count", 0)

        chart_type_cat = "donut" if 2 <= uniq <= 7 else "bar"
        cat_rows = c_info.get("distribution", [])[:10]

        if dom_pct >= 45.0 or imb >= 3.0 or incons or rare_cnt >= 2:
            incons_msg = f" Label inconsistency suspected ({incons[0]})." if incons else ""
            rare_msg = f" {rare_cnt} rare category label(s) (<2% share) detected." if rare_cnt else ""
            insights.append(_make_insight(
                category="categorical",
                priority="high" if dom_pct >= 70.0 or bool(incons) else "medium",
                title=f"Category Concentration in '{col}': '{dom_cat}' Accounts for {dom_pct}% of Records",
                finding=f"'{dom_cat}' appears {dom_cnt:,} times ({dom_pct}%), whereas '{least_cat}' appears {least_cnt:,} times (imbalance ratio {imb}x across {uniq} categories).{incons_msg}{rare_msg}",
                explanation=(
                    f"Within categorical dimension '{col}' ({uniq} unique categories), frequency is concentrated in '{dom_cat}' ({dom_pct}% share, normalized entropy={c_info['normalized_entropy']})."
                    f"{incons_msg}{rare_msg} Highly imbalanced categories should be evaluated when training predictive models or calculating unweighted averages."
                ),
                supporting_metrics={
                    "column": col,
                    "unique_count": uniq,
                    "dominant_category": dom_cat,
                    "dominant_count": dom_cnt,
                    "dominant_pct": dom_pct,
                    "least_frequent_category": least_cat,
                    "least_frequent_count": least_cnt,
                    "imbalance_ratio": imb,
                    "rare_categories_count": rare_cnt,
                    "inconsistent_labels": incons,
                    "calculation_formula": f"Share = {dom_cnt} / {c_info['count']} * 100 = {dom_pct}%",
                },
                evidence_data={
                    "type": "chart",
                    "chart_type": chart_type_cat,
                    "x_axis": col,
                    "y_axis": "count",
                    "rows": cat_rows,
                },
                chart_spec={
                    "chart_type": chart_type_cat,
                    "title": f"Record Share by {col}",
                    "data_mapping": {"labels": col, "values": col} if chart_type_cat == "donut" else {"x": col, "y": col},
                    "aggregation": "count",
                },
                methodology="Categorical frequency concentration, Shannon entropy, and label normalization scan.",
                confidence_score=0.96,
                confidence_justification=f"Exact frequency count across {c_info['count']:,} non-null records.",
                recommended_action=f"Standardize labels or create a frequency chart for '{col}'.",
                action_type="create_chart",
                action_payload={"title": f"Count by {col}", "chart_type": chart_type_cat, "x": col, "y": col, "aggregation": "count"},
                source_columns=[col],
                rank_score=74.0 if (dom_pct >= 60 or incons) else 58.0,
            ))

    # 5. Cross-Column Comparative & ANOVA Segment Insights (Domain-Agnostic)
    eligible_comp_cats = [
        c for c in cat_cols
        if 2 <= work_df[c].nunique(dropna=True) <= 20
    ]
    comp_candidates: List[Tuple[float, Dict[str, Any]]] = []
    for cat_c in eligible_comp_cats[:5]:
        for num_c in num_cols[:5]:
            anova = compare_groups(work_df, cat_c, num_c)
            if "error" in anova or not anova.get("group_breakdown"):
                continue
            top_g = anova["top_group"]
            bot_g = anova["bottom_group"]
            if not top_g or not bot_g:
                continue
            eta_sq = anova.get("eta_squared") or 0.0
            sig = anova.get("significant_at_0_05", False)
            p_val = anova.get("p_value")
            top_mean = top_g["mean"] or 0.0
            bot_mean = bot_g["mean"] or 0.0
            top_sum = top_g["sum"] or 0.0
            bot_sum = bot_g["sum"] or 0.0
            share_pct = top_g.get("share_pct")

            ratio_sum = round(top_sum / bot_sum, 2) if bot_sum > 0 and top_sum > 0 else None
            diff_mean = round(top_mean - bot_mean, 2)

            if sig or eta_sq >= 0.15 or (ratio_sum is not None and ratio_sum >= 1.5) or (share_pct and share_pct >= 40.0):
                score_comp = (88.0 if sig else 68.0) + min(10.0, eta_sq * 20.0)
                comp_candidates.append((score_comp, {
                    "cat": cat_c,
                    "num": num_c,
                    "anova": anova,
                    "top_g": top_g,
                    "bot_g": bot_g,
                    "ratio_sum": ratio_sum,
                    "diff_mean": diff_mean,
                    "sig": sig,
                    "p_val": p_val,
                    "eta_sq": eta_sq,
                }))

    comp_candidates.sort(key=lambda x: x[0], reverse=True)
    emitted_perf = False
    emitted_comp = False
    for score_comp, item in comp_candidates[:6]:
        cat_c = item["cat"]
        num_c = item["num"]
        anova = item["anova"]
        top_g = item["top_g"]
        bot_g = item["bot_g"]
        sig = item["sig"]
        p_val = item["p_val"]
        ratio_sum = item["ratio_sum"]

        lead_desc = (
            f"mean={top_g['mean']:,.2f} vs '{bot_g['group']}' mean={bot_g['mean']:,.2f}"
            + (f" ({top_g['share_pct']}% of total '{num_c}', {ratio_sum}x sum disparity)" if ratio_sum and ratio_sum >= 1.4 else "")
        )
        stat_note = (
            f"ANOVA F={anova['f_statistic']:.2f}, p={p_val:.4f} (statistically significant at alpha=0.05, eta²={item['eta_sq']})."
            if sig and isinstance(anova.get("f_statistic"), (int, float)) and isinstance(p_val, (int, float))
            else f"Observed across {anova['groups']} groups (ANOVA p={p_val})."
        )

        is_fin = any(k in num_c.lower() for k in ("sales", "revenue", "profit", "cost", "budget", "spend"))
        if is_fin and not emitted_perf:
            cat_label = "performance"
            emitted_perf = True
        elif not is_fin and not emitted_comp:
            cat_label = "comparative"
            emitted_comp = True
        elif not emitted_comp:
            cat_label = "comparative"
            emitted_comp = True
        else:
            cat_label = "performance" if is_fin else "comparative"

        insights.append(_make_insight(
            category=cat_label,
            priority="high" if (sig and item["eta_sq"] >= 0.25) or (ratio_sum and ratio_sum >= 2.5) else "medium",
            title=f"Group Comparison: '{top_g['group']}' Leads '{num_c}' Across '{cat_c}'",
            finding=f"Grouped by '{cat_c}', '{top_g['group']}' records {lead_desc}. {stat_note}",
            explanation=(
                f"Comparing '{num_c}' across '{cat_c}' ({anova['groups']} groups, N={anova['valid_observations']:,}) shows that '{top_g['group']}' "
                f"achieves an average of {top_g['mean']:,.2f} (total {top_g['sum']:,.2f}) while '{bot_g['group']}' averages {bot_g['mean']:,.2f} (total {bot_g['sum']:,.2f}). "
                f"{stat_note}"
            ),
            supporting_metrics={
                "dimension": cat_c,
                "metric": num_c,
                "top_segment": top_g["group"],
                "top_mean": top_g["mean"],
                "top_value": top_g["sum"],
                "bottom_segment": bot_g["group"],
                "bottom_mean": bot_g["mean"],
                "bottom_value": bot_g["sum"],
                "multiplier": ratio_sum,
                "share_percent": top_g.get("share_pct"),
                "f_statistic": anova.get("f_statistic"),
                "p_value": p_val,
                "eta_squared": item["eta_sq"],
                "significant": sig,
                "calculation_formula": f"GROUP BY {cat_c}: Mean/Sum({num_c}), ANOVA p={p_val}",
            },
            evidence_data={
                "type": "chart",
                "chart_type": "bar",
                "x_axis": cat_c,
                "y_axis": num_c,
                "rows": [
                    {cat_c: g["group"], f"Mean {num_c}": g["mean"], f"Total {num_c}": g["sum"], "Count": g["count"]}
                    for g in anova["group_breakdown"][:8]
                ],
            },
            chart_spec={
                "chart_type": "bar",
                "title": f"{num_c} by {cat_c}",
                "data_mapping": {"x": cat_c, "y": num_c},
                "aggregation": "mean" if cat_label == "comparative" else "sum",
            },
            methodology=f"Grouped aggregation & One-way ANOVA significance test ({cat_c} -> {num_c}).",
            confidence_score=0.96 if sig else 0.87,
            confidence_justification=f"Evaluated across N={anova['valid_observations']:,} paired records.",
            recommended_action=f"Pin a '{num_c} by {cat_c}' comparison chart or inspect group variance with Box Plot.",
            action_type="create_chart",
            action_payload={"title": f"{num_c} by {cat_c}", "chart_type": "bar", "x": cat_c, "y": num_c, "aggregation": "mean"},
            source_columns=[cat_c, num_c],
            rank_score=score_comp,
            limitations="Group differences demonstrate observational association, not direct causal impact.",
        ))

    # 6. Correlation & Association Insights (Pearson, Spearman, Cramér's V, Multicollinearity)
    for corr in eda.get("notable_correlations", [])[:4]:
        c1 = corr["col1"]
        c2 = corr["col2"]
        pr = corr.get("pearson_r")
        sr = corr.get("spearman_rho")
        n_obs = corr.get("valid_observations", total_rows)
        strength = corr["strength"]
        direction = corr["direction"]
        r_primary = pr if pr is not None else sr
        is_mc = corr.get("multicollinearity_risk", False)

        # Sample up to 60 valid points evenly across dataset for scatter evidence
        pair_df = work_df[[c1, c2]].dropna()
        if len(pair_df) > 60:
            pair_df = pair_df.sample(60, random_state=42)

        insights.append(_make_insight(
            category="correlation",
            priority="high" if abs(r_primary or 0) >= 0.75 else "medium",
            title=f"{strength.capitalize()} {direction.capitalize()} Relationship: '{c1}' & '{c2}' (r = {r_primary:+.2f})",
            finding=f"Pearson r = {pr:+.3f} (p={corr.get('pearson_p_value')}), Spearman ρ = {sr:+.3f} across {n_obs:,} valid pairs.",
            explanation=(
                f"'{c1}' and '{c2}' exhibit a {strength} {direction} association ({corr.get('recommended_method', 'Pearson & Spearman')}) "
                f"explaining ~{round(((pr or 0) ** 2) * 100, 1)}% shared linear variance across N={n_obs:,} observations. "
                + ("High collinearity (|r| >= 0.85) detected; consider feature selection if building regression models. " if is_mc else "")
                + "Important: Statistical correlation establishes co-variation only and does not prove causation."
            ),
            supporting_metrics={
                "col1": c1,
                "col2": c2,
                "pearson_r": pr,
                "pearson_p_value": corr.get("pearson_p_value"),
                "spearman_rho": sr,
                "r_squared": corr.get("r_squared"),
                "valid_observations": n_obs,
                "multicollinearity_risk": is_mc,
                "calculation_formula": f"Pearson r={pr}, Spearman rho={sr}, N={n_obs}",
            },
            evidence_data={
                "type": "chart",
                "chart_type": "scatter",
                "x_axis": c1,
                "y_axis": c2,
                "rows": [
                    {c1: round(float(row[c1]), 3), c2: round(float(row[c2]), 3)}
                    for _, row in pair_df.iterrows()
                ],
            },
            chart_spec={
                "chart_type": "scatter",
                "title": f"{c1} vs {c2}",
                "data_mapping": {"x": c1, "y": c2},
            },
            methodology=f"{corr.get('recommended_method', 'Pearson & Spearman')} correlation with hypothesis p-value check.",
            confidence_score=0.94 if (corr.get("pearson_p_value") or 1.0) < 0.05 else 0.82,
            confidence_justification=f"Computed over N={n_obs:,} complete paired observations.",
            recommended_action=f"Explore '{c1}' vs '{c2}' in a Scatter Plot to inspect clusters or non-linearity.",
            action_type="create_chart",
            action_payload={"title": f"{c1} vs {c2}", "chart_type": "scatter", "x": c1, "y": c2},
            source_columns=[c1, c2],
            rank_score=84.0 if abs(r_primary or 0) >= 0.75 else 70.0,
            limitations="Correlation does not imply causation; unobserved confounders may drive both variables.",
        ))

    # Cramér's V categorical associations
    for assoc in eda.get("categorical_associations", [])[:2]:
        c1, c2, v, n_obs = assoc["col1"], assoc["col2"], assoc["cramers_v"], assoc["valid_observations"]
        insights.append(_make_insight(
            category="correlation",
            priority="medium",
            title=f"Categorical Association: '{c1}' & '{c2}' (Cramér's V = {v})",
            finding=f"Chi-square association yields Cramér's V = {v} (p={assoc.get('p_value')}, N={n_obs:,}).",
            explanation=(
                f"Discrete categories in '{c1}' and '{c2}' co-occur non-independently ({assoc['strength']} association, Cramér's V={v}). "
                "This indicates segment overlap rather than a causal relationship."
            ),
            supporting_metrics={
                "col1": c1,
                "col2": c2,
                "cramers_v": v,
                "p_value": assoc.get("p_value"),
                "valid_observations": n_obs,
                "calculation_formula": f"Bias-corrected Cramér's V = {v}",
            },
            evidence_data={
                "type": "chart",
                "chart_type": "stacked_bar",
                "x_axis": c1,
                "y_axis": c1,
                "series": c2,
                "rows": [
                    {c1: str(idx), **{str(k): int(val) for k, val in row.items()}}
                    for idx, row in pd.crosstab(work_df[c1], work_df[c2]).head(8).iterrows()
                ],
            },
            chart_spec={
                "chart_type": "stacked_bar",
                "title": f"{c1} vs {c2} Distribution",
                "data_mapping": {"x": c1, "y": c1, "series": c2},
                "aggregation": "count",
            },
            methodology="Pearson Chi-Square Contingency & Bias-Corrected Cramér's V.",
            confidence_score=0.90,
            confidence_justification=f"Statistically significant contingency table across N={n_obs:,} rows.",
            recommended_action=f"View stacked bar breakdown of '{c1}' split by '{c2}'.",
            action_type="create_chart",
            action_payload={"title": f"{c1} by {c2}", "chart_type": "stacked_bar", "x": c1, "y": c1, "series": c2, "aggregation": "count"},
            source_columns=[c1, c2],
            rank_score=67.0,
            limitations="Contingency association does not prove causation.",
        ))

    # 7. Temporal & Trend Insights (chronologically sorted & parsed)
    for dt_diag in eda.get("datetime_diagnostics", [])[:2]:
        d_col = dt_diag["date_column"]
        trends = dt_diag.get("metric_trends", [])
        if not trends:
            insights.append(_make_insight(
                category="trend",
                priority="low",
                title=f"Temporal Coverage: '{d_col}' Spans {dt_diag['earliest_date']} to {dt_diag['latest_date']}",
                finding=f"Found {dt_diag['periods_observed']} {dt_diag['granularity']} periods over {dt_diag['span_days']} days ({dt_diag['missing_periods_count']} missing periods).",
                explanation=f"'{d_col}' spans {dt_diag['span_days']} days. Insufficient numeric measures available for metric trend modeling.",
                supporting_metrics={"date_column": d_col, "span_days": dt_diag["span_days"], "missing_periods": dt_diag["missing_periods_count"]},
                evidence_data={"type": "table", "rows": dt_diag["records_per_period"][:12]},
                methodology="Chronological date span & period coverage diagnostic.",
                confidence_score=0.92,
                confidence_justification=f"Based on {dt_diag['valid_count']:,} valid timestamps.",
                recommended_action="Monitor record ingestion gaps across periods.",
                action_type=None,
                action_payload=None,
                source_columns=[d_col],
                rank_score=50.0,
            ))
            continue

        for t in trends[:2]:
            m_col = t["metric_column"]
            pct = t.get("percent_change")
            delta = t["net_delta"]
            direction = "increased" if delta > 0 else ("decreased" if delta < 0 else "remained flat")
            pct_str = f"by {abs(pct)}%" if pct is not None else f"by {delta:+,.2f}"
            season_note = (
                f"Covers {t['periods_count']} periods — sufficient horizon for seasonal decomposition."
                if t.get("seasonality_eligible")
                else f"Only {t['periods_count']} periods observed; seasonal cycles cannot yet be reliably established."
            )
            missing_p = dt_diag.get("missing_periods_count", 0)
            gap_note = f" Note: {missing_p} intermediate {t['granularity']} period(s) have zero records." if missing_p > 0 else ""

            insights.append(_make_insight(
                category="trend",
                priority="high" if (pct is not None and abs(pct) >= 15.0) else "medium",
                title=f"{t['granularity'].capitalize()} Trend: '{m_col}' {direction.capitalize()} {pct_str} ({t['first_period']} to {t['last_period']})",
                finding=f"'{m_col}' moved from {t['first_value']:,.2f} to {t['last_value']:,.2f} (Peak: {t['peak_value']:,.2f} on {t['peak_period']}; Trough: {t['trough_value']:,.2f} on {t['trough_period']}).",
                explanation=(
                    f"Chronological {t['granularity']} aggregation of '{m_col}' over '{d_col}' across {t['periods_count']} periods "
                    f"shows a net change of {delta:+,.2f} (Spearman time-trend ρ = {t['trend_spearman_rho']}). "
                    f"{season_note}{gap_note}"
                ),
                supporting_metrics={
                    "date_column": d_col,
                    "metric_column": m_col,
                    "granularity": t["granularity"],
                    "periods_count": t["periods_count"],
                    "start_period": t["first_period"],
                    "start_value": t["first_value"],
                    "end_period": t["last_period"],
                    "end_value": t["last_value"],
                    "net_delta": delta,
                    "percent_change": pct,
                    "peak_period": t["peak_period"],
                    "peak_value": t["peak_value"],
                    "trough_period": t["trough_period"],
                    "trough_value": t["trough_value"],
                    "missing_periods_count": missing_p,
                    "calculation_formula": f"{t['last_value']:,.2f} - {t['first_value']:,.2f} = {delta:+,.2f}",
                },
                evidence_data={
                    "type": "chart",
                    "chart_type": "line",
                    "x_axis": d_col,
                    "y_axis": m_col,
                    "rows": [{d_col: l, m_col: v} for l, v in zip(t["labels"], t["values"])],
                },
                chart_spec={
                    "chart_type": "time_series",
                    "title": f"{m_col} Over Time ({t['granularity'].capitalize()})",
                    "data_mapping": {"x": d_col, "y": m_col},
                    "aggregation": "sum",
                },
                methodology=f"Chronologically sorted {t['granularity']} resampling + Spearman trajectory test.",
                confidence_score=0.93 if t["periods_count"] >= 6 else 0.84,
                confidence_justification=f"Grounded in {t['periods_count']} ordered chronological buckets.",
                recommended_action=f"Visualize '{m_col}' over '{d_col}' or run Forecasting Lab if >= 6 periods exist.",
                action_type="create_chart",
                action_payload={"title": f"{m_col} Trend", "chart_type": "time_series", "x": d_col, "y": m_col},
                source_columns=[d_col, m_col],
                rank_score=85.0 if (pct is not None and abs(pct) >= 15) else 72.0,
                limitations=season_note,
            ))

    # 8. Anomaly & Outlier Insights (Univariate IQR/MAD + Multivariate Isolation Forest)
    outlier_summary = eda.get("outlier_summary", {})
    for u_out in outlier_summary.get("univariate", []):
        cnt = u_out.get("flagged_count", 0)
        if cnt <= 0:
            continue
        col = u_out["column"]
        pct_out = u_out["flagged_pct"]
        method_used = u_out["method"]
        threshold = u_out["threshold"]
        sample_vals = [a["value"] for a in u_out.get("anomalies", [])[:5]]
        insights.append(_make_insight(
            category="anomaly",
            priority="high" if pct_out >= 5.0 else "medium",
            title=f"Candidate Anomalies in '{col}': {cnt} Unusual Values ({pct_out}%)",
            finding=f"Method '{method_used}' flagged {cnt} candidate observation(s) using threshold {threshold}. Samples: {sample_vals}.",
            explanation=(
                f"Evaluated {u_out['valid_observations']:,} valid values in '{col}' using {method_used} ({threshold}). "
                f"Flagged {cnt} candidate point(s) ({pct_out}%). These records are statistical candidate anomalies — "
                "not automatically errors — and no records were deleted."
            ),
            supporting_metrics={
                "column": col,
                "method": method_used,
                "threshold": threshold,
                "flagged_count": cnt,
                "flagged_pct": pct_out,
                "sample_outliers": sample_vals,
                "calculation_formula": f"{method_used}: {threshold}",
            },
            evidence_data={
                "type": "table",
                "rows": [
                    {"Row Index": a["index"], "Observed Value": a["value"], "Details": a.get("bound_exceeded") or f"Score {a.get('score')}"}
                    for a in u_out.get("anomalies", [])[:8]
                ],
            },
            chart_spec={
                "chart_type": "box",
                "title": f"Outlier Spread: {col}",
                "data_mapping": {"y": col},
            },
            methodology=f"Robust univariate anomaly detection ({method_used}).",
            confidence_score=0.93,
            confidence_justification=f"Scanned N={u_out['valid_observations']:,} valid values with threshold {threshold}.",
            recommended_action=f"Inspect candidate anomalies in '{col}' via Box Plot or Data Prep Studio.",
            action_type="deeper_analysis",
            action_payload={"column": col, "technique": "anomaly_scan"},
            source_columns=[col],
            rank_score=80.0 if pct_out >= 4.0 else 65.0,
            limitations="Candidate anomalies may represent genuine extreme occurrences rather than data entry errors.",
        ))

    mv_out = outlier_summary.get("multivariate")
    if mv_out and mv_out.get("flagged_count", 0) > 0:
        insights.append(_make_insight(
            category="anomaly",
            priority="medium",
            title=f"Multivariate Anomalies: {mv_out['flagged_count']} Unusual Cross-Metric Records (Isolation Forest)",
            finding=f"Isolation Forest flagged {mv_out['flagged_count']} rows ({mv_out['flagged_pct']}%) across {len(mv_out['columns_evaluated'])} numeric features.",
            explanation=(
                f"Evaluated combinations across {', '.join(mv_out['columns_evaluated'][:5])} simultaneously using Isolation Forest (contamination=5%). "
                "These rows exhibit unusual joint combinations even when individual column values look normal."
            ),
            supporting_metrics={
                "method": "IsolationForest",
                "columns_evaluated": mv_out["columns_evaluated"],
                "flagged_count": mv_out["flagged_count"],
                "flagged_pct": mv_out["flagged_pct"],
                "flagged_indices": mv_out["flagged_indices"][:15],
                "calculation_formula": "IsolationForest(contamination=0.05) across multivariate numeric space",
            },
            evidence_data={
                "type": "table",
                "rows": [{"Row Index": idx, "Flag": "Multivariate Candidate"} for idx in mv_out["flagged_indices"][:10]],
            },
            methodology="Unsupervised Multivariate Isolation Forest anomaly detection.",
            confidence_score=0.88,
            confidence_justification=f"Trained on N={mv_out['valid_observations']:,} complete joint observations.",
            recommended_action="Audit flagged row indices in Dataset Explorer before automated modeling.",
            action_type=None,
            action_payload=None,
            source_columns=mv_out["columns_evaluated"][:6],
            rank_score=66.0,
            limitations="Unsupervised contamination parameter assumes ~5% baseline anomaly budget; treat flagged rows as candidates.",
        ))

    # 9. Predictive Insights & Recommendations (Domain-Neutral)
    if dt_cols and eda.get("time_trend") and len(eda["time_trend"]["labels"]) >= 6:
        tt = eda["time_trend"]
        insights.append(_make_insight(
            category="predictive",
            priority="medium",
            title=f"Forecasting Readiness: '{tt['target_column']}' Has {len(tt['labels'])} Historical Periods",
            finding=f"'{tt['date_column']}' provides {len(tt['labels'])} {tt.get('granularity', 'chronological')} intervals suitable for baseline trend modeling.",
            explanation=(
                f"With {len(tt['labels'])} chronological observations of '{tt['target_column']}' over '{tt['date_column']}', "
                "time-series models can estimate continuation trajectories and confidence intervals (note: forecasts are model estimates, not guarantees)."
            ),
            supporting_metrics={"date_column": tt["date_column"], "target_column": tt["target_column"], "periods": len(tt["labels"])},
            evidence_data={"type": "chart", "chart_type": "line", "x_axis": tt["date_column"], "y_axis": tt["target_column"], "rows": [{tt["date_column"]: l, tt["target_column"]: v} for l, v in zip(tt["labels"], tt["values"])]},
            methodology="Temporal observation density & forecasting eligibility assessment.",
            confidence_score=0.89,
            confidence_justification=f"Verified {len(tt['labels'])} ordered chronological periods.",
            recommended_action="Open Forecasting Lab to evaluate ETS, ARIMA, or Linear models with backtesting.",
            action_type=None,
            action_payload=None,
            source_columns=[tt["date_column"], tt["target_column"]],
            rank_score=62.0,
        ))
    elif eda.get("notable_correlations"):
        top_corr = eda["notable_correlations"][0]
        insights.append(_make_insight(
            category="predictive",
            priority="medium",
            title=f"Predictive Driver Signal: '{top_corr['col1']}' Strongly Co-varies with '{top_corr['col2']}'",
            finding=f"Shared linear variance R² = {round((top_corr.get('r_squared') or 0) * 100, 1)}% between '{top_corr['col1']}' and '{top_corr['col2']}'.",
            explanation=(
                f"While correlation does not establish causation, '{top_corr['col1']}' and '{top_corr['col2']}' share measurable co-movement, "
                "making them strong candidate features for exploratory regression or scenario analysis."
            ),
            supporting_metrics=top_corr,
            evidence_data={"type": "table", "rows": [top_corr]},
            methodology="Linear explained variance (R²) predictive screening.",
            confidence_score=0.85,
            confidence_justification=f"Grounded in N={top_corr.get('valid_observations', total_rows):,} paired rows.",
            recommended_action="Test feature interactions via Scatter Plot or What-If Scenario Simulator.",
            action_type="create_chart",
            action_payload={"title": f"{top_corr['col1']} vs {top_corr['col2']}", "chart_type": "scatter", "x": top_corr["col1"], "y": top_corr["col2"]},
            source_columns=[top_corr["col1"], top_corr["col2"]],
            rank_score=56.0,
        ))

    # Actionable Domain-Neutral Recommendation
    rec_items: List[str] = []
    if null_cells > 0 or dup_rows > 0:
        rec_items.append(f"Clean {null_cells:,} missing cell(s) and {dup_rows:,} duplicate row(s) in Data Prep Studio before reporting aggregates.")
    if comp_candidates:
        top_c = comp_candidates[0][1]
        rec_items.append(f"Investigate drivers behind '{top_c['top_g']['group']}' leading '{top_c['num']}' across '{top_c['cat']}'.")
    if eda.get("multicollinear_pairs"):
        mp = eda["multicollinear_pairs"][0]
        rec_items.append(f"Account for high collinearity (r={mp['pearson_r']}) between '{mp['col1']}' and '{mp['col2']}' before fitting multivariate models.")
    if not rec_items:
        rec_items.append("Build a focused visual dashboard combining your highest-variance numerical metrics with primary grouping dimensions.")

    insights.append(_make_insight(
        category="opportunity",
        priority="medium",
        title=f"Recommended Analytical Next Steps for '{dataset.name}'",
        finding=rec_items[0],
        explanation=" ".join(rec_items),
        supporting_metrics={"recommendations": rec_items, "calculation_formula": "Prioritized rule synthesis from quality, disparity, correlation & temporal findings"},
        evidence_data={"type": "table", "rows": [{"Priority": i + 1, "Recommended Action": r} for i, r in enumerate(rec_items)]},
        methodology="Evidence-backed decision synthesis.",
        confidence_score=0.90,
        confidence_justification="Synthesized directly from computed statistical findings.",
        recommended_action=rec_items[0],
        action_type=None,
        action_payload=None,
        source_columns=[],
        rank_score=55.0,
    ))

    return _deduplicate_and_rank(insights)


def build_executive_summary(
    df: pd.DataFrame,
    dataset_name: str,
    eda: Dict[str, Any],
    insights: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generates a structured, domain-neutral executive brief with category coverage status."""
    total_rows = int(eda.get("row_count", len(df)))
    total_cols = int(eda.get("column_count", len(df.columns)))
    q_score = eda.get("quality_score", 100.0)
    numeric_stats = eda.get("numeric_stats", {})

    key_metrics = [
        {"label": "Total Records", "value": f"{total_rows:,}", "subtext": "Validated rows"},
        {"label": "Data Dimensions", "value": f"{total_cols} Columns", "subtext": f"{len(numeric_stats)} Numeric Metrics"},
        {"label": "Data Quality Index", "value": f"{q_score}%", "subtext": "Transparent scoring"},
        {"label": "Verified Insights", "value": str(len(insights)), "subtext": "Evidence-backed findings"},
    ]

    key_findings = [
        {
            "title": ins["title"],
            "explanation": ins["explanation"],
            "category": ins["category"],
            "priority": ins["priority"],
        }
        for ins in insights if ins["category"] != "overview"
    ][:4]
    if not key_findings and insights:
        key_findings = [{"title": insights[0]["title"], "explanation": insights[0]["explanation"], "category": insights[0]["category"], "priority": insights[0]["priority"]}]

    opportunities = [
        i["recommended_action"]
        for i in insights
        if i["category"] in ("opportunity", "performance", "comparative", "predictive") and i.get("recommended_action")
    ][:3] or ["Explore group comparisons and distributions in Visualization Studio."]

    risks = [
        i["explanation"]
        for i in insights
        if i["category"] in ("anomaly", "quality")
    ][:3] or ["No severe statistical anomalies or critical data hygiene risks detected in this snapshot."]

    next_actions = [
        "1. Review any missing-value or duplicate warnings in Data Prep Studio (creates a separate cleaned version).",
        "2. Inspect linked visualizations for the top ranked findings in Visualization Studio.",
        "3. Ask follow-up questions in AI Business Analyst grounded in verified statistics.",
    ]

    limitations = [
        f"Analysis grounded in N={total_rows:,} recorded rows across {total_cols} attributes.",
        "Correlations and group disparities indicate statistical association, not proven causation.",
    ]
    if total_rows < 30:
        limitations.append("Small sample size (N < 30) limits statistical power and generalizability of distributional claims.")
    if eda.get("identifier_columns"):
        limitations.append(f"Identifier columns ({', '.join(eda['identifier_columns'][:4])}) were excluded from numeric aggregations.")

    # Category Coverage Report (explicitly handles insufficient evidence per category)
    category_coverage: List[Dict[str, Any]] = []
    for cat_key, cat_label in INSIGHT_CATEGORIES:
        matched = [i for i in insights if i["category"] == cat_key]
        category_coverage.append({
            "category": cat_key,
            "label": cat_label,
            "count": len(matched),
            "status": "available" if matched else "insufficient_evidence",
            "message": (
                f"{len(matched)} verified insight(s) generated."
                if matched
                else "No reliable insight could be generated for this category with the available data."
            ),
        })

    return {
        "project_overview": (
            f"Automated universal audit of '{dataset_name}' analyzing {total_rows:,} records across "
            f"{total_cols} dimensions ({len(numeric_stats)} numeric metrics, "
            f"{len(eda.get('categorical_columns', []))} categorical dimensions, "
            f"{len(eda.get('datetime_columns', []))} temporal axes) with a Data Quality Index of {q_score}%."
        ),
        "key_metrics": key_metrics,
        "key_findings": key_findings,
        "opportunities": opportunities,
        "risks": risks,
        "recommended_next_actions": next_actions,
        "limitations_and_uncertainties": limitations,
        "category_coverage": category_coverage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def execute_project_insights_pipeline(
    dataset: Dataset,
    df: pd.DataFrame,
    force_refresh: bool = False,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the complete Project Insights lifecycle:
    - Fingerprint & version cache check
    - Universal Data Understanding + Automated EDA
    - Evidence-grounded Insight Generation & Chart Linkage
    - Executive Summary & Category Coverage
    - Database persistence & stale invalidation
    """
    fingerprint = compute_dataset_fingerprint(dataset, df)

    if db and not force_refresh:
        cached_run = (
            db.query(ProjectAnalysisRun)
            .filter(
                ProjectAnalysisRun.dataset_id == dataset.id,
                ProjectAnalysisRun.dataset_fingerprint == fingerprint,
            )
            .order_by(ProjectAnalysisRun.created_at.desc())
            .first()
        )
        if cached_run:
            cached_insights = (
                db.query(ProjectInsight)
                .filter(ProjectInsight.analysis_run_id == cached_run.id)
                .order_by(ProjectInsight.id.asc())
                .all()
            )
            return {
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
                "dataset_version": getattr(dataset, "version", 1),
                "dataset_fingerprint": fingerprint,
                "is_stale": False,
                "cached": True,
                "executive_summary": cached_run.executive_summary,
                "eda": cached_run.eda_summary,
                "quality_score": cached_run.quality_score,
                "insights": [
                    {
                        "id": ins.id,
                        "category": ins.category,
                        "priority": ins.priority,
                        "title": ins.title,
                        "explanation": ins.explanation,
                        "supporting_metrics": ins.supporting_metrics,
                        "evidence_data": ins.evidence_data,
                        "methodology": ins.methodology,
                        "confidence_score": ins.confidence_score,
                        "confidence_justification": ins.confidence_justification,
                        "recommended_action": ins.recommended_action,
                        "action_type": ins.action_type,
                        "action_payload": ins.action_payload,
                        "source_columns": ins.source_columns,
                        "status": ins.status,
                        "is_stale": ins.is_stale,
                        "created_at": ins.created_at.isoformat() if ins.created_at else None,
                    }
                    for ins in cached_insights
                ],
            }

    understanding = understand_dataset(df, dataset_name=dataset.name, sanitize=True)
    eda = build_automated_eda(df, dataset.name, understanding=understanding)
    raw_insights = discover_business_insights(df, dataset, eda, fingerprint)
    exec_summary = build_executive_summary(df, dataset.name, eda, raw_insights)

    insights_records = []
    if db:
        try:
            db.query(ProjectInsight).filter(
                ProjectInsight.dataset_id == dataset.id,
                ProjectInsight.dataset_fingerprint != fingerprint,
            ).update({"is_stale": True}, synchronize_session=False)

            run_record = ProjectAnalysisRun(
                dataset_id=dataset.id,
                dataset_fingerprint=fingerprint,
                executive_summary=exec_summary,
                eda_summary=eda,
                quality_score=eda["quality_score"],
                status="completed",
                created_at=datetime.now(timezone.utc),
            )
            db.add(run_record)
            db.flush()

            for item in raw_insights:
                insight_model = ProjectInsight(
                    dataset_id=dataset.id,
                    analysis_run_id=run_record.id,
                    dataset_fingerprint=fingerprint,
                    category=item["category"],
                    priority=item["priority"],
                    title=item["title"][:255],
                    explanation=item["explanation"],
                    supporting_metrics=item.get("supporting_metrics"),
                    evidence_data={
                        **(item.get("evidence_data") or {}),
                        **({"chart_spec": item["chart_spec"]} if item.get("chart_spec") else {}),
                        "finding": item.get("finding"),
                        "limitations": item.get("limitations"),
                        "rank_score": item.get("rank_score"),
                    },
                    methodology=item.get("methodology"),
                    confidence_score=item.get("confidence_score", 0.90),
                    confidence_justification=item.get("confidence_justification"),
                    recommended_action=item.get("recommended_action"),
                    action_type=item.get("action_type"),
                    action_payload=item.get("action_payload"),
                    source_columns=item.get("source_columns"),
                    status="new",
                    is_stale=False,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(insight_model)
                db.flush()
                item["id"] = insight_model.id
                insights_records.append(item)

            db.commit()
        except Exception:
            db.rollback()
            for idx, item in enumerate(raw_insights, 1):
                item["id"] = idx
            insights_records = raw_insights
    else:
        for idx, item in enumerate(raw_insights, 1):
            item["id"] = idx
        insights_records = raw_insights

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "dataset_version": getattr(dataset, "version", 1),
        "dataset_fingerprint": fingerprint,
        "is_stale": False,
        "cached": False,
        "executive_summary": exec_summary,
        "eda": eda,
        "quality_score": eda["quality_score"],
        "insights": insights_records,
    }
