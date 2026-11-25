from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    context: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1024


class ChatResponse(BaseModel):
    answer: str
    model: str
    available: bool
    error: Optional[str] = None


class CommandRequest(BaseModel):
    dataset_id: int
    command: str


class CommandResponse(BaseModel):
    action: str
    chart_type: Optional[str] = None
    data_mapping: Dict[str, Any] = Field(default_factory=dict)
    value: Any = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    available: bool = True
    error: Optional[str] = None


class ModelStatus(BaseModel):
    available: bool
    active_model: str
    active_model_installed: bool
    installed_models: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class ToolPlan(BaseModel):
    """A constrained plan only; it is never executable code."""
    tool: Literal[
        "profile_dataset", "summarize_dataset", "top_categories", "numeric_summary",
        "correlation_summary", "describe_column", "recommend_chart", "build_chart_config",
        "explain_kpi",
    ]
    arguments: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(max_length=500)


class AnalysisPlanRequest(BaseModel):
    dataset_id: int
    question: str = Field(min_length=3, max_length=2000)


class AnalysisPlanResponse(BaseModel):
    plan: List[ToolPlan] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    available: bool
    error: Optional[str] = None
