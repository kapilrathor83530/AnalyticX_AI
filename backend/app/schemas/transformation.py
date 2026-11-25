from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TransformationSpec(BaseModel):
    type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class TransformationApplyRequest(BaseModel):
    transformations: List[TransformationSpec]


class TransformationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    transformation_type: str
    parameters: Dict[str, Any]
    description: Optional[str] = None
    row_count_before: int
    row_count_after: int
    applied_at: datetime
