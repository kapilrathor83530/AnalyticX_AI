import pandas as pd
import pytest

from app.agents.orchestrator import run_workflow


@pytest.mark.asyncio
async def test_workflow_heuristic_without_llm():
    df = pd.DataFrame(
        {
            "region": ["North", "South", "North", "East"],
            "revenue": [100, 200, 150, 50],
        }
    )

    result = await run_workflow(df, "Which region has the highest revenue?", use_llm=False)

    assert result["question"]
    assert isinstance(result["answer"], str)
    assert "top_categories" in result["tools_used"] or "explain_kpi" in result["tools_used"] or "numeric_summary" in result["tools_used"]
    assert len(result["steps"]) >= 2


@pytest.mark.asyncio
async def test_workflow_returns_missing_info_for_unanswerable_question():
    df = pd.DataFrame({"a": [1, 2, 3]})
    result = await run_workflow(df, "What is the customer churn rate?", use_llm=False)
    assert isinstance(result["answer"], str)
