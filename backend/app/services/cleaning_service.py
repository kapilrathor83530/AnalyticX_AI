"""Data Cleaning, Versioning, and Reversible Transformation Orchestration Service."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import shutil
import uuid
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.cleaning_engine import apply_cleaning_action
from app.analytics.data_quality import inspect_data_quality
from app.context.context_freshness_service import record_context_mutation
from app.core.config import settings
from app.models.dataset import Dataset
from app.models.project_insight import ProjectInsight
from app.models.transformation import Transformation
from app.services.data_service import invalidate_dataset_cache, load_dataset_df


def get_dataset_quality_report(dataset: Dataset, db: Session) -> Dict[str, Any]:
    df = load_dataset_df(dataset)
    report = inspect_data_quality(df)
    # Cache quality score on dataset
    dataset.quality_score = report["quality_score"]
    dataset.status = "Analysis Ready" if report["quality_score"] >= 80 else "Needs Attention"
    db.commit()
    return report


def apply_cleaning_decision(
    dataset: Dataset,
    action: Dict[str, Any],
    trigger_source: str,
    db: Session,
    save_as_new_version: bool = False,
) -> Dict[str, Any]:
    """
    Applies a cleaning decision, updates data and DB, records audit log.
    """
    df_before = load_dataset_df(dataset)
    rows_before = int(df_before.shape[0])
    cols_before = int(df_before.shape[1])
    score_before = dataset.quality_score or inspect_data_quality(df_before)["quality_score"]

    df_after, audit = apply_cleaning_action(df_before, action)
    rows_after = int(df_after.shape[0])
    cols_after = int(df_after.shape[1])

    # Re-evaluate quality
    quality_after = inspect_data_quality(df_after)
    score_after = quality_after["quality_score"]

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if save_as_new_version:
        new_stored_path = upload_dir / f"{uuid.uuid4().hex}_v{dataset.version + 1}.csv"
        df_after.to_csv(new_stored_path, index=False)
        target_dataset = Dataset(
            name=f"{dataset.name} (v{dataset.version + 1})",
            original_filename=dataset.original_filename,
            stored_path=str(new_stored_path),
            size_bytes=new_stored_path.stat().st_size,
            row_count=rows_after,
            column_count=cols_after,
            status="Analysis Ready" if score_after >= 80 else "Needs Attention",
            parent_id=dataset.id,
            version=dataset.version + 1,
            quality_score=score_after,
        )
        db.add(target_dataset)
        db.commit()
        db.refresh(target_dataset)
        record_dataset_id = target_dataset.id
    else:
        # Overwrite current dataset stored path (clean version)
        # Preserve original if version == 1 by creating a copy of original first
        if dataset.version == 1 and not dataset.parent_id:
            orig_backup = upload_dir / f"{uuid.uuid4().hex}_original_{Path(dataset.stored_path).name}"
            shutil.move(str(dataset.stored_path), str(orig_backup))
            # Create a separate historical record for original
            orig_record = Dataset(
                name=f"{dataset.name} (Original Raw)",
                original_filename=dataset.original_filename,
                stored_path=str(orig_backup),
                size_bytes=orig_backup.stat().st_size,
                row_count=rows_before,
                column_count=cols_before,
                status="Uploaded",
                parent_id=dataset.id,
                version=1,
                quality_score=score_before,
            )
            db.add(orig_record)

        old_stored_path = Path(dataset.stored_path)
        cleaned_path = upload_dir / f"{uuid.uuid4().hex}_cleaned.csv"
        df_after.to_csv(cleaned_path, index=False)
        invalidate_dataset_cache(dataset.stored_path)

        # Prune previous intermediate cleaned file to prevent disk bloat
        if old_stored_path.exists() and old_stored_path.resolve() != cleaned_path.resolve():
            other_ref = db.query(Dataset.id).filter(Dataset.id != dataset.id, Dataset.stored_path == str(old_stored_path)).first()
            if not other_ref and any(k in old_stored_path.name for k in ("_cleaned", "_autocleaned", "_reverted")):
                try:
                    old_stored_path.unlink(missing_ok=True)
                except Exception:
                    pass

        dataset.stored_path = str(cleaned_path)
        dataset.size_bytes = cleaned_path.stat().st_size
        dataset.row_count = rows_after
        dataset.column_count = cols_after
        dataset.version += 1
        dataset.quality_score = score_after
        dataset.status = "Analysis Ready" if score_after >= 80 else "Needs Attention"
        db.commit()
        record_dataset_id = dataset.id

    # Record transformation audit log
    transformation = Transformation(
        dataset_id=record_dataset_id,
        transformation_type=audit["action_type"],
        parameters=audit["parameters"],
        description=audit["description"],
        columns_affected=[audit["column"]] if audit.get("column") else [],
        status="applied",
        trigger_source=trigger_source,
        row_count_before=rows_before,
        row_count_after=rows_after,
    )
    db.add(transformation)
    db.query(ProjectInsight).filter(ProjectInsight.dataset_id == record_dataset_id).update(
        {"is_stale": True}, synchronize_session=False
    )
    db.commit()
    record_context_mutation("dataset", record_dataset_id)

    return {
        "success": True,
        "dataset_id": record_dataset_id,
        "action": audit,
        "before": {
            "rows": rows_before,
            "columns": cols_before,
            "quality_score": score_before,
        },
        "after": {
            "rows": rows_after,
            "columns": cols_after,
            "quality_score": score_after,
        },
        "quality_report": quality_after,
    }


def auto_clean_dataset(
    dataset: Dataset,
    db: Session,
    save_as_new_version: bool = True,
) -> Dict[str, Any]:
    """
    Executes automated cleaning on all safe recommendations.
    """
    df_current = load_dataset_df(dataset)
    initial_report = inspect_data_quality(df_current)
    initial_score = initial_report["quality_score"]
    rows_initial = int(df_current.shape[0])

    applied_actions = []
    current_df = df_current.copy()

    for rec in initial_report["recommendations"]:
        if not rec.get("safe_for_auto", False):
            continue

        action_spec = {
            "action_type": rec["issue_type"],
            "column": rec.get("column"),
            "strategy": rec["recommended_action"],
            "parameters": rec.get("config", {}),
        }
        try:
            current_df, audit = apply_cleaning_action(current_df, action_spec)
            applied_actions.append(audit)
        except Exception:
            continue

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    rows_final = int(current_df.shape[0])
    cols_final = int(current_df.shape[1])
    final_quality = inspect_data_quality(current_df)
    final_score = final_quality["quality_score"]

    if save_as_new_version:
        new_path = upload_dir / f"{uuid.uuid4().hex}_autocleaned.csv"
        current_df.to_csv(new_path, index=False)
        cleaned_dataset = Dataset(
            name=f"{dataset.name} (Auto-Cleaned)",
            original_filename=dataset.original_filename,
            stored_path=str(new_path),
            size_bytes=new_path.stat().st_size,
            row_count=rows_final,
            column_count=cols_final,
            status="Analysis Ready",
            parent_id=dataset.id,
            version=dataset.version + 1,
            quality_score=final_score,
        )
        db.add(cleaned_dataset)
        db.commit()
        db.refresh(cleaned_dataset)
        target_id = cleaned_dataset.id
    else:
        old_stored_path = Path(dataset.stored_path)
        new_path = upload_dir / f"{uuid.uuid4().hex}_autocleaned.csv"
        current_df.to_csv(new_path, index=False)
        invalidate_dataset_cache(dataset.stored_path)

        # Prune previous intermediate cleaned file
        if old_stored_path.exists() and old_stored_path.resolve() != new_path.resolve():
            other_ref = db.query(Dataset.id).filter(Dataset.id != dataset.id, Dataset.stored_path == str(old_stored_path)).first()
            if not other_ref and any(k in old_stored_path.name for k in ("_cleaned", "_autocleaned", "_reverted")):
                try:
                    old_stored_path.unlink(missing_ok=True)
                except Exception:
                    pass

        dataset.stored_path = str(new_path)
        dataset.row_count = rows_final
        dataset.column_count = cols_final
        dataset.quality_score = final_score
        dataset.status = "Analysis Ready"
        dataset.version += 1
        db.commit()
        target_id = dataset.id

    for audit in applied_actions:
        db.add(Transformation(
            dataset_id=target_id,
            transformation_type=audit["action_type"],
            parameters=audit["parameters"],
            description=audit["description"],
            columns_affected=[audit["column"]] if audit.get("column") else [],
            status="applied",
            trigger_source="auto_mode",
            row_count_before=audit["rows_before"],
            row_count_after=audit["rows_after"],
        ))
    db.query(ProjectInsight).filter(ProjectInsight.dataset_id == target_id).update(
        {"is_stale": True}, synchronize_session=False
    )
    db.commit()
    record_context_mutation("dataset", target_id)

    return {
        "success": True,
        "dataset_id": target_id,
        "operations_count": len(applied_actions),
        "applied_actions": applied_actions,
        "before": {
            "rows": rows_initial,
            "quality_score": initial_score,
        },
        "after": {
            "rows": rows_final,
            "quality_score": final_score,
        },
        "quality_report": final_quality,
    }


def undo_last_transformation(dataset: Dataset, db: Session) -> Dict[str, Any]:
    """
    Reverts the last transformation applied to this dataset if a parent version exists.
    """
    last_transformation = (
        db.query(Transformation)
        .filter(Transformation.dataset_id == dataset.id, Transformation.status == "applied")
        .order_by(Transformation.applied_at.desc())
        .first()
    )
    if not last_transformation:
        raise ValueError("No active transformations found to undo.")

    # Mark as reverted
    last_transformation.status = "reverted"
    db.query(ProjectInsight).filter(ProjectInsight.dataset_id == dataset.id).update(
        {"is_stale": True}, synchronize_session=False
    )
    db.commit()
    record_context_mutation("dataset", dataset.id)

    # If dataset has a parent dataset, we can restore from parent
    if dataset.parent_id:
        parent = db.query(Dataset).filter(Dataset.id == dataset.parent_id).first()
        if parent and Path(parent.stored_path).exists():
            parent_df = load_dataset_df(parent)
            upload_dir = Path(settings.UPLOAD_DIR)
            restored_path = upload_dir / f"{uuid.uuid4().hex}_reverted.csv"
            parent_df.to_csv(restored_path, index=False)

            invalidate_dataset_cache(dataset.stored_path)
            dataset.stored_path = str(restored_path)
            dataset.row_count = int(parent_df.shape[0])
            dataset.column_count = int(parent_df.shape[1])
            dataset.quality_score = parent.quality_score
            db.commit()
            return {
                "success": True,
                "reverted_transformation": last_transformation.description,
                "dataset_id": dataset.id,
                "current_rows": dataset.row_count,
            }

    return {
        "success": True,
        "reverted_transformation": last_transformation.description,
        "dataset_id": dataset.id,
        "note": "Transformation marked as reverted.",
    }


def export_dataset_file(dataset: Dataset, format_type: str, db: Session) -> Tuple[Path, str, str]:
    """
    Generates downloadable export file.
    Returns (file_path, filename, media_type).
    """
    df = load_dataset_df(dataset)
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(dataset.name).stem.replace(" ", "_")

    if format_type.lower() == "csv":
        out_path = upload_dir / f"{base_name}_export_{uuid.uuid4().hex[:6]}.csv"
        df.to_csv(out_path, index=False)
        return out_path, f"cleaned_{base_name}.csv", "text/csv"

    if format_type.lower() in ("xlsx", "excel"):
        out_path = upload_dir / f"{base_name}_export_{uuid.uuid4().hex[:6]}.xlsx"
        df.to_excel(out_path, index=False, engine="openpyxl")
        return out_path, f"cleaned_{base_name}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    if format_type.lower() in ("report", "summary", "markdown", "md"):
        quality = inspect_data_quality(df)
        transformations = (
            db.query(Transformation)
            .filter(Transformation.dataset_id == dataset.id)
            .order_by(Transformation.applied_at.asc())
            .all()
        )
        lines = [
            f"# Data Preprocessing & Quality Summary Report",
            f"**Dataset**: {dataset.name}",
            f"**File**: {dataset.original_filename or dataset.name}",
            f"**Status**: {dataset.status}",
            f"**Overall Quality Score**: {quality.get('quality_score', 0)} / 100",
            f"**Row Count**: {df.shape[0]} | **Column Count**: {df.shape[1]}",
            f"**Duplicates Detected**: {quality.get('duplicate_rows', 0)}",
            "",
            "## Data Transformations Applied",
        ]
        if transformations:
            for i, t in enumerate(transformations, 1):
                lines.append(f"{i}. **{t.transformation_type}**: {t.description} (Rows: {t.row_count_before} -> {t.row_count_after})")
        else:
            lines.append("_No manual transformations recorded._")

        lines.extend([
            "",
            "## Column Quality Health",
            "| Column | Data Type | Null Count | Null % | Unique Values | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for col_info in quality.get("columns", []):
            lines.append(
                f"| {col_info.get('name')} | {col_info.get('data_type')} | {col_info.get('null_count')} | {col_info.get('null_percentage', 0)}% | {col_info.get('unique_count')} | {'Healthy' if col_info.get('null_count', 0) == 0 else 'Issues Present'} |"
            )

        out_path = upload_dir / f"{base_name}_quality_report_{uuid.uuid4().hex[:6]}.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path, f"{base_name}_quality_report.md", "text/markdown"

    if format_type.lower() == "log":
        transformations = (
            db.query(Transformation)
            .filter(Transformation.dataset_id == dataset.id)
            .order_by(Transformation.applied_at.asc())
            .all()
        )
        log_data = {
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "quality_score": dataset.quality_score,
            "transformations": [
                {
                    "id": t.id,
                    "type": t.transformation_type,
                    "description": t.description,
                    "parameters": t.parameters,
                    "rows_before": t.row_count_before,
                    "rows_after": t.row_count_after,
                    "status": t.status,
                    "applied_at": t.applied_at.isoformat() if t.applied_at else None,
                }
                for t in transformations
            ],
        }
        out_path = upload_dir / f"{base_name}_audit_log_{uuid.uuid4().hex[:6]}.json"
        out_path.write_text(json.dumps(log_data, indent=2), encoding="utf-8")
        return out_path, f"{base_name}_cleaning_log.json", "application/json"

    raise ValueError(f"Unsupported export format: {format_type}")


def prune_stale_cleaning_files(db: Session) -> Dict[str, Any]:
    """
    Scans the upload directory and safely removes orphaned intermediate cleaned/exported files
    that are not referenced by any active Dataset in the database.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        return {"pruned_count": 0, "freed_bytes": 0, "freed_mb": 0.0}

    # Fetch all referenced paths from Dataset table
    referenced_records = db.query(Dataset.stored_path).all()
    referenced_paths = {Path(r[0]).resolve() for r in referenced_records if r[0]}

    pruned_count = 0
    freed_bytes = 0

    patterns = ["*_cleaned.csv", "*_autocleaned.csv", "*_reverted.csv", "*_export_*.*", "*_audit_log_*.json"]
    for pattern in patterns:
        for file_path in upload_dir.glob(pattern):
            if file_path.is_file():
                try:
                    resolved = file_path.resolve()
                    if resolved not in referenced_paths:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        pruned_count += 1
                        freed_bytes += size
                except Exception:
                    pass

    return {
        "pruned_count": pruned_count,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
    }

