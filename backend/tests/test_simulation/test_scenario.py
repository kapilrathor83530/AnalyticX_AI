import pandas as pd

from app.decision_engine.baseline import compute_baseline
from app.decision_engine.scenario import run_scenario


def sample_df():
    return pd.DataFrame(
        {
            "revenue": [1000, 2000, 1500],
            "cost": [400, 800, 600],
        }
    )


def test_baseline_totals():
    df = sample_df()
    baseline = compute_baseline(df, metric_columns={"revenue": "revenue", "cost": "cost"})
    assert baseline["totals"]["revenue"] == 4500
    assert baseline["totals"]["cost"] == 1800
    assert baseline["totals"]["profit"] == 2700


def test_scenario_percent_adjustment():
    df = sample_df()
    baseline = compute_baseline(df, metric_columns={"revenue": "revenue", "cost": "cost"})
    result = run_scenario(
        baseline,
        adjustments=[{"field": "revenue", "mode": "percent", "value": 10}],
    )
    assert result["scenario"]["revenue"] > baseline["totals"]["revenue"]
    assert "differences" in result


def test_scenario_absolute_adjustment():
    df = sample_df()
    baseline = compute_baseline(df, metric_columns={"revenue": "revenue", "cost": "cost"})
    result = run_scenario(
        baseline,
        adjustments=[{"field": "cost", "mode": "absolute", "value": -500}],
    )
    assert result["scenario"]["cost"] == baseline["totals"]["cost"] - 500
