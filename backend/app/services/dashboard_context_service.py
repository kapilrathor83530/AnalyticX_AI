"""Build compact, permission-scoped context for the dashboard assistant."""
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.dashboard import Dashboard
from app.repositories import dashboard_repo
from app.services.data_service import load_dataset_df


def dashboard_context(db: Session, dashboard: Dashboard, df: pd.DataFrame | None = None) -> dict[str, Any]:
    frame = df if df is not None else load_dataset_df(dashboard.dataset)
    widgets = dashboard_repo.list_widgets(db, dashboard.id)
    return {
        "dashboard_id": dashboard.id,
        "dashboard_name": dashboard.name,
        "dataset_id": dashboard.dataset_id,
        "dataset_name": dashboard.dataset.name if dashboard.dataset else None,
        "columns": [{"name": str(column), "dtype": str(dtype)} for column, dtype in frame.dtypes.items()],
        "row_count": int(len(frame)),
        "dashboard_filters": (dashboard.layout_config or {}).get("dashboard_filters", []),
        "widgets": [
            {
                "id": widget.id,
                "title": widget.title,
                "chart_type": widget.chart_type,
                "data_mapping": widget.data_mapping or {},
                "aggregation": (widget.config or {}).get("aggregation", "sum"),
                "visual_filters": (widget.config or {}).get("visual_filters", []),
                "position": widget.position or {},
                "size": widget.size or {},
            }
            for widget in widgets
        ],
    }
