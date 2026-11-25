from typing import Dict, List

from app.visualization.chart_schemas import ChartTypeDefinition, DataRole


def _role(name: str, label: str, role_type: str, required: bool = False, multiple: bool = False) -> DataRole:
    return DataRole(name=name, label=label, type=role_type, required=required, multiple=multiple)


CHARTS: List[ChartTypeDefinition] = [
    # Comparison
    ChartTypeDefinition(
        id="bar",
        name="Bar Chart",
        category="comparison",
        icon="bar-chart",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True)],
        config_options=["title", "subtitle", "colors", "axis_titles", "legend", "labels", "sort", "limit"],
        default_config={"orientation": "vertical"},
    ),
    ChartTypeDefinition(
        id="horizontal_bar",
        name="Horizontal Bar Chart",
        category="comparison",
        icon="bar-chart-horizontal",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True)],
        config_options=["title", "subtitle", "colors", "axis_titles", "legend", "labels", "sort", "limit"],
        default_config={"orientation": "horizontal"},
    ),
    ChartTypeDefinition(
        id="column",
        name="Column Chart",
        category="comparison",
        icon="bar-chart-2",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True)],
        config_options=["title", "subtitle", "colors", "axis_titles", "legend", "labels", "sort", "limit"],
        default_config={"orientation": "horizontal"},
    ),
    ChartTypeDefinition(
        id="grouped_bar",
        name="Grouped Bar",
        category="comparison",
        icon="bar-chart",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True), _role("series", "Series", "dimension")],
        config_options=["title", "colors", "axis_titles", "legend", "labels", "sort", "limit"],
        default_config={"barmode": "group"},
    ),
    ChartTypeDefinition(
        id="clustered_bar",
        name="Clustered Bar",
        category="comparison",
        icon="bar-chart",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True), _role("series", "Series", "dimension")],
        config_options=["title", "colors", "legend", "labels"],
        default_config={"barmode": "group"},
    ),
    ChartTypeDefinition(
        id="stacked_bar",
        name="Stacked Bar",
        category="comparison",
        icon="bar-chart",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True), _role("series", "Series", "dimension")],
        config_options=["title", "colors", "legend", "labels"],
        default_config={"barmode": "stack"},
    ),
    ChartTypeDefinition(
        id="hundred_percent_stacked_bar",
        name="100% Stacked Bar",
        category="comparison",
        icon="bar-chart",
        data_roles=[_role("x", "Category", "dimension", True), _role("y", "Values (select one or more)", "measure", True, True), _role("series", "Series", "dimension")],
        config_options=["title", "colors", "legend", "labels"],
        default_config={"barmode": "stack", "normalized": True},
    ),
    # Trend
    ChartTypeDefinition(
        id="line",
        name="Line Chart",
        category="trend",
        icon="line-chart",
        data_roles=[_role("x", "X Axis", "dimension", True), _role("y", "Y Axis values (select one or more)", "measure", True, True), _role("series", "Series", "dimension")],
        config_options=["title", "colors", "axis_titles", "legend", "labels", "smooth"],
    ),
    ChartTypeDefinition(
        id="area",
        name="Area Chart",
        category="trend",
        icon="area-chart",
        data_roles=[_role("x", "X Axis", "dimension", True), _role("y", "Y Axis values (select one or more)", "measure", True, True), _role("series", "Series", "dimension")],
        config_options=["title", "colors", "legend", "labels"],
    ),
    ChartTypeDefinition(
        id="stacked_area",
        name="Stacked Area",
        category="trend",
        icon="area-chart",
        data_roles=[_role("x", "X Axis", "dimension", True), _role("y", "Y Axis values (select one or more)", "measure", True, True), _role("series", "Series", "dimension", True)],
        config_options=["title", "colors", "legend"],
    ),
    ChartTypeDefinition(
        id="time_series",
        name="Time Series",
        category="trend",
        icon="activity",
        data_roles=[_role("x", "Date", "date", True), _role("y", "Value", "measure", True)],
        config_options=["title", "colors", "date_format"],
    ),
    # Composition
    ChartTypeDefinition(
        id="pie",
        name="Pie Chart",
        category="composition",
        icon="pie-chart",
        data_roles=[_role("labels", "Category", "dimension", True), _role("values", "Value", "measure", True)],
        config_options=["title", "colors", "labels", "legend", "donut"],
    ),
    ChartTypeDefinition(
        id="donut",
        name="Donut Chart",
        category="composition",
        icon="pie-chart",
        data_roles=[_role("labels", "Category", "dimension", True), _role("values", "Value", "measure", True)],
        config_options=["title", "colors", "labels", "legend"],
        default_config={"hole": 0.5},
    ),
    ChartTypeDefinition(
        id="treemap",
        name="Treemap",
        category="composition",
        icon="layout-grid",
        data_roles=[_role("labels", "Category", "dimension", True), _role("values", "Value", "measure", True), _role("parent", "Parent", "dimension")],
        config_options=["title", "colors"],
    ),
    ChartTypeDefinition(
        id="funnel",
        name="Funnel Chart",
        category="composition",
        icon="filter",
        data_roles=[_role("labels", "Stage", "dimension", True), _role("values", "Value", "measure", True)],
        config_options=["title", "colors"],
    ),
    # Statistical
    ChartTypeDefinition(
        id="scatter",
        name="Scatter Plot",
        category="statistical",
        icon="scatter-chart",
        data_roles=[_role("x", "X Axis", "measure", True), _role("y", "Y Axis", "measure", True), _role("color", "Color", "dimension")],
        config_options=["title", "colors", "axis_titles", "trendline"],
    ),
    ChartTypeDefinition(
        id="bubble",
        name="Bubble Chart",
        category="statistical",
        icon="circle",
        data_roles=[_role("x", "X Axis", "measure", True), _role("y", "Y Axis", "measure", True), _role("size", "Size", "measure", True), _role("color", "Color", "dimension")],
        config_options=["title", "colors", "axis_titles"],
    ),
    ChartTypeDefinition(
        id="histogram",
        name="Histogram",
        category="statistical",
        icon="bar-chart",
        data_roles=[_role("x", "Value", "measure", True)],
        config_options=["title", "colors", "bins"],
    ),
    ChartTypeDefinition(
        id="box",
        name="Box Plot",
        category="statistical",
        icon="box",
        data_roles=[_role("y", "Value", "measure", True), _role("x", "Category", "dimension")],
        config_options=["title", "colors", "axis_titles"],
    ),
    ChartTypeDefinition(
        id="violin",
        name="Violin Plot",
        category="statistical",
        icon="activity",
        data_roles=[_role("y", "Value", "measure", True), _role("x", "Category", "dimension")],
        config_options=["title", "colors", "axis_titles"],
    ),
    ChartTypeDefinition(
        id="heatmap",
        name="Correlation Heatmap",
        category="statistical",
        icon="grid",
        data_roles=[_role("columns", "Columns", "measure", True, multiple=True)],
        config_options=["title", "colors"],
    ),
    ChartTypeDefinition(
        id="correlation_matrix",
        name="Correlation Matrix",
        category="statistical",
        icon="grid",
        data_roles=[_role("columns", "Columns", "measure", False, multiple=True)],
        config_options=["title", "colors", "method"],
    ),
    ChartTypeDefinition(
        id="geo_map",
        name="Geographic Map",
        category="comparison",
        icon="globe",
        data_roles=[_role("location", "Location (Country/State)", "dimension", True), _role("value", "Metric Value", "measure", True)],
        config_options=["title", "colors", "scope"],
    ),
    # Business
    ChartTypeDefinition(
        id="kpi",
        name="KPI Card",
        category="business",
        icon="hash",
        data_roles=[_role("value", "Value", "measure", True), _role("comparison", "Comparison", "measure")],
        config_options=["title", "prefix", "suffix", "decimals", "comparison_label"],
    ),
    ChartTypeDefinition(
        id="table",
        name="Table",
        category="business",
        icon="table",
        data_roles=[_role("columns", "Columns", "dimension", True, multiple=True)],
        config_options=["title", "sort", "limit", "page_size"],
    ),
    ChartTypeDefinition(
        id="matrix",
        name="Matrix",
        category="business",
        icon="grid-3x3",
        data_roles=[_role("rows", "Rows", "dimension", True, multiple=True), _role("columns", "Columns", "dimension", True, multiple=True), _role("values", "Values", "measure", True)],
        config_options=["title", "aggregation"],
    ),
    ChartTypeDefinition(
        id="gauge",
        name="Gauge",
        category="business",
        icon="gauge",
        data_roles=[_role("value", "Value", "measure", True), _role("target", "Target", "measure")],
        config_options=["title", "min", "max", "thresholds"],
    ),
    ChartTypeDefinition(
        id="forecast",
        name="Forecast Chart",
        category="business",
        icon="trending-up",
        data_roles=[_role("date", "Date", "date", True), _role("value", "Value", "measure", True)],
        config_options=["title", "horizon", "model"],
    ),
    ChartTypeDefinition(
        id="waterfall",
        name="Waterfall Chart",
        category="composition",
        icon="bar-chart",
        data_roles=[_role("labels", "Step", "dimension", True), _role("values", "Value", "measure", True)],
        config_options=["title", "colors"],
    ),
]


CHART_REGISTRY: Dict[str, ChartTypeDefinition] = {chart.id: chart for chart in CHARTS}


def list_charts() -> List[ChartTypeDefinition]:
    return CHARTS


def get_chart(chart_id: str) -> ChartTypeDefinition | None:
    return CHART_REGISTRY.get(chart_id)
