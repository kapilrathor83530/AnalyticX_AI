"""Active Workspace and Context Resolver for Analyticx AI Copilot."""
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.models.dashboard import Dashboard
from app.models.dataset import Dataset
from app.models.widget import Widget
from app.schemas.copilot import WorkspaceContext
from app.services.data_service import load_dataset_df


def resolve_active_context(
    context: Optional[Any],
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Resolves the user's active workspace state into an enriched structured dictionary
    with live dataset statistics, column info, dashboard metrics, or document page metadata.
    Handles WorkspaceContext, LiveApplicationContext, or plain dictionary.
    """
    if not context:
        return {
            "workspace_mode": "general",
            "summary_text": "General workspace (no active dataset, dashboard, or document selected).",
            "has_dataset": False,
            "has_document": False,
            "has_dashboard": False,
        }

    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    resolved: Dict[str, Any] = {
        "workspace_mode": _get(context, "workspace_mode") or "dataset",
        "dataset_id": _get(context, "dataset_id"),
        "dataset_name": _get(context, "dataset_name"),
        "document_id": _get(context, "document_id"),
        "page_number": _get(context, "page_number"),
        "selected_column": _get(context, "selected_column"),
        "dashboard_id": _get(context, "dashboard_id"),
        "dashboard_name": _get(context, "dashboard_name"),
        "widget_id": _get(context, "widget_id"),
        "widget_title": _get(context, "widget_title"),
        "chart_type": _get(context, "chart_type"),
        "active_filters": _get(context, "active_filters") or {},
        "language_override": _get(context, "language_override") or "auto",
        "user_role": _get(context, "user_role"),
        "experience_level": _get(context, "experience_level"),
        "explanation_level": _get(context, "explanation_level"),
        "summary_text": "",
        "has_dataset": False,
        "has_document": False,
        "has_dashboard": False,
        "column_details": None,
        "dataset_summary": None,
        "pdf_path": _get(context, "pdf_path"),
    }

    summary_lines = [f"Workspace Mode: {resolved['workspace_mode']}"]

    # 1. Resolve Dataset & Column Context
    ds_id = resolved.get("dataset_id")
    if ds_id and db:
        dataset = db.query(Dataset).filter(Dataset.id == ds_id).first()
        if dataset:
            resolved["has_dataset"] = True
            resolved["dataset_name"] = dataset.name
            path = Path(dataset.stored_path)
            is_pdf = path.suffix.lower() == ".pdf"
            if is_pdf:
                resolved["has_document"] = True
                resolved["pdf_path"] = str(path)
                summary_lines.append(f"Active PDF Document: '{dataset.name}'")
                if resolved.get("page_number"):
                    summary_lines.append(f"Active Page: {resolved['page_number']}")
            else:
                summary_lines.append(f"Active Dataset: '{dataset.name}' ({dataset.row_count:,} rows, {dataset.column_count} columns, Quality Score: {dataset.quality_score or 'N/A'}%)")

            # Inspect selected column if provided
            sel_col = resolved.get("selected_column")
            if sel_col and not is_pdf:
                try:
                    df = load_dataset_df(dataset)
                    col = sel_col
                    if col in df.columns:
                        series = df[col]
                        missing = int(series.isna().sum())
                        dtype_str = str(series.dtype)
                        col_info = {
                            "name": col,
                            "dtype": dtype_str,
                            "missing_count": missing,
                            "missing_pct": round((missing / max(1, len(df))) * 100, 2),
                            "unique_count": int(series.nunique()),
                        }
                        if pd.api.types.is_numeric_dtype(series):
                            col_info["mean"] = round(float(series.mean()), 2) if not series.empty else 0
                            col_info["median"] = round(float(series.median()), 2) if not series.empty else 0
                            col_info["min"] = round(float(series.min()), 2) if not series.empty else 0
                            col_info["max"] = round(float(series.max()), 2) if not series.empty else 0
                        resolved["column_details"] = col_info
                        summary_lines.append(f"Focused Column: '{col}' (Type: {dtype_str}, Missing: {missing})")
                except Exception:
                    pass

    if resolved.get("pdf_path"):
        resolved["has_document"] = True

    # 2. Resolve Dashboard & Widget Context
    dash_id = resolved.get("dashboard_id")
    if dash_id and db:
        dashboard = db.query(Dashboard).filter(Dashboard.id == dash_id).first()
        if dashboard:
            resolved["has_dashboard"] = True
            resolved["dashboard_name"] = dashboard.name
            summary_lines.append(f"Active Dashboard: '{dashboard.name}'")

    widget_id = resolved.get("widget_id")
    if widget_id and db:
        widget = db.query(Widget).filter(Widget.id == widget_id).first()
        if widget:
            resolved["widget_title"] = widget.title
            resolved["chart_type"] = widget.chart_type
            summary_lines.append(f"Focused Chart: '{widget.title}' ({widget.chart_type})")

    resolved["summary_text"] = " | ".join(summary_lines)
    return resolved
