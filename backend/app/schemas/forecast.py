from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ForecastTrainRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    dataset_id: int
    date_column: str
    target_column: str
    horizon: int = 12
    frequency: str = "M"
    model_type: Optional[str] = None
    group_dimension: Optional[str] = None
    group_value: Optional[str] = None
    fill_strategy: Optional[str] = "interpolate"
    handle_outliers: Optional[bool] = True
    custom_assumptions: Optional[Dict[str, Any]] = None


class ForecastMetrics(BaseModel):
    mae: Optional[float] = None
    rmse: Optional[float] = None
    wape: Optional[float] = None
    mase: Optional[float] = None
    mape: Optional[float] = None
    r2: Optional[float] = None
    baseline_mae: Optional[float] = None
    baseline_rmse: Optional[float] = None
    baseline_wape: Optional[float] = None
    wape_improvement_vs_naive_pct: Optional[float] = None


class ForecastPoint(BaseModel):
    date: str
    value: float
    lower_80: Optional[float] = None
    upper_80: Optional[float] = None
    lower_95: Optional[float] = None
    upper_95: Optional[float] = None


class ForecastTrainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    dataset_id: int
    model_type: str
    target_column: str
    date_column: str
    group_dimension: Optional[str] = None
    group_value: Optional[str] = None
    horizon: int
    frequency: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)
    candidate_models: List[Dict[str, Any]] = Field(default_factory=list)
    backtest_results: Dict[str, Any] = Field(default_factory=dict)
    confidence_intervals: Dict[str, Any] = Field(default_factory=dict)
    scenarios: Dict[str, Any] = Field(default_factory=dict)
    insights: Dict[str, Any] = Field(default_factory=dict)
    data_validation: Dict[str, Any] = Field(default_factory=dict)
    training_time_ms: Optional[float] = 0.0
    notes: Optional[str] = None
    created_at: datetime


class ForecastRead(ForecastTrainResponse):
    pass
