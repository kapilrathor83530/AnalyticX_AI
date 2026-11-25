"""Universal Dataset Validation, Type Inference, and Semantic Understanding Engine.

Transforms any tabular DataFrame into:
1. A non-destructive validation report (duplicates, empty rows/cols, duplicate headers, warnings).
2. A normalized working DataFrame (safely parsing currency, percentage, numeric strings,
   and date/timestamp strings while strictly protecting identifiers/leading-zero codes).
3. Rich per-column semantic metadata and dataset-level structural summaries.
"""
from __future__ import annotations

import re
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_CURRENCY_RE = re.compile(r"^\s*[-+]?\s*(?:[₹$€£¥]|rs\.?|inr|usd|eur|gbp)\s*[-+]?\s*[\d,]+(?:\.\d+)?\s*$|^\s*\(\s*[₹$€£¥]?\s*[\d,]+(?:\.\d+)?\s*\)\s*$", re.IGNORECASE)
_PERCENT_RE = re.compile(r"^\s*[-+]?\s*[\d,]+(?:\.\d+)?\s*%\s*$")
_LEADING_ZERO_ID_RE = re.compile(r"^0\d{2,}$")
_NUMERIC_STR_RE = re.compile(r"^\s*[-+]?\s*[\d,]+(?:\.\d+)?\s*$")
_HAS_DATE_TOKEN_RE = re.compile(r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|q[1-4]\s*[-/]?\s*\d{4}|\d{4}\s*[-/]?\s*q[1-4]|t\d{2}:\d{2})", re.IGNORECASE)
_QUARTER_RE = re.compile(r"^(?:(\d{4})[-/\s]?Q([1-4])|Q([1-4])[-/\s]?(\d{4}))$", re.IGNORECASE)

_ID_COL_HINTS = {
    "id", "uuid", "guid", "sku", "code", "roll", "roll_no", "roll_number", "reg_no",
    "registration", "serial", "sr_no", "sno", "index", "key", "account_no", "account_id",
    "invoice_id", "invoice_no", "order_id", "order_no", "customer_id", "emp_id",
    "employee_id", "student_id", "patient_id", "transaction_id", "txn_id", "phone",
    "mobile", "zip", "zipcode", "postal", "postal_code", "pincode", "ssn",
}

_GEO_COL_HINTS = {
    "country": "country",
    "nation": "country",
    "country_code": "country",
    "iso_code": "country",
    "state": "state",
    "province": "state",
    "city": "city",
    "town": "city",
    "district": "city",
    "region": "region",
    "territory": "region",
    "continent": "region",
    "zone": "region",
    "area": "region",
    "location": "region",
    "latitude": "latitude",
    "lat": "latitude",
    "longitude": "longitude",
    "lon": "longitude",
    "lng": "longitude",
}

_FINANCIAL_HINTS = {
    "revenue", "sales", "profit", "cost", "price", "amount", "budget", "spend",
    "salary", "income", "wage", "pay", "margin", "tax", "fee", "discount", "total",
    "expense", "turnover", "ebitda", "arr", "mrr", "ltv", "cac",
}

_BOOL_TRUE = {"true", "yes", "y", "t"}
_BOOL_FALSE = {"false", "no", "n", "f"}


def _col_name_matches_id(col_name: str) -> bool:
    low = str(col_name).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", low).strip("_")
    if normalized in _ID_COL_HINTS:
        return True
    tokens = set(normalized.split("_"))
    if normalized.endswith(("_id", "_no", "_num", "_code", "_key", "_sku")) or "roll" in tokens or "uuid" in tokens:
        return True
    return False


def _detect_geo_role(col_name: str) -> Optional[str]:
    low = str(col_name).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", low).strip("_")
    if normalized in _GEO_COL_HINTS:
        return _GEO_COL_HINTS[normalized]
    for token in normalized.split("_"):
        if token in _GEO_COL_HINTS:
            return _GEO_COL_HINTS[token]
    return None


def _detect_financial_hint(col_name: str) -> bool:
    low = str(col_name).strip().lower()
    tokens = set(re.sub(r"[^a-z0-9]+", "_", low).strip("_").split("_"))
    return bool(tokens & _FINANCIAL_HINTS)


