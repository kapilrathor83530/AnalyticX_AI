import io
import json
import zipfile
from fastapi.testclient import TestClient
import openpyxl
import pytest

from app.main import app

client = TestClient(app)


def _upload_test_dataset():
    csv_content = (
        "date,category,sales,profit,units\n"
        "2024-01-01,Tech,1000,200,10\n"
        "2024-02-01,Furniture,500,50,5\n"
        "2024-03-01,Tech,1200,300,12\n"
        "2024-04-01,Office,300,30,15\n"
        "2024-05-01,Tech,1500,400,15\n"
        "2024-06-01,Furniture,700,70,7\n"
        "2024-07-01,Tech,1800,500,18\n"
        "2024-08-01,Office,400,40,20\n"
    )
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sales_analytics.csv", csv_content, "text/csv")},
    )
    assert res.status_code == 200
    return res.json()["id"]


def test_list_reports_endpoint():
    res = client.get("/api/v1/reports")
    assert res.status_code == 200
    data = res.json()
    assert "reports" in data
    assert "total" in data
    assert isinstance(data["reports"], list)


def test_generate_statistical_report_xlsx_and_pdf():
    dataset_id = _upload_test_dataset()

    # 1. Excel XLSX
    res_xlsx = client.post(
        "/api/v1/reports/generate",
        json={"dataset_id": dataset_id, "report_type": "statistical", "export_format": "xlsx"},
    )
    assert res_xlsx.status_code == 200
    meta_xlsx = res_xlsx.json()
    assert meta_xlsx["success"] is True
    assert meta_xlsx["export_format"] == "xlsx"
    assert meta_xlsx["file_size_bytes"] > 0

    # Download it
    dl_xlsx = client.get(f"/api/v1/reports/{meta_xlsx['report_id']}/download")
    assert dl_xlsx.status_code == 200
    assert "application/vnd.openxmlformats" in dl_xlsx.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(dl_xlsx.content))
    assert "Overview" in wb.sheetnames
    assert "Numerical_Stats" in wb.sheetnames
    assert "Schema" in wb.sheetnames

    # 2. PDF
    res_pdf = client.post(
        "/api/v1/reports/generate",
        json={"dataset_id": dataset_id, "report_type": "statistical", "export_format": "pdf"},
    )
    assert res_pdf.status_code == 200
    meta_pdf = res_pdf.json()
    dl_pdf = client.get(f"/api/v1/reports/{meta_pdf['report_id']}/download")
    assert dl_pdf.status_code == 200
    assert dl_pdf.headers["content-type"] == "application/pdf"
    assert dl_pdf.content.startswith(b"%PDF-")


