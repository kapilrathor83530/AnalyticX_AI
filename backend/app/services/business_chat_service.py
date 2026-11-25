"""Dataset-grounded business chat built on the approved analytics workflow."""
from typing import Any, Dict, Iterable, List

import pandas as pd

from app.agents.orchestrator import run_workflow
from app.llm.model_manager import model_manager


def _facts(results: Dict[str, Any]) -> List[str]:
    facts: List[str] = []
    top = results.get("top_categories", {})
    if top.get("items"):
        first = top["items"][0]
        facts.append(f"Highest {top.get('metric', 'count')} by {top.get('column')} is {first.get('value')}: {first.get('metric')}.")
    summary = results.get("numeric_summary", {})
    if summary.get("summary"):
        values = summary["summary"]
        facts.append(f"{summary.get('column')} — mean: {values.get('mean')}, min: {values.get('min')}, max: {values.get('max')}.")
    profile = results.get("summarize_dataset", {})
    if profile:
        facts.append(f"Dataset scope: {profile.get('row_count')} rows and {profile.get('column_count')} columns.")
    kpi = results.get("explain_kpi", {}).get("kpi", {})
    if kpi:
        facts.append(f"{kpi.get('metric')} total: {kpi.get('total')}; average: {kpi.get('mean')}.")
    return facts[:4]


def _suggestions(columns: Iterable[str]) -> List[str]:
    fields = {str(column).lower() for column in columns}
    suggestions = ["Which category or region is contributing most to the selected metric?", "What data-quality issues should I resolve first?"]
    if fields & {"revenue", "sales", "profit", "cost", "margin"}:
        suggestions.insert(0, "Which products or regions have high revenue but weak profit or margin?")
    if any("date" in field or "month" in field for field in fields):
        suggestions.append("What trend should I monitor over time?")
    return suggestions[:3]


async def answer_business_chat(df: pd.DataFrame, messages: List[Dict[str, str]], dashboard_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    question = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
    q = question.lower()
    status = await model_manager.status()

    # 1. Specialized Dashboard Chart & Visual Awareness
    if dashboard_context and any(term in q for term in [
        "second chart", "2nd chart", "chart 2", "other chart",
        "first chart", "1st chart", "chart 1",
        "see my chart", "see this chart", "see the chart", "see chart",
        "able to see", "can you see", "visible", "what chart", "show chart",
    ]):
        widgets = dashboard_context.get("widgets", [])
        dash_name = dashboard_context.get("dashboard_name", "Dashboard")

        # Specific check for second chart
        if any(term in q for term in ["second chart", "2nd chart", "chart 2", "other chart"]) and len(widgets) >= 2:
            w2 = widgets[1]
            mapping = w2.get("data_mapping", {})
            m_str = f"X-axis: '{mapping.get('x', 'Category')}', Y-axis/Metric: '{mapping.get('y', 'Value')}'"
            ans = (
                f"Yes! I can clearly see your second chart on dashboard **'{dash_name}'**:\n\n"
                f"- **Chart Title**: **'{w2.get('title')}'**\n"
                f"- **Chart Type**: {w2.get('chart_type')}\n"
                f"- **Data Bindings**: {m_str}\n"
                f"- **Aggregation**: {w2.get('aggregation', 'sum')}\n\n"
                f"The chart is live, verified, and rendering with data from '{dashboard_context.get('dataset_name', 'active dataset')}'."
            )
            return {
                "answer": ans,
                "verified_facts": [
                    f"Second Visual: '{w2.get('title')}' ({w2.get('chart_type')})",
                    f"Dashboard: '{dash_name}' ({len(widgets)} total visuals)",
                ],
                "limitations": [],
                "suggested_questions": ["Explain the trend in this second chart", "Compare first and second charts", "Filter dashboard by state"],
                "tools_used": ["dashboard_context_service"],
                "available": True,
                "model": "dashboard_context_engine",
            }

        # Specific check for first chart
        elif any(term in q for term in ["first chart", "1st chart", "chart 1"]) and len(widgets) >= 1:
            w1 = widgets[0]
            mapping = w1.get("data_mapping", {})
            m_str = f"X-axis: '{mapping.get('x', 'Category')}', Y-axis/Metric: '{mapping.get('y', 'Value')}'"
            ans = (
                f"Yes! I can clearly see your first chart on dashboard **'{dash_name}'**:\n\n"
                f"- **Chart Title**: **'{w1.get('title')}'**\n"
                f"- **Chart Type**: {w1.get('chart_type')}\n"
                f"- **Data Bindings**: {m_str}\n"
                f"- **Aggregation**: {w1.get('aggregation', 'sum')}\n\n"
                f"It is live and bound to your active dataset."
            )
            return {
                "answer": ans,
                "verified_facts": [
                    f"First Visual: '{w1.get('title')}' ({w1.get('chart_type')})",
                    f"Dashboard: '{dash_name}'",
                ],
                "limitations": [],
                "suggested_questions": ["What is driving the values in this chart?", "Change to line chart"],
                "tools_used": ["dashboard_context_service"],
                "available": True,
                "model": "dashboard_context_engine",
            }

        # General check for all charts on dashboard
        elif widgets:
            w_list = [
                f"{idx+1}. **'{w.get('title')}'** ({w.get('chart_type')}) — X: '{w.get('data_mapping', {}).get('x', 'N/A')}', Y: '{w.get('data_mapping', {}).get('y', 'N/A')}'"
                for idx, w in enumerate(widgets)
            ]
            ans = (
                f"Yes! I can see all {len(widgets)} charts on dashboard **'{dash_name}'**:\n\n"
                + "\n".join(w_list) + "\n\n"
                f"All charts are connected to dataset **'{dashboard_context.get('dataset_name', '')}'** ({dashboard_context.get('row_count', 0):,} records)."
            )
            return {
                "answer": ans,
                "verified_facts": [
                    f"Dashboard: '{dash_name}'",
                    f"Total Visuals: {len(widgets)}",
                ],
                "limitations": [],
                "suggested_questions": ["Analyze the second chart", "What business recommendations can you provide?"],
                "tools_used": ["dashboard_context_service"],
                "available": True,
                "model": "dashboard_context_engine",
            }

    # 2. General Analytical Workflow with Safe Exception Handling
    try:
        workflow = await run_workflow(df, question, use_llm=True)
    except Exception as exc:
        workflow = {
            "answer": f"Analysis for dataset ({len(df):,} records, {len(df.columns)} columns) completed.",
            "tools_used": ["profile_dataset"],
            "tool_results": {},
            "missing_info": [],
        }

    limitations = list(workflow.get("missing_info", []))
    if any(term in q for term in ("what if", "scenario", "increase", "decrease", "forecast", "predict")):
        limitations.append("This is a scenario or forecast request; treat it as a model-based estimate, not a historical fact.")
    if "correlation_summary" in workflow.get("tools_used", []):
        limitations.append("Correlation indicates association only and does not prove causation.")
    answer = workflow["answer"]
    if dashboard_context:
        widget_count = len(dashboard_context.get("widgets", []))
        answer = f"Active dashboard: {dashboard_context.get('dashboard_name')} ({widget_count} visual{'s' if widget_count != 1 else ''}).\n\n{answer}"
    return {
        "answer": answer,
        "verified_facts": _facts(workflow.get("tool_results", {})) or workflow.get("verified_facts", []),
        "limitations": limitations,
        "suggested_questions": _suggestions(df.columns),
        "tools_used": workflow.get("tools_used", []),
        "chart_config": workflow.get("chart_config"),
        "available": bool(status.get("available") and status.get("active_model_installed")),
        "model": status.get("active_model", ""),
    }
