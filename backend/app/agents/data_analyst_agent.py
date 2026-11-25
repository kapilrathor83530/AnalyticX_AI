"""Data Analyst Agent for Analyticx AI.
Executes deterministic analytical routines, aggregations, groupings, statistical summaries, trends, and comparisons.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from app.agents.base_agent import BaseSpecializedAgent
from app.agents.tool_registry import tool_registry
from app.analytics.profiling import profile_dataframe, to_python


class DataAnalystAgent(BaseSpecializedAgent):
    """
    Executes deterministic analytical routines, aggregations, groupings,
    statistical summaries, trends, and comparisons on active or referenced datasets.
    """

    def __init__(self):
        super().__init__(
            name="DataAnalystAgent",
            description="Executes deterministic analytical routines, aggregations, groupings, and statistical summaries.",
        )

    def profile_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        return tool_registry.execute("profile_dataset", df=df)

    def summarize_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {
            "row_count": int(df.shape[0]),
            "column_count": int(df.shape[1]),
            "numeric_columns": [str(c) for c in df.select_dtypes(include="number").columns],
            "categorical_columns": [
                str(c) for c in df.select_dtypes(include=["object", "category", "bool"]).columns
            ],
        }

    def numeric_summary(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        return tool_registry.execute("numeric_summary", df=df, column=column)

    def top_categories(self, df: pd.DataFrame, dimension: str, metric: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        return tool_registry.execute("top_categories", df=df, dimension=dimension, metric=metric, limit=limit)

    def correlation_summary(self, df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Any]:
        return tool_registry.execute("correlation_summary", df=df, columns=columns)

    def describe_column(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        if column not in df.columns:
            return {"error": f"Column '{column}' not found"}
        series = df[column]
        result = {
            "column": column,
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            result["summary"] = {str(k): to_python(v) for k, v in series.describe().to_dict().items()}
        else:
            result["top_values"] = [
                {"value": to_python(k), "count": int(v)}
                for k, v in series.value_counts(dropna=False).head(10).items()
            ]
        return result


data_analyst_agent = DataAnalystAgent()
