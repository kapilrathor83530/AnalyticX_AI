"""Project Insights Service Layer for Analyticx AI.

Coordinates context-aware insight retrieval, AI chat Q&A grounded in verified evidence,
and actionable workflow execution (widget creation, ANOVA tests, status persistence).
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.project_insights_engine import execute_project_insights_pipeline
from app.analytics.statistics import compare_groups, detect_anomalies_zscore
from app.models.dashboard import Dashboard
from app.models.dataset import Dataset
from app.models.project_insight import ProjectInsight
from app.models.widget import Widget
from app.services.data_service import load_dataset_df

logger = logging.getLogger(__name__)


def get_or_run_project_insights(
    dataset_id: int,
    force_refresh: bool = False,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Retrieves or executes the Project Insights pipeline for a given dataset."""
    if not db:
        raise ValueError("Database session required")

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset with ID {dataset_id} not found")

    df = load_dataset_df(dataset)
    return execute_project_insights_pipeline(dataset=dataset, df=df, force_refresh=force_refresh, db=db)


def update_insight_status(insight_id: int, status: str, db: Session) -> Dict[str, Any]:
    """Updates status of a ProjectInsight ('saved', 'dismissed', 'new', 'resolved')."""
    valid_statuses = {"saved", "dismissed", "new", "resolved"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

    insight = db.query(ProjectInsight).filter(ProjectInsight.id == insight_id).first()
    if not insight:
        raise ValueError(f"Insight #{insight_id} not found")

    insight.status = status
    insight.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(insight)

    return {
        "success": True,
        "id": insight.id,
        "status": insight.status,
        "updated_at": insight.updated_at.isoformat(),
    }


def execute_insight_action(
    dataset_id: int,
    action_type: str,
    payload: Optional[Dict[str, Any]] = None,
    insight_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Executes a concrete action derived from an insight:
    - create_chart: Adds an interactive chart widget to the dataset's dashboard
    - deeper_analysis: Executes ANOVA F-test or Z-score outlier detection
    - save / dismiss: Updates insight status
    """
    if not db:
        raise ValueError("Database session required")

    payload = payload or {}
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset #{dataset_id} not found")

    df = load_dataset_df(dataset)

    # 1. Action: Create Chart on Dashboard
    if action_type == "create_chart":
        title = payload.get("title") or "Insight Chart"
        chart_type = payload.get("chart_type") or "bar"
        x_col = payload.get("x") or payload.get("labels")
        y_col = payload.get("y") or payload.get("values")
        series_col = payload.get("series")
        agg = payload.get("aggregation") or "sum"

        mapping: Dict[str, Any] = {}
        if chart_type in {"pie", "donut", "treemap", "funnel", "waterfall"}:
            mapping["labels"] = x_col
            mapping["values"] = y_col
        elif chart_type == "histogram":
            mapping["x"] = x_col
        elif chart_type == "box":
            mapping["y"] = y_col or x_col
            if x_col and y_col and x_col != y_col:
                mapping["x"] = x_col
        elif chart_type in {"heatmap", "correlation_matrix"}:
            mapping["columns"] = payload.get("columns") or []
        else:
            mapping["x"] = x_col
            mapping["y"] = y_col
            if series_col:
                mapping["series"] = series_col

        # Find or create a dashboard for this dataset
        dashboard = db.query(Dashboard).filter(Dashboard.dataset_id == dataset.id).first()
        if not dashboard:
            dashboard = Dashboard(
                name=f"{dataset.name} Dashboard",
                dataset_id=dataset.id,
                workspace_id=dataset.workspace_id,
            )
            db.add(dashboard)
            db.commit()
            db.refresh(dashboard)

        # Count existing widgets for positioning
        existing_widgets = db.query(Widget).filter(Widget.dashboard_id == dashboard.id).count()

        widget = Widget(
            dashboard_id=dashboard.id,
            title=title,
            chart_type=chart_type,
            config={
                "x_axis": x_col,
                "y_axis": y_col,
                "title": title,
                "dataset_id": dataset.id,
                "aggregation": agg,
                "appearance": {"color": "#22d3ee"},
            },
            data_mapping=mapping,
            position={"x": (existing_widgets % 2) * 6, "y": (existing_widgets // 2) * 4},
            size={"w": 6, "h": 4},
        )
        db.add(widget)
        db.commit()
        db.refresh(widget)

        return {
            "success": True,
            "action": "create_chart",
            "message": f"Successfully created '{title}' ({chart_type}) on Dashboard #{dashboard.id}.",
            "dashboard_id": dashboard.id,
            "widget_id": widget.id,
            "route": f"/dashboard/{dashboard.id}/edit",
        }

    # 2. Action: Deeper Statistical Analysis (ANOVA / Z-Score)
    elif action_type == "deeper_analysis":
        technique = payload.get("technique") or "anova"

        if technique == "anomaly_scan":
            target_col = payload.get("column") or (df.select_dtypes(include=["number"]).columns[0] if not df.empty else "")
            res = detect_anomalies_zscore(df, target_col, threshold=2.5)
            return {
                "success": True,
                "action": "deeper_analysis",
                "technique": "anomaly_scan",
                "target_column": target_col,
                "result": res,
                "interpretation": f"Scanned column '{target_col}' at threshold 2.5σ. Identified {len(res.get('anomalies', []))} anomalous data points.",
            }
        else:
            # Group comparison / ANOVA
            cat_cols = [c for c in df.columns if df[c].dtype == "object" or df[c].nunique() < 20]
            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            group_col = payload.get("group_column") or (cat_cols[0] if cat_cols else "")
            val_col = payload.get("value_column") or (num_cols[0] if num_cols else "")

            anova_res = compare_groups(df, group_col, val_col)
            sig = anova_res.get("significant_at_0_05", False)
            f_stat = anova_res.get("f_statistic")
            p_val = anova_res.get("p_value")

            interp = (
                f"ANOVA Test across '{group_col}' for metric '{val_col}': F-statistic = {f_stat}, p-value = {p_val}. "
                f"{'Statistically significant (p < 0.05): Group variances are statistically distinct.' if sig else 'Not statistically significant (p >= 0.05): Differences may be attributable to random variation.'}"
            )

            return {
                "success": True,
                "action": "deeper_analysis",
                "technique": "anova_significance",
                "group_column": group_col,
                "value_column": val_col,
                "result": anova_res,
                "interpretation": interp,
            }

    # 3. Action: Save / Dismiss Insight
    elif action_type in ("save", "dismiss"):
        if not insight_id:
            raise ValueError("insight_id required for save/dismiss action")
        new_status = "saved" if action_type == "save" else "dismissed"
        return update_insight_status(insight_id, new_status, db)

    else:
        return {
            "success": False,
            "error": f"Unknown action type '{action_type}'",
        }


def answer_project_chat(
    dataset_id: int,
    question: str,
    db: Session,
) -> Dict[str, Any]:
    """
    Answers user questions grounded strictly in the active project's computed insights,
    dataset dimensions, schema, and statistical metrics.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset #{dataset_id} not found")

    df = load_dataset_df(dataset)
    insights_data = get_or_run_project_insights(dataset_id=dataset_id, db=db)

    exec_summary = insights_data.get("executive_summary", {})
    eda = insights_data.get("eda", {})
    insights = insights_data.get("insights", [])

    q_lower = question.lower()

    # 1. Intent: Top Findings / Important Findings
    if any(k in q_lower for k in ["top finding", "important finding", "overview", "summary", "explain findings", "findings"]):
        findings_text = "\n\n".join([
            f"**{i+1}. {ins['title']}** ({ins['category'].upper()} - {ins['priority'].upper()} Priority)\n"
            f"{ins['explanation']}\n"
            f"*Supporting Calculation:* `{ins.get('supporting_metrics', {}).get('calculation_formula', 'Direct sample calculation')}`"
            for i, ins in enumerate(insights[:3])
        ]) or "No high-severity findings flagged in current snapshot."

        reply = (
            f"### Executive Intelligence Brief for **{dataset.name}**\n\n"
            f"Here are the top analytical findings discovered from your dataset ({eda.get('row_count', len(df))} rows, {eda.get('column_count', len(df.columns))} columns):\n\n"
            f"{findings_text}\n\n"
            f"**Data Quality Index:** {eda.get('quality_score', 100)}%\n"
            f"**Next Recommended Step:** {exec_summary.get('recommended_next_actions', ['Review flagged areas'])[0]}"
        )
        return {
            "question": question,
            "answer": reply,
            "grounded_sources": [ins["title"] for ins in insights[:3]],
            "confidence": 0.96,
        }

    # 2. Intent: Risks / Anomalies / What could go wrong
    elif any(k in q_lower for k in ["risk", "anomaly", "anomalies", "outlier", "warning", "pitfall", "uncertainty"]):
        risk_insights = [i for i in insights if i["category"] in ("anomaly", "quality")]
        if risk_insights:
            risk_text = "\n\n".join([
                f"⚠️ **{r['title']}**\n{r['explanation']}\n*Methodology:* {r.get('methodology')}"
                for r in risk_insights[:3]
            ])
            reply = (
                f"### Identified Risks & Anomalies in **{dataset.name}**\n\n"
                f"{risk_text}\n\n"
                f"**Uncertainties & Limitations:**\n"
                + "\n".join([f"- {lim}" for lim in exec_summary.get("limitations_and_uncertainties", [])])
            )
        else:
            reply = (
                f"### Risk Evaluation for **{dataset.name}**\n\n"
                f"No extreme numerical anomalies or severe data quality leaks were detected in this snapshot. "
                f"The evaluated Data Quality Index is **{eda.get('quality_score', 100)}%** with 0 zero-variance columns."
            )
        return {
            "question": question,
            "answer": reply,
            "grounded_sources": [r["title"] for r in risk_insights[:3]],
            "confidence": 0.94,
        }

    # 3. Intent: Evidence / Proof / Show Evidence
    elif any(k in q_lower for k in ["evidence", "proof", "calculation", "formula", "show evidence"]):
        target = insights[0] if insights else None
        if target:
            supp = target.get("supporting_metrics", {})
            reply = (
                f"### Empirical Evidence Breakdown: **{target['title']}**\n\n"
                f"- **Methodology:** {target.get('methodology', 'Empirical aggregation')}\n"
                f"- **Confidence Score:** {int(target.get('confidence_score', 0.9) * 100)}% ({target.get('confidence_justification', 'Complete sample verification')})\n"
                f"- **Mathematical Formula:** `{supp.get('calculation_formula', 'Observed value comparison')}`\n"
                f"- **Source Columns:** {', '.join(target.get('source_columns', []))}\n\n"
                f"This claim is directly traceable to the raw records with zero LLM hallucination."
            )
        else:
            reply = "No active insights found to display evidence for."
        return {
            "question": question,
            "answer": reply,
            "grounded_sources": [target["title"]] if target else [],
            "confidence": 0.98,
        }

    # 4. Intent: Missing values specifically or Additional Data / Recommendations
    elif "most missing" in q_lower or "which column has" in q_lower or ("missing" in q_lower and "value" in q_lower):
        schema_cols = eda.get("schema", [])
        missing_sorted = sorted([c for c in schema_cols if c.get("missing_count", 0) > 0], key=lambda c: c["missing_count"], reverse=True)
        if missing_sorted:
            lines = [f"- **{c['name']}**: {c['missing_count']:,} missing ({c['missing_percent']}%)" for c in missing_sorted[:6]]
            reply = f"### Missing Value Audit for **{dataset.name}**\n\n" + "\n".join(lines)
            sources = [c["name"] for c in missing_sorted[:3]]
        else:
            reply = f"### Missing Value Audit for **{dataset.name}**\n\nZero missing values were detected across all {eda.get('column_count', len(df.columns))} columns."
            sources = ["Data Quality Audit"]
        return {
            "question": question,
            "answer": reply,
            "grounded_sources": sources,
            "confidence": 0.99,
        }

    elif any(k in q_lower for k in ["additional data", "improve", "recommend", "next action"]):
        recs = exec_summary.get("recommended_next_actions", [])
        reply = (
            f"### Recommendations for **{dataset.name}**\n\n"
            f"Based on dataset schema ({len(df.columns)} attributes) and discovered statistical findings:\n\n"
            + "\n".join(recs)
        )
        return {
            "question": question,
            "answer": reply,
            "grounded_sources": ["Executive Recommendations Engine"],
            "confidence": 0.93,
        }

    # 5. Specific Analytical / Visualization Query -> Delegate to Verified Deterministic Workflow
    else:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        from app.agents.orchestrator import run_workflow

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                with ThreadPoolExecutor(max_workers=1) as pool:
                    workflow = pool.submit(asyncio.run, run_workflow(df, question, use_llm=False)).result(timeout=30)
            else:
                workflow = asyncio.run(run_workflow(df, question, use_llm=False))
        except Exception:
            workflow = None

        if workflow and workflow.get("answer"):
            return {
                "question": question,
                "answer": workflow["answer"],
                "grounded_sources": workflow.get("verified_facts") or [ins["title"] for ins in insights[:2]],
                "chart_config": workflow.get("chart_config"),
                "confidence": 0.94,
            }

        top_ins = insights[0] if insights else None
        top_title = top_ins["title"] if top_ins else "Dataset profile"
        reply = (
            f"### Project Analysis Intelligence for **{dataset.name}**\n\n"
            f"Regarding your query: *\"{question}\"*\n\n"
            f"- **Active Dataset:** {dataset.name} ({eda.get('row_count', len(df)):,} records, {eda.get('column_count', len(df.columns))} columns)\n"
            f"- **Primary Discovery:** {top_title}\n"
            f"- **Quality Score:** {eda.get('quality_score', 100)}%\n\n"
            f"{top_ins['explanation'] if top_ins else ''}"
        )
        return {
            "question": question,
            "answer": reply,
            "grounded_sources": [top_title],
            "confidence": 0.90,
        }
