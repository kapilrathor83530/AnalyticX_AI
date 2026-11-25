from typing import Any, Dict, List

import numpy as np
import pandas as pd


def drop_missing(df: pd.DataFrame, columns: List[str], how: str = "any") -> pd.DataFrame:
    cols = [c for c in columns if c in df.columns]
    if how == "all":
        return df.dropna(subset=cols, how="all")
    return df.dropna(subset=cols, how="any")


def impute_missing(df: pd.DataFrame, column: str, strategy: str) -> pd.DataFrame:
    if column not in df.columns:
        return df
    result = df.copy()
    series = result[column]

    if strategy == "mean" and pd.api.types.is_numeric_dtype(series):
        result[column] = series.fillna(series.mean())
    elif strategy == "median" and pd.api.types.is_numeric_dtype(series):
        result[column] = series.fillna(series.median())
    elif strategy == "mode":
        mode = series.mode()
        if not mode.empty:
            result[column] = series.fillna(mode.iloc[0])
    elif strategy == "ffill":
        result[column] = series.ffill()
    elif strategy == "bfill":
        result[column] = series.bfill()
    elif strategy == "drop":
        result = result.dropna(subset=[column])
    return result


def convert_type(df: pd.DataFrame, column: str, target_type: str) -> pd.DataFrame:
    if column not in df.columns:
        return df
    result = df.copy()
    try:
        if target_type == "numeric":
            result[column] = pd.to_numeric(result[column], errors="coerce")
        elif target_type == "datetime":
            result[column] = pd.to_datetime(result[column], errors="coerce")
        elif target_type == "string":
            result[column] = result[column].astype(str)
        elif target_type == "boolean":
            result[column] = result[column].astype("boolean")
    except Exception:
        pass
    return result


def remove_duplicates(df: pd.DataFrame, subset: List[str] | None = None) -> pd.DataFrame:
    if subset:
        cols = [c for c in subset if c in df.columns]
        return df.drop_duplicates(subset=cols or None)
    return df.drop_duplicates()


def drop_outliers_iqr(df: pd.DataFrame, column: str, factor: float = 1.5) -> pd.DataFrame:
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return df
    series = df[column]
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    return df[(series >= lower) & (series <= upper)]


def drop_outliers_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return df
    series = df[column]
    if series.std() == 0 or series.std() is None:
        return df
    z = np.abs((series - series.mean()) / series.std())
    return df[z <= threshold]


def normalize_categories(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return df
    result = df.copy()
    result[column] = result[column].astype(str).str.strip().str.lower().replace({"nan": None})
    return result


def apply_transformations(df: pd.DataFrame, transformations: List[Dict[str, Any]]) -> pd.DataFrame:
    result = df.copy()
    for t in transformations:
        t_type = t.get("type")
        params = t.get("parameters", {}) or {}

        if t_type == "drop_missing":
            result = drop_missing(result, params.get("columns", []), params.get("how", "any"))
        elif t_type == "impute_missing":
            result = impute_missing(result, params.get("column", ""), params.get("strategy", "mean"))
        elif t_type == "convert_type":
            result = convert_type(result, params.get("column", ""), params.get("target_type", "numeric"))
        elif t_type == "remove_duplicates":
            result = remove_duplicates(result, params.get("subset"))
        elif t_type == "drop_outliers_iqr":
            result = drop_outliers_iqr(result, params.get("column", ""), params.get("factor", 1.5))
        elif t_type == "drop_outliers_zscore":
            result = drop_outliers_zscore(result, params.get("column", ""), params.get("threshold", 3.0))
        elif t_type == "normalize_categories":
            result = normalize_categories(result, params.get("column", ""))

    return result
