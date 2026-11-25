from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScenarioAdjustment(BaseModel):
    field: str
    mode: str  # "percent" | "absolute"
    value: float


class ScenarioRunRequest(BaseModel):
    dataset_id: int
    name: str
    description: Optional[str] = None
    adjustments: List[ScenarioAdjustment] = Field(default_factory=list)
    metric_columns: Dict[str, str] = Field(default_factory=dict)
    elasticity: Optional[float] = None


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    name: str
    description: Optional[str] = None
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)
    assumptions: Dict[str, Any] = Field(default_factory=dict)
    adjustments: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ScenarioCompareRequest(BaseModel):
    scenario_ids: List[int]
