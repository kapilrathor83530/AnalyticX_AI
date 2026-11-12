# Analyticx AI

**Analyticx AI — Agentic Business Analytics and Decision Intelligence Platform**

## AI-Guided Data Preparation & Automated EDA Studio

This platform includes a complete, end-to-end **AI-Guided Data Preparation & Automated EDA Studio** that transforms raw datasets into clean, validated, analysis-ready datasets with evidence-based insights.

### Key Capabilities

1. **Multi-Format Upload Center:**
   - Drag-and-drop support for **CSV, Excel (.xlsx, .xls)** and **PDF documents** (automatic table & text extraction via `pdfplumber`).
   - Immediate persistent storage in local backend and SQLite database.
   - Live status tracking: `Uploaded`, `Inspecting`, `Awaiting User Input`, `Cleaning`, `Validating`, `Analysis Ready`, `Needs Attention`.

2. **Automated Data Quality Profiling & Scoring:**
   - **Quality Score (0-100%):** Multi-factor health index penalized for missing values, duplicates, outliers, and zero-variance columns.
   - Comprehensive detection of missing cells, duplicate rows, and statistical outliers (1.5× IQR fences & Z-score > 3).
   - Detection of inconsistent text whitespace, mixed casing, and candidate identifier columns.

3. **Data Quality & Cleaning Decisions Center:**
   - Actionable recommendation cards with issue severity badges (High, Medium, Low).
   - **Guided Mode:** Users can review issues, select statistical resolution strategies (e.g., Median vs Mean, Mode vs Unknown, Custom Constant, Winsorize/Cap, Flag, Drop), and apply or skip them.
   - **Auto-Clean All Mode:** One-click safe automated cleaning applying recommended policies with before-and-after comparison.
   - Full reversibility with **Undo Last Action** and transformation history audit logging.

4. **Automated EDA & Evidence-Grounded Line-by-Line Insights:**
   - Interactive Plotly numerical histograms and categorical frequency bar charts.
   - Pairwise correlation heatmap with top association indicators (with explicit correlation != causation warnings).
   - Time series trend trajectories when chronological date fields are present.
   - Structured analytical report:
     - 1. Dataset Summary & Scope
     - 2. Column-Level Statistical Findings
     - 3. Relationships & Correlations
     - 4. Anomalies & Extreme Observations
     - 5. Core Business & Segment Insights
     - 6. Recommended Next Steps & Explorations
     - 7. Data Dictionary & Field Catalog

5. **Persistent AI Data Analyst Chat:**
   - Persistent assistant docked beside the workspace with active dataset & column context.
   - Explains statistical concepts (e.g., why median is preferred for skewed data).
   - Understands and executes natural-language cleaning commands (e.g., *"remove duplicates"*, *"replace missing salary with median"*, *"cap outliers in revenue"*, *"auto clean this dataset"*).
   - Integrates with local open-weight LLMs (Ollama) with deterministic fallback.

6. **Export & Download Center:**
   - Cleaned CSV export.
   - Cleaned Excel (.xlsx) workbook export.
   - JSON transformation audit log export.

---

## Windows Setup & Execution

### 1. Backend

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

- Backend API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Frontend

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

- Web App: [http://localhost:5173](http://localhost:5173)
- Upload Center: [http://localhost:5173/workspace](http://localhost:5173/workspace)
- AI Prep Studio: [http://localhost:5173/data-prep/:id](http://localhost:5173/data-prep/:id)

### 3. Tests

```powershell
# Backend Pytest
cd backend
pytest -v

# Frontend Vitest
cd frontend
npm test
```
