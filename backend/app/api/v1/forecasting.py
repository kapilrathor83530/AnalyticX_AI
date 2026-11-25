from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dataset import Dataset
from app.schemas.forecast import ForecastRead, ForecastTrainRequest
from app.services.data_service import load_dataset_df
from app.services.forecasting_service import (
    chat_forecast,
    get_forecast_run,
    inspect_dataset_for_forecasting,
    list_forecasts,
    pin_forecast_widget,
    train_forecast,
)

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


def _get_df(db: Session, dataset_id: int):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return load_dataset_df(dataset)


@router.post("/inspect")
def inspect_dataset(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Inspects dataset readiness, detects dates, numeric targets, and frequencies."""
    dataset_id = payload.get("dataset_id")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")

    try:
        report = inspect_dataset_for_forecasting(db, dataset_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train", response_model=ForecastRead)
def train(payload: ForecastTrainRequest, db: Session = Depends(get_db)):
    """Trains forecasting models with chronological holdout evaluation and scenario generation."""
    df = _get_df(db, payload.dataset_id)
    try:
        run = train_forecast(
            db=db,
            df=df,
            dataset_id=payload.dataset_id,
            date_column=payload.date_column,
            target_column=payload.target_column,
            horizon=payload.horizon,
            frequency=payload.frequency,
            model_type=payload.model_type,
            group_dimension=payload.group_dimension,
            group_value=payload.group_value,
            fill_strategy=payload.fill_strategy or "interpolate",
            handle_outliers=payload.handle_outliers if payload.handle_outliers is not None else True,
            custom_assumptions=payload.custom_assumptions,
        )
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")


@router.get("/{dataset_id}", response_model=List[ForecastRead])
def list_dataset_forecasts(dataset_id: int, db: Session = Depends(get_db)):
    """Lists all forecast runs for a dataset."""
    return list_forecasts(db, dataset_id)


@router.get("/run/{run_id}", response_model=ForecastRead)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Gets a specific forecast run by ID."""
    run = get_forecast_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return run


@router.post("/run/{run_id}/pin")
def pin_to_dashboard(run_id: int, db: Session = Depends(get_db)):
    """Pins the forecast chart to the project dashboard."""
    try:
        return pin_forecast_widget(db, run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{run_id}/chat")
def forecast_chat(
    run_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Context-grounded Q&A for the forecasting run."""
    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        return chat_forecast(db, run_id, question)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendation/{dataset_id}")
def get_forecasting_recommendation(dataset_id: int, db: Session = Depends(get_db)):
    """Provides automatic forecasting recommendation for Project Insights."""
    try:
        readiness = inspect_dataset_for_forecasting(db, dataset_id)
        if not readiness["is_ready"]:
            return {
                "has_recommendation": False,
                "message": readiness["reason"],
                "readiness": readiness,
            }

        d_col = readiness["recommended_date_column"]
        t_col = readiness["recommended_target_column"]
        freq = readiness["recommended_frequency"]
        freq_label = "monthly" if "M" in freq else ("daily" if "D" in freq else ("weekly" if "W" in freq else "quarterly"))

        return {
            "has_recommendation": True,
            "title": f"Time-Series Forecasting Recommended: '{t_col}' over '{d_col}'",
            "message": (
                f"Your dataset contains {readiness['row_count']} chronological records across date dimension '{d_col}'. "
                f"Executing a {freq_label} forecast on '{t_col}' will model future momentum, seasonal peaks, and uncertainty bands."
            ),
            "date_column": d_col,
            "target_column": t_col,
            "frequency": freq,
            "route": f"/forecasting/{dataset_id}",
            "readiness": readiness,
        }
    except Exception as e:
        return {"has_recommendation": False, "error": str(e)}
