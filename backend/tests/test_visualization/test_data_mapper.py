import pandas as pd

from app.visualization.chart_schemas import ChartConfig
from app.visualization.data_mapper import build_chart_data


def sample_df():
    return pd.DataFrame(
        {
            "region": ["North", "South", "North", "East", "South"],
            "revenue": [100, 200, 150, 50, 300],
            "month": ["2025-01", "2025-01", "2025-02", "2025-02", "2025-03"],
        }
    )


def test_bar_chart_aggregates_by_category():
    df = sample_df()
    config = ChartConfig(chart_type="bar", data_mapping={"x": "region", "y": "revenue"}, aggregation="sum")
    data = build_chart_data(df, config)

    assert len(data) == 3
    north = next(row for row in data if row["region"] == "North")
    assert north["revenue"] == 250


def test_line_chart_returns_grouped_series():
    df = sample_df()
    config = ChartConfig(chart_type="line", data_mapping={"x": "month", "y": "revenue"}, aggregation="sum")
    data = build_chart_data(df, config)

    assert len(data) >= 2
    assert "month" in data[0]
    assert "revenue" in data[0]


def test_scatter_returns_points():
    df = sample_df()
    config = ChartConfig(chart_type="scatter", data_mapping={"x": "revenue", "y": "revenue"})
    data = build_chart_data(df, config)

    assert len(data) == 5


def test_pie_chart_uses_labels_values():
    df = sample_df()
    config = ChartConfig(chart_type="pie", data_mapping={"labels": "region", "values": "revenue"}, aggregation="sum")
    data = build_chart_data(df, config)

    assert len(data) == 3


def test_kpi_returns_single_value():
    df = sample_df()
    config = ChartConfig(chart_type="kpi", data_mapping={"value": "revenue"}, aggregation="sum")
    data = build_chart_data(df, config)

    assert len(data) == 1
    assert data[0]["value"] == 800
