"""Data Quality Agent for Analyticx AI.
Profiles data, detects missing values, duplicates, outliers, and anomalies; proposes and verifies cleaning operations.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from app.agents.base_agent import BaseSpecializedAgent
from app.agents.tool_registry import tool_registry
from app.analytics.data_quality import inspect_data_quality


class DataQualityAgent(BaseSpecializedAgent):
    """
    Profiles data, detects missing values, duplicates, outliers, type mismatches,
    and anomalies; proposes and verifies cleaning operations.
    """

    def __init__(self):
        super().__init__(
            name="DataQualityAgent",
            description="Profiles data quality, detects anomalies/outliers/duplicates/missing values, and generates cleaning policies.",
        )

    def detect_quality_issues(self, df: pd.DataFrame) -> Dict[str, Any]:
        return tool_registry.execute("detect_data_quality_issues", df=df)

    def preview_cleaning(
        self,
        df: pd.DataFrame,
        action_type: str,
        column: Optional[str] = None,
        strategy: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return tool_registry.execute(
            "preview_cleaning_changes",
            df=df,
            action_type=action_type,
            column=column,
            strategy=strategy,
            parameters=parameters or {},
        )

    def generate_cleaning_plan(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        report = inspect_data_quality(df)
        plan: List[Dict[str, Any]] = []

        # 1. Duplicates
        if report["summary"]["duplicate_rows"] > 0:
            plan.append({
                "action_type": "remove_duplicates",
                "strategy": "remove_exact",
                "priority": "high",
                "reason": f"Found {report['summary']['duplicate_rows']} duplicate rows.",
            })

        # 2. Missing values
        for col, count in report.get("missing_by_column", {}).items():
            if count > 0:
                is_num = pd.api.types.is_numeric_dtype(df[col]) if col in df.columns else False
                strat = "median" if is_num else "mode"
                plan.append({
                    "action_type": "impute_missing",
                    "column": col,
                    "strategy": strat,
                    "priority": "medium",
                    "reason": f"Column '{col}' has {count} missing values ({count / len(df) * 100:.1f}%).",
                })

        # 3. Outliers
        for col, count in report.get("outliers_by_column", {}).items():
            if count > 0:
                plan.append({
                    "action_type": "handle_outliers",
                    "column": col,
                    "strategy": "winsorize",
                    "priority": "low",
                    "reason": f"Column '{col}' has {count} statistical outliers.",
                })

        return plan


data_quality_agent = DataQualityAgent()
