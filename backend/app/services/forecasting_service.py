"""Forecasting Service Orchestration for Analyticx AI."""
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.forecasting.insights_agent import answer_forecasting_chat
from app.forecasting.predictor import run_advanced_forecast
from app.forecasting.preprocessor import detect_time_series_readiness
from app.models.dashboard import Dashboard
from app.models.dataset import Dataset
from app.models.forecast import ForecastRun
from app.models.widget import Widget
from app.services.data_service import load_dataset_df

logger = logging.getLogger(__name__)


def inspect_dataset_for_forecasting(db: Session, dataset_id: int) -> Dict[str, Any]:
    """Inspects a dataset and returns readiness, candidate date/target columns, and frequency."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset #{dataset_id} not found.")

    df = load_dataset_df(dataset)
    return detect_time_series_readiness(df)


def train_forecast(
    db: Session,
    df: pd.DataFrame,
    dataset_id: int,
    date_column: str,
    target_column: str,
    horizon: int = 12,
    frequency: str = "M",
    model_type: Optional[str] = None,
    group_dimension: Optional[str] = None,
    group_value: Optional[str] = None,
    fill_strategy: str = "interpolate",
    handle_outliers: bool = True,
    custom_assumptions: Optional[Dict[str, Any]] = None,
) -> ForecastRun:
    """Trains candidate models, performs chronological backtesting, generates forecast, scenarios, and persists."""
    result = run_advanced_forecast(
        df=df,
        date_column=date_column,
        target_column=target_column,
        horizon=horizon,
        frequency=frequency,
        model_type=model_type,
        group_dimension=group_dimension,
        group_value=group_value,
        fill_strategy=fill_strategy,
        handle_outliers=handle_outliers,
        custom_assumptions=custom_assumptions,
    )

    if "error" in result:
        raise ValueError(result["error"])

    run = ForecastRun(
        dataset_id=dataset_id,
        model_type=result.get("model_type", model_type or "naive"),
        target_column=target_column,
        date_column=date_column,
        group_dimension=group_dimension,
        group_value=group_value,
        horizon=horizon,
        frequency=result.get("frequency", frequency),
        metrics=result.get("metrics", {}),
        predictions=result.get("predictions", []),
        candidate_models=result.get("candidate_models", []),
        backtest_results=result.get("backtest_results", {}),
        confidence_intervals=result.get("confidence_intervals", {}),
        scenarios=result.get("scenarios", {}),
        insights=result.get("insights", {}),
        data_validation=result.get("data_validation", {}),
        training_time_ms=result.get("training_time_ms", 0.0),
        notes=result.get("selection_reason"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_forecasts(db: Session, dataset_id: int) -> List[ForecastRun]:
    """Lists recent forecasting runs for a dataset."""
    return (
        db.query(ForecastRun)
        .filter(ForecastRun.dataset_id == dataset_id)
        .order_by(ForecastRun.created_at.desc())
        .all()
    )


def get_forecast_run(db: Session, run_id: int) -> Optional[ForecastRun]:
    """Fetches a specific forecast run by ID."""
    return db.query(ForecastRun).filter(ForecastRun.id == run_id).first()


def pin_forecast_widget(db: Session, run_id: int) -> Dict[str, Any]:
    """Pins the forecast chart and its prediction intervals onto the dataset's dashboard."""
    run = get_forecast_run(db, run_id)
    if not run:
        raise ValueError(f"Forecast run #{run_id} not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset #{run.dataset_id} not found.")

    dashboard = db.query(Dashboard).filter(Dashboard.dataset_id == dataset.id).first()
    if not dashboard:
        dashboard = Dashboard(
            name=f"{dataset.name} Forecast & Decision Dashboard",
            dataset_id=dataset.id,
            workspace_id=dataset.dataset_metadata.get("workspace_id") if dataset.dataset_metadata else None,
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)

    existing_count = db.query(Widget).filter(Widget.dashboard_id == dashboard.id).count()

    widget = Widget(
        dashboard_id=dashboard.id,
        title=f"Forecast: {run.target_column} ({run.model_type.upper()})",
        chart_type="line",
        config={
            "x_axis": run.date_column,
            "y_axis": run.target_column,
            "dataset_id": dataset.id,
            "forecast_run_id": run.id,
            "horizon": run.horizon,
            "appearance": {"color": "#22d3ee"},
        },
        data_mapping={"x": run.date_column, "y": run.target_column},
        position={"x": (existing_count % 2) * 6, "y": (existing_count // 2) * 4},
        size={"w": 6, "h": 4},
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)

    return {
        "success": True,
        "dashboard_id": dashboard.id,
        "widget_id": widget.id,
        "route": f"/dashboard/{dashboard.id}/edit",
    }


def chat_forecast(db: Session, run_id: int, question: str) -> Dict[str, Any]:
    """Processes Q&A grounded strictly in the forecast run's outputs."""
    run = get_forecast_run(db, run_id)
    if not run:
        raise ValueError(f"Forecast run #{run_id} not found.")

    return answer_forecasting_chat(run, question)
