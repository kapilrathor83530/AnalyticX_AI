import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.analytics.eda import eda_dataframe
from app.analytics.profiling import profile_dataframe
from app.database import get_db
from app.models import Dataset
from app.schemas import DatasetPreview, DatasetProfile, DatasetRead
from app.services.data_service import load_dataframe_from_path, load_dataset_df, save_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])


def get_dataset_or_404(db: Session, dataset_id: int) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/upload", response_model=DatasetRead)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        stored_path, size = await save_upload(file)
        df = load_dataframe_from_path(stored_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    dataset = Dataset(
        name=file.filename or "Untitled dataset",
        original_filename=file.filename or "Untitled dataset",
        stored_path=str(stored_path),
        size_bytes=size,
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get("", response_model=list[DatasetRead])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    return get_dataset_or_404(db, dataset_id)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(
    dataset_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    dataset = get_dataset_or_404(db, dataset_id)
    df = load_dataset_df(dataset)
    head = df.head(limit)

    rows = json.loads(head.to_json(orient="records", date_format="iso"))

    return DatasetPreview(
        columns=[str(col) for col in df.columns],
        rows=rows,
        total_rows=int(df.shape[0]),
        returned_rows=len(rows),
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def profile_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    df = load_dataset_df(dataset)
    return profile_dataframe(df)


@router.get("/{dataset_id}/eda")
def eda_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)
    df = load_dataset_df(dataset)
    return eda_dataframe(df)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = get_dataset_or_404(db, dataset_id)

    try:
        Path(dataset.stored_path).unlink(missing_ok=True)
    except OSError:
        pass

    db.delete(dataset)
    db.commit()

    return {"deleted": True, "dataset_id": dataset_id}
