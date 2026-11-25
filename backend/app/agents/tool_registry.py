"""Approved Tool Registry with Typed Schemas, Argument Validation, and Bounded Execution for Analyticx AI."""
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.analytics.cleaning import apply_transformations
from app.analytics.data_quality import inspect_data_quality
from app.analytics.data_understanding import understand_dataset
from app.analytics.eda_engine import generate_eda_report
from app.analytics.statistics import (
    analyze_categorical_column,
    analyze_datetime_column,
    analyze_numerical_column,
    calculate_correlation,
    compare_groups,
    detect_outliers,
)
from app.services.pdf_rag_service import get_pdf_index, query_pdf_document
from app.visualization.chart_recommender import recommend_charts_for_dataset, select_best_chart_for_query
from app.visualization.chart_schemas import ChartConfig
from app.visualization.chart_validator import validate_chart_config


class ToolExecutionError(Exception):
    def __init__(self, message: str, failure_type: str = "invalid_input", recoverable: bool = True):
        super().__init__(message)
        self.failure_type = failure_type  # transient, invalid_input, unsupported_operation, permission_failure, resource_unavailable
        self.recoverable = recoverable


# Tool Argument Schemas
class NumericSummaryArgs(BaseModel):
    column: str = Field(description="Target numeric column name")


class TopCategoriesArgs(BaseModel):
    dimension: str = Field(description="Categorical column name")
    metric: Optional[str] = Field(default=None, description="Optional numerical metric to aggregate")
    limit: int = Field(default=5, ge=1, le=50)


class CorrelationSummaryArgs(BaseModel):
    columns: Optional[List[str]] = Field(default=None, description="Optional subset of numeric columns")


class QualityIssuesArgs(BaseModel):
    threshold_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class CleaningPreviewArgs(BaseModel):
    action_type: str
    column: Optional[str] = None
    strategy: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ChartRecommendArgs(BaseModel):
    query: Any = ""
    dimension: Optional[str] = None
    metric: Optional[str] = None

    @field_validator("query", mode="before")
    def ensure_str_query(cls, v):
        if isinstance(v, (list, tuple)):
            return " ".join(str(x) for x in v)
        return str(v) if v is not None else ""


class CategoricalColumnArgs(BaseModel):
    column: str = Field(description="Target categorical column name")


class DatetimeColumnArgs(BaseModel):
    column: str = Field(description="Target date/time column name")
    numeric_columns: Optional[List[str]] = Field(default=None)


class OutliersArgs(BaseModel):
    column: Optional[str] = None
    method: str = "auto"


class GroupComparisonArgs(BaseModel):
    group_column: str
    value_column: str


class TimeSeriesArgs(BaseModel):
    date_column: str
    metric_column: str


class ValidateChartArgs(BaseModel):
    config: Dict[str, Any]


class PdfPageQueryArgs(BaseModel):
    document_path: str
    page_number: int = Field(ge=1)
    query: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    category: str
    schema_cls: Any
    handler: Any


