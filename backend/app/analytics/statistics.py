"""Deterministic Universal Statistical Analysis Engine for Analyticx AI.

Provides verified Pandas, NumPy, SciPy, and Scikit-learn computations for:
- Numerical column deep analysis (moments, quantiles, CV, zeros/negatives, outliers)
- Categorical column analysis (frequencies, dominance, rare labels, imbalance, case inconsistencies)
- Datetime & temporal trend analysis (coverage, cadence, gaps, trends, seasonality checks)
- Relationship analysis (Pearson, Spearman, Cramér's V, ANOVA F-test, multicollinearity)
- Outlier & anomaly detection (IQR, Z-score, Modified Z-score MAD, Isolation Forest)
- Dynamic cross-column segment comparisons
"""
from __future__ import annotations

import math
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from app.analytics.profiling import to_python


def _safe_float(val: Any, digits: int = 4) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if not math.isfinite(f):
            return None
        return round(f, digits)
    except (TypeError, ValueError):
        return None


def analyze_numerical_column(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Comprehensive deterministic statistics for a numerical column."""
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    raw_series = df[column]
    series = pd.to_numeric(raw_series, errors="coerce")
    total_rows = int(len(raw_series))
    missing_count = int(series.isna().sum())
    valid = series.dropna()
    n = int(len(valid))

    if n == 0:
        return {
            "column": column,
            "count": 0,
            "missing_count": missing_count,
            "missing_pct": round((missing_count / total_rows * 100), 2) if total_rows else 0.0,
            "insufficient_data": True,
            "reason": f"Column '{column}' has 0 valid numeric observations.",
        }

    mean_val = float(valid.mean())
    median_val = float(valid.median())
    min_val = float(valid.min())
    max_val = float(valid.max())
    val_range = max_val - min_val
    total_sum = float(valid.sum())
    std_val = float(valid.std(ddof=1)) if n > 1 else 0.0
    var_val = float(valid.var(ddof=1)) if n > 1 else 0.0

    # Mode only when meaningful (most frequent value occurs > 1 time)
    mode_counts = valid.value_counts()
    mode_val = None
    if not mode_counts.empty and int(mode_counts.iloc[0]) > 1:
        mode_val = float(mode_counts.index[0])

    q1 = float(valid.quantile(0.25))
    q3 = float(valid.quantile(0.75))
    iqr = q3 - q1
    p5 = float(valid.quantile(0.05))
    p10 = float(valid.quantile(0.10))
    p90 = float(valid.quantile(0.90))
    p95 = float(valid.quantile(0.95))

    skewness = float(valid.skew()) if n >= 3 and std_val > 0 else 0.0
    kurtosis = float(valid.kurtosis()) if n >= 4 and std_val > 0 else None
    cv = (std_val / abs(mean_val) * 100.0) if abs(mean_val) > 1e-9 and n > 1 else None

    zero_count = int((valid == 0).sum())
    negative_count = int((valid < 0).sum())
    positive_count = int((valid > 0).sum())

    # IQR outlier candidates
    iqr_low = q1 - 1.5 * iqr
    iqr_high = q3 + 1.5 * iqr
    if n >= 4 and iqr > 0:
        iqr_mask = (valid < iqr_low) | (valid > iqr_high)
        iqr_outlier_count = int(iqr_mask.sum())
        outlier_samples = [to_python(v) for v in valid[iqr_mask].head(10).tolist()]
    else:
        iqr_outlier_count = 0
        outlier_samples = []

    z_outlier_count = 0
    if n >= 10 and std_val > 0:
        z_scores = np.abs((valid - mean_val) / std_val)
        z_outlier_count = int((z_scores > 3.0).sum())

    insufficient = n < 3

    return {
        "column": column,
        "count": n,
        "missing_count": missing_count,
        "missing_pct": round((missing_count / total_rows * 100), 2) if total_rows else 0.0,
        "unique_count": int(valid.nunique()),
        "sum": _safe_float(total_sum),
        "mean": _safe_float(mean_val),
        "median": _safe_float(median_val),
        "mode": _safe_float(mode_val),
        "min": _safe_float(min_val),
        "max": _safe_float(max_val),
        "range": _safe_float(val_range),
        "variance": _safe_float(var_val),
        "std": _safe_float(std_val),
        "q1": _safe_float(q1),
        "q25": _safe_float(q1),
        "q3": _safe_float(q3),
        "q75": _safe_float(q3),
        "iqr": _safe_float(iqr),
        "p5": _safe_float(p5),
        "p10": _safe_float(p10),
        "p90": _safe_float(p90),
        "p95": _safe_float(p95),
        "skewness": _safe_float(skewness, 3),
        "kurtosis": _safe_float(kurtosis, 3),
        "cv_pct": _safe_float(cv, 2),
        "zero_count": zero_count,
        "negative_count": negative_count,
        "positive_count": positive_count,
        "iqr_lower_fence": _safe_float(iqr_low),
        "iqr_upper_fence": _safe_float(iqr_high),
        "iqr_outlier_count": iqr_outlier_count,
        "iqr_outlier_pct": round((iqr_outlier_count / n * 100), 2) if n else 0.0,
        "zscore_outlier_count": z_outlier_count,
        "outlier_samples": outlier_samples,
        "mean_median_gap_pct": round(abs(mean_val - median_val) / abs(median_val) * 100, 1) if abs(median_val) > 1e-9 else None,
        "insufficient_data": insufficient,
        "reason": "Fewer than 3 non-null observations; distribution spread metrics are limited." if insufficient else None,
    }


def descriptive_statistics(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Backward-compatible wrapper returning rich numerical statistics."""
    res = analyze_numerical_column(df, column)
    if "error" in res:
        return res
    if res.get("insufficient_data") and res.get("count", 0) == 0:
        return {"error": f"Column '{column}' has no values"}
    return res


def analyze_categorical_column(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Comprehensive frequency, dominance, imbalance, rare-category, and label hygiene analysis."""
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    series = df[column]
    total_rows = int(len(series))
    missing_count = int(series.isna().sum())
    valid = series.dropna().astype(str)
    n = int(len(valid))

    if n == 0:
        return {
            "column": column,
            "count": 0,
            "missing_count": missing_count,
            "unique_count": 0,
            "insufficient_data": True,
        }

    counts = valid.value_counts()
    unique_count = int(len(counts))
    top_cat = str(counts.index[0])
    top_count = int(counts.iloc[0])
    top_pct = round(top_count / n * 100, 2)

    least_cat = str(counts.index[-1])
    least_count = int(counts.iloc[-1])
    least_pct = round(least_count / n * 100, 2)

    rare_threshold = max(1, int(math.floor(n * 0.02)))
    rare_mask = counts <= rare_threshold
    rare_categories = [str(k) for k in counts[rare_mask].index[:10]]
    rare_count = int(rare_mask.sum())

    imbalance_ratio = round(top_count / max(1, least_count), 2)

    # Normalized Shannon entropy: 0 = completely concentrated in 1 value, 1 = perfectly uniform
    probs = counts.values / float(n)
    entropy = -float(np.sum(probs * np.log2(np.clip(probs, 1e-12, 1.0))))
    max_entropy = math.log2(unique_count) if unique_count > 1 else 1.0
    normalized_entropy = round(entropy / max_entropy, 3) if unique_count > 1 else 0.0

    # Detect potential case / whitespace label duplicates ("North", "north ", "NORTH")
    norm_groups: Dict[str, List[str]] = {}
    for raw_label in counts.index[:100]:
        key = str(raw_label).strip().lower()
        norm_groups.setdefault(key, []).append(str(raw_label))
    inconsistent_labels = [variants for variants in norm_groups.values() if len(variants) > 1]

    distribution = [
        {
            "category": str(k),
            "count": int(v),
            "percentage": round(float(v / n * 100), 2),
        }
        for k, v in counts.head(15).items()
    ]

    return {
        "column": column,
        "count": n,
        "missing_count": missing_count,
        "missing_pct": round(missing_count / total_rows * 100, 2) if total_rows else 0.0,
        "unique_count": unique_count,
        "dominant_category": top_cat,
        "dominant_count": top_count,
        "dominant_pct": top_pct,
        "least_frequent_category": least_cat,
        "least_frequent_count": least_count,
        "least_frequent_pct": least_pct,
        "rare_categories_count": rare_count,
        "rare_categories": rare_categories,
        "imbalance_ratio": imbalance_ratio,
        "normalized_entropy": normalized_entropy,
        "inconsistent_labels": inconsistent_labels[:5],
        "distribution": distribution,
        "insufficient_data": n < 2,
    }


def analyze_datetime_column(
    df: pd.DataFrame,
    date_column: str,
    numeric_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Analyzes temporal span, cadence, missing periods, and trend trajectories safely."""
    if date_column not in df.columns:
        return {"error": f"Date column '{date_column}' not found"}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed = pd.to_datetime(df[date_column], format="mixed", errors="coerce")
        except TypeError:
            parsed = pd.to_datetime(df[date_column], errors="coerce")

    valid_idx = parsed.dropna().index
    if len(valid_idx) < 3:
        return {
            "date_column": date_column,
            "valid_count": int(len(valid_idx)),
            "insufficient_data": True,
            "reason": f"Fewer than 3 valid dates found in '{date_column}'.",
        }

    dt_series = parsed.loc[valid_idx].sort_values()
    earliest = dt_series.iloc[0]
    latest = dt_series.iloc[-1]
    span_days = int((latest - earliest).days)
    unique_dates = int(dt_series.nunique())

    if span_days >= 730:
        granularity = "QE"
        period_freq = "Q"
        granularity_label = "quarterly"
    elif span_days >= 60:
        granularity = "ME"
        period_freq = "M"
        granularity_label = "monthly"
    elif span_days >= 14:
        granularity = "W"
        period_freq = "W"
        granularity_label = "weekly"
    else:
        granularity = "D"
        period_freq = "D"
        granularity_label = "daily"

    counts_by_period = dt_series.dt.to_period(period_freq).value_counts().sort_index()
    missing_periods_count = 0
    if len(counts_by_period) >= 2:
        try:
            full_range = pd.period_range(counts_by_period.index.min(), counts_by_period.index.max(), freq=period_freq)
            missing_periods_count = max(0, int(len(full_range) - len(counts_by_period)))
        except Exception:
            missing_periods_count = 0

    unique_sorted = pd.Series(dt_series.unique()).sort_values()
    diffs = unique_sorted.diff().dropna().dt.total_seconds() / 86400.0
    unusual_gaps = 0
    median_interval_days = None
    if len(diffs) >= 3:
        med_gap = float(diffs.median())
        median_interval_days = round(med_gap, 2)
        if med_gap > 0:
            unusual_gaps = int((diffs > med_gap * 3.0).sum())

    metric_trends: List[Dict[str, Any]] = []
    candidate_nums = numeric_columns or [
        c for c in df.select_dtypes(include=[np.number]).columns if c != date_column
    ]
    for m_col in candidate_nums[:4]:
        if m_col not in df.columns:
            continue
        vals = pd.to_numeric(df.loc[valid_idx, m_col], errors="coerce")
        temp = pd.DataFrame({"__dt": parsed.loc[valid_idx], "__val": vals}).dropna()
        if len(temp) < 3:
            continue
        temp = temp.sort_values("__dt")
        grouped = temp.set_index("__dt")["__val"].resample(granularity).sum()
        grouped = grouped[temp.set_index("__dt")["__val"].resample(granularity).count() > 0]
        if len(grouped) < 2:
            continue
        first_val = float(grouped.iloc[0])
        last_val = float(grouped.iloc[-1])
        delta = last_val - first_val
        pct = round((delta / abs(first_val) * 100), 2) if abs(first_val) > 1e-9 else None

        rho, _ = stats.spearmanr(np.arange(len(grouped)), grouped.values)
        rho_val = _safe_float(rho, 3)

        peak_idx = grouped.idxmax()
        trough_idx = grouped.idxmin()

        metric_trends.append({
            "metric_column": m_col,
            "granularity": granularity_label,
            "periods_count": int(len(grouped)),
            "labels": [str(idx.date()) if hasattr(idx, "date") else str(idx) for idx in grouped.index],
            "values": [round(float(v), 2) for v in grouped.values],
            "first_period": str(grouped.index[0].date()),
            "last_period": str(grouped.index[-1].date()),
            "first_value": round(first_val, 2),
            "last_value": round(last_val, 2),
            "net_delta": round(delta, 2),
            "percent_change": pct,
            "trend_spearman_rho": rho_val,
            "peak_period": str(peak_idx.date()),
            "peak_value": round(float(grouped.max()), 2),
            "trough_period": str(trough_idx.date()),
            "trough_value": round(float(grouped.min()), 2),
            "seasonality_eligible": len(grouped) >= 12,
        })

    return {
        "date_column": date_column,
        "valid_count": int(len(valid_idx)),
        "unique_dates": unique_dates,
        "earliest_date": str(earliest.date()),
        "latest_date": str(latest.date()),
        "span_days": span_days,
        "granularity": granularity_label,
        "periods_observed": int(len(counts_by_period)),
        "missing_periods_count": missing_periods_count,
        "median_interval_days": median_interval_days,
        "unusual_gaps_count": unusual_gaps,
        "records_per_period": [
            {"period": str(p), "count": int(c)} for p, c in counts_by_period.items()
        ][:36],
        "metric_trends": metric_trends,
        "insufficient_data": False,
    }


def _cramers_v(x: pd.Series, y: pd.Series) -> Tuple[Optional[float], Optional[float], int]:
    """Computes bias-corrected Cramér's V and chi-square p-value for two categoricals."""
    sub = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(sub)
    if n < 10:
        return None, None, n
    table = pd.crosstab(sub["x"], sub["y"])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return None, None, n
    chi2, p_val, _, _ = stats.chi2_contingency(table)
    phi2 = chi2 / n
    r, k = table.shape
    phi2corr = max(0.0, phi2 - ((k - 1) * (r - 1)) / max(1, n - 1))
    rcorr = r - ((r - 1) ** 2) / max(1, n - 1)
    kcorr = k - ((k - 1) ** 2) / max(1, n - 1)
    denom = min((kcorr - 1), (rcorr - 1))
    if denom <= 0:
        return None, _safe_float(p_val, 5), n
    v = math.sqrt(phi2corr / denom)
    return _safe_float(v, 3), _safe_float(p_val, 5), n


def calculate_correlation(
    df: pd.DataFrame,
    col1: Optional[str] = None,
    col2: Optional[str] = None,
    numeric_columns: Optional[List[str]] = None,
    categorical_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculates Pearson, Spearman, Cramér's V, and multicollinearity with sample sizes and causal disclaimers."""
    if col1 and col2:
        if col1 not in df.columns or col2 not in df.columns:
            return {"error": "Specified columns not found in dataset."}
        s1 = pd.to_numeric(df[col1], errors="coerce")
        s2 = pd.to_numeric(df[col2], errors="coerce")
        pair = pd.DataFrame({col1: s1, col2: s2}).dropna()
        n = int(len(pair))
        if n < 4:
            return {
                "col1": col1,
                "col2": col2,
                "valid_observations": n,
                "insufficient_data": True,
                "reason": f"Need at least 4 paired non-null numeric observations (found {n}).",
            }
        if pair[col1].std() == 0 or pair[col2].std() == 0:
            return {
                "col1": col1,
                "col2": col2,
                "valid_observations": n,
                "insufficient_data": True,
                "reason": "Zero variance in at least one column prevents correlation computation.",
            }
        pr, pp = stats.pearsonr(pair[col1], pair[col2])
        sr, sp = stats.spearmanr(pair[col1], pair[col2])
        abs_r = max(abs(float(pr)), abs(float(sr)))
        strength = "strong" if abs_r >= 0.7 else ("moderate" if abs_r >= 0.4 else "weak")
        direction = "positive" if pr >= 0 else "negative"
        return {
            "col1": col1,
            "col2": col2,
            "pearson_r": _safe_float(pr, 4),
            "pearson_p_value": _safe_float(pp, 5),
            "spearman_rho": _safe_float(sr, 4),
            "spearman_p_value": _safe_float(sp, 5),
            "r_squared": _safe_float(float(pr) ** 2, 4),
            "valid_observations": n,
            "strength": strength,
            "direction": direction,
            "multicollinearity_flag": abs(float(pr)) >= 0.85,
            "limitations": "Correlation measures statistical association only and does not prove causation.",
        }

    num_cols = [
        c for c in (numeric_columns or df.select_dtypes(include=[np.number]).columns.tolist())
        if c in df.columns
    ]
    cat_cols = [
        c for c in (categorical_columns or [])
        if c in df.columns and 2 <= df[c].nunique(dropna=True) <= 15
    ]

    pearson_matrix: Dict[str, Dict[str, Optional[float]]] = {}
    spearman_matrix: Dict[str, Dict[str, Optional[float]]] = {}
    numerical_pairs: List[Dict[str, Any]] = []
    multicollinear_pairs: List[Dict[str, Any]] = []

    if len(num_cols) >= 2:
        num_df = df[num_cols].apply(pd.to_numeric, errors="coerce")
        p_corr = num_df.corr(method="pearson")
        s_corr = num_df.corr(method="spearman")

        for c in num_cols:
            pearson_matrix[c] = {idx: _safe_float(val, 4) for idx, val in p_corr[c].items()}
            spearman_matrix[c] = {idx: _safe_float(val, 4) for idx, val in s_corr[c].items()}

        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                c1, c2 = num_cols[i], num_cols[j]
                pair = num_df[[c1, c2]].dropna()
                n_obs = int(len(pair))
                if n_obs < 4 or pair[c1].std() == 0 or pair[c2].std() == 0:
                    continue
                pr, pp = stats.pearsonr(pair[c1], pair[c2])
                sr, sp = stats.spearmanr(pair[c1], pair[c2])
                dominant_r = float(pr) if abs(float(pr)) >= abs(float(sr)) else float(sr)
                abs_r = abs(dominant_r)
                if abs_r >= 0.35:
                    strength = "strong" if abs_r >= 0.7 else "moderate"
                    direction = "positive" if dominant_r > 0 else "negative"
                    method_note = "Pearson & Spearman" if abs(abs(float(pr)) - abs(float(sr))) < 0.15 else (
                        "Spearman (monotonic)" if abs(float(sr)) > abs(float(pr)) else "Pearson (linear)"
                    )
                    entry = {
                        "col1": c1,
                        "col2": c2,
                        "correlation": _safe_float(pr, 3),
                        "pearson_r": _safe_float(pr, 4),
                        "pearson_p_value": _safe_float(pp, 5),
                        "spearman_rho": _safe_float(sr, 4),
                        "spearman_p_value": _safe_float(sp, 5),
                        "r_squared": _safe_float(float(pr) ** 2, 3),
                        "valid_observations": n_obs,
                        "strength": strength,
                        "direction": direction,
                        "recommended_method": method_note,
                        "multicollinearity_risk": abs(float(pr)) >= 0.85,
                    }
                    numerical_pairs.append(entry)
                    if abs(float(pr)) >= 0.85:
                        multicollinear_pairs.append(entry)

        numerical_pairs.sort(key=lambda x: max(abs(x["pearson_r"] or 0), abs(x["spearman_rho"] or 0)), reverse=True)

    categorical_associations: List[Dict[str, Any]] = []
    for i in range(min(len(cat_cols), 8)):
        for j in range(i + 1, min(len(cat_cols), 8)):
            c1, c2 = cat_cols[i], cat_cols[j]
            v, p_val, n_obs = _cramers_v(df[c1], df[c2])
            if v is not None and v >= 0.2 and (p_val is None or p_val < 0.05):
                categorical_associations.append({
                    "col1": c1,
                    "col2": c2,
                    "cramers_v": v,
                    "p_value": p_val,
                    "valid_observations": n_obs,
                    "strength": "strong" if v >= 0.5 else "moderate",
                })
    categorical_associations.sort(key=lambda x: x["cramers_v"], reverse=True)

    return {
        "pearson_matrix": pearson_matrix,
        "spearman_matrix": spearman_matrix,
        "notable_correlations": numerical_pairs,
        "categorical_associations": categorical_associations[:8],
        "multicollinear_pairs": multicollinear_pairs,
    }


def compare_groups(df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
    """One-way ANOVA F-test & rich per-group breakdown for numeric vs categorical relationship."""
    if group_col not in df.columns or value_col not in df.columns:
        return {"error": "One of the columns was not found"}

    vals = pd.to_numeric(df[value_col], errors="coerce")
    work = pd.DataFrame({group_col: df[group_col], value_col: vals}).dropna()
    if work.empty:
        return {"error": "No valid pairs for group comparison"}

    grouped_series = [(name, g[value_col].values) for name, g in work.groupby(group_col) if len(g) >= 2]
    if len(grouped_series) < 2:
        return {"error": "Need at least two groups with more than one value"}

    try:
        arrays = [arr for _, arr in grouped_series]
        f_stat, p_value = stats.f_oneway(*arrays)
    except Exception as exc:
        return {"error": f"ANOVA failed: {exc}"}

    agg_df = (
        work.groupby(group_col)[value_col]
        .agg(["count", "sum", "mean", "median", "std", "min", "max"])
        .reset_index()
        .sort_values(by="mean", ascending=False)
    )
    total_sum = float(work[value_col].sum())
    group_rows = []
    for _, r in agg_df.iterrows():
        s_val = float(r["sum"])
        group_rows.append({
            "group": str(r[group_col]),
            "count": int(r["count"]),
            "sum": _safe_float(s_val, 2),
            "share_pct": round((s_val / total_sum * 100), 2) if abs(total_sum) > 1e-9 else None,
            "mean": _safe_float(r["mean"], 2),
            "median": _safe_float(r["median"], 2),
            "std": _safe_float(r["std"], 2) or 0.0,
            "min": _safe_float(r["min"], 2),
            "max": _safe_float(r["max"], 2),
        })

    grand_mean = float(work[value_col].mean())
    ss_between = sum(len(g) * (float(np.mean(g)) - grand_mean) ** 2 for _, g in grouped_series)
    ss_total = float(np.sum((work[value_col].values - grand_mean) ** 2))
    eta_sq = round(ss_between / ss_total, 4) if ss_total > 0 else 0.0

    sig = bool(math.isfinite(float(p_value)) and float(p_value) < 0.05)

    return {
        "group_column": group_col,
        "value_column": value_col,
        "groups": int(len(grouped_series)),
        "valid_observations": int(len(work)),
        "f_statistic": to_python(f_stat),
        "p_value": to_python(p_value),
        "eta_squared": eta_sq,
        "significant_at_0_05": sig,
        "group_breakdown": group_rows,
        "top_group": group_rows[0] if group_rows else None,
        "bottom_group": group_rows[-1] if group_rows else None,
    }


def detect_outliers(
    df: pd.DataFrame,
    column: Optional[str] = None,
    numeric_columns: Optional[List[str]] = None,
    method: str = "auto",
) -> Dict[str, Any]:
    """
    Detects candidate anomalies safely using IQR, Z-score, Modified Z-score (MAD),
    and Isolation Forest (multivariate) without modifying or deleting any rows.
    """
    if column:
        if column not in df.columns:
            return {"error": f"Column '{column}' not found"}
        s = pd.to_numeric(df[column], errors="coerce").dropna()
        n = len(s)
        if n < 4:
            return {
                "column": column,
                "method": "none",
                "flagged_count": 0,
                "anomalies": [],
                "insufficient_data": True,
                "note": f"Fewer than 4 valid numeric observations in '{column}'; candidate anomaly scan skipped.",
            }

        q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
        iqr = q3 - q1
        mean_val = float(s.mean())
        std_val = float(s.std(ddof=1)) if n > 1 else 0.0
        skew_val = abs(float(s.skew())) if n > 2 and std_val > 0 else 0.0

        chosen = method
        if chosen == "auto":
            if iqr > 0:
                chosen = "modified_zscore" if skew_val >= 2.0 else "iqr"
            elif std_val > 0:
                chosen = "zscore"
            else:
                chosen = "iqr"

        anomalies: List[Dict[str, Any]] = []
        threshold_desc = ""
        if chosen == "zscore" and std_val > 0:
            z = np.abs((s - mean_val) / std_val)
            mask = z > 3.0
            threshold_desc = "|z| > 3.0"
            anomalies = [
                {"index": int(idx), "value": to_python(val), "score": _safe_float(z.loc[idx], 3)}
                for idx, val in s[mask].items()
            ]
        elif chosen == "modified_zscore":
            med = float(s.median())
            mad = float(np.median(np.abs(s.values - med)))
            if mad > 0:
                mod_z = 0.6745 * np.abs(s - med) / mad
                mask = mod_z > 3.5
                threshold_desc = "Modified Z-score (MAD) > 3.5"
                anomalies = [
                    {"index": int(idx), "value": to_python(val), "score": _safe_float(mod_z.loc[idx], 3)}
                    for idx, val in s[mask].items()
                ]
            else:
                chosen = "iqr"

        if chosen == "iqr":
            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr
            threshold_desc = f"[{_safe_float(low, 2)}, {_safe_float(high, 2)}] (1.5 * IQR)"
            if iqr > 0:
                mask = (s < low) | (s > high)
                anomalies = [
                    {"index": int(idx), "value": to_python(val), "bound_exceeded": "upper" if val > high else "lower"}
                    for idx, val in s[mask].items()
                ]

        return {
            "column": column,
            "method": chosen,
            "threshold": threshold_desc,
            "valid_observations": n,
            "flagged_count": len(anomalies),
            "flagged_pct": round(len(anomalies) / n * 100, 2) if n else 0.0,
            "anomalies": anomalies[:100],
            "note": "Flagged records are statistical candidate anomalies and may represent genuine extreme values rather than errors.",
        }

    num_cols = [c for c in (numeric_columns or df.select_dtypes(include=[np.number]).columns.tolist()) if c in df.columns]
    univariate_results = [detect_outliers(df, column=c) for c in num_cols]
    multivariate = None

    if len(num_cols) >= 2 and len(df) >= 25:
        try:
            from sklearn.ensemble import IsolationForest

            sub = df[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
            if len(sub) >= 25 and sub.nunique().min() > 1:
                iso = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
                preds = iso.fit_predict(sub.values)
                flagged_idx = sub.index[preds == -1].tolist()
                multivariate = {
                    "method": "IsolationForest",
                    "columns_evaluated": num_cols,
                    "contamination": 0.05,
                    "valid_observations": int(len(sub)),
                    "flagged_count": int(len(flagged_idx)),
                    "flagged_pct": round(len(flagged_idx) / len(sub) * 100, 2),
                    "flagged_indices": [int(i) for i in flagged_idx[:50]],
                    "note": "Multivariate Isolation Forest detects unusual combinations across columns; flagged rows are candidate anomalies.",
                }
        except Exception:
            multivariate = None

    return {
        "univariate": univariate_results,
        "multivariate": multivariate,
    }


def detect_anomalies_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> Dict[str, Any]:
    """Backward-compatible Z-score outlier scanner."""
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty or series.std() == 0:
        return {"column": column, "anomalies": [], "threshold": threshold}

    z = np.abs((series - series.mean()) / series.std())
    mask = z > threshold
    anomalies = [
        {"index": int(idx), "value": to_python(val), "z_score": to_python(z.loc[idx])}
        for idx, val in series[mask].items()
    ]
    return {"column": column, "threshold": threshold, "anomalies": anomalies[:100]}
