from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChartConfigPayload(BaseModel):
    chart_type: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    data_mapping: Dict[str, Any] = Field(default_factory=dict)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    sort: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    appearance: Dict[str, Any] = Field(default_factory=dict)
    aggregation: Optional[str] = None
