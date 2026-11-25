"""Robust Data Cleaning & Transformation Execution Engine for Analyticx AI."""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def apply_cleaning_action(df: pd.DataFrame, action: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Applies a validated cleaning action to df.
    Returns (transformed_df, audit_summary).
    """
    action_type = action.get("action_type") or action.get("type") or ""
    params = action.get("parameters") or action.get("config") or {}
    column = params.get("column") or action.get("column")
    strategy = params.get("strategy") or action.get("strategy") or ""

    rows_before = int(df.shape[0])
    cols_before = int(df.shape[1])
    result = df.copy()
    affected_count = 0
    description = ""

    # 1. Missing Values Imputation
    if action_type in ("impute_missing", "missing_values"):
        if column not in result.columns:
            raise ValueError(f"Column '{column}' not found in dataset")
        s = result[column]
        missing_mask = s.isna()
        affected_count = int(missing_mask.sum())

        if affected_count > 0:
            if strategy == "median":
                if pd.api.types.is_numeric_dtype(s):
                    med = float(s.median())
                    result[column] = s.fillna(med)
                    description = f"Filled {affected_count} missing value(s) in '{column}' with median ({round(med, 2)})"
                else:
                    mode_val = s.mode().iloc[0] if not s.mode().empty else "Unknown"
                    result[column] = s.fillna(mode_val)
                    description = f"Filled {affected_count} missing value(s) in '{column}' with mode ('{mode_val}')"

            elif strategy == "mean":
                if pd.api.types.is_numeric_dtype(s):
                    mean_val = float(s.mean())
                    result[column] = s.fillna(mean_val)
                    description = f"Filled {affected_count} missing value(s) in '{column}' with mean ({round(mean_val, 2)})"
                else:
                    mode_val = s.mode().iloc[0] if not s.mode().empty else "Unknown"
                    result[column] = s.fillna(mode_val)
                    description = f"Filled {affected_count} missing value(s) in '{column}' with mode ('{mode_val}')"

            elif strategy == "mode":
                mode_val = s.mode().iloc[0] if not s.mode().empty else "Unknown"
                result[column] = s.fillna(mode_val)
                description = f"Filled {affected_count} missing value(s) in '{column}' with mode ('{mode_val}')"

            elif strategy == "unknown":
                result[column] = s.fillna("Unknown")
                description = f"Filled {affected_count} missing value(s) in '{column}' with 'Unknown'"

            elif strategy == "constant":
                custom_val = params.get("constant_value")
                if custom_val is None:
                    custom_val = 0 if pd.api.types.is_numeric_dtype(s) else "Unknown"
                if pd.api.types.is_numeric_dtype(s):
                    try:
                        custom_val = float(custom_val)
                    except (ValueError, TypeError):
                        custom_val = 0
                result[column] = s.fillna(custom_val)
                description = f"Filled {affected_count} missing value(s) in '{column}' with constant ({custom_val})"

            elif strategy == "ffill":
                result[column] = s.ffill()
                description = f"Forward-filled {affected_count} missing value(s) in '{column}'"

            elif strategy == "bfill":
                result[column] = s.bfill()
                description = f"Backward-filled {affected_count} missing value(s) in '{column}'"

            elif strategy == "drop_rows":
                result = result.dropna(subset=[column])
                description = f"Dropped {affected_count} row(s) with missing values in '{column}'"

            elif strategy == "keep":
                description = f"Kept missing values in '{column}' unchanged"

    # 2. Outlier Handling
    elif action_type in ("handle_outliers", "outliers"):
        if column not in result.columns:
            raise ValueError(f"Column '{column}' not found in dataset")
        s = result[column].dropna()
        if pd.api.types.is_numeric_dtype(s) and len(s) >= 4:
            q1 = float(s.quantile(0.25))
            q3 = float(s.quantile(0.75))
            iqr = q3 - q1
            lower_bound = float(params.get("lower", q1 - 1.5 * iqr))
            upper_bound = float(params.get("upper", q3 + 1.5 * iqr))

            outlier_mask = (result[column] < lower_bound) | (result[column] > upper_bound)
            affected_count = int(outlier_mask.sum())

            if strategy == "winsorize":
                result[column] = result[column].clip(lower=lower_bound, upper=upper_bound)
                description = f"Capped {affected_count} outlier(s) in '{column}' to range [{round(lower_bound, 2)}, {round(upper_bound, 2)}]"

            elif strategy == "flag":
                flag_col = f"is_outlier_{column}"
                result[flag_col] = outlier_mask
                description = f"Flagged {affected_count} outlier(s) in new indicator column '{flag_col}'"

            elif strategy == "drop_rows":
                result = result[~outlier_mask]
                description = f"Removed {affected_count} row(s) with extreme values in '{column}'"

            elif strategy == "keep":
                description = f"Kept all outlier values in '{column}' unchanged"

    # 3. Duplicate Rows Removal
    elif action_type in ("remove_duplicates", "duplicates"):
        subset = params.get("subset")
        if subset:
            subset = [c for c in subset if c in result.columns]
        dup_mask = result.duplicated(subset=subset or None, keep="first")
        affected_count = int(dup_mask.sum())
        if affected_count > 0:
            result = result.drop_duplicates(subset=subset or None, keep="first")
            description = f"Removed {affected_count} duplicate row(s)" + (f" on subset {subset}" if subset else "")
        else:
            description = "No duplicate rows found to remove"

    # 4. Text & Whitespace Cleaning
    elif action_type in ("clean_text", "formatting"):
        if column not in result.columns:
            raise ValueError(f"Column '{column}' not found in dataset")
        s = result[column]
        if strategy == "strip_whitespace":
            result[column] = s.astype(str).str.strip().replace({"nan": None, "None": None})
            description = f"Stripped leading and trailing whitespace from '{column}'"
            affected_count = int(rows_before)

        elif strategy == "lowercase":
            result[column] = s.astype(str).str.strip().str.lower().replace({"nan": None, "None": None})
            description = f"Normalized '{column}' to lowercase"
            affected_count = int(rows_before)

        elif strategy == "titlecase":
            result[column] = s.astype(str).str.strip().str.title().replace({"nan": None, "None": None})
            description = f"Normalized '{column}' to Title Case"
            affected_count = int(rows_before)

    # 5. Type Conversion
    elif action_type == "convert_type":
        if column not in result.columns:
            raise ValueError(f"Column '{column}' not found in dataset")
        target_type = params.get("target_type", "numeric")
        if target_type == "numeric":
            result[column] = pd.to_numeric(result[column], errors="coerce")
            description = f"Converted '{column}' to numeric type"
        elif target_type == "datetime":
            result[column] = pd.to_datetime(result[column], errors="coerce")
            description = f"Converted '{column}' to datetime type"
        elif target_type == "string":
            result[column] = result[column].astype(str)
            description = f"Converted '{column}' to text/string"
        elif target_type == "boolean":
            result[column] = result[column].astype("boolean")
            description = f"Converted '{column}' to boolean"
        affected_count = int(rows_before)

    # 6. Drop Column
    elif action_type == "drop_column":
        if column in result.columns:
            result = result.drop(columns=[column])
            description = f"Dropped column '{column}' from dataset"
            affected_count = int(rows_before)

    # 7. Rename Column
    elif action_type == "rename_column":
        new_name = params.get("new_name") or params.get("target_name") or strategy
        if column not in result.columns:
            raise ValueError(f"Column '{column}' not found in dataset")
        if not new_name:
            raise ValueError("New column name is required")
        clean_new_name = str(new_name).strip()
        result = result.rename(columns={column: clean_new_name})
        description = f"Renamed column '{column}' to '{clean_new_name}'"
        affected_count = int(rows_before)

    audit_summary = {
        "action_type": action_type,
        "column": column,
        "strategy": strategy,
        "parameters": params,
        "rows_before": rows_before,
        "rows_after": int(result.shape[0]),
        "columns_before": cols_before,
        "columns_after": int(result.shape[1]),
        "affected_records": affected_count,
        "description": description or f"Applied {action_type} on '{column or 'dataset'}'",
    }
    return result, audit_summary
