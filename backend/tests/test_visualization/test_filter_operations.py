import pandas as pd

from app.visualization.data_mapper import _apply_filters


def test_include_exclude_text_and_between_filters_use_real_data():
    df = pd.DataFrame({"region": ["North", "South", "East"], "revenue": [10, 20, 30]})
    assert _apply_filters(df, [{"column": "region", "op": "in", "value": ["North", "East"]}]).shape[0] == 2
    assert _apply_filters(df, [{"column": "region", "op": "not_in", "value": ["North"]}]).shape[0] == 2
    assert _apply_filters(df, [{"column": "region", "op": "contains", "value": "ou"}]).iloc[0]["region"] == "South"
    assert _apply_filters(df, [{"column": "revenue", "op": "between", "value": [15, 30]}]).shape[0] == 2
