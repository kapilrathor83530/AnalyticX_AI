from typing import Any, Dict

import pandas as pd

from app.agents.orchestrator import run_workflow


async def run_query(df: pd.DataFrame, question: str, use_llm: bool = True) -> Dict[str, Any]:
    return await run_workflow(df, question, use_llm=use_llm)
