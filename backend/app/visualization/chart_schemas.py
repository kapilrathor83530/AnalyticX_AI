from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataRole(BaseModel):
    name: str
    label: str
    type: str  # "dimension" | "measure" | "date" | "size" | "color"
    required: bool = False
    multiple: bool = False


class ChartTypeDefinition(BaseModel):
    id: str
    name: str
    category: str
    icon: str
    data_roles: List[DataRole]
    config_options: List[str]
    default_config: Dict[str, Any] = Field(default_factory=dict)


class ChartConfig(BaseModel):
    chart_type: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    data_mapping: Dict[str, Any] = Field(default_factory=dict)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    sort: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    appearance: Dict[str, Any] = Field(default_factory=dict)
    aggregation: Optional[str] = None


class ChartValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggested_alternative: Optional[str] = None


class ChartRenderRequest(BaseModel):
    dataset_id: int
    config: ChartConfig


class ChartRenderResponse(BaseModel):
    chart_type: str
    data: List[Dict[str, Any]]
    layout: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
