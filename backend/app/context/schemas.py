"""Pydantic schemas for Analyticx AI's Shared Live Application Context Engine."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ScreenMetadata(BaseModel):
    route: str = Field(default="/", description="Current frontend route (e.g. /workspace, /data-prep/33)")
    screen_name: str = Field(default="Workspace", description="Human-readable screen title")
    screen_description: Optional[str] = Field(default=None, description="What the user can do on this screen")


class FileContext(BaseModel):
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[Literal["csv", "excel", "pdf", "extracted_table", "report"]] = None
    pdf_page_number: Optional[int] = None
    pdf_total_pages: Optional[int] = None
    selected_pdf_text: Optional[str] = None


class DatasetContext(BaseModel):
    dataset_id: Optional[int] = None
    dataset_name: Optional[str] = None
    version: int = 1
    row_count: int = 0
    column_count: int = 0
    quality_score: Optional[float] = None
    selected_columns: List[str] = Field(default_factory=list)
    focused_column: Optional[str] = None
    focused_column_stats: Optional[Dict[str, Any]] = None
    pending_decisions_count: int = 0
    last_cleaning_action: Optional[str] = None


class DashboardContext(BaseModel):
    dashboard_id: Optional[int] = None
    dashboard_name: Optional[str] = None
    selected_widget_id: Optional[int] = None
    selected_chart_type: Optional[str] = None
    selected_chart_title: Optional[str] = None
    active_measures: List[str] = Field(default_factory=list)
    active_dimensions: List[str] = Field(default_factory=list)
    active_filters: Dict[str, Any] = Field(default_factory=dict)
    widgets_count: int = 0


class ActivityContext(BaseModel):
    recent_actions: List[Dict[str, Any]] = Field(default_factory=list)
    task_status: Literal["idle", "running", "completed", "failed"] = "idle"
    has_unsaved_changes: bool = False


class VisualSnapshotData(BaseModel):
    has_snapshot: bool = False
    snapshot_timestamp: Optional[str] = None
    dom_summary: Optional[str] = Field(default=None, description="Structured text summary of visible workspace elements")
    image_base64: Optional[str] = Field(default=None, description="Optional base64 encoded PNG of workspace")


class LiveApplicationContext(BaseModel):
    """Authoritative shared live context object captured from the frontend."""
    workspace_id: Optional[str] = "default"
    workspace_name: Optional[str] = "Main Workspace"
    screen: ScreenMetadata = Field(default_factory=ScreenMetadata)
    file: FileContext = Field(default_factory=FileContext)
    dataset: DatasetContext = Field(default_factory=DatasetContext)
    dashboard: DashboardContext = Field(default_factory=DashboardContext)
    activity: ActivityContext = Field(default_factory=ActivityContext)
    visual: Optional[VisualSnapshotData] = None
    language_preference: str = "auto"


class ScreenExplanationRequest(BaseModel):
    question: Optional[str] = Field(default="What does the current screen show?", description="User question about screen")
    context: LiveApplicationContext
    language: Optional[str] = "auto"
    use_llm: bool = True


class ScreenExplanationResponse(BaseModel):
    screen_summary: str
    active_file_summary: Optional[str] = None
    analysis_status: str
    recommended_next_steps: List[str] = Field(default_factory=list)
    key_observations: List[str] = Field(default_factory=list)
    warnings_or_issues: List[str] = Field(default_factory=list)
    detected_language: str
    language_name: str
    is_visual_analysis: bool = False


class VisualAnalysisRequest(BaseModel):
    image_base64: Optional[str] = None
    context: LiveApplicationContext
    query: Optional[str] = "Analyze what is visible on this screen"
    language: Optional[str] = "auto"


class VisualAnalysisResponse(BaseModel):
    explanation: str
    visual_elements_detected: List[str] = Field(default_factory=list)
    layout_health: str = "Good"
    numerical_grounding_note: str
    suggested_actions: List[str] = Field(default_factory=list)
