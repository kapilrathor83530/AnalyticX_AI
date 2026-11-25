"""Comprehensive Export Engine for Analyticx AI.

Supports generating:
1. Multi-sheet styled Excel (XLSX) workbooks using openpyxl.
2. Professional executive PDF reports using reportlab with page numbering, cards, and tables.
3. Tabular CSV exports.
4. Structured ZIP package archives with manifest.json and README.txt.
"""
from datetime import datetime
import io
import json
import math
from typing import Any, Dict, List, Optional
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


# --- Numbered Canvas for PDF Header / Footer ---
class NumberedCanvas(canvas.Canvas):
    """Adds header bar and dynamic footer 'Page X of Y' to every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#06b6d4"))

        # Header
        self.drawString(54, 800, "Analyticx AI")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(110, 800, "· Enterprise Intelligence & Reporting Engine")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 792, 545, 792)

        # Footer
        self.line(54, 45, 545, 45)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#94a3b8"))
        self.drawString(54, 32, "Confidential · Decision Support Report · Deterministic Calculation")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(545, 32, page_str)
        self.restoreState()


# --- OpenPyXL Helpers ---
DARK_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
SUB_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=13, bold=True, color="0F172A")
BOLD_FONT = Font(name="Calibri", size=9.5, bold=True, color="1E293B")
NORMAL_FONT = Font(name="Calibri", size=9.5, color="334155")
THIN_BORDER = Border(
    left=Side(style="thin", color="E2E8F0"),
    right=Side(style="thin", color="E2E8F0"),
    top=Side(style="thin", color="E2E8F0"),
    bottom=Side(style="thin", color="E2E8F0"),
)


def _autofit_columns(ws):
    """Autofits column widths in an openpyxl worksheet."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if "\n" in val_str:
                val_str = max(val_str.split("\n"), key=len)
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(11, min(max_len + 3, 50))


# ==============================================================================
# 1. STATISTICAL REPORT EXPORTERS (XLSX, PDF, CSV)
# ==============================================================================

