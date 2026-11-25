from typing import Any, Dict, List, Optional

import pandas as pd

from app.analytics.data_understanding import understand_dataset
from app.visualization.chart_recommender import recommend_charts_for_dataset
from app.visualization.chart_registry import get_chart, list_charts
from app.visualization.chart_schemas import ChartConfig, ChartValidationResult
from app.visualization.chart_validator import validate_chart_config
from app.visualization.data_mapper import build_chart_data


def get_available_charts() -> List[Dict[str, Any]]:
    return [chart.model_dump() for chart in list_charts()]


def validate_config(
    df: pd.DataFrame,
    config_payload: Dict[str, Any],
    understanding: Optional[Dict[str, Any]] = None,
) -> ChartValidationResult:
    config = ChartConfig(**config_payload)
    return validate_chart_config(df, config, understanding=understanding)


def recommend_charts(
    df: pd.DataFrame,
    query: str = "",
    understanding: Optional[Dict[str, Any]] = None,
    max_recommendations: int = 8,
) -> List[Dict[str, Any]]:
    return recommend_charts_for_dataset(
        df,
        query=query,
        understanding=understanding,
        max_recommendations=max_recommendations,
    )


def render_chart(
    df: pd.DataFrame,
    config_payload: Dict[str, Any],
    understanding: Optional[Dict[str, Any]] = None,
    dataset_version: int = 1,
) -> Dict[str, Any]:
    config = ChartConfig(**config_payload)
    definition = get_chart(config.chart_type)
    if not definition:
        return {
            "chart_type": config.chart_type,
            "data": [],
            "layout": {},
            "warnings": [],
            "metadata": {"dataset_version": dataset_version},
            "error": f"Unknown chart type '{config.chart_type}'",
        }

    if understanding is None:
        understanding = understand_dataset(df, sanitize=True)

    norm_df = understanding["normalized_df"]
    validation = validate_chart_config(norm_df, config, understanding=understanding)
    if not validation.valid:
        return {
            "chart_type": config.chart_type,
            "data": [],
            "layout": {"title": config.title or definition.name},
            "warnings": validation.warnings,
            "error": "; ".join(validation.errors),
            "suggested_alternative": validation.suggested_alternative,
            "metadata": {"dataset_version": dataset_version, "validation_passed": False},
        }

    data = build_chart_data(norm_df, config, normalized_df=norm_df)
    total_rows = int(len(norm_df))
    sampled = config.chart_type in {"scatter", "bubble"} and total_rows > 2000 and len(data) == 2000

    layout: Dict[str, Any] = {
        "title": config.title or definition.name,
        "subtitle": config.subtitle,
        "appearance": config.appearance or {},
        "orientation": definition.default_config.get("orientation"),
        "barmode": definition.default_config.get("barmode"),
        "normalized": definition.default_config.get("normalized", False),
    }

    warnings_out = list(validation.warnings)
    if not data:
        warnings_out.append("No matching records remained after applying filters or excluding missing values.")

    return {
        "chart_type": config.chart_type,
        "data": data,
        "layout": layout,
        "warnings": warnings_out,
        "metadata": {
            "dataset_version": dataset_version,
            "total_source_rows": total_rows,
            "rendered_points": len(data),
            "sampled": sampled,
            "validation_passed": True,
        },
    }
