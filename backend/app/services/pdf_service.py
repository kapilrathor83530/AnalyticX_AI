"""PDF Document Inspection and Table Extraction Service for Analyticx AI."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid
import pandas as pd
import pdfplumber

from app.core.config import settings


def extract_tables_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts structured tables from a PDF file.
    Returns list of table candidates with headers, sample rows, and row counts.
    """
    extracted_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue
                # Clean headers
                raw_headers = table[0]
                headers = [str(h).strip() if h is not None and str(h).strip() else f"Column_{i+1}" for i, h in enumerate(raw_headers)]
                # Ensure unique headers
                seen = set()
                unique_headers = []
                for h in headers:
                    col_name = h
                    count = 1
                    while col_name in seen:
                        col_name = f"{h}_{count}"
                        count += 1
                    seen.add(col_name)
                    unique_headers.append(col_name)

                # Clean rows
                rows = []
                for r in table[1:]:
                    if any(cell is not None and str(cell).strip() for cell in r):
                        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in r[:len(unique_headers)]]
                        # Pad if shorter
                        while len(cleaned_row) < len(unique_headers):
                            cleaned_row.append("")
                        rows.append(cleaned_row)

                if len(rows) > 0:
                    extracted_tables.append({
                        "table_id": f"p{page_idx+1}_t{t_idx+1}",
                        "page_number": page_idx + 1,
                        "columns": unique_headers,
                        "row_count": len(rows),
                        "preview_rows": rows[:5],
                        "all_rows": rows,
                    })

    return extracted_tables


def save_pdf_table_as_dataset(table_info: Dict[str, Any], original_pdf_name: str) -> Tuple[Path, int, pd.DataFrame]:
    """
    Converts extracted table into a CSV file and saves in upload storage.
    """
    columns = table_info["columns"]
    rows = table_info["all_rows"]
    df = pd.DataFrame(rows, columns=columns)

    # Attempt to convert numeric columns
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="ignore")
        df[col] = converted

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    csv_name = f"{uuid.uuid4().hex}_extracted.csv"
    stored_path = upload_dir / csv_name
    df.to_csv(stored_path, index=False)
    size_bytes = stored_path.stat().st_size

    return stored_path, size_bytes, df
