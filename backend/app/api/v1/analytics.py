import re
import sqlite3
import time
from fastapi import APIRouter, Depends, HTTPException
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.kpi import compute_kpis, compute_trend
from app.analytics.root_cause import analyze_root_cause
from app.analytics.statistics import compare_groups, descriptive_statistics, detect_anomalies_zscore
from app.database import get_db
from app.models.dataset import Dataset
from app.services.data_service import load_dataset_df
from app.services.sql_studio_service import (
    extract_schema_metadata,
    generate_sql_from_natural_language,
    explain_sql_statement,
    validate_sql_with_query_plan,
    generate_context_aware_query_suggestions,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_df(db: Session, dataset_id: int):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return load_dataset_df(dataset)


@router.post("/{dataset_id}/kpi")
def kpi(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    return compute_kpis(
        df,
        metrics=payload.get("metrics", []),
        dimensions=payload.get("dimensions", []),
        date_column=payload.get("date_column"),
    )


@router.post("/{dataset_id}/trend")
def trend(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    freq = payload.get("freq", "M")
    if freq == "M":
        freq = "ME"
    return compute_trend(
        df,
        date_column=payload["date_column"],
        metric_column=payload["metric_column"],
        freq=freq,
    )


@router.post("/{dataset_id}/descriptive")
def descriptive(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    return descriptive_statistics(df, payload["column"])


@router.post("/{dataset_id}/compare-groups")
def compare(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    return compare_groups(df, payload["group_column"], payload["value_column"])


@router.post("/{dataset_id}/anomalies")
def anomalies(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    return detect_anomalies_zscore(
        df, payload["column"], threshold=float(payload.get("threshold", 3.0))
    )


@router.get("/{dataset_id}/schema")
def get_dataset_schema(dataset_id: int, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        is_num = bool(pd.api.types.is_numeric_dtype(df[col]))
        columns.append({
            "name": col,
            "type": dtype,
            "is_numeric": is_num,
            "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
        })
    return {"dataset_id": dataset_id, "columns": columns, "total_rows": int(len(df))}


@router.post("/{dataset_id}/sql")
def execute_sql_query(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    query = (payload.get("query") or "").strip()
    limit = int(payload.get("limit", 500))

    if not query:
        raise HTTPException(status_code=400, detail="SQL query is required")

    clean_q = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)
    clean_q = re.sub(r"/\*.*?\*/", "", clean_q, flags=re.DOTALL).strip()
    first_token = clean_q.split()[0].upper() if clean_q.split() else ""
    if first_token not in ("SELECT", "WITH", "EXPLAIN"):
        raise HTTPException(status_code=400, detail="Only read-only SELECT or WITH statements are allowed")

    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH", "DETACH", "PRAGMA", "REINDEX"]
    tokens = [t.strip(";").upper() for t in clean_q.split()]
    for f in forbidden:
        if f in tokens:
            raise HTTPException(status_code=400, detail=f"Operation '{f}' is forbidden in read-only SQL studio")

    conn = sqlite3.connect(":memory:")
    try:
        t0 = time.perf_counter()
        df.to_sql("dataset", conn, index=False, if_exists="replace")
        df.to_sql("data", conn, index=False, if_exists="replace")

        cur = conn.cursor()
        cur.execute(query)
        col_names = [d[0] for d in cur.description] if cur.description else []
        rows_raw = cur.fetchmany(limit)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        records = [dict(zip(col_names, row)) for row in rows_raw]
        return {
            "success": True,
            "columns": col_names,
            "rows": records,
            "row_count": len(records),
            "execution_time_ms": elapsed_ms,
            "truncated": len(rows_raw) == limit,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL Execution Error: {str(e)}")
    finally:
        conn.close()


@router.post("/{dataset_id}/sql/generate")
def generate_sql_query_endpoint(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    """Generates schema-grounded SQLite query from natural language request."""
    df = _get_df(db, dataset_id)
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Natural language prompt is required")

    schema = extract_schema_metadata(df, dataset_id)
    result = generate_sql_from_natural_language(prompt=prompt, schema=schema)
    return {"success": True, **result}


@router.post("/{dataset_id}/sql/explain")
def explain_sql_query_endpoint(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    """Explains SQL statement in plain English with clause and performance analysis."""
    df = _get_df(db, dataset_id)
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="SQL query is required")

    schema = extract_schema_metadata(df, dataset_id)
    explanation = explain_sql_statement(query=query, schema=schema)
    return {"success": True, **explanation}


@router.post("/{dataset_id}/sql/validate")
def validate_sql_query_endpoint(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    """Validates SQL query syntax and schema references via SQLite EXPLAIN QUERY PLAN."""
    df = _get_df(db, dataset_id)
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="SQL query is required")

    result = validate_sql_with_query_plan(query=query, df=df)
    return {"success": True, **result}


@router.get("/{dataset_id}/sql/suggestions")
def get_sql_suggestions_endpoint(dataset_id: int, db: Session = Depends(get_db)):
    """Returns context-aware query recommendations tailored to active dataset schema."""
    df = _get_df(db, dataset_id)
    schema = extract_schema_metadata(df, dataset_id)
    suggestions = generate_context_aware_query_suggestions(schema)
    return {"success": True, "suggestions": suggestions}


@router.post("/{dataset_id}/root-cause")
def root_cause_analysis(dataset_id: int, payload: dict, db: Session = Depends(get_db)):
    df = _get_df(db, dataset_id)
    metric = payload.get("metric_column") or payload.get("metric_col") or payload.get("metric")
    if not metric:
        raise HTTPException(status_code=400, detail="metric_column is required")

    dimensions = payload.get("dimension_columns") or payload.get("dimensions")
    if not dimensions and ("dimension_col" in payload or "dimension" in payload):
        dim = payload.get("dimension_col") or payload.get("dimension")
        dimensions = [dim] if dim else None

    date_column = payload.get("date_column") or payload.get("period_col") or payload.get("date_col")

    try:
        result = analyze_root_cause(
            df=df,
            metric_column=metric,
            dimension_columns=dimensions,
            date_column=date_column,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Root-cause analysis error: {str(e)}")
