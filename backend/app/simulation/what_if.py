from typing import Any, Dict, List

from app.decision_engine.baseline import compute_baseline
from app.decision_engine.scenario import run_scenario


def run_what_if(
    df,
    metric_columns: Dict[str, str],
    adjustments: List[Dict[str, Any]],
    elasticity: float | None = None,
) -> Dict[str, Any]:
    baseline = compute_baseline(df, metric_columns=metric_columns)
    return run_scenario(baseline, adjustments, elasticity=elasticity)
