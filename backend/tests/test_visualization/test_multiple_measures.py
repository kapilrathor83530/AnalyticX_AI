import pandas as pd

from app.visualization.chart_schemas import ChartConfig
from app.visualization.data_mapper import build_chart_data


def test_bar_data_supports_multiple_measure_columns():
    df = pd.DataFrame({"region": ["North", "South", "North"], "revenue": [10, 20, 5], "cost": [4, 8, 2]})
    config = ChartConfig(chart_type="bar", data_mapping={"x": "region", "y": ["revenue", "cost"]}, aggregation="sum")
    rows = build_chart_data(df, config)
    assert {row["region"] for row in rows} == {"North", "South"}
    north = next(row for row in rows if row["region"] == "North")
    assert north["revenue"] == 15
    assert north["cost"] == 6
