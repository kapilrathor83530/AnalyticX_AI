from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.decision_engine.comparator import compare_scenarios
from app.models.dataset import Dataset
from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCompareRequest, ScenarioRead, ScenarioRunRequest
from app.services.data_service import load_dataset_df
from app.services.simulation_service import list_scenarios, run_and_save_scenario, sensitivity

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _get_df(db: Session, dataset_id: int):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return load_dataset_df(dataset)


@router.post("/scenario", response_model=ScenarioRead)
def create_scenario(payload: ScenarioRunRequest, db: Session = Depends(get_db)):
    df = _get_df(db, payload.dataset_id)
    scenario = run_and_save_scenario(
        db,
        df,
        dataset_id=payload.dataset_id,
        name=payload.name,
        description=payload.description,
        metric_columns=payload.metric_columns,
        adjustments=[a.model_dump() for a in payload.adjustments],
        elasticity=payload.elasticity,
    )
    return scenario


@router.get("/scenarios/{dataset_id}", response_model=list[ScenarioRead])
def list_dataset_scenarios(dataset_id: int, db: Session = Depends(get_db)):
    return list_scenarios(db, dataset_id)


@router.post("/compare")
def compare(payload: ScenarioCompareRequest, db: Session = Depends(get_db)):
    scenarios = (
        db.query(Scenario).filter(Scenario.id.in_(payload.scenario_ids)).all()
    )
    if not scenarios:
        raise HTTPException(status_code=404, detail="No scenarios found")

    payload_list = [
        {
            "id": s.id,
            "name": s.name,
            "scenario": (s.results or {}).get("scenario", {}),
        }
        for s in scenarios
    ]
    return compare_scenarios(payload_list)


@router.post("/sensitivity")
def run_sensitivity(payload: dict, db: Session = Depends(get_db)):
    dataset_id = payload.get("dataset_id")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id required")
    df = _get_df(db, dataset_id)
    return sensitivity(
        df,
        metric_columns=payload.get("metric_columns", {}),
        field=payload["field"],
        values=payload.get("values", []),
        mode=payload.get("mode", "percent"),
        elasticity=payload.get("elasticity"),
    )