# Implementation of Safe, Parameterized Tools
def run_profile_dataset(df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    understanding = understand_dataset(df, sanitize=True)
    prof = understanding["profile"]
    return {
        "row_count": prof["row_count"],
        "column_count": prof["column_count"],
        "columns": [c["name"] for c in prof["columns"]],
        "dtypes": {c["name"]: c["dtype"] for c in prof["columns"]},
        "detected_types": {c["name"]: c["detected_type"] for c in prof["columns"]},
        "numerical_columns": prof["numerical_columns"],
        "categorical_columns": prof["categorical_columns"],
        "datetime_columns": prof["datetime_columns"],
        "identifier_columns": prof["identifier_columns"],
        "constant_columns": prof["constant_columns"],
        "missing_cells": int(understanding["normalized_df"].isna().sum().sum()),
        "duplicate_rows": prof["duplicate_rows"],
    }


def run_numeric_summary(df: pd.DataFrame, column: str, **kwargs) -> Dict[str, Any]:
    if column not in df.columns:
        raise ToolExecutionError(f"Column '{column}' does not exist in dataset.", failure_type="invalid_input", recoverable=True)
    norm_df = understand_dataset(df, sanitize=False)["normalized_df"]
    series = pd.to_numeric(norm_df[column], errors="coerce")
    valid_series = series.dropna()
    if valid_series.empty:
        raise ToolExecutionError(f"Column '{column}' has no valid numeric values.", failure_type="invalid_input", recoverable=True)

    return analyze_numerical_column(norm_df, column)


def run_analyze_categorical(df: pd.DataFrame, column: str, **kwargs) -> Dict[str, Any]:
    if column not in df.columns:
        raise ToolExecutionError(f"Column '{column}' does not exist in dataset.", failure_type="invalid_input", recoverable=True)
    return analyze_categorical_column(df, column)


def run_analyze_datetime(df: pd.DataFrame, column: str, numeric_columns: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    if column not in df.columns:
        raise ToolExecutionError(f"Date column '{column}' does not exist in dataset.", failure_type="invalid_input", recoverable=True)
    norm_df = understand_dataset(df, sanitize=False)["normalized_df"]
    return analyze_datetime_column(norm_df, column, numeric_columns=numeric_columns)


def run_calculate_correlation(df: pd.DataFrame, columns: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    norm_df = understand_dataset(df, sanitize=False)["normalized_df"]
    return calculate_correlation(norm_df, numeric_columns=columns)


def run_detect_outliers(df: pd.DataFrame, column: Optional[str] = None, method: str = "auto", **kwargs) -> Dict[str, Any]:
    understanding = understand_dataset(df, sanitize=False)
    return detect_outliers(
        understanding["normalized_df"],
        column=column,
        numeric_columns=understanding["profile"]["numerical_columns"],
        method=method,
    )


def run_group_comparison(df: pd.DataFrame, group_column: str, value_column: str, **kwargs) -> Dict[str, Any]:
    if group_column not in df.columns or value_column not in df.columns:
        raise ToolExecutionError("Group or value column missing from dataset.", failure_type="invalid_input", recoverable=True)
    norm_df = understand_dataset(df, sanitize=False)["normalized_df"]
    return compare_groups(norm_df, group_column, value_column)


def run_generate_time_series(df: pd.DataFrame, date_column: str, metric_column: str, **kwargs) -> Dict[str, Any]:
    if date_column not in df.columns or metric_column not in df.columns:
        raise ToolExecutionError("Date or metric column missing from dataset.", failure_type="invalid_input", recoverable=True)
    norm_df = understand_dataset(df, sanitize=False)["normalized_df"]
    return analyze_datetime_column(norm_df, date_column, numeric_columns=[metric_column])


def run_validate_chart(df: pd.DataFrame, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    res = validate_chart_config(df, ChartConfig(**config))
    return res.model_dump()


def run_top_categories(df: pd.DataFrame, dimension: str, metric: Optional[str] = None, limit: int = 5, **kwargs) -> Dict[str, Any]:
    if dimension not in df.columns:
        raise ToolExecutionError(f"Dimension '{dimension}' does not exist in dataset.", failure_type="invalid_input", recoverable=True)
    norm_df = understand_dataset(df, sanitize=False)["normalized_df"]

    if metric:
        if metric not in norm_df.columns:
            raise ToolExecutionError(f"Metric '{metric}' does not exist in dataset.", failure_type="invalid_input", recoverable=True)
        num_s = pd.to_numeric(norm_df[metric], errors="coerce")
        grouped = norm_df.assign(_m=num_s).groupby(dimension)["_m"].agg(["sum", "mean", "count"]).reset_index()
        grouped = grouped.sort_values(by="sum", ascending=False).head(limit)
        items = [
            {"value": str(row[dimension]), "metric": round(float(row["sum"]), 2), "mean": round(float(row["mean"]), 2), "count": int(row["count"])}
            for _, row in grouped.iterrows()
        ]
    else:
        counts = norm_df[dimension].value_counts().head(limit)
        items = [{"value": str(idx), "metric": int(val)} for idx, val in counts.items()]

    return {
        "dimension": dimension,
        "metric": metric or "count",
        "items": items,
        "total_categories": int(norm_df[dimension].nunique()),
    }


def run_correlation_summary(df: pd.DataFrame, columns: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    understanding = understand_dataset(df, sanitize=False)
    norm_df = understanding["normalized_df"]
    num_cols = columns or understanding["profile"]["numerical_columns"]
    if len(num_cols) < 2:
        return {"correlations": [], "message": "At least 2 numeric columns required for correlation."}

    res = calculate_correlation(norm_df, numeric_columns=num_cols)
    # Also compute all pairs if none hit >= 0.35 so test_22 or low-corr inspects exact value cleanly
    pairs = list(res.get("notable_correlations", []))
    if not pairs and len(num_cols) >= 2:
        p_mat = res.get("pearson_matrix", {})
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                c1, c2 = num_cols[i], num_cols[j]
                val = (p_mat.get(c1) or {}).get(c2)
                if val is not None:
                    pairs.append({
                        "col1": c1,
                        "col2": c2,
                        "correlation": round(float(val), 3),
                        "pearson_r": float(val),
                        "strength": "strong" if abs(val) >= 0.7 else ("moderate" if abs(val) >= 0.4 else "weak"),
                    })
    return {
        "correlations": pairs[:10],
        "categorical_associations": res.get("categorical_associations", []),
        "columns_evaluated": num_cols,
        "note": "Correlation reflects statistical association, not causation.",
    }


def run_detect_data_quality_issues(df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    report = inspect_data_quality(df)
    return {
        "quality_score": report["quality_score"],
        "summary": report["summary"],
        "recommendations": report["recommendations"],
        "missing_columns_count": len(report["missing_by_column"]),
        "outlier_columns_count": len(report["outliers_by_column"]),
    }


def run_preview_cleaning_changes(df: pd.DataFrame, action_type: str, column: Optional[str] = None, strategy: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    if action_type == "remove_duplicates":
        dups = int(df.duplicated().sum())
        return {
            "action_type": action_type,
            "rows_before": len(df),
            "rows_after": len(df) - dups,
            "impact": f"Removes {dups} duplicate records.",
        }
    elif action_type == "impute_missing":
        if not column or column not in df.columns:
            raise ToolExecutionError(f"Target column '{column}' required for imputation.", failure_type="invalid_input", recoverable=True)
        missing = int(df[column].isna().sum())
        return {
            "action_type": action_type,
            "column": column,
            "strategy": strategy or "median",
            "missing_filled": missing,
            "impact": f"Fills {missing} missing values using {strategy or 'median'}.",
        }
    elif action_type == "handle_outliers":
        if not column or column not in df.columns:
            raise ToolExecutionError(f"Target column '{column}' required for outlier handling.", failure_type="invalid_input", recoverable=True)
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        q25, q75 = series.quantile(0.25), series.quantile(0.75)
        iqr = q75 - q25
        lower, upper = q25 - 1.5 * iqr, q75 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        return {
            "action_type": action_type,
            "column": column,
            "strategy": strategy or "winsorize",
            "outliers_count": outlier_count,
            "bounds": [float(lower), float(upper)],
            "impact": f"Caps {outlier_count} values outside [{lower:.2f}, {upper:.2f}].",
        }
    return {"action_type": action_type, "status": "preview_ready"}


def run_recommend_chart(df: pd.DataFrame, query: str = "", dimension: Optional[str] = None, metric: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    return select_best_chart_for_query(df, query=query, dimension=dimension, metric=metric)


def run_retrieve_pdf_page(document_path: str, page_number: int, query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    path = Path(document_path)
    if not path.exists():
        raise ToolExecutionError(f"Document file '{document_path}' does not exist.", failure_type="resource_unavailable", recoverable=False)
    index = get_pdf_index(path)
    page = index.get_page(page_number)
    if not page:
        raise ToolExecutionError(f"Page {page_number} out of bounds (Document has {len(index.pages)} pages).", failure_type="invalid_input", recoverable=True)

    return {
        "document_name": path.name,
        "page_number": page.page_number,
        "text": page.text,
        "char_count": page.char_count,
        "tables_count": page.tables_count,
        "tables": page.tables,
    }


class ToolRegistry:
    """Central registry of validated, bounded analytical tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, name: str, description: str, category: str, schema_cls: Any, handler: Callable):
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            category=category,
            schema_cls=schema_cls,
            handler=handler,
        )

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "category": t.category}
            for t in self._tools.values()
        ]

    def execute(self, name: str, df: Optional[pd.DataFrame] = None, **kwargs) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            raise ToolExecutionError(f"Tool '{name}' is not registered in the approved tool registry.", failure_type="unsupported_operation", recoverable=False)

        # Validate arguments using Pydantic schema if provided
        if tool.schema_cls is not None:
            try:
                validated_args = tool.schema_cls(**kwargs).model_dump()
            except ValidationError as ve:
                raise ToolExecutionError(f"Argument validation failed for tool '{name}': {ve}", failure_type="invalid_input", recoverable=True)
        else:
            validated_args = kwargs

        # Execute handler
        try:
            if df is not None:
                return tool.handler(df=df, **validated_args)
            return tool.handler(**validated_args)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"Error executing tool '{name}': {str(exc)}", failure_type="transient", recoverable=True)

    def _register_default_tools(self):
        self.register("profile_dataset", "Profiles overall dataset structure and health", "data_analyst", None, run_profile_dataset)
        self.register("numeric_summary", "Calculates mean, median, mode, min, max, std, and quantiles", "data_analyst", NumericSummaryArgs, run_numeric_summary)
        self.register("analyze_numerical_column", "Detailed numerical distribution & anomaly scan", "data_analyst", NumericSummaryArgs, run_numeric_summary)
        self.register("analyze_categorical_column", "Frequency, dominance, imbalance, and rare categories", "data_analyst", CategoricalColumnArgs, run_analyze_categorical)
        self.register("analyze_datetime_column", "Temporal span, cadence, gaps, and metric trend analysis", "data_analyst", DatetimeColumnArgs, run_analyze_datetime)
        self.register("top_categories", "Computes highest or lowest categorical aggregates", "data_analyst", TopCategoriesArgs, run_top_categories)
        self.register("correlation_summary", "Computes pairwise Pearson and Spearman correlations", "data_analyst", CorrelationSummaryArgs, run_correlation_summary)
        self.register("calculate_correlation", "Computes Pearson, Spearman, and categorical Cramér's V associations", "data_analyst", CorrelationSummaryArgs, run_calculate_correlation)
        self.register("detect_outliers", "Detects candidate univariate and multivariate anomalies", "data_quality", OutliersArgs, run_detect_outliers)
        self.register("analyze_group_comparison", "Runs ANOVA and per-group numerical comparisons", "data_analyst", GroupComparisonArgs, run_group_comparison)
        self.register("generate_time_series", "Generates chronological time-series breakdown", "data_analyst", TimeSeriesArgs, run_generate_time_series)
        self.register("detect_data_quality_issues", "Finds missing values, duplicates, and outliers", "data_quality", None, run_detect_data_quality_issues)
        self.register("preview_cleaning_changes", "Previews transformation impacts before applying", "data_quality", CleaningPreviewArgs, run_preview_cleaning_changes)
        self.register("recommend_chart", "Recommends chart type and dimension/metric mapping", "visualization", ChartRecommendArgs, run_recommend_chart)
        self.register("validate_chart", "Validates chart configuration compatibility", "visualization", ValidateChartArgs, run_validate_chart)
        self.register("retrieve_pdf_page", "Retrieves text and tables from a specific PDF page", "document_intelligence", PdfPageQueryArgs, run_retrieve_pdf_page)


tool_registry = ToolRegistry()
