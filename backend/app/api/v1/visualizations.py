from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dataset import Dataset
from app.services.data_service import get_dataset_understanding, load_dataset_df
from app.services.visualization_service import (
    get_available_charts,
    recommend_charts,
    render_chart,
    validate_config,
)

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


def _get_dataset_or_404(db: Session, dataset_id: int) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/charts")
def list_charts():
    return get_available_charts()


@router.get("/recommend/{dataset_id}")
def recommend_visualizations(
    dataset_id: int,
    query: str = Query("", description="Optional analytical question or goal"),
    limit: int = Query(8, ge=1, le=15),
    db: Session = Depends(get_db),
):
    dataset = _get_dataset_or_404(db, dataset_id)
    understanding = get_dataset_understanding(dataset)
    recommendations = recommend_charts(
        understanding["normalized_df"],
        query=query,
        understanding=understanding,
        max_recommendations=limit,
    )
    return {
        "dataset_id": dataset.id,
        "dataset_version": getattr(dataset, "version", 1),
        "recommendations": recommendations,
    }


@router.post("/validate")
def validate_chart(payload: dict, db: Session = Depends(get_db)):
    dataset_id = payload.get("dataset_id")
    config = payload.get("config")
    if not dataset_id or not config:
        raise HTTPException(status_code=400, detail="dataset_id and config are required")

    dataset = _get_dataset_or_404(db, dataset_id)
    understanding = get_dataset_understanding(dataset)
    result = validate_config(understanding["normalized_df"], config, understanding=understanding)
    return result.model_dump()


@router.post("/render")
def render(payload: dict, db: Session = Depends(get_db)):
    dataset_id = payload.get("dataset_id")
    config = payload.get("config")
    if not dataset_id or not config:
        raise HTTPException(status_code=400, detail="dataset_id and config are required")

    dataset = _get_dataset_or_404(db, dataset_id)
    understanding = get_dataset_understanding(dataset)
    return render_chart(
        understanding["normalized_df"],
        config,
        understanding=understanding,
        dataset_version=getattr(dataset, "version", 1),
    )
