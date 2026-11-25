import pandas as pd

from app.analytics.eda import eda_dataframe
from app.analytics.profiling import profile_dataframe


def test_profile_dataframe_basic():
    df = pd.DataFrame(
        {
            "revenue": [100, 200, None, 400],
            "region": ["North", "South", "North", "East"],
        }
    )

    profile = profile_dataframe(df)

    assert profile["row_count"] == 4
    assert profile["column_count"] == 2
    assert profile["duplicate_rows"] == 0

    revenue_col = next(col for col in profile["columns"] if col["name"] == "revenue")
    assert revenue_col["missing_count"] == 1
    assert revenue_col["inferred_type"] == "numeric"


def test_eda_dataframe_has_correlations_and_distributions():
    df = pd.DataFrame(
        {
            "revenue": [100, 200, 300, 400],
            "cost": [40, 80, 120, 160],
        }
    )

    eda = eda_dataframe(df)

    assert "revenue" in eda["numeric_summary"]
    assert "revenue" in eda["numeric_distributions"]
    assert "revenue" in eda["correlations"]
