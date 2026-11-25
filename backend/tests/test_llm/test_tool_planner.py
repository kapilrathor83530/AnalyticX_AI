from app.llm.tool_planner import ToolPlanEnvelope, validate_plan
from app.schemas.llm import ToolPlan


def test_plan_rejects_unknown_column_argument():
    candidate = ToolPlanEnvelope(plan=[ToolPlan(
        tool="top_categories", arguments={"dimension": "made_up", "metric": "revenue"}, rationale="test"
    )])
    validated = validate_plan(candidate, ["region", "revenue"])
    assert validated.plan == []
    assert validated.clarification_needed is True


def test_plan_accepts_allowed_tool_and_real_columns():
    candidate = ToolPlanEnvelope(plan=[ToolPlan(
        tool="top_categories", arguments={"dimension": "region", "metric": "revenue", "limit": 10}, rationale="test"
    )])
    validated = validate_plan(candidate, ["region", "revenue"])
    assert len(validated.plan) == 1
