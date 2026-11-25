import csv
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Tuple

import pandas as pd
from fastapi import UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf"}
_DATAFRAME_CACHE: "OrderedDict[str, tuple[int, pd.DataFrame]]" = OrderedDict()
_UNDERSTANDING_CACHE: "OrderedDict[str, tuple[int, dict]]" = OrderedDict()
_MAX_CACHED_DATASETS = 6


def safe_extension(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}. Allowed: CSV, XLSX, XLS, PDF")
    return ext


def safe_stored_name(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


async def save_upload(file: UploadFile) -> Tuple[Path, int]:
    ext = safe_extension(file.filename or "")
    contents = await file.read()

    size = len(contents)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    if size == 0:
        raise ValueError("Uploaded file is empty (0 bytes).")
    if size > max_bytes:
        raise ValueError(f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_path = upload_dir / safe_stored_name(ext)
    stored_path.write_bytes(contents)

    return stored_path, size


def _read_csv_resilient(path: Path) -> pd.DataFrame:
    """Reads CSV with encoding fallbacks, delimiter sniffing, and header disambiguation."""
    if path.stat().st_size == 0:
        raise ValueError("CSV file is empty (0 bytes).")

    raw_bytes = path.read_bytes()
    text_sample = ""
    chosen_encoding = "utf-8"
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            text_sample = raw_bytes[:8192].decode(enc)
            chosen_encoding = enc
            break
        except UnicodeDecodeError:
            continue
    else:
        text_sample = raw_bytes[:8192].decode("latin1", errors="replace")
        chosen_encoding = "latin1"

    if not text_sample.strip():
        raise ValueError("CSV file contains only whitespace and no tabular records.")

    sep = None
    try:
        dialect = csv.Sniffer().sniff(text_sample, delimiters=",;\t|")
        sep = dialect.delimiter
    except csv.Error:
        sep = ","

    try:
        df = pd.read_csv(path, encoding=chosen_encoding, sep=sep, on_bad_lines="warn")
    except Exception:
        df = pd.read_csv(path, encoding=chosen_encoding, sep=None, engine="python", on_bad_lines="skip")

    if df.shape[1] == 0:
        raise ValueError("CSV file contains no readable columns.")
    return df


def _read_excel_resilient(path: Path) -> pd.DataFrame:
    """Reads first usable non-empty Excel sheet, skipping blank leading banner rows if needed."""
    if path.stat().st_size == 0:
        raise ValueError("Excel file is empty (0 bytes).")

    excel_file = pd.ExcelFile(path)
    selected_df = None
    for sheet_name in excel_file.sheet_names:
        candidate = excel_file.parse(sheet_name)
        if not candidate.empty and candidate.shape[1] > 0:
            selected_df = candidate
            break

    if selected_df is None or selected_df.empty:
        raise ValueError("Excel workbook contains no usable data rows across its sheets.")

    # Handle spreadsheets that have a leading title banner row where most columns are Unnamed
    unnamed_ratio = sum(1 for c in selected_df.columns if str(c).startswith("Unnamed:")) / max(1, len(selected_df.columns))
    if unnamed_ratio > 0.6 and len(selected_df) >= 2:
        for idx in range(min(5, len(selected_df))):
            row_vals = selected_df.iloc[idx].dropna()
            if len(row_vals) >= max(2, int(selected_df.shape[1] * 0.5)):
                new_headers = [str(v).strip() if pd.notna(v) else f"Column_{i+1}" for i, v in enumerate(selected_df.iloc[idx])]
                promoted = selected_df.iloc[idx + 1:].copy().reset_index(drop=True)
                promoted.columns = new_headers
                if not promoted.empty:
                    selected_df = promoted
                break

    return selected_df


def load_dataframe_from_path(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()

    if ext == ".csv":
        return _read_csv_resilient(path)

    if ext in {".xlsx", ".xls"}:
        return _read_excel_resilient(path)

    if ext == ".pdf":
        from app.services.pdf_service import extract_tables_from_pdf
        tables = extract_tables_from_pdf(path)
        if tables:
            first_table = tables[0]
            df = pd.DataFrame(first_table["all_rows"], columns=first_table["columns"])
            for c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="ignore")
            return df
        else:
            # Fallback to text lines extraction
            import pdfplumber
            lines = []
            with pdfplumber.open(path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    for line in text.split("\n"):
                        if line.strip():
                            lines.append({"page": idx + 1, "content": line.strip()})
            if lines:
                return pd.DataFrame(lines)
            return pd.DataFrame({"page": [1], "content": ["Empty PDF or scanned document without extractable text"]})

    raise ValueError(f"Unsupported file type: {ext}")


def load_dataset_df(dataset) -> pd.DataFrame:
    path = Path(dataset.stored_path)
    key = str(path.resolve())
    mtime_ns = path.stat().st_mtime_ns if path.exists() else 0
    cached = _DATAFRAME_CACHE.get(key)
    if cached and cached[0] == mtime_ns:
        _DATAFRAME_CACHE.move_to_end(key)
        return cached[1]
    df = load_dataframe_from_path(path)
    _DATAFRAME_CACHE[key] = (mtime_ns, df)
    _DATAFRAME_CACHE.move_to_end(key)
    while len(_DATAFRAME_CACHE) > _MAX_CACHED_DATASETS:
        _DATAFRAME_CACHE.popitem(last=False)
    return df


def get_dataset_understanding(dataset, df: pd.DataFrame | None = None) -> dict:
    """Returns shared cached profiling, validation, and safely normalized DataFrame for dataset version."""
    from app.analytics.data_understanding import understand_dataset

    path = Path(dataset.stored_path) if getattr(dataset, "stored_path", None) else Path(f"mem_{getattr(dataset, 'id', 0)}")
    mtime_ns = path.stat().st_mtime_ns if path.exists() else 0
    version = getattr(dataset, "version", 1)
    cache_key = f"{getattr(dataset, 'id', 0)}_v{version}_{str(path.resolve())}"

    if df is None:
        cached = _UNDERSTANDING_CACHE.get(cache_key)
        if cached and cached[0] == mtime_ns:
            _UNDERSTANDING_CACHE.move_to_end(cache_key)
            return cached[1]
        df = load_dataset_df(dataset)

    result = understand_dataset(df, dataset_name=getattr(dataset, "name", "Dataset"))
    _UNDERSTANDING_CACHE[cache_key] = (mtime_ns, result)
    _UNDERSTANDING_CACHE.move_to_end(cache_key)
    while len(_UNDERSTANDING_CACHE) > _MAX_CACHED_DATASETS:
        _UNDERSTANDING_CACHE.popitem(last=False)
    return result


def invalidate_dataset_cache(stored_path: str) -> None:
    """Remove a deleted/replaced upload from the in-process data and understanding caches."""
    resolved = str(Path(stored_path).resolve())
    _DATAFRAME_CACHE.pop(resolved, None)
    stale_keys = [k for k in _UNDERSTANDING_CACHE if k.endswith(f"_{resolved}")]
    for k in stale_keys:
        _UNDERSTANDING_CACHE.pop(k, None)
