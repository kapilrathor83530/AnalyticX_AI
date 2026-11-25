import math
from typing import Any, Dict

import numpy as np
import pandas as pd


def to_python(value: Any) -> Any:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def infer_column_type(series: pd.Series) -> str:
    """Infers column analytical type intelligently beyond raw pandas dtypes."""
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    from app.analytics.data_understanding import understand_dataset

    col_name = str(series.name or "col")
    res = understand_dataset(pd.DataFrame({col_name: series}), sanitize=False)
    cols = res["profile"].get("columns", [])
    if cols:
        return cols[0].get("inferred_type", "categorical")
    return "categorical"


def profile_dataframe(df: pd.DataFrame, dataset_name: str = "Dataset") -> Dict[str, Any]:
    """Generates full universal dataset profile using the shared Data Understanding Engine."""
    from app.analytics.data_understanding import understand_dataset

    result = understand_dataset(df, dataset_name=dataset_name, sanitize=True)
    return result["profile"]
