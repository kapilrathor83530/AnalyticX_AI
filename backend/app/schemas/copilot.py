"""Schemas for Analyticx AI's Multilingual, Context-Aware Business Copilot."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class WorkspaceContext(BaseModel):
    """Structured context capturing the user's active workspace state."""
    workspace_mode: Optional[str] = Field(
        default="dataset",
        description="Active area: dataset, data_prep, pdf_analysis, dashboard, visualization, forecasting, simulation",
    )
    dataset_id: Optional[int] = None
    dataset_name: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    selected_column: Optional[str] = None
    dashboard_id: Optional[int] = None
    dashboard_name: Optional[str] = None
    widget_id: Optional[int] = None
    widget_title: Optional[str] = None
    chart_type: Optional[str] = None
    active_filters: Optional[Dict[str, Any]] = None
    language_override: Optional[str] = Field(default="auto", description="User chosen language code or 'auto'")
    user_role: Optional[str] = None
    experience_level: Optional[str] = None
    explanation_level: Optional[str] = None


class CopilotChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=5000)


class Citation(BaseModel):
    page: int
    source_type: str = "text"  # "text" | "table" | "heading"
    snippet: str
    confidence: float = 1.0


class CopilotChatRequest(BaseModel):
    messages: List[CopilotChatMessage] = Field(min_length=1)
    context: Optional[WorkspaceContext] = None
    language: Optional[str] = "auto"
    use_llm: bool = True


class CopilotChatResponse(BaseModel):
    answer: str
    detected_language: str
    language_name: str
    script: str
    active_context: Optional[Dict[str, Any]] = None
    citations: List[Citation] = Field(default_factory=list)
    verified_facts: List[str] = Field(default_factory=list)
    method_explanation: Optional[str] = None
    business_insights: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    executed_action: Optional[Dict[str, Any]] = None
    tools_used: List[str] = Field(default_factory=list)
    available: bool = True
    model: str = ""


class PdfPageContent(BaseModel):
    page_number: int
    text: str
    tables_count: int
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    char_count: int


class PdfAskRequest(BaseModel):
    dataset_id: Optional[int] = None
    document_path: Optional[str] = None
    question: str
    page_number: Optional[int] = None
    language: Optional[str] = "auto"


class LanguageOption(BaseModel):
    code: str
    name: str
    script: str
    native: str
