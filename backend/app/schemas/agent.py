from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class TaskState(str, Enum):
    PENDING = "Pending"
    PLANNING = "Planning"
    RUNNING = "Running"
    AWAITING_USER_INPUT = "Awaiting User Input"
    VALIDATING = "Validating"
    RETRYING = "Retrying"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class AgentStep(BaseModel):
    agent: str
    tool: str
    status: str  # "ok" | "error" | "skipped"
    message: str
    result: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


class AgentExecutionStep(BaseModel):
    step_number: int = Field(ge=1, le=11)
    step_name: str
    status: str = "ok"  # "ok" | "warning" | "error"
    agent: Optional[str] = None
    tool: Optional[str] = None
    duration_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    details: str = ""


class ValidationReport(BaseModel):
    passed: bool
    checks: List[ValidationCheck] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0


class AgentQueryRequest(BaseModel):
    dataset_id: int
    question: str
    use_llm: bool = True


class AgentQueryResponse(BaseModel):
    question: str
    answer: str
    tools_used: List[str] = Field(default_factory=list)
    steps: List[AgentStep] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    verified_facts: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    chart_config: Optional[Dict[str, Any]] = None
    available: bool = True
    error: Optional[str] = None


class BusinessChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class BusinessChatRequest(BaseModel):
    dataset_id: int
    messages: List[BusinessChatMessage] = Field(min_length=1, max_length=12)


class BusinessChatResponse(BaseModel):
    answer: str
    verified_facts: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    chart_config: Optional[Dict[str, Any]] = None
    available: bool
    model: str


class AgentTaskRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    dataset_id: Optional[int] = None
    document_id: Optional[int] = None
    page_number: Optional[int] = None
    language_override: Optional[str] = "auto"
    use_llm: bool = True


class AgentTaskResponse(BaseModel):
    task_id: str
    state: TaskState
    query: str
    detected_language: str = "en"
    assigned_agent: str
    plan: List[str] = Field(default_factory=list)
    execution_steps: List[AgentExecutionStep] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    validation: ValidationReport
    retries_count: int = 0
    answer: str
    verified_facts: List[str] = Field(default_factory=list)
    business_insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    chart_config: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)
    duration_total_ms: float = 0.0
