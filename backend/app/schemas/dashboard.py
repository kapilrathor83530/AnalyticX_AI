from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WidgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dashboard_id: int
    chart_type: str
    title: str
    config: Dict[str, Any]
    data_mapping: Dict[str, Any]
    position: Dict[str, Any]
    size: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


class WidgetCreate(BaseModel):
    chart_type: str
    title: str
    config: Dict[str, Any] = Field(default_factory=dict)
    data_mapping: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, Any] = Field(default_factory=lambda: {"x": 0, "y": 0})
    size: Dict[str, Any] = Field(default_factory=lambda: {"w": 6, "h": 4})


class WidgetUpdate(BaseModel):
    chart_type: Optional[str] = None
    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    data_mapping: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None
    size: Optional[Dict[str, Any]] = None


class DashboardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    workspace_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    layout_config: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class DashboardCreate(BaseModel):
    dataset_id: int
    workspace_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    layout_config: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


class LayoutUpdate(BaseModel):
    layout_config: Dict[str, Any] = Field(default_factory=dict)
