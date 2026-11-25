"""Context Freshness and State Invalidation Service for Analyticx AI."""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.services.data_service import invalidate_dataset_cache

# In-memory freshness timestamps: (entity_type, entity_id) -> timestamp
_FRESHNESS_TIMESTAMPS: Dict[str, float] = {}
_ACCESS_TIMESTAMPS: Dict[str, float] = {}


def record_context_mutation(entity_type: str, entity_id: int | str, details: Optional[Dict[str, Any]] = None) -> None:
    """Marks an entity as mutated, updating its freshness timestamp."""
    key = f"{entity_type}:{entity_id}"
    _FRESHNESS_TIMESTAMPS[key] = datetime.utcnow().timestamp()


def mark_context_accessed(entity_type: str, entity_id: int | str) -> None:
    """Records the timestamp an entity context was actively queried or accessed."""
    key = f"{entity_type}:{entity_id}"
    _ACCESS_TIMESTAMPS[key] = datetime.utcnow().timestamp()



def is_context_stale(
    entity_type: str,
    entity_id: int | str,
    client_timestamp: float = 0.0,
    last_known_timestamp: Optional[float] = None,
) -> bool:
    """Checks if the client's context timestamp is older than the last known mutation."""
    key = f"{entity_type}:{entity_id}"
    last_mutation = _FRESHNESS_TIMESTAMPS.get(key, 0.0)
    ts = last_known_timestamp if last_known_timestamp is not None else client_timestamp
    if ts is None:
        ts = 0.0
    return ts < last_mutation


def ensure_dataset_freshness(dataset_id: int, client_version: int, db: Session) -> Dict[str, Any]:
    """
    Validates that the client is looking at the latest dataset version.
    If the database version is higher, returns latest metadata and invalidates cache.
    """
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        return {"exists": False, "is_fresh": False, "latest_version": None}

    is_fresh = (ds.version == client_version)
    if not is_fresh:
        # Invalidate local data cache for this dataset path
        invalidate_dataset_cache(ds.stored_path)

    return {
        "exists": True,
        "is_fresh": is_fresh,
        "current_db_version": ds.version,
        "client_version": client_version,
        "row_count": ds.row_count,
        "quality_score": ds.quality_score,
        "status": ds.status,
    }
