"""
SQL Studio AI Service for Analyticx AI.
Provides Schema-Aware Natural Language to SQL Generation, Query Explanation,
Contextual Query Recommendations, and Safe SQLite Query Plan Validation.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple
import sqlite3
import pandas as pd


FORBIDDEN_OPERATIONS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE",
    "ATTACH", "DETACH", "PRAGMA", "REINDEX", "VACUUM", "REPLACE"
]


def extract_schema_metadata(df: pd.DataFrame, dataset_id: int) -> Dict[str, Any]:
    """Extracts rich schema metadata including inferred types and sample values."""
    columns = []
    numeric_cols = []
    categorical_cols = []
    datetime_cols = []

    for col in df.columns:
        col_name = str(col)
        dtype_str = str(df[col].dtype)
        is_num = bool(pd.api.types.is_numeric_dtype(df[col]))
        is_dt = bool(pd.api.types.is_datetime64_any_dtype(df[col]))

        # Check if text column might be a date
        if not is_dt and not is_num and ("date" in col_name.lower() or "time" in col_name.lower() or "year" in col_name.lower()):
            is_dt = True

        sample_vals = [str(v) for v in df[col].dropna().head(3).tolist()]
        col_meta = {
            "name": col_name,
            "type": dtype_str,
            "is_numeric": is_num,
            "is_datetime": is_dt,
            "sample_values": sample_vals,
            "null_count": int(df[col].isna().sum()),
        }
        columns.append(col_meta)

        if is_num:
            numeric_cols.append(col_name)
        elif is_dt:
            datetime_cols.append(col_name)
        else:
            categorical_cols.append(col_name)

    return {
        "dataset_id": dataset_id,
        "total_rows": int(len(df)),
        "columns": columns,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
    }


def find_best_matching_column(target: str, available_columns: List[str]) -> Optional[str]:
    """Finds the best matching column name using exact, lowercase, or substring matching."""
    t_clean = target.strip().lower().replace("_", " ").replace("-", " ")
    
    # 1. Exact match
    for c in available_columns:
        if c.lower() == target.lower():
            return c

    # 2. Normalized match
    for c in available_columns:
        c_clean = c.lower().replace("_", " ").replace("-", " ")
        if c_clean == t_clean:
            return c

    # 3. Substring match
    for c in available_columns:
        c_clean = c.lower()
        if t_clean in c_clean or c_clean in t_clean:
            return c

    # 4. Token overlap
    t_tokens = set(t_clean.split())
    best_match = None
    best_overlap = 0
    for c in available_columns:
        c_tokens = set(c.lower().replace("_", " ").split())
        overlap = len(t_tokens.intersection(c_tokens))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = c

    return best_match if best_overlap > 0 else None


def generate_sql_from_natural_language(
    prompt: str,
    schema: Dict[str, Any],
    table_name: str = "dataset"
) -> Dict[str, Any]:
    """
    Transforms natural language requests into schema-grounded SQLite queries.
    Handles aggregations, top-N, groupings, filters, data-quality audits, and time trends.
    """
    q = prompt.strip().lower()
    columns_info = schema.get("columns", [])
    col_names = [c["name"] for c in columns_info]
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    dt_cols = schema.get("datetime_columns", [])

    assumptions = []
    warnings = []
    columns_used = []
    query_type = "scan"
    is_ambiguous = False
    clarifying_questions = []

    # 1. Total row count intent
    if any(k in q for k in ["count total", "total records", "number of rows", "how many rows", "row count", "count rows", "total count"]):
        sql = f'SELECT COUNT(*) AS total_records\nFROM {table_name};'
        explanation = "Counts all total records present in the dataset."
        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": [],
            "query_type": "aggregation",
            "assumptions": ["Assuming full count without row filters"],
            "warnings": [],
            "is_ambiguous": False,
            "clarifying_questions": [],
        }

    # 2. Missing value audit intent
    if any(k in q for k in ["missing", "null", "blank", "empty values", "na values"]):
        # Check if a specific column is requested
        target_col = None
        for c in col_names:
            if c.lower() in q:
                target_col = c
                break

        if target_col:
            sql = f'SELECT *\nFROM {table_name}\nWHERE "{target_col}" IS NULL OR "{target_col}" = \'\';'
            explanation = f'Retrieves rows where the "{target_col}" column contains NULL or empty string values.'
            columns_used.append(target_col)
        else:
            # Audit missing counts across all columns
            sub_clauses = [f'SUM(CASE WHEN "{c}" IS NULL OR "{c}" = \'\' THEN 1 ELSE 0 END) AS "{c}_missing_count"' for c in col_names[:10]]
            sql = f'SELECT\n  {",\n  ".join(sub_clauses)}\nFROM {table_name};'
            explanation = "Audits and sums the missing and null occurrences across the primary dataset columns."
            columns_used = col_names[:10]

        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": columns_used,
            "query_type": "data_quality",
            "assumptions": ["Treating empty strings '' as missing alongside NULL values"],
            "warnings": ["Showing up to 10 columns for audit overview"] if not target_col else [],
            "is_ambiguous": False,
            "clarifying_questions": [],
        }

    # 3. Duplicate records intent
    if any(k in q for k in ["duplicate", "duplicates", "repeated"]):
        target_col = None
        for c in col_names:
            if c.lower() in q:
                target_col = c
                break

        if target_col:
            sql = (
                f'SELECT "{target_col}", COUNT(*) AS occurrences\n'
                f'FROM {table_name}\n'
                f'GROUP BY "{target_col}"\n'
                f'HAVING COUNT(*) > 1\n'
                f'ORDER BY occurrences DESC;'
            )
            explanation = f'Finds duplicated values in column "{target_col}" appearing more than once.'
            columns_used.append(target_col)
        elif cat_cols:
            best_cat = cat_cols[0]
            sql = (
                f'SELECT "{best_cat}", COUNT(*) AS occurrences\n'
                f'FROM {table_name}\n'
                f'GROUP BY "{best_cat}"\n'
                f'HAVING COUNT(*) > 1\n'
                f'ORDER BY occurrences DESC;'
            )
            explanation = f'Finds duplicate occurrences of "{best_cat}" appearing multiple times.'
            columns_used.append(best_cat)
            assumptions.append(f'Selected primary key candidate "{best_cat}" for duplicate group-by check.')
        else:
            sql = (
                f'SELECT *, COUNT(*) AS row_occurrences\n'
                f'FROM {table_name}\n'
                f'GROUP BY 1, 2\n'
                f'HAVING COUNT(*) > 1;'
            )
            explanation = "Identifies duplicate rows grouped across initial columns."

        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": columns_used,
            "query_type": "data_quality",
            "assumptions": assumptions,
            "warnings": [],
            "is_ambiguous": False,
            "clarifying_questions": [],
        }

    # 4. Top N / Ranking Intent
    # e.g., "top 10 products by sales", "highest 5 categories by profit"
    limit_match = re.search(r'\b(?:top|highest|best|first)\s+(\d+)\b', q)
    limit_num = int(limit_match.group(1)) if limit_match else (10 if any(k in q for k in ["top", "highest", "best", "most"]) else None)

    if limit_num is not None or any(k in q for k in ["rank", "leaderboard", "highest", "lowest", "bottom"]):
        # Determine sorting direction
        is_asc = any(k in q for k in ["lowest", "bottom", "worst", "least"])
        sort_dir = "ASC" if is_asc else "DESC"

        # Find metric column (numeric)
        metric_col = None
        for c in num_cols:
            if c.lower() in q:
                metric_col = c
                break
        if not metric_col and num_cols:
            metric_col = num_cols[0]
            assumptions.append(f'Auto-selected primary numerical column "{metric_col}" for ranking metric.')

        # Find dimension column (categorical)
        dim_col = None
        for c in cat_cols:
            if c.lower() in q:
                dim_col = c
                break
        if not dim_col and cat_cols:
            dim_col = cat_cols[0]
            assumptions.append(f'Auto-selected categorical column "{dim_col}" as grouping entity.')

        limit_val = limit_num if limit_num else 10

        if dim_col and metric_col:
            sql = (
                f'SELECT "{dim_col}",\n'
                f'       COUNT(*) AS transaction_count,\n'
                f'       ROUND(SUM("{metric_col}"), 2) AS total_{metric_col.lower()},\n'
                f'       ROUND(AVG("{metric_col}"), 2) AS avg_{metric_col.lower()}\n'
                f'FROM {table_name}\n'
                f'GROUP BY "{dim_col}"\n'
                f'ORDER BY total_{metric_col.lower()} {sort_dir}\n'
                f'LIMIT {limit_val};'
            )
            explanation = (
                f'Ranks the {sort_dir.lower()} {limit_val} "{dim_col}" entities by cumulative '
                f'"{metric_col}", showing total sums and averages.'
            )
            columns_used.extend([dim_col, metric_col])
            query_type = "ranking"
        elif metric_col:
            sql = (
                f'SELECT *\n'
                f'FROM {table_name}\n'
                f'ORDER BY "{metric_col}" {sort_dir}\n'
                f'LIMIT {limit_val};'
            )
            explanation = f'Retrieves the {limit_val} records with the {sort_dir.lower()} values in "{metric_col}".'
            columns_used.append(metric_col)
            query_type = "ranking"
        else:
            sql = f'SELECT *\nFROM {table_name}\nLIMIT {limit_val};'
            explanation = f'Retrieves the first {limit_val} records from the dataset.'
            query_type = "scan"

        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": columns_used,
            "query_type": query_type,
            "assumptions": assumptions,
            "warnings": warnings,
            "is_ambiguous": is_ambiguous,
            "clarifying_questions": clarifying_questions,
        }

    # 5. Group by / Average / Sum intent
    # e.g., "average sales for each region", "total profit by category"
    if any(k in q for k in ["for each", "by", "per", "grouped by", "group by"]):
        dim_col = None
        for c in cat_cols:
            if c.lower() in q:
                dim_col = c
                break
        if not dim_col and cat_cols:
            dim_col = cat_cols[0]
            assumptions.append(f'Assumed grouping entity "{dim_col}".')

        metric_col = None
        for c in num_cols:
            if c.lower() in q:
                metric_col = c
                break
        if not metric_col and num_cols:
            metric_col = num_cols[0]
            assumptions.append(f'Assumed numerical measure "{metric_col}".')

        is_avg = any(k in q for k in ["average", "avg", "mean"])
        agg_func = "AVG" if is_avg else "SUM"
        agg_label = f"avg_{metric_col.lower()}" if is_avg and metric_col else f"total_{metric_col.lower()}" if metric_col else "record_count"

        if dim_col and metric_col:
            sql = (
                f'SELECT "{dim_col}",\n'
                f'       COUNT(*) AS count,\n'
                f'       ROUND({agg_func}("{metric_col}"), 2) AS {agg_label}\n'
                f'FROM {table_name}\n'
                f'GROUP BY "{dim_col}"\n'
                f'ORDER BY {agg_label} DESC;'
            )
            explanation = f'Calculates the {agg_func.lower()} of "{metric_col}" broken down across distinct "{dim_col}" groups.'
            columns_used.extend([dim_col, metric_col])
        elif dim_col:
            sql = (
                f'SELECT "{dim_col}", COUNT(*) AS total_count\n'
                f'FROM {table_name}\n'
                f'GROUP BY "{dim_col}"\n'
                f'ORDER BY total_count DESC;'
            )
            explanation = f'Groups records by "{dim_col}" and counts the frequency of each category.'
            columns_used.append(dim_col)
        else:
            sql = f'SELECT * FROM {table_name} LIMIT 50;'
            explanation = "Default scan query across dataset."

        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": columns_used,
            "query_type": "aggregation",
            "assumptions": assumptions,
            "warnings": warnings,
            "is_ambiguous": is_ambiguous,
            "clarifying_questions": clarifying_questions,
        }

    # 6. Time / Monthly / Yearly Analysis intent
    if any(k in q for k in ["month", "monthly", "year", "yearly", "day", "daily", "trend", "over time"]) and dt_cols:
        date_col = dt_cols[0]
        metric_col = num_cols[0] if num_cols else None
        columns_used.append(date_col)

        if "year" in q:
            strftime_fmt = "%Y"
            time_label = "year"
        else:
            strftime_fmt = "%Y-%m"
            time_label = "month"

        if metric_col:
            columns_used.append(metric_col)
            sql = (
                f'SELECT strftime(\'{strftime_fmt}\', "{date_col}") AS {time_label},\n'
                f'       COUNT(*) AS transaction_count,\n'
                f'       ROUND(SUM("{metric_col}"), 2) AS total_{metric_col.lower()}\n'
                f'FROM {table_name}\n'
                f'WHERE "{date_col}" IS NOT NULL\n'
                f'GROUP BY {time_label}\n'
                f'ORDER BY {time_label} ASC;'
            )
            explanation = f'Aggregates cumulative "{metric_col}" by {time_label} over chronology in "{date_col}".'
        else:
            sql = (
                f'SELECT strftime(\'{strftime_fmt}\', "{date_col}") AS {time_label},\n'
                f'       COUNT(*) AS record_count\n'
                f'FROM {table_name}\n'
                f'WHERE "{date_col}" IS NOT NULL\n'
                f'GROUP BY {time_label}\n'
                f'ORDER BY {time_label} ASC;'
            )
            explanation = f'Counts record frequencies by {time_label} over time in "{date_col}".'

        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": columns_used,
            "query_type": "time_series",
            "assumptions": [f'Used SQLite strftime formatting on "{date_col}"'],
            "warnings": [],
            "is_ambiguous": False,
            "clarifying_questions": [],
        }

    # 7. Filtering Threshold intent
    # e.g., "products with discount greater than 20%", "sales above 1000"
    comp_match = re.search(r'\b(greater than|more than|above|>|over|exceeding)\s+([\d.]+)', q)
    less_match = re.search(r'\b(less than|below|<|under)\s+([\d.]+)', q)

    if comp_match or less_match:
        is_greater = bool(comp_match)
        threshold_val = float(comp_match.group(2) if is_greater else less_match.group(2))
        op = ">" if is_greater else "<"

        # Find target column
        matched_num_col = None
        for c in num_cols:
            if c.lower() in q:
                matched_num_col = c
                break
        if not matched_num_col and num_cols:
            matched_num_col = num_cols[0]
            assumptions.append(f'Assumed numerical column "{matched_num_col}" for threshold evaluation.')

        if matched_num_col:
            sql = (
                f'SELECT *\n'
                f'FROM {table_name}\n'
                f'WHERE "{matched_num_col}" {op} {threshold_val}\n'
                f'ORDER BY "{matched_num_col}" DESC\n'
                f'LIMIT 50;'
            )
            explanation = f'Filters records where "{matched_num_col}" is {op} {threshold_val}, limited to 50 rows.'
            columns_used.append(matched_num_col)
            return {
                "sql": sql,
                "explanation": explanation,
                "tables_used": [table_name],
                "columns_used": columns_used,
                "query_type": "filter",
                "assumptions": assumptions,
                "warnings": ["Query capped at 50 records for responsive viewing"],
                "is_ambiguous": False,
                "clarifying_questions": [],
            }

    # 8. Distinct / Cardinality intent
    if any(k in q for k in ["distinct", "unique"]):
        target_col = None
        for c in col_names:
            if c.lower() in q:
                target_col = c
                break
        if not target_col and cat_cols:
            target_col = cat_cols[0]

        if target_col:
            sql = f'SELECT DISTINCT "{target_col}"\nFROM {table_name}\nORDER BY 1 ASC\nLIMIT 50;'
            explanation = f'Lists unique distinct values from "{target_col}".'
            columns_used.append(target_col)
        else:
            sql = f'SELECT DISTINCT * FROM {table_name} LIMIT 25;'
            explanation = "Retrieves unique distinct records across the dataset."

        return {
            "sql": sql,
            "explanation": explanation,
            "tables_used": [table_name],
            "columns_used": columns_used,
            "query_type": "distinct",
            "assumptions": assumptions,
            "warnings": [],
            "is_ambiguous": False,
            "clarifying_questions": [],
        }

    # 9. Default intelligent fallback: Select specific or sample columns
    sample_cols = col_names[:6]
    cols_str = ", ".join(f'"{c}"' for c in sample_cols)
    sql = f'SELECT {cols_str}\nFROM {table_name}\nLIMIT 25;'
    explanation = f'Displays sample rows of primary columns ({", ".join(sample_cols)}).'

    return {
        "sql": sql,
        "explanation": explanation,
        "tables_used": [table_name],
        "columns_used": sample_cols,
        "query_type": "scan",
        "assumptions": ["Defaulted to first 6 columns with 25-row preview"],
        "warnings": [],
        "is_ambiguous": False,
        "clarifying_questions": [],
    }


def explain_sql_statement(query: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses and explains a SQL statement in plain, human-readable English,
    identifying clauses, aggregates, filters, groupings, and potential performance notes.
    """
    clean_q = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)
    clean_q = re.sub(r"/\*.*?\*/", "", clean_q, flags=re.DOTALL).strip()
    upper_q = clean_q.upper()

    col_names = [c["name"] for c in schema.get("columns", [])]
    tables_found = ["dataset"] if "DATASET" in upper_q or "DATA" in upper_q else []

    # Detect columns referenced in query
    cols_referenced = []
    for c in col_names:
        # Check quoted or unquoted presence
        if f'"{c.lower()}"' in clean_q.lower() or re.search(r'\b' + re.escape(c.lower()) + r'\b', clean_q.lower()):
            cols_referenced.append(c)

    # Detect aggregations
    aggs = []
    if "COUNT(" in upper_q: aggs.append("COUNT (counts rows/frequencies)")
    if "SUM(" in upper_q: aggs.append("SUM (computes numerical total)")
    if "AVG(" in upper_q: aggs.append("AVG (computes arithmetic mean)")
    if "MIN(" in upper_q: aggs.append("MIN (finds minimum value)")
    if "MAX(" in upper_q: aggs.append("MAX (finds maximum value)")
    if "ROUND(" in upper_q: aggs.append("ROUND (rounds floating decimal precision)")

    # Detect clauses
    has_where = "WHERE" in upper_q
    has_group = "GROUP BY" in upper_q
    has_having = "HAVING" in upper_q
    has_order = "ORDER BY" in upper_q
    has_limit = "LIMIT" in upper_q
    has_cte = "WITH " in upper_q

    # Extract limit number if present
    limit_match = re.search(r'\bLIMIT\s+(\d+)\b', upper_q)
    limit_val = int(limit_match.group(1)) if limit_match else None

    # Construct narrative explanation
    narrative_parts = []
    if has_cte:
        narrative_parts.append("Defines a Common Table Expression (CTE) to pre-aggregate intermediate results.")

    if has_group:
        narrative_parts.append("Groups records into category buckets to calculate summary statistics per segment.")
    elif aggs:
        narrative_parts.append("Computes whole-dataset aggregate summaries across the matched rows.")
    else:
        narrative_parts.append("Scans records directly from the dataset.")

    if has_where:
        narrative_parts.append("Filters the input data to include only rows matching specific WHERE criteria.")

    if has_having:
        narrative_parts.append("Applies a post-aggregation HAVING threshold filter on computed group totals.")

    if has_order:
        sort_order = "descending order (highest first)" if "DESC" in upper_q else "ascending order (lowest first)"
        narrative_parts.append(f"Sorts the final output rows in {sort_order}.")

    if limit_val:
        narrative_parts.append(f"Restricts the result set to the first {limit_val} rows.")
    else:
        narrative_parts.append("Does not specify an explicit LIMIT; sandbox defaults to a 500-row cap.")

    explanation = " ".join(narrative_parts)

    performance_notes = []
    if not has_limit:
        performance_notes.append("No LIMIT clause specified; automatically capped at 500 records by sandbox.")
    if "SELECT *" in upper_q and has_group:
        performance_notes.append("Using SELECT * with GROUP BY in SQLite returns arbitrary non-aggregated column values.")
    if "%" in clean_q and "LIKE" in upper_q:
        performance_notes.append("Leading wildcard search '%value' forces a full sequential table scan.")

    return {
        "explanation": explanation,
        "tables_referenced": tables_found or ["dataset"],
        "columns_referenced": cols_referenced,
        "aggregations_used": aggs,
        "has_filters": has_where,
        "has_group_by": has_group,
        "has_order_by": has_order,
        "limit": limit_val,
        "performance_notes": performance_notes,
    }


