"""Validation Agent for Analyticx AI.
Independently verifies calculations, intermediate results, edge cases, citations, and numerical consistency.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from app.agents.base_agent import BaseSpecializedAgent
from app.schemas.agent import ValidationCheck, ValidationReport
from app.visualization.chart_registry import CHART_REGISTRY
from app.visualization.chart_schemas import ChartConfig
from app.visualization.chart_validator import validate_chart_config


class ValidationAgent(BaseSpecializedAgent):
    """
    Independently checks calculation inputs, intermediate results, edge cases,
    citation references, chart encodings, and numerical consistency before output presentation.
    """

    def __init__(self):
        super().__init__(
            name="ValidationAgent",
            description="Independently verifies calculation results, bounds, schemas, citations, and numerical consistency.",
        )

    def verify_numeric_summary(self, summary: Dict[str, Any], df: Optional[pd.DataFrame] = None) -> ValidationReport:
        checks: List[ValidationCheck] = []
        issues: List[str] = []

        # Check column existence if df provided
        col = summary.get("column")
        if df is not None and col:
            exists = col in df.columns
            checks.append(ValidationCheck(name="column_exists", passed=exists, details=f"Column '{col}' in DataFrame."))
            if not exists:
                issues.append(f"Column '{col}' not found in dataset.")

        # Check counts non-negative
        count = summary.get("count", 0)
        checks.append(ValidationCheck(name="count_non_negative", passed=(count >= 0), details=f"Count is {count}."))
        if count < 0:
            issues.append(f"Count cannot be negative ({count}).")

        # Check min <= mean <= max
        min_v = summary.get("min")
        mean_v = summary.get("mean")
        max_v = summary.get("max")
        if min_v is not None and max_v is not None and mean_v is not None:
            bounds_ok = (min_v <= mean_v <= max_v)
            checks.append(ValidationCheck(name="mean_within_bounds", passed=bounds_ok, details=f"{min_v} <= {mean_v} <= {max_v}"))
            if not bounds_ok:
                issues.append(f"Mean {mean_v} is outside the range [{min_v}, {max_v}].")

        # Check std >= 0
        std_v = summary.get("std")
        if std_v is not None:
            std_ok = (std_v >= 0)
            checks.append(ValidationCheck(name="std_non_negative", passed=std_ok, details=f"Standard deviation: {std_v}"))
            if not std_ok:
                issues.append(f"Standard deviation cannot be negative ({std_v}).")

        passed = len(issues) == 0
        return ValidationReport(passed=passed, checks=checks, issues=issues, confidence_score=1.0 if passed else 0.5)

    def verify_chart_config(self, chart_config: Dict[str, Any], df: Optional[pd.DataFrame] = None) -> ValidationReport:
        checks: List[ValidationCheck] = []
        issues: List[str] = []

        chart_type = chart_config.get("chart_type")
        valid_types = set(CHART_REGISTRY.keys())
        type_ok = chart_type in valid_types
        checks.append(ValidationCheck(name="valid_chart_type", passed=type_ok, details=f"Type: {chart_type}"))
        if not type_ok:
            issues.append(f"Invalid chart type '{chart_type}'.")

        mapping = dict(chart_config.get("data_mapping") or {})
        if not mapping:
            if chart_config.get("x"):
                mapping["x"] = chart_config["x"]
            if chart_config.get("y"):
                mapping["y"] = chart_config["y"]

        if df is not None and not df.empty and type_ok and mapping:
            try:
                cfg = ChartConfig(
                    chart_type=str(chart_type),
                    title=chart_config.get("title"),
                    data_mapping=mapping,
                    aggregation=chart_config.get("aggregation") or "sum",
                )
                vres = validate_chart_config(df, cfg)
                checks.append(ValidationCheck(name="chart_schema_validation", passed=vres.valid, details="; ".join(vres.errors or vres.warnings or ["ok"])))
                if not vres.valid:
                    issues.extend(vres.errors)
            except Exception as exc:
                issues.append(f"Chart validation error: {exc}")

        passed = len(issues) == 0
        return ValidationReport(passed=passed, checks=checks, issues=issues, confidence_score=1.0 if passed else 0.5)

    def verify_insight(self, insight: Dict[str, Any], df: Optional[pd.DataFrame] = None) -> ValidationReport:
        checks: List[ValidationCheck] = []
        issues: List[str] = []

        has_title = bool(insight.get("title"))
        has_explanation = bool(insight.get("explanation") or insight.get("finding"))
        has_metrics = bool(insight.get("supporting_metrics"))
        has_methodology = bool(insight.get("methodology"))
        checks.append(ValidationCheck(name="insight_completeness", passed=all([has_title, has_explanation, has_metrics, has_methodology]), details="Title, explanation, supporting metrics, methodology checked"))
        if not has_title or not has_explanation:
            issues.append("Insight missing title or explanation.")
        if not has_metrics:
            issues.append("Insight lacks numerical supporting_metrics evidence.")

        # Correlation insights must include non-causality disclaimer
        if insight.get("category") == "correlation":
            text = f"{insight.get('explanation', '')} {insight.get('limitations', '')}".lower()
            no_causal = "causation" in text or "association" in text
            checks.append(ValidationCheck(name="no_causal_claim_in_correlation", passed=no_causal, details="Causality disclaimer checked"))
            if not no_causal:
                issues.append("Correlation insight lacks causality disclaimer.")

        if df is not None:
            for col in insight.get("source_columns") or []:
                if col not in df.columns:
                    issues.append(f"Referenced source column '{col}' does not exist in dataset.")

        passed = len(issues) == 0
        return ValidationReport(passed=passed, checks=checks, issues=issues, confidence_score=1.0 if passed else 0.5)

    def verify_citation(self, citation: Dict[str, Any], total_pages: Optional[int] = None) -> ValidationReport:
        checks: List[ValidationCheck] = []
        issues: List[str] = []

        page = citation.get("page", 1)
        page_positive = page >= 1
        checks.append(ValidationCheck(name="page_positive", passed=page_positive, details=f"Page: {page}"))
        if not page_positive:
            issues.append(f"Citation page number must be >= 1 (got {page}).")

        if total_pages is not None:
            page_in_bounds = (1 <= page <= total_pages)
            checks.append(ValidationCheck(name="page_within_document", passed=page_in_bounds, details=f"1 <= {page} <= {total_pages}"))
            if not page_in_bounds:
                issues.append(f"Citation page {page} exceeds total document pages ({total_pages}).")

        has_snippet = bool(citation.get("snippet") or citation.get("text"))
        checks.append(ValidationCheck(name="snippet_non_empty", passed=has_snippet, details="Evidence snippet present"))
        if not has_snippet:
            issues.append("Citation lacks verified evidence snippet.")

        passed = len(issues) == 0
        return ValidationReport(passed=passed, checks=checks, issues=issues, confidence_score=1.0 if passed else 0.5)

    def verify_general_result(self, result: Dict[str, Any]) -> ValidationReport:
        checks = [ValidationCheck(name="result_is_dict", passed=isinstance(result, dict), details="Result structure valid")]
        issues = []
        if not isinstance(result, dict):
            issues.append("Result is not a structured dictionary.")
        if "error" in result:
            issues.append(str(result["error"]))
        return ValidationReport(passed=len(issues) == 0, checks=checks, issues=issues, confidence_score=1.0 if not issues else 0.4)


validation_agent = ValidationAgent()
