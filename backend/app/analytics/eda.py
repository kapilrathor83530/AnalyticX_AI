from typing import Any, Dict, Optional

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


def eda_dataframe(df: pd.DataFrame, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Unified exploratory data analysis driven by Universal Data Understanding."""
    if profile is None:
        understanding = understand_dataset(df, sanitize=True)
        norm_df = understanding["normalized_df"]
        profile = understanding["profile"]
    else:
        norm_df = df

    num_cols = profile.get("numerical_columns", [])
    cat_cols = profile.get("categorical_columns", []) + profile.get("boolean_columns", [])
    dt_cols = profile.get("datetime_columns", [])

    # Correlations (Pearson + Spearman + notable pairs)
    corr_res = calculate_correlation(
        norm_df,
        numeric_columns=num_cols,
        categorical_columns=cat_cols,
    )

    # Numeric Distributions
    numeric_distributions: Dict[str, Dict[str, Any]] = {}
    numeric_stats: Dict[str, Dict[str, Any]] = {}
    for col in num_cols:
        numeric_stats[col] = analyze_numerical_column(norm_df, col)
        clean = pd.to_numeric(norm_df[col], errors="coerce").dropna()
        if clean.empty or clean.nunique() < 2:
            continue
        bins_count = min(10, max(2, int(clean.nunique())))
        counts, bins = np.histogram(clean, bins=bins_count)
        numeric_distributions[str(col)] = {
            "bins": [to_python(round(float(b), 4)) for b in bins.tolist()],
            "counts": [int(c) for c in counts.tolist()],
        }

    # Categorical Breakdowns
    categorical_breakdowns: Dict[str, Any] = {}
    for col in cat_cols[:8]:
        cat_info = analyze_categorical_column(norm_df, col)
        if not cat_info.get("insufficient_data"):
            categorical_breakdowns[str(col)] = cat_info.get("distribution", [])

    # Temporal summary if datetime column present
    time_trends = None
    if dt_cols:
        dt_info = analyze_datetime_column(norm_df, dt_cols[0], numeric_columns=num_cols)
        if dt_info.get("metric_trends"):
            first_trend = dt_info["metric_trends"][0]
            time_trends = {
                "date_column": dt_cols[0],
                "target_column": first_trend["metric_column"],
                "labels": first_trend["labels"],
                "values": first_trend["values"],
            }

    return {
        **profile,
        "correlations": corr_res.get("pearson_matrix", {}),
        "spearman_correlations": corr_res.get("spearman_matrix", {}),
        "notable_correlations": corr_res.get("notable_correlations", []),
        "categorical_associations": corr_res.get("categorical_associations", []),
        "numeric_distributions": numeric_distributions,
        "numeric_stats": numeric_stats,
        "categorical_breakdowns": categorical_breakdowns,
        "time_trends": time_trends,
    }
