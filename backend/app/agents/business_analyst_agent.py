"""Business Analyst Agent for Analyticx AI.
Interprets analytical outputs, derives business implications, benchmarks metrics, flags risks, and generates actionable recommendations.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from app.agents.base_agent import BaseSpecializedAgent
from app.analytics.profiling import to_python


class BusinessAnalystAgent(BaseSpecializedAgent):
    """
    Interprets analytical outputs, derives business implications,
    benchmarks metrics, flags risks, and generates actionable recommendations.
    """

    def __init__(self):
        super().__init__(
            name="BusinessAnalystAgent",
            description="Translates raw numbers into strategic business insights, benchmarks, risk factors, and recommended decisions.",
        )

    def explain_kpi(self, df: pd.DataFrame, metric: str, dimension: Optional[str] = None) -> Dict[str, Any]:
        if metric not in df.columns:
            return {"error": f"Metric '{metric}' not found"}
        if not pd.api.types.is_numeric_dtype(df[metric]):
            return {"error": f"Metric '{metric}' is not numeric"}

        valid_s = pd.to_numeric(df[metric], errors="coerce").dropna()
        total = float(valid_s.sum())
        mean = float(valid_s.mean())

        result: Dict[str, Any] = {
            "metric": metric,
            "total": to_python(round(total, 2)),
            "mean": to_python(round(mean, 2)),
            "min": to_python(round(float(valid_s.min()), 2)),
            "max": to_python(round(float(valid_s.max()), 2)),
        }

        if dimension and dimension in df.columns:
            grouped = df.groupby(dimension)[metric].sum().sort_values(ascending=False).head(5)
            result["top_dimension"] = dimension
            result["top_values"] = [
                {"value": to_python(k), "metric": to_python(round(float(v), 2))}
                for k, v in grouped.items()
            ]

        return result

    def generate_recommendations(self, findings: Dict[str, Any]) -> List[str]:
        recommendations = []
        if "top_values" in findings and findings["top_values"]:
            top = findings["top_values"][0]
            recommendations.append(
                f"Double-down on high-performing segment '{top['value']}' which generated {top['metric']:,} in {findings.get('metric', 'value')}."
            )
        if "quality_score" in findings and findings["quality_score"] < 80:
            recommendations.append(
                f"Prioritize data hygiene: dataset quality score is {findings['quality_score']}%; resolve missing records before executive reporting."
            )
        if "outliers_count" in findings and findings["outliers_count"] > 0:
            recommendations.append(
                f"Investigate {findings['outliers_count']} outlier transactions to identify potential anomalies or data entry errors."
            )
        if not recommendations:
            recommendations.append("Establish automated periodic KPI tracking to detect shifts in volume and variance.")
        return recommendations

    def identify_risks(self, findings: Dict[str, Any]) -> List[str]:
        risks = []
        if "missing_count" in findings and findings["missing_count"] > 0:
            risks.append(f"{findings['missing_count']} unrecorded data points may skew downstream financial projections.")
        if "duplicate_rows" in findings and findings["duplicate_rows"] > 0:
            risks.append("Duplicate transactions risk inflating overall revenue and KPI reporting.")
        if not risks:
            risks.append("Market volatility and unobserved confounding variables may affect performance trajectories.")
        return risks


business_analyst_agent = BusinessAnalystAgent()
