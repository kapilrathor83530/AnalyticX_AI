from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    original_filename: str
    size_bytes: int
    row_count: int
    column_count: int
    created_at: datetime


class DatasetPreview(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    returned_rows: int


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    inferred_type: str
    missing_count: int
    missing_percent: float
    unique_count: int
    sample_values: List[Any]


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: List[ColumnProfile]
    numeric_summary: Dict[str, Dict[str, Any]]
    categorical_summary: Dict[str, List[Dict[str, Any]]]