def _strip_numeric_formatting(val: str) -> Optional[float]:
    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "null", "na", "n/a", "-", "--"}:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    s = re.sub(r"^(?:rs\.?|inr|usd|eur|gbp)\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[₹$€£¥%$,\s]", "", s)
    if not s:
        return None
    try:
        num = float(s)
        return -num if negative else num
    except ValueError:
        return None


def _parse_quarter_or_datetime(series: pd.Series) -> Tuple[Optional[pd.Series], Optional[str]]:
    """Safely attempts datetime conversion on string series with date-like tokens."""
    non_null = series.dropna().astype(str).str.strip()
    non_null = non_null[non_null != ""]
    if len(non_null) == 0:
        return None, None

    sample = non_null.head(100)
    # Handle Quarter strings like 2025-Q1 or Q1 2025
    quarter_hits = sample.apply(lambda x: bool(_QUARTER_RE.match(x))).mean()
    if quarter_hits >= 0.8:
        def _q_to_date(text: Any) -> Any:
            if pd.isna(text):
                return pd.NaT
            m = _QUARTER_RE.match(str(text).strip())
            if not m:
                return pd.NaT
            if m.group(1):
                year, q = int(m.group(1)), int(m.group(2))
            else:
                q, year = int(m.group(3)), int(m.group(4))
            month = (q - 1) * 3 + 1
            return pd.Timestamp(year=year, month=month, day=1)

        parsed = series.apply(_q_to_date)
        return pd.to_datetime(parsed, errors="coerce"), "quarter"

    date_like_ratio = sample.apply(lambda x: bool(_HAS_DATE_TOKEN_RE.search(x))).mean()
    if date_like_ratio < 0.7:
        return None, None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed_sample = pd.to_datetime(sample, format="mixed", errors="coerce")
        except TypeError:
            parsed_sample = pd.to_datetime(sample, errors="coerce")

    valid_ratio = parsed_sample.notna().mean()
    if valid_ratio < 0.8:
        return None, None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed_full = pd.to_datetime(series, format="mixed", errors="coerce")
        except TypeError:
            parsed_full = pd.to_datetime(series, errors="coerce")

    if parsed_full.notna().sum() == 0:
        return None, None
    return parsed_full, "datetime"


