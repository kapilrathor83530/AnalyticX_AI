"""Schema-constrained, non-executable planning for business analytics."""

from typing import Any, Dict, Iterable, List

from pydantic import BaseModel, Field, ValidationError

from app.agents.validation_layer import ALLOWED_TOOLS
from app.llm.model_manager import ModelManager, model_manager
from app.llm.prompt_templates import TOOL_PLAN_SYSTEM, build_tool_plan_prompt
from app.llm.response_parser import extract_json
from app.schemas.llm import ToolPlan


class ToolPlanEnvelope(BaseModel):
    plan: List[ToolPlan] = Field(default_factory=list, max_length=6)
    clarification_needed: bool = False
    clarification_question: str | None = Field(default=None, max_length=500)


def _contains_only_known_columns(value: Any, columns: set[str]) -> bool:
    if isinstance(value, str):
        # Non-column values are only allowed in known chart configuration keys.
        return value in columns or value in {"bar", "line", "pie", "donut", "scatter", "kpi", "asc", "desc"}
    if isinstance(value, (int, float)):
        return isinstance(value, int) and 0 < value <= 100
    if isinstance(value, list):
        return all(_contains_only_known_columns(item, columns) for item in value)
    if isinstance(value, dict):
        return all(_contains_only_known_columns(item, columns) for item in value.values())
    return value is None


def validate_plan(envelope: ToolPlanEnvelope, columns: Iterable[str]) -> ToolPlanEnvelope:
    allowed_columns = {str(column) for column in columns}
    accepted: List[ToolPlan] = []
    for step in envelope.plan:
        if step.tool not in ALLOWED_TOOLS:
            continue
        if not _contains_only_known_columns(step.arguments, allowed_columns):
            continue
        accepted.append(step)
    if envelope.plan and not accepted:
        return ToolPlanEnvelope(
            clarification_needed=True,
            clarification_question="Please specify dataset columns using the names shown in the dataset explorer.",
        )
    return ToolPlanEnvelope(
        plan=accepted,
        clarification_needed=envelope.clarification_needed,
        clarification_question=envelope.clarification_question,
    )


async def create_plan(question: str, columns: Iterable[str], manager: ModelManager = model_manager) -> ToolPlanEnvelope:
    column_list = [str(column) for column in columns]
    status = await manager.status()
    if not status.get("available") or not status.get("active_model_installed"):
        return ToolPlanEnvelope(
            clarification_needed=True,
            clarification_question="Local model is unavailable. You can still use the deterministic dataset tools.",
        )
    raw = await manager.generate(
        prompt=build_tool_plan_prompt(question, sorted(ALLOWED_TOOLS), column_list),
        system=TOOL_PLAN_SYSTEM,
        format_json=ToolPlanEnvelope.model_json_schema(),
        temperature=0,
        max_tokens=700,
    )
    try:
        payload = extract_json(raw) or {}
        return validate_plan(ToolPlanEnvelope.model_validate(payload), column_list)
    except ValidationError:
        return ToolPlanEnvelope(
            clarification_needed=True,
            clarification_question="I could not produce a valid safe analysis plan. Please rephrase the request.",
        )
