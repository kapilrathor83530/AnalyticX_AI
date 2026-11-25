import io
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dataset import Dataset
from app.models.scenario import Scenario
from app.services.data_service import load_dataset_df
from app.services.export_service import DARK_FILL, HEADER_FONT, THIN_BORDER, _autofit_columns
from app.services.report_center_service import (
    delete_report_record,
    export_scenario_comparison_report,
    export_single_insight,
    generate_project_package_zip,
    generate_report_artifact,
    generate_selected_reports_zip,
    get_report_record,
    list_reports,
)
from app.services.report_service import (
    analysis_summary_to_csv,
    build_docx_report,
    build_pdf_report,
    build_pdf_report_with_charts,
    build_pptx_report,
    build_report_metadata,
    dataset_to_csv,
    scenario_report_to_csv,
)

router = APIRouter(prefix="/reports", tags=["reports"])


# ==============================================================================
# REPORT CENTER CORE ENDPOINTS
# ==============================================================================

@router.get("")
@router.get("/")
def get_reports_library(
    dataset_id: Optional[int] = Query(None),
    report_type: Optional[str] = Query(None),
    export_format: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """Lists generated reports with multi-criteria filtering, search, and pagination."""
    items, total = list_reports(
        db,
        dataset_id=dataset_id,
        report_type=report_type,
        export_format=export_format,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"reports": items, "total": total}


@router.post("/generate")
def create_report(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Generates and persists a report artifact (statistical, insights, forecast, dashboard, cleaning)."""
    dataset_id = payload.get("dataset_id")
    report_type = payload.get("report_type")
    export_format = payload.get("export_format", "pdf")
    title = payload.get("title")
    parameters = payload.get("parameters", {})

    if not dataset_id or not report_type:
        raise HTTPException(status_code=400, detail="dataset_id and report_type are required")

    try:
        record, content, media_type = generate_report_artifact(
            db=db,
            dataset_id=dataset_id,
            report_type=report_type,
            export_format=export_format,
            title=title,
            parameters=parameters,
        )
        return {
            "success": True,
            "report_id": record.id,
            "title": record.title,
            "report_type": record.report_type,
            "export_format": record.export_format,
            "file_size_bytes": record.file_size_bytes,
            "download_url": f"/api/v1/reports/{record.id}/download",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


@router.post("/export-package")
def create_export_package(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Builds a complete multi-folder project report ZIP archive with README and manifest."""
    dataset_id = payload.get("dataset_id")
    selected_categories = payload.get("selected_categories")

    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")

    try:
        record, zip_bytes = generate_project_package_zip(
            db=db,
            dataset_id=dataset_id,
            selected_categories=selected_categories,
        )
        clean_filename = f"Analyticx_Package_dataset_{dataset_id}.zip"
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export package error: {str(e)}")


@router.post("/batch-download")
def create_batch_selected_download(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Packages a user-selected set of reports into a clean ZIP archive with manifest and README."""
    report_ids = payload.get("report_ids", [])
    if not report_ids:
        raise HTTPException(status_code=400, detail="report_ids list is required and cannot be empty.")

    try:
        zip_bytes, manifest = generate_selected_reports_zip(db=db, report_ids=report_ids)
        filename = f"Analyticx_Selected_Reports_{len(report_ids)}_items.zip"
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch download error: {str(e)}")


@router.post("/batch-delete")
def batch_delete_reports(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Deletes multiple selected reports from the database and storage."""
    report_ids = payload.get("report_ids", [])
    if not report_ids:
        raise HTTPException(status_code=400, detail="report_ids list is required.")

    deleted_count = 0
    for r_id in report_ids:
        if delete_report_record(db, r_id):
            deleted_count += 1
    return {"success": True, "deleted_count": deleted_count}


@router.post("/insight/export")
def download_single_insight(payload: Dict[str, Any] = Body(...)):
    """Exports an individual insight finding into PDF, CSV, Word DOCX, or JSON format."""
    insight = payload.get("insight")
    if not insight or not isinstance(insight, dict):
        raise HTTPException(status_code=400, detail="Valid insight dictionary is required.")
    export_format = payload.get("format", "pdf").lower()

    try:
        content_bytes, media_type = export_single_insight(insight, export_format=export_format)
        clean_title = "".join(c for c in insight.get("title", "Insight") if c.isalnum() or c in ("-", "_")).strip() or "Insight"
        filename = f"Analyticx_Insight_{clean_title}.{export_format}"
        return Response(
            content=content_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insight export error: {str(e)}")


@router.get("/scenarios/{dataset_id}/download")
def download_scenario_comparison_report(
    dataset_id: int,
    format: str = Query("pdf"),
    db: Session = Depends(get_db),
):
    """Direct download for Business Decision Scenario Simulation reports (PDF, XLSX, CSV, JSON, DOCX)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    scenarios = db.query(Scenario).filter(Scenario.dataset_id == dataset_id).all()
    try:
        content_bytes, media_type = export_scenario_comparison_report(
            scenarios=scenarios,
            dataset_name=dataset.name,
            export_format=format.lower(),
        )
        filename = f"Analyticx_Scenario_Report_dataset_{dataset_id}.{format.lower()}"
        return Response(
            content=content_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chart/export-data")
def export_chart_data(payload: Dict[str, Any] = Body(...)):
    """Exports raw or aggregated data for ANY chart across Analyticx AI as CSV or Excel."""
    title = payload.get("title", "Chart_Data")
    columns = payload.get("columns", [])
    rows = payload.get("rows", [])
    if not rows and "data" in payload and isinstance(payload["data"], list):
        rows = payload["data"]
    if not columns and rows and isinstance(rows[0], dict):
        columns = list(rows[0].keys())

    fmt = payload.get("format", "csv").lower()

    clean_title = "".join(c for c in title if c.isalnum() or c in ("-", "_")).strip() or "Chart_Data"

    if fmt == "xlsx":
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = clean_title[:31]
        ws.views.sheetView[0].showGridLines = True

        ws.append(columns)
        for cell in ws[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT

        for r_idx, row in enumerate(rows, start=2):
            ws.append([row.get(c, "") for c in columns])
            for c_idx in range(1, len(columns) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.border = THIN_BORDER
        _autofit_columns(ws)

        buf = io.BytesIO()
        wb.save(buf)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.xlsx"'},
        )
    else:
        # CSV output
        import csv
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})
        return Response(
            content=buf.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.csv"'},
        )


# ==============================================================================
# DIRECT WORKSPACE DOWNLOAD ENDPOINTS (INSTANT SINGLE-CLICK)
# ==============================================================================

@router.get("/statistical/{dataset_id}/download")
def download_statistical_report_direct(
    dataset_id: int,
    format: str = Query("pdf"),
    db: Session = Depends(get_db),
):
    """Direct instant download for Complete Statistical Report (PDF, XLSX, CSV, JSON)."""
    try:
        record, content, media_type = generate_report_artifact(
            db=db,
            dataset_id=dataset_id,
            report_type="statistical",
            export_format=format.lower(),
        )
        filename = f"Analyticx_Statistical_Report_dataset_{dataset_id}.{format.lower()}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/{dataset_id}/download")
def download_insights_report_direct(
    dataset_id: int,
    format: str = Query("pdf"),
    db: Session = Depends(get_db),
):
    """Direct instant download for Project Insights (PDF, XLSX, JSON, PPTX, DOCX)."""
    try:
        record, content, media_type = generate_report_artifact(
            db=db,
            dataset_id=dataset_id,
            report_type="insights",
            export_format=format.lower(),
        )
        filename = f"Analyticx_Project_Insights_dataset_{dataset_id}.{format.lower()}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/{dataset_id}/download")
def download_forecast_report_direct(
    dataset_id: int,
    format: str = Query("pdf"),
    run_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Direct instant download for Forecasting Lab (PDF, XLSX, CSV, JSON)."""
    try:
        record, content, media_type = generate_report_artifact(
            db=db,
            dataset_id=dataset_id,
            report_type="forecast",
            export_format=format.lower(),
            parameters={"run_id": run_id} if run_id else {},
        )
        filename = f"Analyticx_Forecast_Report_dataset_{dataset_id}.{format.lower()}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/{dataset_id}/download")
def download_dashboard_report_direct(
    dataset_id: int,
    format: str = Query("xlsx"),
    db: Session = Depends(get_db),
):
    """Direct instant download for Dashboard (XLSX, PDF, JSON)."""
    try:
        record, content, media_type = generate_report_artifact(
            db=db,
            dataset_id=dataset_id,
            report_type="dashboard",
            export_format=format.lower(),
        )
        filename = f"Analyticx_Dashboard_dataset_{dataset_id}.{format.lower()}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleaning/{dataset_id}/download")
def download_cleaning_report_direct(
    dataset_id: int,
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """Direct instant download for Data Prep & Cleaning Report (CSV, JSON, PDF)."""
    try:
        record, content, media_type = generate_report_artifact(
            db=db,
            dataset_id=dataset_id,
            report_type="cleaning",
            export_format=format.lower(),
        )
        filename = f"Analyticx_Data_Cleaning_Report_dataset_{dataset_id}.{format.lower()}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/item/{report_id}")
def get_single_report(report_id: int, db: Session = Depends(get_db)):
    """Retrieves report metadata by ID."""
    rec = get_report_record(db, report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": rec.id,
        "title": rec.title,
        "report_type": rec.report_type,
        "export_format": rec.export_format,
        "dataset_id": rec.dataset_id,
        "dataset_name": rec.dataset.name if rec.dataset else "System Workspace",
        "file_size_bytes": rec.file_size_bytes or 0,
        "status": rec.status,
        "dataset_version": rec.dataset_version,
        "is_stale": rec.is_stale,
        "parameters": rec.parameters or {},
        "report_metadata": rec.report_metadata or {},
        "created_at": rec.created_at.isoformat() if rec.created_at else "",
        "download_url": f"/api/v1/reports/{rec.id}/download",
    }


@router.get("/{report_id}/download")
def download_saved_report(
    report_id: int,
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Downloads a saved report binary artifact, or dynamically generates in the user-selected format."""
    rec = get_report_record(db, report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Report not found")

    target_format = format.lower() if format else rec.export_format

    media_map = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "zip": "application/zip",
        "json": "application/json",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    # If user selected a specific format different from the record's primary format, generate on-the-fly!
    if format and target_format != rec.export_format and rec.dataset_id:
        try:
            _, content_bytes, media_type = generate_report_artifact(
                db=db,
                dataset_id=rec.dataset_id,
                report_type=rec.report_type,
                export_format=target_format,
                title=rec.title,
                parameters=rec.parameters,
            )
            clean_title = "".join(c for c in rec.title if c.isalnum() or c in ("-", "_")).strip() or f"report_{rec.id}"
            filename = f"Analyticx_{clean_title}.{target_format}"
            return Response(
                content=content_bytes,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot generate format '{target_format}': {str(e)}")

    if not rec.file_path or not os.path.exists(rec.file_path):
        if rec.dataset_id:
            try:
                _, content_bytes, media_type = generate_report_artifact(
                    db=db,
                    dataset_id=rec.dataset_id,
                    report_type=rec.report_type,
                    export_format=target_format,
                    title=rec.title,
                    parameters=rec.parameters,
                )
                clean_title = "".join(c for c in rec.title if c.isalnum() or c in ("-", "_")).strip() or f"report_{rec.id}"
                filename = f"Analyticx_{clean_title}.{target_format}"
                return Response(
                    content=content_bytes,
                    media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
            except Exception:
                raise HTTPException(status_code=404, detail="Report file not found and could not be regenerated")
        raise HTTPException(status_code=404, detail="Report file not found on storage")

    filename = os.path.basename(rec.file_path)
    media_type = media_map.get(rec.export_format, "application/octet-stream")

    with open(rec.file_path, "rb") as f:
        file_bytes = f.read()

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}")
def delete_single_report(report_id: int, db: Session = Depends(get_db)):
    """Deletes a saved report and cleans up its stored file."""
    success = delete_report_record(db, report_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True, "message": "Report deleted successfully"}



@router.get("/dataset/{dataset_id}/csv")
def export_dataset_csv(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(dataset)
    content = dataset_to_csv(df)
    filename = f"dataset_{dataset_id}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dataset/{dataset_id}/summary.csv")
def export_summary(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    summary = {"profile": {"row_count": dataset.row_count, "column_count": dataset.column_count}}
    content = analysis_summary_to_csv(summary)
    filename = f"summary_{dataset_id}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/scenarios/{dataset_id}.csv")
def export_scenarios(dataset_id: int, db: Session = Depends(get_db)):
    scenarios = db.query(Scenario).filter(Scenario.dataset_id == dataset_id).all()
    payload = [{"name": s.name, "results": s.results} for s in scenarios]
    content = scenario_report_to_csv(payload)
    filename = f"scenarios_{dataset_id}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/metadata/{dataset_id}")
def report_metadata(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return build_report_metadata(dataset.name)

from fastapi import Body


@router.api_route("/dataset/{dataset_id}/pdf", methods=["GET", "POST"])
def export_pdf(dataset_id: int, payload: Optional[dict] = Body(default=None), db: Session = Depends(get_db)):
    payload = payload or {}
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    metadata = build_report_metadata(dataset.name)

    sections = payload.get("sections", []) or [
        {
            "title": "Dataset Summary",
            "rows": [
                {"Field": "Rows", "Value": dataset.row_count},
                {"Field": "Columns", "Value": dataset.column_count},
                {"Field": "Original Filename", "Value": dataset.original_filename},
            ],
        }
    ]

    pdf_bytes = build_pdf_report(metadata, sections)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{dataset_id}.pdf"'},
    )

@router.post("/dataset/{dataset_id}/pdf-full")
def export_pdf_full(dataset_id: int, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    metadata = build_report_metadata(dataset.name)
    sections = payload.get("sections", []) or [
        {
            "title": "Dataset Summary",
            "rows": [
                {"Field": "Rows", "Value": dataset.row_count},
                {"Field": "Columns", "Value": dataset.column_count},
                {"Field": "Filename", "Value": dataset.original_filename},
            ],
        }
    ]
    charts = payload.get("charts", [])

    pdf_bytes = build_pdf_report_with_charts(metadata, sections, charts)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_full_{dataset_id}.pdf"'},
    )


@router.api_route("/dataset/{dataset_id}/pptx", methods=["GET", "POST"])
def export_pptx(dataset_id: int, payload: Optional[dict] = Body(default=None), db: Session = Depends(get_db)):
    payload = payload or {}
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    metadata = build_report_metadata(dataset.name)
    sections = payload.get("sections", []) or [
        {
            "title": "Dataset Summary",
            "rows": [
                {"Field": "Rows", "Value": dataset.row_count},
                {"Field": "Columns", "Value": dataset.column_count},
                {"Field": "Filename", "Value": dataset.original_filename},
            ],
        }
    ]
    recommendations = payload.get("recommendations", [])

    pptx_bytes = build_pptx_report(metadata, sections, recommendations)
    filename = f"Analyticx_{dataset.name.replace(' ', '_')}_Executive_Deck.pptx"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.api_route("/dataset/{dataset_id}/docx", methods=["GET", "POST"])
def export_docx(dataset_id: int, payload: Optional[dict] = Body(default=None), db: Session = Depends(get_db)):
    payload = payload or {}
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    metadata = build_report_metadata(dataset.name)
    sections = payload.get("sections", []) or [
        {
            "title": "Dataset Summary",
            "rows": [
                {"Field": "Rows", "Value": dataset.row_count},
                {"Field": "Columns", "Value": dataset.column_count},
                {"Field": "Filename", "Value": dataset.original_filename},
            ],
        }
    ]
    recommendations = payload.get("recommendations", [])

    docx_bytes = build_docx_report(metadata, sections, recommendations)
    filename = f"Analyticx_{dataset.name.replace(' ', '_')}_Executive_Report.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# In-memory storage for publicly shared executive reports
_SHARED_REPORTS: dict[str, dict] = {}


@router.post("/dataset/{dataset_id}/share")
def create_shareable_report(dataset_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    import uuid
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    token = uuid.uuid4().hex
    report_record = {
        "share_token": token,
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "quality_score": getattr(dataset, "quality_score", None) or 95.0,
        "title": payload.get("title", f"Executive Report: {dataset.name}"),
        "generated_at": payload.get("generated_at") or "2026-10-28T00:00:00Z",
        "executive_summary": payload.get("executive_summary", ""),
        "root_cause_data": payload.get("root_cause_data"),
        "sections": payload.get("sections", []),
        "recommendations": payload.get("recommendations", []),
    }
    _SHARED_REPORTS[token] = report_record
    return {
        "success": True,
        "share_token": token,
        "share_url": f"/shared/report/{token}",
    }


@router.get("/shared/{token}")
def get_shared_report(token: str):
    report = _SHARED_REPORTS.get(token)
    if not report:
        raise HTTPException(status_code=404, detail="Shared report not found or link has expired")
    return report



# In-memory storage for scheduled report automation configurations
_REPORT_SCHEDULES: dict[int, list[dict]] = {}


@router.get("/dataset/{dataset_id}/schedules")
def list_report_schedules(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    schedules = _REPORT_SCHEDULES.get(dataset_id, [
        {
            "id": f"sched_{dataset_id}_1",
            "name": "Weekly Executive Management Digest",
            "frequency": "weekly",
            "day": "Monday",
            "time": "08:00 UTC",
            "format": "pdf",
            "active": True,
            "recipient_emails": ["executive@analyticx.ai"],
            "last_run": "2026-10-27T08:00:00Z",
            "next_run": "2026-11-03T08:00:00Z",
        }
    ])
    _REPORT_SCHEDULES[dataset_id] = schedules
    return {"dataset_id": dataset_id, "schedules": schedules}


@router.post("/dataset/{dataset_id}/schedules")
def create_report_schedule(dataset_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    import uuid
    new_schedule = {
        "id": f"sched_{uuid.uuid4().hex[:8]}",
        "name": payload.get("name", "Executive Scheduled Report"),
        "frequency": payload.get("frequency", "weekly"),
        "day": payload.get("day", "Monday"),
        "time": payload.get("time", "09:00 UTC"),
        "format": payload.get("format", "pdf"),
        "active": True,
        "recipient_emails": payload.get("recipient_emails", ["executive@analyticx.ai"]),
        "last_run": None,
        "next_run": "Scheduled on cron trigger",
    }
    schedules = _REPORT_SCHEDULES.setdefault(dataset_id, [])
    schedules.append(new_schedule)
    return {"success": True, "schedule": new_schedule}

