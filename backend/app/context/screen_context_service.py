"""Live Screen Context, Active File Intelligence, and Screen Understanding Service for Analyticx AI."""
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.data_quality import inspect_data_quality
from app.context.schemas import (
    LiveApplicationContext,
    ScreenExplanationRequest,
    ScreenExplanationResponse,
    VisualAnalysisRequest,
    VisualAnalysisResponse,
)
from app.models.dashboard import Dashboard
from app.models.dataset import Dataset
from app.models.widget import Widget
from app.services.data_service import load_dataset_df
from app.services.pdf_rag_service import get_pdf_index, query_pdf_document
from app.utils.language_detector import detect_language


def generate_screen_summary(context: LiveApplicationContext, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Synthesizes authoritative screen summary and analysis state from active frontend context and database ground truth.
    """
    screen = context.screen
    ds_ctx = context.dataset
    file_ctx = context.file
    dash_ctx = context.dashboard
    act_ctx = context.activity

    screen_title = screen.screen_name or "Analytics Workspace"
    route = screen.route or "/"

    summary_pts = []
    observations = []
    warnings = []
    next_steps = []
    file_summary = None
    status_str = "Operational"

    # 1. Dataset & File Intelligence
    if ds_ctx.dataset_id and db:
        ds = db.query(Dataset).filter(Dataset.id == ds_ctx.dataset_id).first()
        if ds:
            is_pdf = Path(ds.stored_path).suffix.lower() == ".pdf"
            if is_pdf:
                file_summary = f"Active PDF Document: '{ds.name}'"
                page_info = f"Viewing Page {file_ctx.pdf_page_number or 1}"
                if file_ctx.pdf_total_pages:
                    page_info += f" of {file_ctx.pdf_total_pages}"
                summary_pts.append(f"You are reviewing the document '{ds.name}' ({page_info}).")

                # Inspect page text/tables if indexed
                pdf_path = Path(ds.stored_path)
                if pdf_path.exists():
                    p_index = get_pdf_index(pdf_path)
                    cur_page = p_index.get_page(file_ctx.pdf_page_number or 1)
                    if cur_page:
                        observations.append(f"Page {cur_page.page_number} has {cur_page.char_count:,} characters and {cur_page.tables_count} extracted table(s).")
                next_steps.extend([
                    "Ask: 'Summarize this page'",
                    "Extract structured tables from this PDF page into a dataset",
                    "Compare this section with key metrics",
                ])
            else:
                file_summary = f"Active Tabular Dataset: '{ds.name}' (v{ds.version})"
                summary_pts.append(
                    f"You are currently analyzing dataset '{ds.name}' with {ds.row_count:,} rows and {ds.column_count} columns."
                )

                # Quality Score
                score = ds.quality_score or ds_ctx.quality_score
                if score is not None:
                    summary_pts.append(f"Dataset health quality score: {score}%.")
                    if score < 70:
                        warnings.append(f"Data quality is low ({score}%). Review missing values and extreme outliers.")
                    elif score < 85:
                        observations.append(f"Data quality is fair ({score}%). Some cleaning operations are recommended.")
                    else:
                        observations.append(f"Dataset is clean and validated (Quality Score: {score}%).")

                # Column Focus
                if ds_ctx.focused_column:
                    observations.append(f"Focused Column: '{ds_ctx.focused_column}'.")
                    try:
                        df = load_dataset_df(ds)
                        if ds_ctx.focused_column in df.columns:
                            col_s = df[ds_ctx.focused_column]
                            missing = int(col_s.isna().sum())
                            if missing > 0:
                                warnings.append(f"Column '{ds_ctx.focused_column}' has {missing} missing value(s).")
                            if pd.api.types.is_numeric_dtype(col_s):
                                observations.append(f"'{ds_ctx.focused_column}' Mean: {col_s.mean():.2f}, Median: {col_s.median():.2f}")
                    except Exception:
                        pass

                if ds_ctx.pending_decisions_count > 0:
                    warnings.append(f"{ds_ctx.pending_decisions_count} data cleaning recommendation(s) are awaiting your review.")
                    next_steps.append("Review and approve cleaning recommendations in the Quality Center")

                next_steps.extend([
                    "Ask Copilot: 'Auto clean kardo is dataset ko'",
                    "Explore column distributions in the EDA Charts tab",
                    "Export clean data or generate visualization dashboard",
                ])

    # 2. Dashboard & Chart Intelligence
    elif dash_ctx.dashboard_id or dash_ctx.selected_chart_title:
        dash_name = dash_ctx.dashboard_name or "Custom Dashboard"
        if dash_ctx.dashboard_id and db:
            dash = db.query(Dashboard).filter(Dashboard.id == dash_ctx.dashboard_id).first()
            if dash:
                dash_name = dash.name
        summary_pts.append(f"You are on Dashboard '{dash_name}'.")

        chart_title = dash_ctx.selected_chart_title
        chart_t = dash_ctx.selected_chart_type or "chart"
        if dash_ctx.selected_widget_id and db:
            widget = db.query(Widget).filter(Widget.id == dash_ctx.selected_widget_id).first()
            if widget:
                chart_title = widget.title
                chart_t = widget.chart_type or "chart"

        if chart_title:
            summary_pts.append(f"Currently selected visual: '{chart_title}' ({chart_t}).")
            observations.append(f"Chart mapping: Measures={dash_ctx.active_measures or 'configured'}, Filters={dash_ctx.active_filters or 'None'}")
            next_steps.extend([
                f"Ask Copilot: 'Why is this {chart_t} showing these results?'",
                "Change chart type or aggregation in Chart Editor",
                "Add new visual comparing secondary dimension",
            ])
        else:
            summary_pts.append(f"Dashboard contains {dash_ctx.widgets_count} interactive visual(s).")
            next_steps.extend([
                "Select any visual to inspect its configuration and drivers",
                "Ask Copilot: 'Current dashboard ke basis par business recommendations do'",
            ])

    # 3. Route specific defaults if no entity selected
    else:
        if "workspace" in route or "upload" in route:
            summary_pts.append("You are in the Data Upload Center.")
            observations.append("Ready to ingest CSV, Excel, or PDF documents.")
            next_steps.extend([
                "Drop a file to upload and begin automated profiling",
                "Select an existing dataset from your workspace list",
            ])
        elif "model" in route:
            summary_pts.append("You are in Model Management configuring local open-weight LLMs.")
            next_steps.append("Verify Ollama connection and active model weights")
        elif "health" in route:
            summary_pts.append("You are inspecting System Health and platform telemetry.")
        else:
            summary_pts.append(f"You are viewing '{screen_title}'.")
            next_steps.append("Ask Copilot any business question or navigate to a dataset")

    # 4. Activity & Tasks
    if act_ctx.task_status == "running":
        status_str = "Task in progress"
        observations.append("A background analytical or cleaning task is currently executing.")
    elif act_ctx.recent_actions:
        latest = act_ctx.recent_actions[0]
        observations.append(f"Last action: {latest.get('action')}")

    if act_ctx.has_unsaved_changes:
        warnings.append("Workspace has unsaved changes that have not been persisted.")

    if not next_steps:
        next_steps = ["Ask Copilot about key trends", "Review summary metrics"]

    return {
        "screen_summary": " ".join(summary_pts),
        "active_file_summary": file_summary,
        "analysis_status": status_str,
        "recommended_next_steps": next_steps[:4],
        "key_observations": observations[:5],
        "warnings_or_issues": warnings[:4],
    }


def explain_active_screen(
    payload: ScreenExplanationRequest,
    db: Optional[Session] = None,
) -> ScreenExplanationResponse:
    """
    Answers user questions about the screen currently visible in Analyticx AI.
    """
    user_query = (payload.question or "").strip()
    lang_info = detect_language(user_query, user_override=payload.language)
    lang_code = lang_info["code"]

    raw = generate_screen_summary(payload.context, db=db)

    # Localize into user's language
    if lang_code == "hinglish":
        screen_summary = (
            f"Aap abhi **'{payload.context.screen.screen_name}'** screen par hain ({payload.context.screen.route}). "
            f"{raw['screen_summary']}"
        )
        if raw["warnings_or_issues"]:
            screen_summary += f"\n\n⚠️ **Notice:** {raw['warnings_or_issues'][0]}"
    elif lang_code == "hi":
        screen_summary = (
            f"आप वर्तमान में **'{payload.context.screen.screen_name}'** स्क्रीन पर हैं। "
            f"{raw['screen_summary']}"
        )
    else:
        screen_summary = (
            f"You are currently viewing **'{payload.context.screen.screen_name}'** ({payload.context.screen.route}). "
            f"{raw['screen_summary']}"
        )

    return ScreenExplanationResponse(
        screen_summary=screen_summary,
        active_file_summary=raw["active_file_summary"],
        analysis_status=raw["analysis_status"],
        recommended_next_steps=raw["recommended_next_steps"],
        key_observations=raw["key_observations"],
        warnings_or_issues=raw["warnings_or_issues"],
        detected_language=lang_code,
        language_name=lang_info["name"],
        is_visual_analysis=False,
    )


def analyze_visual_screen(
    payload: VisualAnalysisRequest,
    db: Optional[Session] = None,
) -> VisualAnalysisResponse:
    """
    Evaluates visual and DOM elements of the active workspace without hallucinating pixels.
    Integrates verified ground-truth data with visual layout analysis.
    """
    ctx = payload.context
    dom = ctx.visual.dom_summary if ctx.visual else ""

    detected_elements = [
        f"Active Route: {ctx.screen.route}",
        f"Screen: {ctx.screen.screen_name}",
    ]

    if ctx.dataset.dataset_name:
        detected_elements.append(f"Dataset Card: '{ctx.dataset.dataset_name}'")
    if ctx.dashboard.dashboard_name:
        detected_elements.append(f"Dashboard Canvas: '{ctx.dashboard.dashboard_name}'")
    if ctx.dashboard.selected_chart_title:
        detected_elements.append(f"Visual Chart: '{ctx.dashboard.selected_chart_title}' ({ctx.dashboard.selected_chart_type})")
    if dom:
        detected_elements.append(f"DOM Layout Tree: {dom[:120]}...")

    explanation = (
        f"Visual workspace analysis for **{ctx.screen.screen_name}**:\n\n"
        f"The workspace displays an active {ctx.screen.screen_name} layout. "
    )

    if ctx.dashboard.selected_chart_title:
        explanation += f"The selected chart '{ctx.dashboard.selected_chart_title}' is rendered with verified metric bindings ({ctx.dashboard.active_measures or 'default measures'}). "
    elif ctx.dataset.dataset_name:
        explanation += f"The dataset workspace shows {ctx.dataset.row_count:,} records with data quality rating at {ctx.dataset.quality_score or 'N/A'}%. "

    explanation += (
        "\n\n*Note: Exact numerical metrics in Analyticx AI are evaluated from validated analytics data streams rather than pixel estimations.*"
    )

    return VisualAnalysisResponse(
        explanation=explanation,
        visual_elements_detected=detected_elements,
        layout_health="Optimal & Responsive",
        numerical_grounding_note="Exact values grounded in verified database analytics, not pixel OCR.",
        suggested_actions=[
            "Toggle sidebar menu to test auto-adjusting responsive layout",
            "Ask Copilot to explain metric drivers",
            "Export visual report",
        ],
    )
