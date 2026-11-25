from typing import Any, Dict, List

from app.decision_engine.baseline import compute_baseline
from app.decision_engine.scenario import run_scenario


def sensitivity_analysis(
    df,
    metric_columns: Dict[str, str],
    field: str,
    values: List[float],
    mode: str = "percent",
    elasticity: float | None = None,
) -> Dict[str, Any]:
    baseline = compute_baseline(df, metric_columns=metric_columns)
    results = []

    for value in values:
        scenario = run_scenario(
            baseline,
            adjustments=[{"field": field, "mode": mode, "value": value}],
            elasticity=elasticity,
        )
        results.append(
            {
                "value": value,
                "scenario": scenario["scenario"],
                "profit": scenario["scenario"].get("profit"),
                "revenue": scenario["scenario"].get("revenue"),
            }
        )

    return {"field": field, "mode": mode, "results": results, "baseline": baseline.get("totals", {})}