def validate_sql_with_query_plan(query: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates SQL safety and runs SQLite's EXPLAIN QUERY PLAN to verify syntax and column validity
    in an isolated in-memory sandbox without mutating data or running expensive payloads.
    """
    clean_q = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)
    clean_q = re.sub(r"/\*.*?\*/", "", clean_q, flags=re.DOTALL).strip()

    if not clean_q:
        return {"valid": False, "error": "Query string is empty", "query_plan": [], "read_only": True}

    tokens = [t.strip(";").upper() for t in clean_q.split()]
    first_token = tokens[0] if tokens else ""

    if first_token not in ("SELECT", "WITH", "EXPLAIN"):
        return {
            "valid": False,
            "error": f"Operation '{first_token}' is forbidden. Only read-only SELECT or WITH statements are permitted.",
            "query_plan": [],
            "read_only": False,
        }

    for f in FORBIDDEN_OPERATIONS:
        if f in tokens:
            return {
                "valid": False,
                "error": f"Forbidden statement '{f}' detected in read-only SQL studio.",
                "query_plan": [],
                "read_only": False,
            }

    conn = sqlite3.connect(":memory:")
    try:
        # Load schema structure (head(1) is sufficient for plan check)
        df.head(1).to_sql("dataset", conn, index=False, if_exists="replace")
        df.head(1).to_sql("data", conn, index=False, if_exists="replace")

        cur = conn.cursor()
        cur.execute(f"EXPLAIN QUERY PLAN {query}")
        plan_rows = cur.fetchall()
        plan_lines = [f"{row[0]} | {row[1]} | {row[2]} | {row[3]}" if len(row) >= 4 else str(row) for row in plan_rows]

        return {
            "valid": True,
            "error": None,
            "query_plan": plan_lines,
            "read_only": True,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "query_plan": [],
            "read_only": True,
        }
    finally:
        conn.close()


def generate_context_aware_query_suggestions(schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Generates tailored, high-value SQL query recommendations grounded strictly in the active dataset's actual schema.
    """
    col_names = [c["name"] for c in schema.get("columns", [])]
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    dt_cols = schema.get("datetime_columns", [])

    suggestions: List[Dict[str, str]] = []

    # 1. Top categories by primary metric
    if cat_cols and num_cols:
        cat = cat_cols[0]
        num = num_cols[0]
        suggestions.append({
            "title": f"Top 10 {cat} by Total {num}",
            "prompt": f"Show top 10 {cat} by {num}",
            "category": "Ranking & Aggregations",
            "sql": (
                f'SELECT "{cat}",\n'
                f'       COUNT(*) AS transaction_count,\n'
                f'       ROUND(SUM("{num}"), 2) AS total_{num.lower()},\n'
                f'       ROUND(AVG("{num}"), 2) AS avg_{num.lower()}\n'
                f'FROM dataset\n'
                f'GROUP BY "{cat}"\n'
                f'ORDER BY total_{num.lower()} DESC\n'
                f'LIMIT 10;'
            ),
        })

    # 2. Average metric breakdown
    if len(cat_cols) > 0 and len(num_cols) > 1:
        cat = cat_cols[0]
        num2 = num_cols[1]
        suggestions.append({
            "title": f"Average {num2} by {cat}",
            "prompt": f"Average {num2} grouped by {cat}",
            "category": "Aggregations",
            "sql": (
                f'SELECT "{cat}",\n'
                f'       ROUND(AVG("{num2}"), 2) AS average_{num2.lower()},\n'
                f'       ROUND(MIN("{num2}"), 2) AS min_{num2.lower()},\n'
                f'       ROUND(MAX("{num2}"), 2) AS max_{num2.lower()}\n'
                f'FROM dataset\n'
                f'GROUP BY "{cat}"\n'
                f'ORDER BY average_{num2.lower()} DESC\n'
                f'LIMIT 15;'
            ),
        })

    # 3. Chronological Time Trend
    if dt_cols and num_cols:
        dt = dt_cols[0]
        num = num_cols[0]
        suggestions.append({
            "title": f"Monthly {num} Trend over {dt}",
            "prompt": f"Monthly {num} by {dt}",
            "category": "Time-Series",
            "sql": (
                f'SELECT strftime(\'%Y-%m\', "{dt}") AS month,\n'
                f'       COUNT(*) AS record_count,\n'
                f'       ROUND(SUM("{num}"), 2) AS monthly_{num.lower()}\n'
                f'FROM dataset\n'
                f'WHERE "{dt}" IS NOT NULL\n'
                f'GROUP BY month\n'
                f'ORDER BY month ASC;'
            ),
        })

    # 4. Outlier & Threshold Detection
    if num_cols:
        num = num_cols[0]
        suggestions.append({
            "title": f"High-Value Outliers in {num}",
            "prompt": f"Records with {num} above average",
            "category": "Advanced Analytics",
            "sql": (
                f'WITH stats AS (\n'
                f'  SELECT AVG("{num}") AS mean_val, AVG("{num}") + 2 * (AVG("{num} * "{num}") - AVG("{num}")*AVG("{num}")) AS upper_threshold\n'
                f'  FROM dataset\n'
                f')\n'
                f'SELECT d.*, ROUND(d."{num}", 2) AS metric_value\n'
                f'FROM dataset d, stats\n'
                f'WHERE d."{num}" > stats.mean_val\n'
                f'ORDER BY d."{num}" DESC\n'
                f'LIMIT 25;'
            ),
        })

    # 5. Missing Data Health Check
    suggestions.append({
        "title": "Data Quality: Audit Null & Missing Cells",
        "prompt": "Find missing values across columns",
        "category": "Data Quality",
        "sql": (
            f'SELECT\n' +
            ",\n".join([f'  SUM(CASE WHEN "{c}" IS NULL OR "{c}" = \'\' THEN 1 ELSE 0 END) AS "{c}_nulls"' for c in col_names[:8]]) +
            f'\nFROM dataset;'
        ),
    })

    # 6. Duplicates Check
    if cat_cols:
        cat = cat_cols[0]
        suggestions.append({
            "title": f"Find Duplicate Values in {cat}",
            "prompt": f"Find duplicate {cat}",
            "category": "Data Quality",
            "sql": (
                f'SELECT "{cat}", COUNT(*) AS occurrences\n'
                f'FROM dataset\n'
                f'GROUP BY "{cat}"\n'
                f'HAVING COUNT(*) > 1\n'
                f'ORDER BY occurrences DESC\n'
                f'LIMIT 20;'
            ),
        })

    return suggestions
