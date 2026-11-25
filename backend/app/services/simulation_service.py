from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from app.decision_engine.baseline import compute_baseline
from app.decision_engine.scenario import run_scenario
from app.models.scenario import Scenario
from app.simulation.sensitivity import sensitivity_analysis


def run_and_save_scenario(
    db: Session,
    df: pd.DataFrame,
    dataset_id: int,
    name: str,
    description: str | None,
    metric_columns: Dict[str, str],
    adjustments: List[Dict[str, Any]],
    elasticity: float | None,
) -> Scenario:
    baseline = compute_baseline(df, metric_columns=metric_columns)
    result = run_scenario(baseline, adjustments, elasticity=elasticity)

    scenario = Scenario(
        dataset_id=dataset_id,
        name=name,
        description=description,
        baseline_metrics=baseline,
        assumptions={"elasticity": elasticity},
        adjustments={"items": adjustments},
        results=result,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def list_scenarios(db: Session, dataset_id: int) -> List[Scenario]:
    return (
        db.query(Scenario)
        .filter(Scenario.dataset_id == dataset_id)
        .order_by(Scenario.created_at.desc())
        .all()
    )


def sensitivity(
    df: pd.DataFrame,
    metric_columns: Dict[str, str],
    field: str,
    values: List[float],
    mode: str,
    elasticity: float | None,
) -> Dict[str, Any]:
    return sensitivity_analysis(
        df,
        metric_columns=metric_columns,
        field=field,
        values=values,
        mode=mode,
        elasticity=elasticity,
    )
