"""Context Agent for Analyticx AI.
Resolves active file, screen, page, dataset, chart, filters, and previous actions.
"""
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseSpecializedAgent
from app.context.context_freshness_service import is_context_stale
from app.context.schemas import LiveApplicationContext
from app.models.dataset import Dataset
from app.services.context_resolver import resolve_active_context


class ContextAgent(BaseSpecializedAgent):
    """
    Resolves the active file, screen, page, dataset, chart, current filters,
    relevant previous actions, and user intents.
    """

    def __init__(self):
        super().__init__(
            name="ContextAgent",
            description="Resolves active application workspace state, active dataset/document, page, filters, and intent modality.",
        )

    def resolve_context(
        self,
        raw_context: Optional[Any] = None,
        dataset_id: Optional[int] = None,
        document_id: Optional[int] = None,
        page_number: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Builds authoritative, unified context dictionary from explicit inputs and live context.
        """
        resolved = resolve_active_context(raw_context, db=db)

        # Explicit overrides if provided
        if dataset_id is not None:
            resolved["dataset_id"] = dataset_id
        if document_id is not None:
            resolved["document_id"] = document_id
        if page_number is not None:
            resolved["page_number"] = page_number

        # If dataset_id is present, enrich with dataset details
        if resolved.get("dataset_id") and db:
            ds = db.query(Dataset).filter(Dataset.id == resolved["dataset_id"]).first()
            if ds:
                resolved["dataset_name"] = ds.name
                resolved["stored_path"] = ds.stored_path
                resolved["row_count"] = ds.row_count
                resolved["column_count"] = ds.column_count
                resolved["version"] = getattr(ds, "version", 1)

                # Check if stale
                last_ts = ds.created_at.timestamp() if hasattr(ds, "created_at") and ds.created_at else 0.0
                if is_context_stale("dataset", ds.id, client_timestamp=last_ts):
                    resolved["is_stale"] = True

        return resolved

    def classify_target_modality(self, query: str, context: Dict[str, Any]) -> str:
        """
        Determines target modality: 'document' (PDF), 'dataset' (tabular), 'dashboard' (chart/visual), or 'general'.
        """
        q = query.lower()
        if context.get("has_document") or context.get("pdf_path") or any(k in q for k in ["pdf", "document", "page", "clause", "citation"]):
            return "document"
        if any(k in q for k in ["chart", "plot", "dashboard", "graph", "visualize", "bar chart", "line chart", "pie chart"]):
            return "dashboard"
        if context.get("dataset_id") or any(k in q for k in ["data", "dataset", "column", "rows", "table", "missing", "duplicate", "clean", "outlier", "sales", "revenue"]):
            return "dataset"
        return "general"


context_agent = ContextAgent()