def export_statistical_report_xlsx(report: Dict[str, Any]) -> bytes:
    """Generates a professional multi-sheet Excel workbook from statistical report data."""
    wb = openpyxl.Workbook()
    overview = report.get("overview", {})

    # 1. Sheet: Overview
    ws_over = wb.active
    ws_over.title = "Overview"
    ws_over.views.sheetView[0].showGridLines = True

    ws_over["A1"] = f"Analyticx AI — Statistical Profile: {overview.get('dataset_name', 'Dataset')}"
    ws_over["A1"].font = TITLE_FONT
    ws_over["A2"] = f"Generated at: {overview.get('generated_at', '')} | Quality Score: {report.get('quality_analysis', {}).get('quality_score', 100)}%"
    ws_over["A2"].font = Font(name="Calibri", size=9, italic=True, color="64748B")

    overview_rows = [
        ("Dataset Name", overview.get("dataset_name")),
        ("Total Rows", overview.get("row_count")),
        ("Total Columns", overview.get("column_count")),
        ("Total Cells", overview.get("total_cells")),
        ("Memory Footprint", overview.get("memory_formatted")),
        ("Numerical Columns", overview.get("numeric_columns_count")),
        ("Categorical Columns", overview.get("categorical_columns_count")),
        ("Datetime Columns", overview.get("datetime_columns_count")),
        ("Columns with Missing Values", overview.get("columns_with_missing_count")),
        ("Duplicate Rows", f"{overview.get('duplicate_rows_count', 0)} ({overview.get('duplicate_rows_pct', 0)}%)"),
        ("Complete Rows (Zero Nulls)", f"{overview.get('complete_rows_count', 0)} ({overview.get('complete_rows_pct', 0)}%)"),
        ("Data Quality Score", f"{report.get('quality_analysis', {}).get('quality_score', 100)}%"),
    ]

    ws_over.append([])
    ws_over.append(["Metric", "Value"])
    for cell in ws_over[4]:
        cell.fill = DARK_FILL
        cell.font = HEADER_FONT

    for r_idx, (k, v) in enumerate(overview_rows, start=5):
        ws_over.append([k, v])
        ws_over[f"A{r_idx}"].font = BOLD_FONT
        ws_over[f"B{r_idx}"].font = NORMAL_FONT
        if r_idx % 2 == 1:
            ws_over[f"A{r_idx}"].fill = ZEBRA_FILL
            ws_over[f"B{r_idx}"].fill = ZEBRA_FILL
        ws_over[f"A{r_idx}"].border = THIN_BORDER
        ws_over[f"B{r_idx}"].border = THIN_BORDER
    _autofit_columns(ws_over)

    # 2. Sheet: Schema
    ws_schema = wb.create_sheet(title="Schema")
    ws_schema.views.sheetView[0].showGridLines = True
    schema_headers = ["Column Name", "Data Type", "Inferred Type", "Non-Null Count", "Null Count", "Null %", "Unique Count", "Sample Values"]
    ws_schema.append(schema_headers)
    for cell in ws_schema[1]:
        cell.fill = DARK_FILL
        cell.font = HEADER_FONT

    for r_idx, sc in enumerate(overview.get("schema", []), start=2):
        ws_schema.append([
            sc.get("column"),
            sc.get("dtype"),
            sc.get("inferred_type"),
            sc.get("non_null_count"),
            sc.get("null_count"),
            sc.get("null_pct"),
            sc.get("unique_count"),
            ", ".join(str(s) for s in sc.get("sample_values", [])),
        ])
        for c_idx in range(1, 9):
            cell = ws_schema.cell(row=r_idx, column=c_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            if r_idx % 2 == 1:
                cell.fill = ZEBRA_FILL
    _autofit_columns(ws_schema)

    # 3. Sheet: Numerical_Stats
    num_stats = report.get("numeric_stats", {})
    if num_stats:
        ws_num = wb.create_sheet(title="Numerical_Stats")
        ws_num.views.sheetView[0].showGridLines = True
        num_headers = [
            "Column", "Count", "Mean", "Std Dev", "Min", "Q1 (25%)", "Median", "Q3 (75%)",
            "Max", "IQR", "Skewness", "Kurtosis", "CV (%)", "Zeros", "Positives", "Negatives", "Nulls"
        ]
        ws_num.append(num_headers)
        for cell in ws_num[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT

        for r_idx, (col, st) in enumerate(num_stats.items(), start=2):
            ws_num.append([
                col,
                st.get("count"),
                st.get("mean"),
                st.get("std"),
                st.get("min"),
                st.get("q1"),
                st.get("median"),
                st.get("q3"),
                st.get("max"),
                st.get("iqr"),
                st.get("skewness"),
                st.get("kurtosis"),
                st.get("cv_pct") if st.get("cv_pct") is not None else "N/A",
                st.get("zeros_count"),
                st.get("positive_count"),
                st.get("negative_count"),
                st.get("null_count"),
            ])
            for c_idx in range(1, len(num_headers) + 1):
                cell = ws_num.cell(row=r_idx, column=c_idx)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if r_idx % 2 == 1:
                    cell.fill = ZEBRA_FILL
        _autofit_columns(ws_num)

    # 4. Sheet: Outliers
    outlier_stats = report.get("outlier_stats", {})
    if outlier_stats:
        ws_out = wb.create_sheet(title="Outliers")
        ws_out.views.sheetView[0].showGridLines = True
        out_headers = ["Column", "Q1", "Q3", "IQR", "Lower Fence (Q1 - 1.5*IQR)", "Upper Fence (Q3 + 1.5*IQR)", "IQR Outliers Count", "IQR Outliers %", "Z-Score (>3.0) Count", "Z-Score %"]
        ws_out.append(out_headers)
        for cell in ws_out[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT

        for r_idx, (col, st) in enumerate(outlier_stats.items(), start=2):
            ws_out.append([
                col, st.get("q1"), st.get("q3"), st.get("iqr"), st.get("lower_fence"), st.get("upper_fence"),
                st.get("iqr_outlier_count"), st.get("iqr_outlier_pct"), st.get("zscore_outlier_count"), st.get("zscore_outlier_pct"),
            ])
            for c_idx in range(1, len(out_headers) + 1):
                cell = ws_out.cell(row=r_idx, column=c_idx)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if r_idx % 2 == 1:
                    cell.fill = ZEBRA_FILL
        _autofit_columns(ws_out)

    # 5. Sheet: Categorical_Stats
    cat_stats = report.get("categorical_stats", {})
    if cat_stats:
        ws_cat = wb.create_sheet(title="Categorical_Stats")
        ws_cat.views.sheetView[0].showGridLines = True
        cat_headers = ["Column", "Cardinality", "Unique Values", "Null Count", "Null %", "Category", "Category Frequency", "Category %", "Cumulative %"]
        ws_cat.append(cat_headers)
        for cell in ws_cat[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT

        r_idx = 2
        for col, st in cat_stats.items():
            for top_c in st.get("top_categories", []):
                ws_cat.append([
                    col, st.get("cardinality"), st.get("unique_count"), st.get("null_count"), st.get("null_pct"),
                    top_c.get("category"), top_c.get("count"), top_c.get("pct"), top_c.get("cumulative_pct")
                ])
                for c_idx in range(1, len(cat_headers) + 1):
                    cell = ws_cat.cell(row=r_idx, column=c_idx)
                    cell.font = NORMAL_FONT
                    cell.border = THIN_BORDER
                    if r_idx % 2 == 1:
                        cell.fill = ZEBRA_FILL
                r_idx += 1
        _autofit_columns(ws_cat)

    # 6. Sheet: Correlations
    corr_p = report.get("correlations_pearson", {})
    if corr_p:
        ws_corr = wb.create_sheet(title="Correlations")
        ws_corr.views.sheetView[0].showGridLines = True
        cols = list(corr_p.keys())
        ws_corr.append(["Variable"] + cols)
        for cell in ws_corr[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT

        for r_idx, c1 in enumerate(cols, start=2):
            row_vals = [c1] + [corr_p[c1].get(c2, 0.0) for c2 in cols]
            ws_corr.append(row_vals)
            for c_idx in range(1, len(cols) + 2):
                cell = ws_corr.cell(row=r_idx, column=c_idx)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if c_idx > 1 and isinstance(cell.value, (int, float)):
                    cell.number_format = "0.0000"
                    if cell.value == 1.0:
                        cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
                    elif abs(cell.value) >= 0.7:
                        cell.fill = PatternFill(start_color="BAE6FD", end_color="BAE6FD", fill_type="solid")
        _autofit_columns(ws_corr)

    # 7. Sheet: Segment_Analysis
    seg = report.get("segment_analysis")
    if seg and seg.get("segments"):
        ws_seg = wb.create_sheet(title="Segment_Analysis")
        ws_seg.views.sheetView[0].showGridLines = True
        ws_seg["A1"] = f"Segment Breakdown: {seg.get('metric_column')} by {seg.get('group_column')}"
        ws_seg["A1"].font = TITLE_FONT
        ws_seg.append([])
        seg_headers = ["Segment Group", "Count", "Sum", "Mean", "Std Dev", "Min", "Median", "Max"]
        ws_seg.append(seg_headers)
        for cell in ws_seg[3]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT

        for r_idx, s in enumerate(seg.get("segments", []), start=4):
            ws_seg.append([
                s.get("group"), s.get("count"), s.get("sum"), s.get("mean"),
                s.get("std"), s.get("min"), s.get("median"), s.get("max")
            ])
            for c_idx in range(1, len(seg_headers) + 1):
                cell = ws_seg.cell(row=r_idx, column=c_idx)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if r_idx % 2 == 1:
                    cell.fill = ZEBRA_FILL
        _autofit_columns(ws_seg)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_statistical_report_pdf(report: Dict[str, Any]) -> bytes:
    """Generates an executive PDF statistical report using ReportLab."""
    overview = report.get("overview", {})
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
    )

    story: List[Any] = []

    # Title & Subtitle
    story.append(Paragraph(f"Statistical Intelligence Profile: {overview.get('dataset_name', 'Dataset')}", title_style))
    story.append(Paragraph(
        f"Generated by Analyticx AI · Date: {overview.get('generated_at', '')[:10]} · "
        f"Records: {overview.get('row_count'):,} · Columns: {overview.get('column_count')} · "
        f"Quality Score: {report.get('quality_analysis', {}).get('quality_score', 100)}%",
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    # KPI Summary Cards Table
    kpi_data = [
        [
            Paragraph(f"<b>Rows</b><br/>{overview.get('row_count'):,}", body_style),
            Paragraph(f"<b>Columns</b><br/>{overview.get('column_count')}", body_style),
            Paragraph(f"<b>Memory</b><br/>{overview.get('memory_formatted')}", body_style),
            Paragraph(f"<b>Complete Rows</b><br/>{overview.get('complete_rows_pct')}%", body_style),
            Paragraph(f"<b>Duplicates</b><br/>{overview.get('duplicate_rows_pct')}%", body_style),
            Paragraph(f"<b>Quality Score</b><br/>{report.get('quality_analysis', {}).get('quality_score', 100)}%", body_style),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[80, 80, 80, 80, 85, 85], hAlign="CENTER")
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # 1. Numerical Statistics
    num_stats = report.get("numeric_stats", {})
    if num_stats:
        story.append(Paragraph("1. Numerical Descriptive Statistics (Moments & Spread)", h2_style))
        headers = ["Column", "Mean", "Std Dev", "Min", "Q1", "Median", "Q3", "Max", "IQR", "Skew"]
        rows = [[Paragraph(h, table_header_style) for h in headers]]
        for col, st in list(num_stats.items())[:12]:
            rows.append([
                Paragraph(col[:14], table_cell_style),
                Paragraph(str(st.get("mean")), table_cell_style),
                Paragraph(str(st.get("std")), table_cell_style),
                Paragraph(str(st.get("min")), table_cell_style),
                Paragraph(str(st.get("q1")), table_cell_style),
                Paragraph(str(st.get("median")), table_cell_style),
                Paragraph(str(st.get("q3")), table_cell_style),
                Paragraph(str(st.get("max")), table_cell_style),
                Paragraph(str(st.get("iqr")), table_cell_style),
                Paragraph(str(st.get("skewness")), table_cell_style),
            ])
        t_num = Table(rows, colWidths=[75, 46, 46, 43, 43, 46, 43, 46, 43, 43], hAlign="CENTER")
        t_num.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_num)
        story.append(Spacer(1, 14))

    # 2. Outliers & Data Quality
    outlier_stats = report.get("outlier_stats", {})
    if outlier_stats:
        story.append(Paragraph("2. Outlier Boundaries & Anomaly Detection (IQR & Z-Score)", h2_style))
        o_headers = ["Metric Column", "Q1 Fence", "Q3 Fence", "Lower Fence", "Upper Fence", "IQR Outliers", "IQR %", "Z-Score (>3.0)"]
        o_rows = [[Paragraph(h, table_header_style) for h in o_headers]]
        for col, st in list(outlier_stats.items())[:8]:
            o_rows.append([
                Paragraph(col[:16], table_cell_style),
                Paragraph(str(st.get("q1")), table_cell_style),
                Paragraph(str(st.get("q3")), table_cell_style),
                Paragraph(str(st.get("lower_fence")), table_cell_style),
                Paragraph(str(st.get("upper_fence")), table_cell_style),
                Paragraph(str(st.get("iqr_outlier_count")), table_cell_style),
                Paragraph(f"{st.get('iqr_outlier_pct')}%", table_cell_style),
                Paragraph(str(st.get("zscore_outlier_count")), table_cell_style),
            ])
        t_out = Table(o_rows, colWidths=[90, 52, 52, 58, 58, 55, 45, 60], hAlign="CENTER")
        t_out.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_out)
        story.append(Spacer(1, 14))

    # 3. Categorical Frequencies
    cat_stats = report.get("categorical_stats", {})
    if cat_stats:
        story.append(Paragraph("3. Dominant Categorical Attributes & Cumulative Shares", h2_style))
        c_headers = ["Column", "Cardinality", "Unique", "Top Category", "Frequency", "Share %", "Cumulative %"]
        c_rows = [[Paragraph(h, table_header_style) for h in c_headers]]
        for col, st in list(cat_stats.items())[:6]:
            top1 = st.get("top_categories", [{}])[0] if st.get("top_categories") else {}
            c_rows.append([
                Paragraph(col[:16], table_cell_style),
                Paragraph(st.get("cardinality", "N/A"), table_cell_style),
                Paragraph(str(st.get("unique_count", 0)), table_cell_style),
                Paragraph(str(top1.get("category", "N/A"))[:18], table_cell_style),
                Paragraph(str(top1.get("count", 0)), table_cell_style),
                Paragraph(f"{top1.get('pct', 0)}%", table_cell_style),
                Paragraph(f"{top1.get('cumulative_pct', 0)}%", table_cell_style),
            ])
        t_cat = Table(c_rows, colWidths=[90, 55, 45, 110, 55, 55, 60], hAlign="CENTER")
        t_cat.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cat)
        story.append(Spacer(1, 14))

    # 4. Correlations & Segment Findings
    notable = report.get("notable_correlations", [])
    if notable:
        story.append(Paragraph("4. Linear & Rank Associations (Pearson & Spearman)", h2_style))
        rel_headers = ["Pair Col 1", "Pair Col 2", "Pearson r", "Spearman r", "Strength", "Direction"]
        rel_rows = [[Paragraph(h, table_header_style) for h in rel_headers]]
        for item in notable[:6]:
            rel_rows.append([
                Paragraph(item["col1"][:16], table_cell_style),
                Paragraph(item["col2"][:16], table_cell_style),
                Paragraph(str(item["pearson"]), table_cell_style),
                Paragraph(str(item["spearman"]), table_cell_style),
                Paragraph(item["strength"], table_cell_style),
                Paragraph(item["direction"], table_cell_style),
            ])
        t_rel = Table(rel_rows, colWidths=[95, 95, 65, 65, 75, 75], hAlign="CENTER")
        t_rel.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_rel)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# ==============================================================================
# 2. FORECASTING REPORT EXPORTERS (PDF, CSV, XLSX)
# ==============================================================================

def export_forecast_report_csv(run: Dict[str, Any]) -> bytes:
    """Exports projected forecast points and confidence bounds to CSV."""
    lines = ["date,projected_value,lower_80,upper_80,lower_95,upper_95\n"]
    for p in run.get("predictions", []):
        d = p.get("date", "")
        v = p.get("value", 0.0)
        l80 = p.get("lower_80", "")
        u80 = p.get("upper_80", "")
        l95 = p.get("lower_95", "")
        u95 = p.get("upper_95", "")
        lines.append(f"{d},{v},{l80},{u80},{l95},{u95}\n")
    return "".join(lines).encode("utf-8")


def export_forecast_report_xlsx(run: Dict[str, Any], dataset_name: str = "Dataset") -> bytes:
    """Exports complete forecasting lab results (predictions, models, scenarios) to Excel."""
    wb = openpyxl.Workbook()

    # Sheet 1: Summary
    ws = wb.active
    ws.title = "Summary"
    ws.views.sheetView[0].showGridLines = True
    ws["A1"] = f"Analyticx AI — Forecasting Lab Report: {dataset_name}"
    ws["A1"].font = TITLE_FONT

    m = run.get("metrics", {})
    summary_rows = [
        ("Target Metric", run.get("target_column")),
        ("Date Dimension", run.get("date_column")),
        ("Forecast Horizon", f"{run.get('horizon')} periods"),
        ("Cadence Frequency", run.get("frequency")),
        ("Champion Model", run.get("model_type")),
        ("Holdout WAPE (%)", m.get("wape")),
        ("Holdout RMSE", m.get("rmse")),
        ("Holdout MAE", m.get("mae")),
        ("Holdout R²", m.get("r2")),
        ("WAPE Lift vs Naive (%)", m.get("wape_improvement_vs_naive_pct")),
        ("Created At", run.get("created_at")),
    ]
    ws.append([])
    ws.append(["Parameter", "Value"])
    for cell in ws[3]:
        cell.fill = DARK_FILL
        cell.font = HEADER_FONT
    for r_idx, (k, v) in enumerate(summary_rows, start=4):
        ws.append([k, v])
        ws[f"A{r_idx}"].font = BOLD_FONT
        ws[f"B{r_idx}"].font = NORMAL_FONT
        ws[f"A{r_idx}"].border = THIN_BORDER
        ws[f"B{r_idx}"].border = THIN_BORDER
        if r_idx % 2 == 1:
            ws[f"A{r_idx}"].fill = ZEBRA_FILL
            ws[f"B{r_idx}"].fill = ZEBRA_FILL
    _autofit_columns(ws)

    # Sheet 2: Predictions
    ws_pred = wb.create_sheet(title="Forecast_Projections")
    ws_pred.views.sheetView[0].showGridLines = True
    p_headers = ["Date", "Projected Forecast", "Lower 80% CI", "Upper 80% CI", "Lower 95% CI", "Upper 95% CI"]
    ws_pred.append(p_headers)
    for cell in ws_pred[1]:
        cell.fill = DARK_FILL
        cell.font = HEADER_FONT
    for r_idx, p in enumerate(run.get("predictions", []), start=2):
        ws_pred.append([
            p.get("date"), p.get("value"), p.get("lower_80"), p.get("upper_80"), p.get("lower_95"), p.get("upper_95")
        ])
        for c_idx in range(1, 7):
            cell = ws_pred.cell(row=r_idx, column=c_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            if r_idx % 2 == 1:
                cell.fill = ZEBRA_FILL
    _autofit_columns(ws_pred)

    # Sheet 3: Candidate Models Evaluation
    candidates = run.get("candidate_models", [])
    if candidates:
        ws_cand = wb.create_sheet(title="Candidate_Models")
        ws_cand.views.sheetView[0].showGridLines = True
        c_headers = ["Model Name", "Description", "WAPE (%)", "RMSE", "MAE", "MASE", "R²", "Status"]
        ws_cand.append(c_headers)
        for cell in ws_cand[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT
        for r_idx, c in enumerate(candidates, start=2):
            cm_m = c.get("metrics", {})
            ws_cand.append([
                c.get("name"), c.get("description"), cm_m.get("wape"), cm_m.get("rmse"),
                cm_m.get("mae"), cm_m.get("mase"), cm_m.get("r2"), c.get("status")
            ])
            for c_idx in range(1, 9):
                cell = ws_cand.cell(row=r_idx, column=c_idx)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if r_idx % 2 == 1:
                    cell.fill = ZEBRA_FILL
        _autofit_columns(ws_cand)

    # Sheet 4: Scenarios
    scenarios = run.get("scenarios", {})
    if scenarios:
        ws_scen = wb.create_sheet(title="Scenarios")
        ws_scen.views.sheetView[0].showGridLines = True
        s_headers = ["Scenario Name", "Description", "Total Projected Sum", "Delta vs Baseline", "Delta %"]
        ws_scen.append(s_headers)
        for cell in ws_scen[1]:
            cell.fill = DARK_FILL
            cell.font = HEADER_FONT
        for r_idx, (s_name, s_data) in enumerate(scenarios.items(), start=2):
            ws_scen.append([
                s_name.capitalize(), s_data.get("description"), s_data.get("total"),
                s_data.get("delta_vs_baseline"), s_data.get("delta_pct_vs_baseline")
            ])
            for c_idx in range(1, 6):
                cell = ws_scen.cell(row=r_idx, column=c_idx)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if r_idx % 2 == 1:
                    cell.fill = ZEBRA_FILL
        _autofit_columns(ws_scen)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_forecast_report_pdf(run: Dict[str, Any], dataset_name: str = "Dataset") -> bytes:
    """Generates an executive PDF forecasting report using ReportLab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ForecastTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ForecastSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "ForecastH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ForecastBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    table_cell_style = ParagraphStyle(
        "FTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
    )
    table_header_style = ParagraphStyle(
        "FTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
    )

    story: List[Any] = []
    m = run.get("metrics", {})
    insights = run.get("insights", {})

    story.append(Paragraph(f"Executive Predictive Forecast: {run.get('target_column')} ({dataset_name})", title_style))
    story.append(Paragraph(
        f"Generated by Analyticx AI Forecasting Lab · Champion Model: {run.get('model_type')} · "
        f"Horizon: {run.get('horizon')} periods ({run.get('frequency')}) · WAPE: {m.get('wape')}%",
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    # Executive Narrative Card
    if insights.get("executive_summary"):
        narrative_p = Paragraph(f"<b>Executive Synthesis:</b> {insights.get('executive_summary')}", body_style)
        narrative_table = Table([[narrative_p]], colWidths=[470], hAlign="CENTER")
        narrative_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(narrative_table)
        story.append(Spacer(1, 12))

    # KPI Summary Cards
    kpi_data = [
        [
            Paragraph(f"<b>Target Metric</b><br/>{run.get('target_column')}", body_style),
            Paragraph(f"<b>Champion Model</b><br/>{run.get('model_type')}", body_style),
            Paragraph(f"<b>Holdout WAPE</b><br/>{m.get('wape')}%", body_style),
            Paragraph(f"<b>Holdout RMSE</b><br/>{m.get('rmse')}", body_style),
            Paragraph(f"<b>Holdout R²</b><br/>{m.get('r2')}", body_style),
            Paragraph(f"<b>WAPE vs Naive</b><br/>+{m.get('wape_improvement_vs_naive_pct')}%", body_style),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[80, 80, 80, 75, 75, 80], hAlign="CENTER")
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Forecast Points Table
    story.append(Paragraph("1. Forward Projections & Expanding Uncertainty Bounds", h2_style))
    p_headers = ["Forecast Date", "Projected Value", "Lower 80% CI", "Upper 80% CI", "Lower 95% CI", "Upper 95% CI"]
    p_rows = [[Paragraph(h, table_header_style) for h in p_headers]]
    for p in run.get("predictions", []):
        p_rows.append([
            Paragraph(str(p.get("date")), table_cell_style),
            Paragraph(f"{p.get('value', 0):,.2f}", table_cell_style),
            Paragraph(f"{p.get('lower_80', 0):,.2f}", table_cell_style),
            Paragraph(f"{p.get('upper_80', 0):,.2f}", table_cell_style),
            Paragraph(f"{p.get('lower_95', 0):,.2f}", table_cell_style),
            Paragraph(f"{p.get('upper_95', 0):,.2f}", table_cell_style),
        ])
    t_pred = Table(p_rows, colWidths=[80, 80, 75, 75, 80, 80], hAlign="CENTER")
    t_pred.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_pred)
    story.append(Spacer(1, 14))

    # Candidate Models Evaluation Table
    candidates = run.get("candidate_models", [])
    if candidates:
        story.append(Paragraph("2. Candidate Models Holdout Backtest Comparison", h2_style))
        c_headers = ["Candidate Model", "WAPE (%)", "RMSE", "MAE", "MASE", "R² Score", "Evaluation Status"]
        c_rows = [[Paragraph(h, table_header_style) for h in c_headers]]
        for c in candidates:
            cm_m = c.get("metrics", {})
            c_rows.append([
                Paragraph(c.get("name", "Model"), table_cell_style),
                Paragraph(f"{cm_m.get('wape')}%", table_cell_style),
                Paragraph(str(cm_m.get("rmse")), table_cell_style),
                Paragraph(str(cm_m.get("mae")), table_cell_style),
                Paragraph(str(cm_m.get("mase")), table_cell_style),
                Paragraph(str(cm_m.get("r2")), table_cell_style),
                Paragraph(str(c.get("status")), table_cell_style),
            ])
        t_cand = Table(c_rows, colWidths=[120, 60, 60, 60, 55, 55, 60], hAlign="CENTER")
        t_cand.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cand)
        story.append(Spacer(1, 14))

    # Scenarios Table
    scenarios = run.get("scenarios", {})
    if scenarios:
        story.append(Paragraph("3. Business Scenarios & What-If Simulation Projections", h2_style))
        s_headers = ["Scenario", "Projected Total", "Delta vs Baseline", "Percentage Impact"]
        s_rows = [[Paragraph(h, table_header_style) for h in s_headers]]
        for s_name, s_data in scenarios.items():
            s_rows.append([
                Paragraph(s_name.capitalize(), table_cell_style),
                Paragraph(f"{s_data.get('total', 0):,.2f}", table_cell_style),
                Paragraph(f"{s_data.get('delta_vs_baseline', 0):+,.2f}", table_cell_style),
                Paragraph(f"{s_data.get('delta_pct_vs_baseline', 0):+.2f}%", table_cell_style),
            ])
        t_scen = Table(s_rows, colWidths=[120, 115, 115, 120], hAlign="CENTER")
        t_scen.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_scen)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# ==============================================================================
# 3. PROJECT INSIGHTS EXPORTERS (XLSX, PDF, CSV)
# ==============================================================================

def export_insights_report_xlsx(insights_data: Dict[str, Any]) -> bytes:
    """Exports Project Insights (Executive Summary, Quality, Insights Table) to Excel."""
    wb = openpyxl.Workbook()
    dataset_name = insights_data.get("dataset_name", "Dataset")

    # Sheet 1: Executive Summary
    ws = wb.active
    ws.title = "Executive_Summary"
    ws.views.sheetView[0].showGridLines = True
    ws["A1"] = f"Analyticx AI — Project Insights: {dataset_name}"
    ws["A1"].font = TITLE_FONT

    ex = insights_data.get("executive_summary", {})
    ws["A3"] = "Project Overview & Business Scope"
    ws["A3"].font = HEADER_FONT
    ws["A3"].fill = DARK_FILL
    ws["A4"] = ex.get("project_overview", "N/A")
    ws["A4"].font = NORMAL_FONT

    ws["A6"] = "Key Metrics"
    ws["A6"].font = HEADER_FONT
    ws["A6"].fill = DARK_FILL
    ws["B6"] = "Value"
    ws["B6"].font = HEADER_FONT
    ws["B6"].fill = DARK_FILL
    r_idx = 7
    for km in ex.get("key_metrics", []):
        ws.append([km.get("label"), km.get("value")])
        ws[f"A{r_idx}"].font = BOLD_FONT
        ws[f"B{r_idx}"].font = NORMAL_FONT
        ws[f"A{r_idx}"].border = THIN_BORDER
        ws[f"B{r_idx}"].border = THIN_BORDER
        r_idx += 1
    _autofit_columns(ws)

    # Sheet 2: Discovered Insights Table
    ws_ins = wb.create_sheet(title="Discovered_Insights")
    ws_ins.views.sheetView[0].showGridLines = True
    i_headers = ["Category", "Priority", "Title", "Explanation", "Confidence", "Methodology", "Calculation Formula", "Recommended Action", "Status"]
    ws_ins.append(i_headers)
    for cell in ws_ins[1]:
        cell.fill = DARK_FILL
        cell.font = HEADER_FONT

    for r_idx, ins in enumerate(insights_data.get("insights", []), start=2):
        sm = ins.get("supporting_metrics") or {}
        ws_ins.append([
            ins.get("category"),
            ins.get("priority"),
            ins.get("title"),
            ins.get("explanation"),
            f"{int(ins.get('confidence_score', 0) * 100)}%",
            ins.get("methodology"),
            sm.get("calculation_formula", ""),
            ins.get("recommended_action", ""),
            ins.get("status", "new"),
        ])
        for c_idx in range(1, len(i_headers) + 1):
            cell = ws_ins.cell(row=r_idx, column=c_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            if r_idx % 2 == 1:
                cell.fill = ZEBRA_FILL
    _autofit_columns(ws_ins)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_insights_report_pdf(insights_data: Dict[str, Any]) -> bytes:
    """Exports Project Insights to a clean executive PDF report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "InsightTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"), spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "InsightSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#64748b"), spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "InsightH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#0f172a"), spaceBefore=12, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "InsightBody", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"),
    )
    table_cell_style = ParagraphStyle(
        "ITableCell", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1e293b"),
    )
    table_header_style = ParagraphStyle(
        "ITableHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=colors.white,
    )

    story: List[Any] = []
    dataset_name = insights_data.get("dataset_name", "Dataset")
    ex = insights_data.get("executive_summary", {})

    story.append(Paragraph(f"Executive Project Intelligence: {dataset_name}", title_style))
    story.append(Paragraph(
        f"Generated by Analyticx AI · Quality Score: {insights_data.get('quality_score', 100)}% · "
        f"Verified Findings: {len(insights_data.get('insights', []))}",
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    if ex.get("project_overview"):
        ov_p = Paragraph(f"<b>Business Scope:</b> {ex.get('project_overview')}", body_style)
        ov_table = Table([[ov_p]], colWidths=[470], hAlign="CENTER")
        ov_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(ov_table)
        story.append(Spacer(1, 12))

    story.append(Paragraph("1. Discovered Empirical Findings & Statistical Evidence", h2_style))
    headers = ["Category", "Priority", "Title", "Confidence", "Methodology"]
    rows = [[Paragraph(h, table_header_style) for h in headers]]
    for ins in insights_data.get("insights", [])[:14]:
        cat_str = str(ins.get("category") or "General")[:12]
        prio_str = str(ins.get("priority") or "medium")[:10]
        title_str = str(ins.get("title") or "Insight")[:32]
        conf_val = float(ins.get("confidence_score") or 0.0)
        conf_str = f"{int(conf_val * 100)}%"
        meth_str = str(ins.get("methodology") or "Deterministic")[:22]
        rows.append([
            Paragraph(cat_str, table_cell_style),
            Paragraph(prio_str, table_cell_style),
            Paragraph(title_str, table_cell_style),
            Paragraph(conf_str, table_cell_style),
            Paragraph(meth_str, table_cell_style),
        ])
    t_ins = Table(rows, colWidths=[70, 55, 175, 60, 110], hAlign="CENTER")
    t_ins.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_ins)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# ==============================================================================
# 4. DASHBOARD & DATA CLEANING EXPORTERS
# ==============================================================================

def export_dashboard_xlsx(dashboard_data: Dict[str, Any]) -> bytes:
    """Exports all widget data tables from a dashboard to a multi-sheet Excel file."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dashboard_Overview"
    ws.views.sheetView[0].showGridLines = True

    dash_title = dashboard_data.get("title", "Dashboard")
    ws["A1"] = f"Analyticx AI Dashboard Export: {dash_title}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = f"Exported: {datetime.utcnow().isoformat()} | Dataset ID: {dashboard_data.get('dataset_id')}"
    ws["A2"].font = Font(name="Calibri", size=9, italic=True, color="64748B")

    widgets = dashboard_data.get("widgets", [])
    ws.append([])
    ws.append(["Widget ID", "Title", "Chart Type", "X Dimension", "Y Metric", "Rows Count"])
    for cell in ws[4]:
        cell.fill = DARK_FILL
        cell.font = HEADER_FONT

    for r_idx, w in enumerate(widgets, start=5):
        cfg = w.get("config", {})
        data_rows = w.get("data", []) or []
        ws.append([
            w.get("id"), w.get("title"), w.get("chart_type"),
            cfg.get("x_col", cfg.get("x", "")), cfg.get("y_col", cfg.get("y", "")), len(data_rows)
        ])
        for c_idx in range(1, 7):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
    _autofit_columns(ws)

    # Sheets for individual widget data
    for idx, w in enumerate(widgets[:10], start=1):
        data_rows = w.get("data", [])
        if data_rows and isinstance(data_rows, list) and isinstance(data_rows[0], dict):
            sheet_name = f"Widget_{w.get('id', idx)}"[:31]
            ws_w = wb.create_sheet(title=sheet_name)
            ws_w.views.sheetView[0].showGridLines = True
            headers = list(data_rows[0].keys())
            ws_w.append(headers)
            for cell in ws_w[1]:
                cell.fill = DARK_FILL
                cell.font = HEADER_FONT
            for row_idx, r in enumerate(data_rows[:1000], start=2):
                ws_w.append([r.get(h) for h in headers])
                for col_idx in range(1, len(headers) + 1):
                    cell = ws_w.cell(row=row_idx, column=col_idx)
                    cell.font = NORMAL_FONT
                    cell.border = THIN_BORDER
                    if row_idx % 2 == 1:
                        cell.fill = ZEBRA_FILL
            _autofit_columns(ws_w)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ==============================================================================
# 5. ZIP PROJECT PACKAGE ARCHIVE BUILDER
# ==============================================================================

def build_zip_package(files_dict: Dict[str, bytes], manifest: Dict[str, Any], readme_text: str) -> bytes:
    """Packages generated files, manifest.json, and README.txt into a zip archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", readme_text)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for filename, data in files_dict.items():
            zf.writestr(filename, data)
    return buf.getvalue()