def test_export_project_package_zip():
    dataset_id = _upload_test_dataset()

    res = client.post(
        "/api/v1/reports/export-package",
        json={"dataset_id": dataset_id, "selected_categories": ["statistical", "cleaning"]},
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert res.content.startswith(b"PK")

    # Unpack and verify zip manifest and folders
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = zf.namelist()
    assert "README.txt" in names
    assert "manifest.json" in names
    assert any("Statistical_Analysis/" in n for n in names)

    manifest_bytes = zf.read("manifest.json")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    assert manifest["dataset_id"] == dataset_id
    assert manifest["total_files"] > 0


def test_chart_export_data_endpoint():
    # 1. CSV
    res_csv = client.post(
        "/api/v1/reports/chart/export-data",
        json={
            "title": "Revenue by Region",
            "columns": ["region", "revenue"],
            "rows": [{"region": "North", "revenue": 5000}, {"region": "South", "revenue": 3000}],
            "format": "csv",
        },
    )
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    assert "revenue" in res_csv.text
    assert "North" in res_csv.text

    # 2. Excel XLSX
    res_xlsx = client.post(
        "/api/v1/reports/chart/export-data",
        json={
            "title": "Quarterly Trend",
            "columns": ["quarter", "sales"],
            "rows": [{"quarter": "Q1", "sales": 1200}, {"quarter": "Q2", "sales": 1500}],
            "format": "xlsx",
        },
    )
    assert res_xlsx.status_code == 200
    assert "application/vnd.openxmlformats" in res_xlsx.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert len(wb.sheetnames) >= 1


def test_direct_download_endpoints():
    dataset_id = _upload_test_dataset()

    # Direct statistical PDF
    res = client.get(f"/api/v1/reports/statistical/{dataset_id}/download?format=pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")

    # Direct statistical XLSX
    res_x = client.get(f"/api/v1/reports/statistical/{dataset_id}/download?format=xlsx")
    assert res_x.status_code == 200
    assert "application/vnd.openxmlformats" in res_x.headers["content-type"]


def test_delete_report_endpoint():
    dataset_id = _upload_test_dataset()
    res = client.post(
        "/api/v1/reports/generate",
        json={"dataset_id": dataset_id, "report_type": "statistical", "export_format": "json"},
    )
    r_id = res.json()["report_id"]

    del_res = client.delete(f"/api/v1/reports/{r_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Attempting to fetch deleted report should 404
    get_res = client.get(f"/api/v1/reports/{r_id}/download")
    assert get_res.status_code == 404


def test_download_report_user_format_selection():
    """Verifies that users can choose ANY supported format when downloading an existing report."""
    dataset_id = _upload_test_dataset()

    # 1. Generate an initial report in PDF
    gen_res = client.post(
        "/api/v1/reports/generate",
        json={"dataset_id": dataset_id, "report_type": "statistical", "export_format": "pdf"},
    )
    assert gen_res.status_code == 200
    report_id = gen_res.json()["report_id"]

    # 2. Download original PDF
    dl_pdf = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_pdf.status_code == 200
    assert dl_pdf.headers["content-type"] == "application/pdf"
    assert dl_pdf.content.startswith(b"%PDF-")

    # 3. User chooses to download as Word DOCX
    dl_docx = client.get(f"/api/v1/reports/{report_id}/download?format=docx")
    assert dl_docx.status_code == 200
    assert "wordprocessingml.document" in dl_docx.headers["content-type"]
    assert len(dl_docx.content) > 100

    # 4. User chooses to download as Excel XLSX
    dl_xlsx = client.get(f"/api/v1/reports/{report_id}/download?format=xlsx")
    assert dl_xlsx.status_code == 200
    assert "spreadsheetml.sheet" in dl_xlsx.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(dl_xlsx.content))
    assert len(wb.sheetnames) >= 1

    # 5. User chooses to download as CSV
    dl_csv = client.get(f"/api/v1/reports/{report_id}/download?format=csv")
    assert dl_csv.status_code == 200
    assert dl_csv.headers["content-type"].startswith("text/csv")
    assert "sales" in dl_csv.text

    # 6. User chooses to download as JSON
    dl_json = client.get(f"/api/v1/reports/{report_id}/download?format=json")
    assert dl_json.status_code == 200
    assert dl_json.headers["content-type"] == "application/json"
    parsed = json.loads(dl_json.text)
    assert "overview" in parsed or "dataset" in parsed


def test_batch_download_and_batch_delete():
    dataset_id = _upload_test_dataset()

    # Generate 2 reports
    res1 = client.post(
        "/api/v1/reports/generate",
        json={"dataset_id": dataset_id, "report_type": "statistical", "export_format": "pdf"},
    )
    res2 = client.post(
        "/api/v1/reports/generate",
        json={"dataset_id": dataset_id, "report_type": "statistical", "export_format": "xlsx"},
    )
    r1_id = res1.json()["report_id"]
    r2_id = res2.json()["report_id"]

    # 1. Batch download as ZIP
    batch_res = client.post(
        "/api/v1/reports/batch-download",
        json={"report_ids": [r1_id, r2_id]},
    )
    assert batch_res.status_code == 200
    assert batch_res.headers["content-type"] == "application/zip"
    assert batch_res.content.startswith(b"PK")

    zf = zipfile.ZipFile(io.BytesIO(batch_res.content))
    assert "README.txt" in zf.namelist()
    assert "manifest.json" in zf.namelist()
    assert len(zf.namelist()) >= 3

    # 2. Batch delete
    del_res = client.post(
        "/api/v1/reports/batch-delete",
        json={"report_ids": [r1_id, r2_id]},
    )
    assert del_res.status_code == 200
    assert del_res.json()["deleted_count"] == 2


def test_export_single_insight():
    insight_payload = {
        "title": "Profit Margin Outlier Detected",
        "category": "anomaly",
        "priority": "high",
        "explanation": "Tech category showed 3.2x higher profit margin than benchmark baseline.",
        "methodology": "Z-score anomaly threshold exceeding 2.5 sigma.",
        "confidence_score": 0.94,
        "supporting_metrics": {"metric_name": "profit_margin", "metric_value": "42.5%"},
    }

    # 1. PDF
    pdf_res = client.post(
        "/api/v1/reports/insight/export",
        json={"insight": insight_payload, "format": "pdf"},
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")

    # 2. CSV
    csv_res = client.post(
        "/api/v1/reports/insight/export",
        json={"insight": insight_payload, "format": "csv"},
    )
    assert csv_res.status_code == 200
    assert "profit_margin" in csv_res.text

    # 3. JSON
    json_res = client.post(
        "/api/v1/reports/insight/export",
        json={"insight": insight_payload, "format": "json"},
    )
    assert json_res.status_code == 200
    assert json_res.json()["title"] == "Profit Margin Outlier Detected"

    # 4. DOCX
    docx_res = client.post(
        "/api/v1/reports/insight/export",
        json={"insight": insight_payload, "format": "docx"},
    )
    assert docx_res.status_code == 200
    assert "wordprocessingml.document" in docx_res.headers["content-type"]


def test_scenario_download_endpoint():
    dataset_id = _upload_test_dataset()

    # Create a scenario simulation first
    sim_res = client.post(
        "/api/v1/simulation/scenario",
        json={
            "dataset_id": dataset_id,
            "name": "Q3 Revenue Expansion",
            "adjustments": [{"field": "sales", "mode": "percent", "value": 15}],
            "metric_columns": {"revenue": "sales", "cost": "profit"},
        },
    )
    assert sim_res.status_code == 200

    # 1. PDF
    pdf_dl = client.get(f"/api/v1/reports/scenarios/{dataset_id}/download?format=pdf")
    assert pdf_dl.status_code == 200
    assert pdf_dl.headers["content-type"] == "application/pdf"

    # 2. XLSX
    xlsx_dl = client.get(f"/api/v1/reports/scenarios/{dataset_id}/download?format=xlsx")
    assert xlsx_dl.status_code == 200
    assert "spreadsheetml.sheet" in xlsx_dl.headers["content-type"]

    # 3. CSV
    csv_dl = client.get(f"/api/v1/reports/scenarios/{dataset_id}/download?format=csv")
    assert csv_dl.status_code == 200, f"CSV DL failed: {csv_dl.text}"
    assert "Q3 Revenue Expansion" in csv_dl.text

