"""Visualization Agent for Analyticx AI.
Selects chart types, validates dimension and metric compatibility, and generates dashboard-ready chart configurations.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from app.agents.base_agent import BaseSpecializedAgent
from app.agents.tool_registry import tool_registry
from app.visualization.chart_registry import get_chart, list_charts


class VisualizationAgent(BaseSpecializedAgent):
    """
    Selects chart types, validates dimension and metric compatibility,
    generates visualization specifications, and prepares dashboard-ready chart configurations.
    """

    def __init__(self):
        super().__init__(
            name="VisualizationAgent",
            description="Recommends chart types, validates dimensions and metrics, and produces dashboard chart configs.",
        )

    def recommend_chart(
        self,
        *args,
        df: Optional[pd.DataFrame] = None,
        query: Optional[str] = None,
        dimension: Optional[str] = None,
        metric: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        target_df = df
        target_query = query or ""
        target_dim = dimension
        target_metric = metric

        if len(args) == 1:
            if isinstance(args[0], pd.DataFrame):
                target_df = args[0]
            elif isinstance(args[0], str):
                target_query = args[0]
        elif len(args) >= 2:
            arg0, arg1 = args[0], args[1]
            if isinstance(arg0, pd.DataFrame):
                target_df = arg0
                target_query = str(arg1) if not isinstance(arg1, (list, tuple)) else ""
            elif isinstance(arg0, str):
                target_query = arg0
                if isinstance(arg1, pd.DataFrame):
                    target_df = arg1
                elif isinstance(arg1, (list, tuple)):
                    target_df = pd.DataFrame(columns=[str(c) for c in arg1])

        if len(args) >= 3 and isinstance(args[2], str):
            target_dim = args[2]
        if len(args) >= 4 and isinstance(args[3], str):
            target_metric = args[3]

        if target_df is None:
            target_df = pd.DataFrame()

        return tool_registry.execute(
            "recommend_chart",
            df=target_df,
            query=str(target_query),
            dimension=target_dim,
            metric=target_metric,
        )

    def build_chart_config(
        self,
        chart_type: str,
        data_mapping: Dict[str, Any],
        title: Optional[str] = None,
        color_scheme: Optional[str] = None,
    ) -> Dict[str, Any]:
        chart = get_chart(chart_type)
        return {
            "chart_type": chart_type,
            "title": title or (chart.name if chart else chart_type.capitalize()),
            "data_mapping": data_mapping,
            "aggregation": "sum",
            "appearance": {
                "color": color_scheme or "#0284c7",
                "legend": True,
                "responsive": True,
            },
        }

    def list_charts(self) -> List[Dict[str, Any]]:
        return [c.model_dump() for c in list_charts()]


visualization_agent = VisualizationAgent()
