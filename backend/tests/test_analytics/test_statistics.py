import pandas as pd

from app.analytics.statistics import compare_groups, descriptive_statistics, detect_anomalies_zscore


def test_descriptive_statistics_basic():
    df = pd.DataFrame({"revenue": [100, 200, 300, 400]})
    result = descriptive_statistics(df, "revenue")
    assert result["mean"] == 250
    assert result["min"] == 100
    assert result["max"] == 400


def test_compare_groups_anova():
    df = pd.DataFrame(
        {
            "region": ["North", "North", "South", "South", "East", "East"],
            "revenue": [100, 110, 200, 210, 300, 310],
        }
    )
    result = compare_groups(df, "region", "revenue")
    assert "p_value" in result
    assert result["significant_at_0_05"] is True


def test_detect_anomalies():
    df = pd.DataFrame({"value": [1, 2, 2, 3, 3, 3, 100]})
    result = detect_anomalies_zscore(df, "value", threshold=1.5)
    assert result["column"] == "value"
    assert len(result["anomalies"]) >= 1