def validate_and_sanitize_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validates structural integrity and cleans empty phantom columns/rows and duplicate column names."""
    warnings_list: List[str] = []
    errors_list: List[str] = []

    if df is None or df.shape[1] == 0:
        return pd.DataFrame(), {
            "valid": False,
            "errors": ["Dataset has no columns."],
            "warnings": [],
            "duplicate_columns": [],
            "empty_columns": [],
            "empty_rows_count": 0,
        }

    work = df.copy()

    # Track and drop completely blank rows
    all_blank_rows = int(work.isna().all(axis=1).sum())
    if all_blank_rows > 0:
        work = work.dropna(how="all").reset_index(drop=True)
        warnings_list.append(f"Removed {all_blank_rows} completely blank row(s) during validation.")

    # Track duplicate raw column names and disambiguate cleanly
    raw_cols = [str(c).strip() if str(c).strip() else f"Column_{i + 1}" for i, c in enumerate(work.columns)]
    seen_counts: Dict[str, int] = {}
    dup_cols: List[str] = []
    unique_cols: List[str] = []
    for col in raw_cols:
        if col in seen_counts:
            seen_counts[col] += 1
            if col not in dup_cols:
                dup_cols.append(col)
            unique_cols.append(f"{col}_{seen_counts[col]}")
        else:
            seen_counts[col] = 1
            unique_cols.append(col)

    work.columns = unique_cols
    if dup_cols:
        warnings_list.append(f"Detected duplicate column names ({', '.join(dup_cols)}); disambiguated suffixes applied.")

    # Identify completely empty columns
    empty_cols = [str(c) for c in work.columns if work[c].dropna().shape[0] == 0]
    unnamed_empty = [c for c in empty_cols if c.lower().startswith("unnamed:")]
    if unnamed_empty:
        work = work.drop(columns=unnamed_empty)
        warnings_list.append(f"Dropped {len(unnamed_empty)} empty unnamed column(s): {', '.join(unnamed_empty[:5])}.")
        empty_cols = [c for c in empty_cols if c not in unnamed_empty]
    if empty_cols:
        warnings_list.append(f"{len(empty_cols)} column(s) contain 100% missing values: {', '.join(empty_cols[:5])}.")

    if work.shape[0] == 0:
        errors_list.append("Dataset contains zero data rows after excluding blank rows.")

    return work, {
        "valid": len(errors_list) == 0,
        "errors": errors_list,
        "warnings": warnings_list,
        "duplicate_columns": dup_cols,
        "empty_columns": empty_cols,
        "empty_rows_count": all_blank_rows,
    }


def understand_dataset(
    df: pd.DataFrame,
    dataset_name: str = "Dataset",
    sanitize: bool = True,
) -> Dict[str, Any]:
    """
    Performs universal data profiling, intelligent type & semantic inference,
    and returns both rich metadata and a safely normalized working DataFrame.
    """
    from app.analytics.profiling import to_python

    if sanitize:
        work_df, validation = validate_and_sanitize_dataframe(df)
    else:
        work_df = df.copy()
        validation = {"valid": not work_df.empty, "errors": [], "warnings": [], "duplicate_columns": [], "empty_columns": [], "empty_rows_count": 0}

    norm_df = work_df.copy()
    total_rows = int(norm_df.shape[0])
    total_cols = int(norm_df.shape[1])
    total_cells = total_rows * total_cols
    memory_bytes = int(norm_df.memory_usage(deep=True).sum())

    columns_meta: List[Dict[str, Any]] = []
    numerical_columns: List[str] = []
    categorical_columns: List[str] = []
    boolean_columns: List[str] = []
    datetime_columns: List[str] = []
    identifier_columns: List[str] = []
    constant_columns: List[str] = []
    high_cardinality_columns: List[str] = []
    geographic_columns: List[str] = []
    text_columns: List[str] = []
    empty_columns: List[str] = []

    for col in list(norm_df.columns):
        col_name = str(col)
        s = norm_df[col]
        raw_dtype = str(s.dtype)
        n_missing = int(s.isna().sum())
        missing_pct = round((n_missing / total_rows * 100), 2) if total_rows else 0.0
        non_null = s.dropna()
        n_valid = int(len(non_null))
        n_unique = int(non_null.nunique()) if n_valid > 0 else 0
        samples = [to_python(v) for v in non_null.head(5).tolist()]

        detected_type = "categorical"
        semantic_type = "attribute"
        format_hint: Optional[str] = None
        is_identifier = False
        is_constant = False
        is_high_cardinality = False
        analysis_eligible = True
        geo_role = _detect_geo_role(col_name)

        # 1. Empty column
        if n_valid == 0:
            detected_type = "empty"
            semantic_type = "empty"
            analysis_eligible = False
            empty_columns.append(col_name)

        # 2. Constant / zero variance
        elif n_unique <= 1:
            is_constant = True
            constant_columns.append(col_name)
            if pd.api.types.is_bool_dtype(s):
                detected_type = "boolean"
            elif pd.api.types.is_numeric_dtype(s):
                detected_type = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(s):
                detected_type = "datetime"
            else:
                detected_type = "categorical"
            semantic_type = "constant"
            analysis_eligible = False

        # 3. Native Boolean
        elif pd.api.types.is_bool_dtype(s):
            detected_type = "boolean"
            semantic_type = "boolean_flag"
            boolean_columns.append(col_name)

        # 4. Native Datetime
        elif pd.api.types.is_datetime64_any_dtype(s):
            detected_type = "datetime"
            semantic_type = "temporal"
            format_hint = "datetime"
            datetime_columns.append(col_name)

        # 5. Native Numeric
        elif pd.api.types.is_numeric_dtype(s):
            name_is_id = _col_name_matches_id(col_name)
            is_int_like = pd.api.types.is_integer_dtype(s) or bool((non_null % 1 == 0).all())
            unique_ratio = n_unique / max(1, n_valid)

            # Protect numeric IDs from being aggregated as business metrics
            if name_is_id and (unique_ratio >= 0.7 or is_int_like):
                is_identifier = True
                detected_type = "identifier"
                semantic_type = "identifier"
                analysis_eligible = False
                identifier_columns.append(col_name)
            else:
                detected_type = "numeric"
                numerical_columns.append(col_name)
                if geo_role in ("latitude", "longitude"):
                    semantic_type = f"geo_{geo_role}"
                    geographic_columns.append(col_name)
                elif _detect_financial_hint(col_name):
                    semantic_type = "financial_measure"
                elif is_int_like and set(non_null.unique()).issubset({0, 1}) and any(
                    k in col_name.lower() for k in ("is_", "has_", "flag", "churn", "attrition", "active", "target", "status")
                ):
                    semantic_type = "binary_indicator"
                elif any(k in col_name.lower() for k in ("year", "yr")) and non_null.min() >= 1900 and non_null.max() <= 2100:
                    semantic_type = "temporal_year"
                    format_hint = "year"
                elif any(k in col_name.lower() for k in ("pct", "percent", "rate", "ratio", "score", "sgpa", "cgpa", "gpa", "marks")):
                    semantic_type = "score_or_rate"
                else:
                    semantic_type = "continuous_measure" if pd.api.types.is_float_dtype(s) else "count_or_measure"

        # 6. Object / String columns -> test Leading-zero ID, Boolean text, Datetime, Numeric/Currency/Percent, Geo, Categorical, Text
        else:
            str_vals = non_null.astype(str).str.strip()
            sample_str = str_vals.head(200)

            # 6a. Leading-zero ID protection ("001245", "09130")
            lz_ratio = sample_str.apply(lambda x: bool(_LEADING_ZERO_ID_RE.match(x))).mean()
            if lz_ratio >= 0.5:
                is_identifier = True
                detected_type = "identifier"
                semantic_type = "leading_zero_identifier"
                format_hint = "leading_zero_id"
                analysis_eligible = False
                identifier_columns.append(col_name)
            else:
                # 6b. Boolean string detection
                lower_set = set(str_vals.str.lower().unique())
                if lower_set.issubset(_BOOL_TRUE | _BOOL_FALSE) and len(lower_set) <= 2:
                    detected_type = "boolean"
                    semantic_type = "boolean_flag"
                    boolean_columns.append(col_name)
                    norm_df[col] = s.map(
                        lambda v: True if pd.notna(v) and str(v).strip().lower() in _BOOL_TRUE else (
                            False if pd.notna(v) and str(v).strip().lower() in _BOOL_FALSE else np.nan
                        )
                    )
                else:
                    # 6c. Datetime string detection
                    parsed_dt, dt_hint = _parse_quarter_or_datetime(s)
                    if parsed_dt is not None:
                        detected_type = "datetime"
                        semantic_type = "temporal"
                        format_hint = dt_hint
                        datetime_columns.append(col_name)
                        norm_df[col] = parsed_dt
                    else:
                        # 6d. Currency / Percentage / Numeric strings
                        curr_ratio = sample_str.apply(lambda x: bool(_CURRENCY_RE.match(x))).mean()
                        pct_ratio = sample_str.apply(lambda x: bool(_PERCENT_RE.match(x))).mean()
                        num_ratio = sample_str.apply(lambda x: bool(_NUMERIC_STR_RE.match(x))).mean()

                        if (curr_ratio >= 0.7 or pct_ratio >= 0.7 or num_ratio >= 0.8) and not _col_name_matches_id(col_name):
                            converted = s.map(lambda v: _strip_numeric_formatting(v) if pd.notna(v) else np.nan)
                            valid_converted = converted.dropna()
                            if len(valid_converted) / max(1, n_valid) >= 0.8:
                                norm_df[col] = pd.to_numeric(converted, errors="coerce")
                                detected_type = "numeric"
                                numerical_columns.append(col_name)
                                if curr_ratio >= 0.5:
                                    semantic_type = "currency"
                                    format_hint = "currency"
                                elif pct_ratio >= 0.5:
                                    semantic_type = "percentage"
                                    format_hint = "percentage"
                                else:
                                    semantic_type = "financial_measure" if _detect_financial_hint(col_name) else "numeric_string"
                                    format_hint = "numeric_string"
                            else:
                                # Fallback to categorical/text below
                                pass

                        if detected_type == "categorical":
                            # 6e. Identifier by column name or 100% unique code strings
                            unique_ratio = n_unique / max(1, n_valid)
                            avg_len = float(str_vals.str.len().mean())
                            has_id_name = _col_name_matches_id(col_name)

                            if (has_id_name and unique_ratio >= 0.7) or (
                                unique_ratio == 1.0 and n_valid >= 10 and not geo_role and bool(
                                    sample_str.str.match(r"^[A-Za-z0-9_-]{3,24}$").mean() >= 0.9
                                ) and has_id_name
                            ):
                                is_identifier = True
                                detected_type = "identifier"
                                semantic_type = "identifier"
                                analysis_eligible = False
                                identifier_columns.append(col_name)
                            elif geo_role:
                                detected_type = "categorical"
                                semantic_type = f"geo_{geo_role}"
                                format_hint = "geographic"
                                geographic_columns.append(col_name)
                                categorical_columns.append(col_name)
                                if n_unique > 50:
                                    is_high_cardinality = True
                                    high_cardinality_columns.append(col_name)
                            elif avg_len > 45 and unique_ratio > 0.6 and n_valid >= 10:
                                detected_type = "text"
                                semantic_type = "free_text"
                                analysis_eligible = False
                                is_high_cardinality = True
                                text_columns.append(col_name)
                                high_cardinality_columns.append(col_name)
                            else:
                                detected_type = "categorical"
                                semantic_type = "category"
                                categorical_columns.append(col_name)
                                if n_unique > 50 or (unique_ratio == 1.0 and n_valid > 25):
                                    is_high_cardinality = True
                                    high_cardinality_columns.append(col_name)

        # Map legacy inferred_type cleanly so all existing API consumers/tests work unchanged
        legacy_inferred = (
            "numeric" if detected_type == "numeric"
            else ("datetime" if detected_type == "datetime"
                  else ("boolean" if detected_type == "boolean"
                        else "categorical"))
        )

        role = (
            "Unique Key / ID" if is_identifier
            else ("Constant" if is_constant
                  else ("Temporal Dimension" if detected_type == "datetime"
                        else ("Metric" if detected_type == "numeric"
                              else ("Free Text" if detected_type == "text"
                                    else ("Geographic Dimension" if geo_role
                                          else "Categorical Dimension")))))
        )

        columns_meta.append({
            "name": col_name,
            "column_name": col_name,
            "dtype": raw_dtype,
            "inferred_type": legacy_inferred,
            "detected_type": detected_type,
            "semantic_type": semantic_type,
            "role": role,
            "format_hint": format_hint,
            "missing_count": n_missing,
            "missing_percent": missing_pct,
            "missing_percentage": missing_pct,
            "unique_count": n_unique,
            "is_identifier": is_identifier,
            "is_constant": is_constant,
            "is_high_cardinality": is_high_cardinality,
            "analysis_eligible": analysis_eligible,
            "sample_values": samples,
        })

    # Build numeric & categorical summaries on normalized DataFrame
    numeric_summary: Dict[str, Dict[str, Any]] = {}
    for col in numerical_columns:
        s = pd.to_numeric(norm_df[col], errors="coerce").dropna()
        if s.empty:
            continue
        desc = s.describe().to_dict()
        numeric_summary[col] = {str(k): to_python(v) for k, v in desc.items()}

    categorical_summary: Dict[str, list] = {}
    for col in categorical_columns + boolean_columns:
        counts = norm_df[col].value_counts(dropna=False).head(10)
        categorical_summary[col] = [
            {"value": to_python(k), "count": int(v)} for k, v in counts.items()
        ]

    duplicate_rows = int(norm_df.duplicated().sum()) if total_rows > 0 else 0

    profile = {
        "dataset_name": dataset_name,
        "row_count": total_rows,
        "column_count": total_cols,
        "total_cells": total_cells,
        "memory_bytes": memory_bytes,
        "duplicate_rows": duplicate_rows,
        "numerical_columns": numerical_columns,
        "categorical_columns": categorical_columns,
        "boolean_columns": boolean_columns,
        "datetime_columns": datetime_columns,
        "identifier_columns": identifier_columns,
        "constant_columns": constant_columns,
        "high_cardinality_columns": high_cardinality_columns,
        "geographic_columns": geographic_columns,
        "text_columns": text_columns,
        "empty_columns": empty_columns,
        "columns": columns_meta,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "validation": validation,
    }

    return {
        "profile": profile,
        "normalized_df": norm_df,
        "validation": validation,
    }
