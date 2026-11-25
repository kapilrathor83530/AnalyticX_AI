"""API Endpoints for Advanced Project Insights Mode in Analyticx AI."""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.project_insights_service import (
    answer_project_chat,
    execute_insight_action,
    get_or_run_project_insights,
    update_insight_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project-insights", tags=["project-insights"])


@router.get("/{dataset_id}")
def get_insights(
    dataset_id: int,
    refresh: bool = Query(False, description="Force re-analysis"),
    db: Session = Depends(get_db),
):
    """Retrieves cached or computed project insights, automated EDA, and executive summary."""
    try:
        data = get_or_run_project_insights(dataset_id=dataset_id, force_refresh=refresh, db=db)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating project insights for dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate project insights: {str(e)}")


@router.post("/{dataset_id}/refresh")
def refresh_insights(dataset_id: int, db: Session = Depends(get_db)):
    """Forces fresh automated analysis and re-generates all insights."""
    try:
        data = get_or_run_project_insights(dataset_id=dataset_id, force_refresh=True, db=db)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error refreshing project insights for dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to refresh project insights: {str(e)}")


@router.patch("/{dataset_id}/insights/{insight_id}")
def set_insight_status(
    dataset_id: int,
    insight_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Updates insight state: 'saved', 'dismissed', 'new', 'resolved'."""
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Missing required field 'status'")
    try:
        res = update_insight_status(insight_id=insight_id, status=status, db=db)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/action")
def run_action(
    dataset_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Executes a concrete action derived from an insight:
    - create_chart: Adds widget directly to dataset's dashboard
    - deeper_analysis: Runs ANOVA F-test or Z-Score anomaly scan
    - save / dismiss: Updates status
    """
    action_type = payload.get("action_type")
    insight_id = payload.get("insight_id")
    action_payload = payload.get("payload") or {}

    if not action_type:
        raise HTTPException(status_code=400, detail="Missing required field 'action_type'")

    try:
        result = execute_insight_action(
            dataset_id=dataset_id,
            action_type=action_type,
            payload=action_payload,
            insight_id=insight_id,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Action execution error on dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/chat")
def project_chat(
    dataset_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Context-aware AI Q&A grounded in active project computations and findings."""
    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        res = answer_project_chat(dataset_id=dataset_id, question=question, db=db)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Project chat error on dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
