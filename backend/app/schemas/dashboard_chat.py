from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DashboardChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DashboardConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dashboard_id: int
    title: str
    mode: Literal["analysis", "edit"]
    created_at: datetime
    updated_at: datetime


class DashboardChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    mode: Literal["analysis", "edit"] = "analysis"


class DashboardChatResponse(BaseModel):
    conversation: DashboardConversationRead
    message: DashboardChatMessageRead
    answer: str
    verified_facts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    available: bool = False
    model: str = ""
    dashboard_context: dict[str, Any] = Field(default_factory=dict)
    action: dict[str, Any] | None = None


class DashboardRestoreRequest(BaseModel):
    configuration: dict[str, Any]
    name: str | None = Field(default=None, max_length=255)
