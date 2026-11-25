from typing import Any, Dict, Iterable, List

ALLOWED_TOOLS = {
    "profile_dataset",
    "summarize_dataset",
    "top_categories",
    "numeric_summary",
    "analyze_numerical_column",
    "analyze_categorical_column",
    "analyze_datetime_column",
    "correlation_summary",
    "calculate_correlation",
    "detect_outliers",
    "analyze_group_comparison",
    "generate_time_series",
    "describe_column",
    "detect_data_quality_issues",
    "recommend_chart",
    "build_chart_config",
    "validate_chart",
    "validate_insight",
    "explain_kpi",
}


def validate_tool_names(tools: Iterable[str]) -> List[str]:
    return [t for t in tools if t in ALLOWED_TOOLS]


def validate_columns(columns: Iterable[str], available: Iterable[str]) -> List[str]:
    available_set = set(available)
    return [c for c in columns if c in available_set]


def validate_result_shape(result: Any) -> bool:
    return isinstance(result, dict)
