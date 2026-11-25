from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    is_sample: bool = False
    name: str
    original_filename: str
    size_bytes: int
    row_count: int
    column_count: int
    status: str = "Analysis Ready"
    parent_id: Optional[int] = None
    version: int = 1
    quality_score: Optional[float] = None
    dataset_metadata: Optional[dict[str, Any]] = None
    created_at: datetime


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int
    returned_rows: int


class ColumnProfile(BaseModel):
    name: str
    column_name: Optional[str] = None
    dtype: str
    inferred_type: str
    detected_type: Optional[str] = None
    semantic_type: Optional[str] = None
    role: Optional[str] = None
    format_hint: Optional[str] = None
    missing_count: int
    missing_percent: float
    missing_percentage: Optional[float] = None
    unique_count: int
    is_identifier: bool = False
    is_constant: bool = False
    is_high_cardinality: bool = False
    analysis_eligible: bool = True
    sample_values: list[Any]


class DatasetProfile(BaseModel):
    dataset_name: Optional[str] = None
    row_count: int
    column_count: int
    total_cells: Optional[int] = None
    memory_bytes: Optional[int] = None
    duplicate_rows: int
    numerical_columns: list[str] = []
    categorical_columns: list[str] = []
    boolean_columns: list[str] = []
    datetime_columns: list[str] = []
    identifier_columns: list[str] = []
    constant_columns: list[str] = []
    high_cardinality_columns: list[str] = []
    geographic_columns: list[str] = []
    text_columns: list[str] = []
    empty_columns: list[str] = []
    columns: list[ColumnProfile]
    numeric_summary: dict[str, dict[str, Any]]
    categorical_summary: dict[str, list[dict[str, Any]]]
    validation: Optional[dict[str, Any]] = None
