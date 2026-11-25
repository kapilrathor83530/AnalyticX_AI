import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.analytics.cleaning import apply_transformations
from app.analytics.data_quality import inspect_data_quality
from app.analytics.eda import eda_dataframe
from app.analytics.eda_engine import generate_eda_report
from app.analytics.profiling import profile_dataframe
from app.database import get_db
from app.models.dataset import Dataset
from app.models.transformation import Transformation
from app.models.user import User
from app.schemas.dataset import DatasetPreview, DatasetProfile, DatasetRead
from app.schemas.transformation import TransformationApplyRequest, TransformationRead
from app.services.activity_service import create_user_notification, record_activity
from app.services.cleaning_service import (
    apply_cleaning_decision,
    auto_clean_dataset,
    export_dataset_file,
    get_dataset_quality_report,
    prune_stale_cleaning_files,
    undo_last_transformation,
)
from app.services.data_analyst_chat_service import handle_analyst_chat
from app.services.data_service import (
    get_dataset_understanding,
    invalidate_dataset_cache,
    load_dataframe_from_path,
    load_dataset_df,
    save_upload,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


class CleaningActionPayload(BaseModel):
    action_type: str
    column: Optional[str] = None
    strategy: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    save_as_new_version: bool = False


class AutoCleanPayload(BaseModel):
    save_as_new_version: bool = False


class AnalystChatPayload(BaseModel):
    messages: List[Dict[str, str]]
    selected_column: Optional[str] = None


def get_dataset_or_404(db: Session, dataset_id: int, user: Optional[User] = None) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if user and dataset.user_id and dataset.user_id != user.id and not dataset.is_sample:
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to access this dataset.")
    return dataset


@router.post("/upload", response_model=DatasetRead)
async def upload_dataset(
    file: UploadFile = File(...),
    workspace_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        stored_path, size = await save_upload(file)
        df = load_dataframe_from_path(stored_path)
        from app.analytics.data_understanding import understand_dataset
        understanding = understand_dataset(df, dataset_name=file.filename or "Untitled dataset")
        if not understanding["validation"]["valid"]:
            Path(stored_path).unlink(missing_ok=True)
            raise ValueError("; ".join(understanding["validation"]["errors"]) or "Uploaded dataset has no valid data.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    norm_df = understanding["normalized_df"]
    profile_meta = understanding["profile"]

    # Quick initial quality check on normalized working frame
    try:
        quality = inspect_data_quality(norm_df)
        score = quality["quality_score"]
        initial_status = "Analysis Ready" if score >= 80 else "Needs Attention"
    except Exception:
        score = None
        initial_status = "Uploaded"

    dataset = Dataset(
        user_id=user.id if user else None,
        workspace_id=workspace_id,
        is_sample=False,
        name=file.filename or "Untitled dataset",
        original_filename=file.filename or "Untitled dataset",
        stored_path=str(stored_path),
        size_bytes=size,
        row_count=int(norm_df.shape[0]),
        column_count=int(norm_df.shape[1]),
        status=initial_status,
        version=1,
        quality_score=score,
        dataset_metadata={
            "validation": understanding["validation"],
            "numerical_columns": profile_meta["numerical_columns"],
            "categorical_columns": profile_meta["categorical_columns"],
            "datetime_columns": profile_meta["datetime_columns"],
            "identifier_columns": profile_meta["identifier_columns"],
            "constant_columns": profile_meta["constant_columns"],
        },
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    if user:
        record_activity(
            db=db,
            user_id=user.id,
            action_type="dataset_uploaded",
            title=f"Uploaded '{dataset.name}'",
            description=f"{dataset.row_count:,} rows × {dataset.column_count} columns",
            entity_type="dataset",
            entity_id=dataset.id,
        )
        create_user_notification(
            db=db,
            user_id=user.id,
            title="Dataset Ready for Analysis",
            message=f"'{dataset.name}' was uploaded and verified ({dataset.row_count:,} rows).",
            level="success",
            link=f"/datasets/{dataset.id}",
            event_type="dataset",
        )

    return dataset


@router.get("", response_model=list[DatasetRead])
def list_datasets(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    q = db.query(Dataset)
    if user:
        q = q.filter((Dataset.user_id == user.id) | (Dataset.is_sample.is_(True)))
    return q.order_by(Dataset.created_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    return get_dataset_or_404(db, dataset_id, user=user)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(
    dataset_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    dataset = get_dataset_or_404(db, dataset_id, user=user)
    from app.analytics.data_understanding import validate_and_sanitize_dataframe
    raw_df = load_dataset_df(dataset)
    clean_df, _ = validate_and_sanitize_dataframe(raw_df)
    rows = json.loads(clean_df.head(limit).to_json(orient="records", date_format="iso"))
    return DatasetPreview(
        columns=[str(column) for column in clean_df.columns],
        rows=rows,
        total_rows=int(clean_df.shape[0]),
        returned_rows=len(rows),
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def profile_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    dataset = get_dataset_or_404(db, dataset_id, user=user)
    return get_dataset_understanding(dataset)["profile"]


@router.get("/{dataset_id}/understanding")
def get_dataset_understanding_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    dataset = get_dataset_or_404(db, dataset_id, user=user)
    understanding = get_dataset_understanding(dataset)
    return {
        "dataset_id": dataset.id,
        "version": dataset.version,
        "profile": understanding["profile"],
        "validation": understanding["validation"],
    }


@router.get("/{dataset_id}/quality-report")
def get_quality_report(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    return get_dataset_quality_report(dataset, db)


@router.get("/{dataset_id}/eda")
def eda_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    understanding = get_dataset_understanding(dataset)
    return eda_dataframe(understanding["normalized_df"], profile=understanding["profile"])


@router.get("/{dataset_id}/eda-report")
def get_detailed_eda_report(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    understanding = get_dataset_understanding(dataset)
    return generate_eda_report(
        understanding["normalized_df"],
        dataset_name=dataset.name,
        understanding=understanding,
    )


@router.post("/{dataset_id}/apply-action")
def apply_action(dataset_id: int, payload: CleaningActionPayload, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        result = apply_cleaning_decision(
            dataset=dataset,
            action=payload.model_dump(),
            trigger_source="user",
            db=db,
            save_as_new_version=payload.save_as_new_version,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{dataset_id}/auto-clean")
def auto_clean(dataset_id: int, payload: AutoCleanPayload, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        result = auto_clean_dataset(
            dataset=dataset,
            db=db,
            save_as_new_version=payload.save_as_new_version,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{dataset_id}/undo")
def undo_transformation(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        return undo_last_transformation(dataset, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{dataset_id}/export/{format_type}")
def export_dataset(dataset_id: int, format_type: str, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        file_path, filename, media_type = export_dataset_file(dataset, format_type, db)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{dataset_id}/analyst-chat")
async def analyst_chat(dataset_id: int, payload: AnalystChatPayload, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    try:
        return await handle_analyst_chat(
            dataset=dataset,
            messages=payload.messages,
            selected_column=payload.selected_column,
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{dataset_id}/clean")
def clean_dataset(dataset_id: int, payload: TransformationApplyRequest, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    df = load_dataset_df(dataset)
    rows_before = int(df.shape[0])
    specs = [item.model_dump() for item in payload.transformations]
    cleaned = apply_transformations(df, specs)
    rows_after = int(cleaned.shape[0])
    cleaned_path = Path(dataset.stored_path).parent / f"{uuid.uuid4().hex}_cleaned.csv"
    cleaned.to_csv(cleaned_path, index=False)
    for spec in specs:
        db.add(Transformation(
            dataset_id=dataset_id,
            transformation_type=spec.get("type", "unknown"),
            parameters=spec.get("parameters", {}),
            description=spec.get("description"),
            row_count_before=rows_before,
            row_count_after=rows_after,
        ))
    db.commit()
    return {
        "cleaned_path": str(cleaned_path),
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns": [str(column) for column in cleaned.columns],
    }


@router.get("/{dataset_id}/transformations", response_model=list[TransformationRead])
def list_transformations(dataset_id: int, db: Session = Depends(get_db)):
    get_dataset_or_404(db, dataset_id)
    return (
        db.query(Transformation)
        .filter(Transformation.dataset_id == dataset_id)
        .order_by(Transformation.applied_at.desc())
        .all()
    )


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    dataset = get_dataset_or_404(db, dataset_id, user=user)
    if dataset.is_sample:
        raise HTTPException(
            status_code=403,
            detail="Sample datasets are system-managed and cannot be deleted.",
        )
    if user and dataset.user_id and dataset.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You do not have permission to delete this dataset.",
        )
    invalidate_dataset_cache(dataset.stored_path)
    try:
        Path(dataset.stored_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(dataset)
    db.commit()

    if user:
        record_activity(
            db=db,
            user_id=user.id,
            action_type="dataset_deleted",
            title=f"Deleted '{dataset.name}'",
            description="Dataset removed from workspace.",
        )

    return {"deleted": True, "dataset_id": dataset_id}


@router.post("/maintenance/prune-storage")
def prune_storage(db: Session = Depends(get_db)):
    """
    Cleans up orphaned intermediate cleaned CSVs and temporary export files to prevent disk bloat.
    """
    return prune_stale_cleaning_files(db)

