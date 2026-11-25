import pandas as pd
import pytest

from app.agents.orchestrator import run_workflow


@pytest.mark.asyncio
async def test_missing_named_metric_is_not_replaced_with_a_count():
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [10, 20]})
    result = await run_workflow(df, "Which region has the highest units_sold?", use_llm=False)
    assert "requested numeric metric column" in result["missing_info"]
    assert "top_categories" not in result["tools_used"]
