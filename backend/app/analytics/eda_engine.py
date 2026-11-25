"""Automated EDA & Evidence-Grounded Line-by-Line Insights Generator for Analyticx AI."""
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from app.analytics.data_understanding import understand_dataset
from app.analytics.profiling import to_python
from app.analytics.statistics import (
    analyze_categorical_column,
    analyze_datetime_column,
    analyze_numerical_column,
    calculate_correlation,
)


def generate_eda_report(
    df: pd.DataFrame,
    dataset_name: str = "Dataset",
    understanding: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if understanding is None:
        understanding = understand_dataset(df, dataset_name=dataset_name, sanitize=True)

    norm_df = understanding["normalized_df"]
    profile = understanding["profile"]
    total_rows = int(profile["row_count"])
    total_cols = int(profile["column_count"])

    num_cols = profile.get("numerical_columns", [])
    cat_cols = [c for c in profile.get("categorical_columns", []) + profile.get("boolean_columns", []) if c not in profile.get("identifier_columns", [])]
    dt_cols = profile.get("datetime_columns", [])

    # 1. Column Profiles & Data Dictionary
    dictionary = []
    for col_meta in profile.get("columns", []):
        dictionary.append({
            "name": col_meta["name"],
            "dtype": col_meta["dtype"],
            "inferred_type": col_meta["inferred_type"],
            "detected_type": col_meta.get("detected_type"),
            "semantic_type": col_meta.get("semantic_type"),
            "unique_count": col_meta["unique_count"],
            "missing_count": col_meta["missing_count"],
            "missing_percent": col_meta["missing_percent"],
            "sample_values": col_meta["sample_values"],
            "role_hint": col_meta.get("role", "Categorical Dimension"),
        })

    # 2. Descriptive Statistics (Numeric)
    numeric_stats = {}
    for col in num_cols:
        st = analyze_numerical_column(norm_df, col)
        if not st.get("count"):
            continue
        numeric_stats[col] = {
            "count": st["count"],
            "mean": st["mean"],
            "std": st["std"],
            "min": st["min"],
            "p25": st["q1"],
            "median": st["median"],
            "p75": st["q3"],
            "max": st["max"],
            "skew": st.get("skewness", 0.0),
        }

    # 3. Distributions (Numeric Histograms)
    distributions = {}
    for col in num_cols[:10]:
        s = pd.to_numeric(norm_df[col], errors="coerce").dropna()
        if len(s) >= 4 and s.nunique() > 1:
            counts, bins = np.histogram(s, bins=min(10, int(s.nunique())))
            distributions[col] = {
                "bins": [to_python(round(float(b), 2)) for b in bins.tolist()],
                "counts": [int(c) for c in counts.tolist()],
            }

    # 4. Categorical Breakdowns
    categorical_breakdowns = {}
    for col in cat_cols[:10]:
        cat_info = analyze_categorical_column(norm_df, col)
        if cat_info.get("distribution"):
            categorical_breakdowns[col] = cat_info["distribution"][:8]

    # 5. Correlations
    corr_res = calculate_correlation(norm_df, numeric_columns=num_cols, categorical_columns=cat_cols)
    correlations = corr_res.get("pearson_matrix", {})
    notable_correlations = corr_res.get("notable_correlations", [])

    # 6. Time Trends (if date column found)
    time_trends = {}
    if dt_cols:
        dt_info = analyze_datetime_column(norm_df, dt_cols[0], numeric_columns=num_cols)
        if dt_info.get("metric_trends"):
            t = dt_info["metric_trends"][0]
            time_trends = {
                "date_column": dt_cols[0],
                "target_column": t["metric_column"],
                "dates": t["labels"],
                "values": t["values"],
            }

    # 7. Line-by-Line Evidence-Grounded Insights
    insights = _build_line_by_line_insights(
        df=norm_df,
        dataset_name=dataset_name,
        total_rows=total_rows,
        total_cols=total_cols,
        dictionary=dictionary,
        numeric_stats=numeric_stats,
        categorical_breakdowns=categorical_breakdowns,
        notable_correlations=notable_correlations,
        time_trends=time_trends,
    )

    return {
        "dataset_name": dataset_name,
        "row_count": total_rows,
        "column_count": total_cols,
        "data_dictionary": dictionary,
        "numeric_statistics": numeric_stats,
        "numeric_distributions": distributions,
        "categorical_breakdowns": categorical_breakdowns,
        "correlation_matrix": correlations,
        "notable_correlations": notable_correlations[:8],
        "time_trends": time_trends,
        "insights_report": insights,
    }


def _build_line_by_line_insights(
    df: pd.DataFrame,
    dataset_name: str,
    total_rows: int,
    total_cols: int,
    dictionary: List[Dict[str, Any]],
    numeric_stats: Dict[str, Any],
    categorical_breakdowns: Dict[str, Any],
    notable_correlations: List[Dict[str, Any]],
    time_trends: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """Builds evidence-backed analytical statements organized by analytical section."""

    # Section 1: Dataset Summary
    num_count = len(numeric_stats)
    cat_count = len(categorical_breakdowns)
    total_missing = sum(item["missing_count"] for item in dictionary)
    summary_findings = [
        {
            "id": "sum_1",
            "statement": f"The dataset '{dataset_name}' contains {total_rows:,} records across {total_cols} attributes.",
            "evidence": f"{total_rows} total rows, {total_cols} columns ({num_count} numerical, {cat_count} categorical/text).",
            "type": "fact",
        },
        {
            "id": "sum_2",
            "statement": f"Data completeness stands at {round((1 - (total_missing / (total_rows * total_cols if total_rows and total_cols else 1))) * 100, 1)}% across all fields.",
            "evidence": f"{total_missing:,} missing cell(s) out of {total_rows * total_cols:,} total cells.",
            "type": "quality",
        },
    ]

    # Section 2: Column-Level Findings
    column_findings = []
    # Numeric highlights
    for col, stat in list(numeric_stats.items())[:4]:
        spread = stat["max"] - stat["min"]
        is_skewed = abs(stat.get("skew", 0)) > 1.0
        column_findings.append({
            "id": f"col_{col}",
            "statement": f"'{col}' averages {stat['mean']:,} (ranging from {stat['min']:,} to {stat['max']:,}).",
            "evidence": f"Median is {stat['median']:,}, Standard Deviation is {stat['std']:,}" + (f", Skewness of {stat['skew']} indicates positive/negative asymmetry" if is_skewed else ""),
            "type": "numeric",
        })

    # Categorical highlights
    for col, items in list(categorical_breakdowns.items())[:3]:
        if items:
            top_item = items[0]
            column_findings.append({
                "id": f"cat_{col}",
                "statement": f"In '{col}', the dominant category is '{top_item['category']}', accounting for {top_item['percentage']}% of records.",
                "evidence": f"Occurs {top_item['count']:,} times out of {total_rows:,} records.",
                "type": "categorical",
            })

    # Section 3: Relationships & Correlations
    relationship_findings = []
    if notable_correlations:
        for item in notable_correlations[:3]:
            relationship_findings.append({
                "id": f"rel_{item['col1']}_{item['col2']}",
                "statement": f"'{item['col1']}' and '{item['col2']}' demonstrate a {item['strength']} {item['direction']} association (r = {item['correlation']}).",
                "evidence": f"Pearson correlation coefficient r = {item['correlation']}. Note: Association indicates co-movement, not causation.",
                "type": "correlation",
            })
    else:
        relationship_findings.append({
            "id": "rel_none",
            "statement": "No pairs of numerical attributes met the threshold for strong linear correlation.",
            "evidence": "All pairwise Pearson r values remain under |0.40|.",
            "type": "correlation",
        })

    # Section 4: Anomalies & Outliers
    anomaly_findings = []
    for col, stat in list(numeric_stats.items())[:6]:
        q1 = stat["p25"]
        q3 = stat["p75"]
        iqr = q3 - q1
        if iqr <= 0:
            continue
        upper_limit = q3 + 1.5 * iqr
        lower_limit = q1 - 1.5 * iqr
        if stat["max"] > upper_limit or stat["min"] < lower_limit:
            anomaly_findings.append({
                "id": f"anom_{col}",
                "statement": f"Candidate tail outliers detected in '{col}' outside the Tukey 1.5*IQR fence [{round(lower_limit, 2):,}, {round(upper_limit, 2):,}].",
                "evidence": f"Observed range [{stat['min']:,}, {stat['max']:,}], Q1={q1:,}, Q3={q3:,}, IQR={round(iqr, 2):,}. Candidate observations require verification rather than automatic deletion.",
                "type": "outlier",
            })

    # Section 5: Comparative Segment & Domain Insights (Dataset-Independent)
    business_findings = []
    biz_cols = [c for c in numeric_stats.keys() if any(k in c.lower() for k in ("sales", "revenue", "profit", "amount", "price", "cost", "salary", "score", "sgpa", "marks"))]
    target_metrics = biz_cols or list(numeric_stats.keys())
    cat_dim = [c for c in categorical_breakdowns.keys() if len(categorical_breakdowns[c]) >= 2]

    if target_metrics and cat_dim:
        m_col = target_metrics[0]
        c_col = cat_dim[0]
        try:
            grouped = df.groupby(c_col)[m_col].agg(["mean", "sum", "count"]).dropna().sort_values(by="mean", ascending=False)
            if len(grouped) >= 2:
                top_cat = grouped.index[0]
                bot_cat = grouped.index[-1]
                top_mean = float(grouped.iloc[0]["mean"])
                bot_mean = float(grouped.iloc[-1]["mean"])
                top_sum = float(grouped.iloc[0]["sum"])
                total_val = float(grouped["sum"].sum())
                share_note = f" ({round(top_sum / total_val * 100, 1)}% of aggregate {m_col})" if abs(total_val) > 1e-9 else ""
                business_findings.append({
                    "id": "biz_1",
                    "statement": f"Across '{c_col}', '{top_cat}' records the highest mean '{m_col}' ({top_mean:,.2f}) compared to '{bot_cat}' ({bot_mean:,.2f}){share_note}.",
                    "evidence": f"Aggregated across {len(grouped)} groups in '{c_col}' from {total_rows:,} rows.",
                    "type": "business",
                })
        except Exception:
            pass

    if not business_findings:
        business_findings.append({
            "id": "biz_general",
            "statement": f"Analyzed {total_rows:,} records across {len(numeric_stats)} numeric and {len(categorical_breakdowns)} categorical attributes.",
            "evidence": "No eligible group-by dimension/measure contrast met variation thresholds for segment ranking.",
            "type": "business",
        })

    # Section 6: Recommended Next Steps
    next_steps = [
        {
            "id": "next_1",
            "statement": "Explore dimensional segment breakdowns in the Visualization Studio.",
            "evidence": "Categorical attributes provide natural grouping dimensions for bar charts and comparative dashboards.",
            "type": "recommendation",
        },
        {
            "id": "next_2",
            "statement": "Evaluate forecasting opportunities if chronological date columns are present.",
            "evidence": "Time series analysis can model seasonal trends and project future performance.",
            "type": "recommendation",
        },
    ]

    return {
        "dataset_summary": summary_findings,
        "column_findings": column_findings,
        "relationships": relationship_findings,
        "anomalies": anomaly_findings,
        "business_insights": business_findings,
        "recommended_next_steps": next_steps,
    }
