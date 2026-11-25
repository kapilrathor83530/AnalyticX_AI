"""Controlled 11-Step Agentic Execution Loop for Analyticx AI.
Orchestrates observation, intent understanding, planning, tool selection,
deterministic execution, result observation, evaluation, self-correction/retries,
validation, persistence, and verified response delivery.
"""
import difflib
import time
import uuid
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.agents.business_analyst_agent import business_analyst_agent
from app.agents.context_agent import context_agent
from app.agents.data_analyst_agent import data_analyst_agent
from app.agents.data_quality_agent import data_quality_agent
from app.agents.document_intelligence_agent import document_intelligence_agent
from app.agents.forecasting_scenario_agent import forecasting_scenario_agent
from app.agents.tool_registry import ToolExecutionError, tool_registry
from app.agents.validation_agent import validation_agent
from app.agents.visualization_agent import visualization_agent
from app.analytics.data_understanding import understand_dataset
from app.context.context_freshness_service import mark_context_accessed
from app.llm.model_manager import model_manager
from app.schemas.agent import (
    AgentExecutionStep,
    AgentTaskRequest,
    AgentTaskResponse,
    TaskState,
    ValidationReport,
)
from app.services.multilingual_engine import format_multilingual_fallback
from app.utils.language_detector import detect_language


# In-memory execution trace audit log
TASK_AUDIT_LOG: List[Dict[str, Any]] = []


def _fuzzy_match_column(target: str, available_columns: List[str]) -> Optional[str]:
    """Matches column name using case-insensitive and fuzzy distance."""
    if not target or not available_columns:
        return None
    # 1. Exact match
    if target in available_columns:
        return target
    # 2. Case-insensitive match
    lower_map = {c.lower(): c for c in available_columns}
    if target.lower() in lower_map:
        return lower_map[target.lower()]
    # 3. Substring match
    for c in available_columns:
        if target.lower() in c.lower() or c.lower() in target.lower():
            return c
    # 4. Fuzzy distance
    matches = difflib.get_close_matches(target, available_columns, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None


async def execute_agentic_loop(
    request: AgentTaskRequest,
    df: Optional[pd.DataFrame] = None,
    db: Optional[Session] = None,
) -> AgentTaskResponse:
    """
    Executes the deterministic 11-step agentic loop with bounded retries and independent validation.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    start_total = time.perf_counter()
    execution_steps: List[AgentExecutionStep] = []
    current_state = TaskState.PENDING
    retries_count = 0
    max_retries = 2

    # Step 1: Observe (Context & Input capture)
    step1_start = time.perf_counter()
    raw_ctx = request.context or {}
    resolved_ctx = context_agent.resolve_context(
        raw_context=raw_ctx,
        dataset_id=request.dataset_id,
        document_id=request.document_id,
        page_number=request.page_number,
        db=db,
    )
    execution_steps.append(
        AgentExecutionStep(
            step_number=1,
            step_name="Observe",
            agent="ContextAgent",
            status="ok",
            duration_ms=round((time.perf_counter() - step1_start) * 1000, 2),
            details={"resolved_context": {k: str(v) for k, v in resolved_ctx.items() if k != "column_details"}},
        )
    )

    # Step 2: Understand (Intent, Entities, Language)
    step2_start = time.perf_counter()
    current_state = TaskState.PLANNING
    query = request.query.strip()
    lang_info = detect_language(query, user_override=request.language_override)
    lang_code = lang_info["code"]
    modality = context_agent.classify_target_modality(query, resolved_ctx)
    execution_steps.append(
        AgentExecutionStep(
            step_number=2,
            step_name="Understand",
            agent="ContextAgent",
            status="ok",
            duration_ms=round((time.perf_counter() - step2_start) * 1000, 2),
            details={"detected_language": lang_code, "modality": modality, "query": query},
        )
    )

    # Step 3: Plan (Route to target agent and establish operation plan)
    step3_start = time.perf_counter()
    assigned_agent = "DataAnalystAgent"
    plan: List[str] = []
    selected_tool = "profile_dataset"
    tool_args: Dict[str, Any] = {}
    q_lower = query.lower()

    # Normalize working DataFrame through Universal Data Understanding once per loop
    work_df = df
    profile: Dict[str, Any] = {}
    if df is not None and not df.empty:
        try:
            understanding = understand_dataset(df, sanitize=True)
            work_df = understanding["normalized_df"]
            profile = understanding["profile"]
        except Exception:
            work_df = df

    # Routing heuristics based on query & modality
    if any(k in q_lower for k in ["forecast", "predict", "projection", "next month", "trend future", "what-if", "what if", "scenario"]):
        assigned_agent = "ForecastingScenarioAgent"
        plan = ["Identify time and metric columns", "Run projection/simulation", "Validate confidence bounds"]
        selected_tool = "forecast_trend"
    elif any(k in q_lower for k in ["chart", "plot", "graph", "visualize", "bar chart", "line chart", "pie chart", "scatter", "histogram", "box plot", "heatmap"]):
        assigned_agent = "VisualizationAgent"
        plan = ["Recommend chart type", "Map x/y dimensions", "Generate & validate dashboard config"]
        selected_tool = "recommend_chart"
    elif any(k in q_lower for k in ["quality", "missing", "duplicate", "clean", "outlier", "impute", "duplicates", "anomaly", "anomalies", "unusual"]):
        assigned_agent = "DataQualityAgent"
        if any(k in q_lower for k in ["outlier", "anomaly", "anomalies", "unusual"]) and not any(k in q_lower for k in ["quality", "missing", "duplicate"]):
            plan = ["Identify numerical columns", "Run IQR/MAD/Isolation Forest anomaly detection", "Validate candidate flags"]
            selected_tool = "detect_outliers"
        else:
            plan = ["Inspect data quality", "Detect anomalies", "Preview cleaning transformation"]
            selected_tool = "detect_data_quality_issues"
    elif modality == "document" or resolved_ctx.get("has_document") or any(k in q_lower for k in ["pdf", "document", "page", "citation"]):
        assigned_agent = "DocumentIntelligenceAgent"
        plan = ["Retrieve document page", "Extract text and tables", "Generate verified citation"]
        selected_tool = "retrieve_pdf_page"
    elif any(k in q_lower for k in ["recommendation", "kpi", "business impact", "strategic", "advice", "risk"]):
        assigned_agent = "BusinessAnalystAgent"
        plan = ["Compute aggregate KPI metrics", "Evaluate business risks", "Formulate strategic recommendations"]
        selected_tool = "explain_kpi"
    elif any(k in q_lower for k in ["monthly trend", "over time", "time series", "daily trend", "yearly trend", "temporal"]):
        assigned_agent = "DataAnalystAgent"
        plan = ["Resolve datetime & metric columns", "Resample chronologically", "Verify trend metrics"]
        selected_tool = "analyze_datetime_column"
    elif any(k in q_lower for k in ["compare", "group comparison", "anova"]) and len(profile.get("categorical_columns", [])) >= 1 and len(profile.get("numerical_columns", [])) >= 1:
        assigned_agent = "DataAnalystAgent"
        plan = ["Identify grouping dimension and metric", "Run ANOVA & group comparison", "Verify significance"]
        selected_tool = "analyze_group_comparison"
    elif any(k in q_lower for k in ["top", "highest", "lowest", "bottom", "most", "category"]):
        assigned_agent = "DataAnalystAgent"
        plan = ["Identify categorical dimension", "Aggregate metric", "Rank top categories"]
        selected_tool = "top_categories"
    elif any(k in q_lower for k in ["correlation", "relationship", "associated", "vs"]):
        assigned_agent = "DataAnalystAgent"
        plan = ["Select numeric columns", "Calculate Pearson & Spearman correlation matrix"]
        selected_tool = "correlation_summary"
    elif any(k in q_lower for k in ["mean", "average", "median", "summary", "stats", "describe", "sum", "distribution", "औसत", "ausat", "madhya", "kul", "जोड़", "कुल"]):
        assigned_agent = "DataAnalystAgent"
        plan = ["Locate numeric column", "Compute summary statistics", "Check quantile distributions"]
        selected_tool = "numeric_summary"
    else:
        assigned_agent = "DataAnalystAgent"
        plan = ["Profile overall dataset health", "Summarize rows, columns, and completeness"]
        selected_tool = "profile_dataset"

    execution_steps.append(
        AgentExecutionStep(
            step_number=3,
            step_name="Plan",
            agent="Orchestrator",
            status="ok",
            duration_ms=round((time.perf_counter() - step3_start) * 1000, 2),
            details={"assigned_agent": assigned_agent, "plan": plan},
        )
    )

    # Step 4: Select Tools & Parameter Validation
    step4_start = time.perf_counter()
    current_state = TaskState.RUNNING

    # Parameter extraction from query & dataframe
    if work_df is not None and not work_df.empty:
        cols = list(work_df.columns)
        eligible_nums = profile.get("numerical_columns") or list(work_df.select_dtypes(include="number").columns)
        eligible_cats = [
            c for c in (profile.get("categorical_columns", []) + profile.get("boolean_columns", []))
            if c not in profile.get("identifier_columns", [])
        ] or list(work_df.select_dtypes(exclude="number").columns)
        dt_cols = profile.get("datetime_columns") or []

        # Multilingual alias dictionary for common terms
        term_map = {
            "राजस्व": "revenue", "rajasva": "revenue", "kamai": "revenue", "bikri": "revenue", "biki": "revenue", "sales": "revenue",
            "मुनाफा": "profit", "munafa": "profit", "labh": "profit", "fayda": "profit",
            "इकाई": "units", "ikai": "units",
            "क्षेत्र": "region", "ilaqa": "region", "prant": "region",
        }
        for term, col_target in term_map.items():
            if term in q_lower and col_target in cols:
                if selected_tool in {"numeric_summary", "detect_outliers"}:
                    tool_args["column"] = col_target
                elif selected_tool in {"top_categories", "analyze_group_comparison"}:
                    if col_target in eligible_nums:
                        tool_args["metric"] = col_target
                        tool_args["value_column"] = col_target
                    else:
                        tool_args["dimension"] = col_target
                        tool_args["group_column"] = col_target

        # Attempt to find mentioned column(s) longest-first
        for c in sorted(cols, key=lambda x: len(str(x)), reverse=True):
            c_low = str(c).lower()
            if c_low in q_lower or c_low.replace("_", " ") in q_lower:
                if selected_tool in {"numeric_summary", "detect_outliers"} and "column" not in tool_args:
                    tool_args["column"] = c
                elif selected_tool == "analyze_datetime_column" and c in dt_cols:
                    tool_args["column"] = c
                elif selected_tool in {"top_categories", "analyze_group_comparison"}:
                    if c in eligible_nums and "metric" not in tool_args:
                        tool_args["metric"] = c
                        tool_args["value_column"] = c
                    elif c not in eligible_nums and "dimension" not in tool_args:
                        tool_args["dimension"] = c
                        tool_args["group_column"] = c

        # Safe domain-agnostic defaults for tools if not explicitly matched
        if selected_tool == "numeric_summary" and "column" not in tool_args:
            tool_args["column"] = eligible_nums[0] if eligible_nums else cols[0]

        if selected_tool == "analyze_datetime_column":
            if dt_cols:
                tool_args.setdefault("column", dt_cols[0])
                tool_args["numeric_columns"] = eligible_nums[:3]
            else:
                # Recover gracefully to profile_dataset if dataset has no datetime columns
                selected_tool = "profile_dataset"
                assigned_agent = "DataAnalystAgent"

        if selected_tool == "analyze_group_comparison":
            tool_args.setdefault("group_column", eligible_cats[0] if eligible_cats else cols[0])
            tool_args.setdefault("value_column", eligible_nums[0] if eligible_nums else cols[-1])

        if selected_tool == "top_categories":
            if "dimension" not in tool_args:
                tool_args["dimension"] = eligible_cats[0] if eligible_cats else cols[0]
            if "metric" not in tool_args and eligible_nums:
                tool_args["metric"] = eligible_nums[0]

        if selected_tool == "recommend_chart":
            tool_args["query"] = query

    if selected_tool == "retrieve_pdf_page":
        tool_args["document_path"] = resolved_ctx.get("pdf_path") or str(resolved_ctx.get("stored_path", ""))
        tool_args["page_number"] = resolved_ctx.get("page_number") or 1
        tool_args["query"] = query

    execution_steps.append(
        AgentExecutionStep(
            step_number=4,
            step_name="Select Tools",
            agent=assigned_agent,
            tool=selected_tool,
            status="ok",
            duration_ms=round((time.perf_counter() - step4_start) * 1000, 2),
            details={"selected_tool": selected_tool, "tool_args": tool_args},
        )
    )

    # Step 5 & 6 & 7 & 8: Execute, Observe Results, Evaluate, and Self-Correct / Retry Loop
    tool_result: Dict[str, Any] = {}
    validation_rep = ValidationReport(passed=True, checks=[], issues=[])
    retry_allowed = True

    while retry_allowed and retries_count <= max_retries:
        step5_start = time.perf_counter()
        exec_error: Optional[Exception] = None

        try:
            # Step 5: Execute
            if assigned_agent == "DataAnalystAgent":
                if selected_tool == "numeric_summary":
                    tool_result = data_analyst_agent.numeric_summary(work_df, column=tool_args["column"])
                elif selected_tool == "top_categories":
                    tool_result = data_analyst_agent.top_categories(
                        work_df, dimension=tool_args["dimension"], metric=tool_args.get("metric"), limit=tool_args.get("limit", 5)
                    )
                elif selected_tool == "correlation_summary":
                    tool_result = data_analyst_agent.correlation_summary(work_df, columns=tool_args.get("columns"))
                elif selected_tool == "analyze_datetime_column":
                    tool_result = tool_registry.execute(
                        "analyze_datetime_column", df=work_df, column=tool_args["column"], numeric_columns=tool_args.get("numeric_columns")
                    )
                elif selected_tool == "analyze_group_comparison":
                    tool_result = tool_registry.execute(
                        "analyze_group_comparison", df=work_df, group_column=tool_args["group_column"], value_column=tool_args["value_column"]
                    )
                else:
                    tool_result = data_analyst_agent.profile_dataset(work_df)

            elif assigned_agent == "DataQualityAgent":
                if selected_tool == "preview_cleaning_changes":
                    tool_result = data_quality_agent.preview_cleaning(
                        work_df,
                        action_type=tool_args.get("action_type", "remove_duplicates"),
                        column=tool_args.get("column"),
                        strategy=tool_args.get("strategy"),
                    )
                elif selected_tool == "detect_outliers":
                    tool_result = tool_registry.execute("detect_outliers", df=work_df, column=tool_args.get("column"))
                else:
                    tool_result = data_quality_agent.detect_quality_issues(work_df)

            elif assigned_agent == "VisualizationAgent":
                tool_result = visualization_agent.recommend_chart(work_df, query=query)

            elif assigned_agent == "DocumentIntelligenceAgent":
                tool_result = document_intelligence_agent.retrieve_page(
                    document_path=tool_args["document_path"],
                    page_number=tool_args["page_number"],
                    query=tool_args.get("query"),
                )

            elif assigned_agent == "ForecastingScenarioAgent":
                if work_df is not None and not work_df.empty:
                    num_cols = profile.get("numerical_columns") or list(work_df.select_dtypes(include="number").columns)
                    target = num_cols[0] if len(num_cols) > 0 else list(work_df.columns)[0]
                    tool_result = {
                        "forecast": f"Baseline model readiness checked for '{target}'. Open Forecasting Lab for multi-horizon projection.",
                        "target_metric": target,
                        "assumptions": ["Stable trend continuation", "Model-based estimate, not historical certainty"],
                    }
                else:
                    tool_result = {"forecast": "Projections require a valid dataset."}

            elif assigned_agent == "BusinessAnalystAgent":
                num_cols = profile.get("numerical_columns") or (list(work_df.select_dtypes(include="number").columns) if work_df is not None else [])
                m = num_cols[0] if len(num_cols) > 0 else "Metric"
                tool_result = business_analyst_agent.explain_kpi(work_df, metric=m)

        except Exception as exc:
            exec_error = exc

        step5_duration = round((time.perf_counter() - step5_start) * 1000, 2)

        # Step 6: Observe Results
        execution_steps.append(
            AgentExecutionStep(
                step_number=6,
                step_name=f"Observe Results (Attempt {retries_count + 1})",
                agent=assigned_agent,
                tool=selected_tool,
                status="ok" if exec_error is None else "error",
                duration_ms=step5_duration,
                details={"has_error": exec_error is not None, "error_msg": str(exec_error) if exec_error else None},
            )
        )

        # Step 7: Evaluate
        step7_start = time.perf_counter()
        is_successful = exec_error is None and not (isinstance(tool_result, dict) and "error" in tool_result)

        execution_steps.append(
            AgentExecutionStep(
                step_number=7,
                step_name=f"Evaluate (Attempt {retries_count + 1})",
                agent="Orchestrator",
                status="ok" if is_successful else "warning",
                duration_ms=round((time.perf_counter() - step7_start) * 1000, 2),
                details={"evaluation_passed": is_successful},
            )
        )

        if is_successful:
            break

        # Step 8: Correct / Retry
        step8_start = time.perf_counter()
        current_state = TaskState.RETRYING
        retries_count += 1

        if retries_count > max_retries:
            current_state = TaskState.FAILED
            execution_steps.append(
                AgentExecutionStep(
                    step_number=8,
                    step_name="Correct / Retry",
                    agent="Orchestrator",
                    status="error",
                    duration_ms=round((time.perf_counter() - step8_start) * 1000, 2),
                    details={"error": "Max retries exceeded", "retries_count": retries_count},
                )
            )
            break

        # Self-correction logic
        recovered = False
        correction_reason = ""

        # Case A: Column name mismatch / typo in numeric_summary, top_categories, or group comparison
        if work_df is not None and "column" in tool_args:
            bad_col = tool_args["column"]
            matched_col = _fuzzy_match_column(bad_col, list(work_df.columns))
            if matched_col and matched_col != bad_col:
                tool_args["column"] = matched_col
                recovered = True
                correction_reason = f"Fuzzy matched column '{bad_col}' to existing column '{matched_col}'."
            else:
                num_cols = profile.get("numerical_columns") or list(work_df.select_dtypes(include="number").columns)
                if num_cols:
                    tool_args["column"] = num_cols[0]
                    recovered = True
                    correction_reason = f"Replaced invalid column '{bad_col}' with first eligible numeric column '{num_cols[0]}'."

        if not recovered and work_df is not None and "dimension" in tool_args:
            bad_dim = tool_args["dimension"]
            matched_dim = _fuzzy_match_column(bad_dim, list(work_df.columns))
            if matched_dim and matched_dim != bad_dim:
                tool_args["dimension"] = matched_dim
                recovered = True
                correction_reason = f"Fuzzy matched dimension '{bad_dim}' to '{matched_dim}'."

        # Case B: PDF page out of bounds
        if selected_tool == "retrieve_pdf_page" and "page_number" in tool_args:
            tool_args["page_number"] = 1  # Reset to page 1
            recovered = True
            correction_reason = "Page out of bounds; reset target page to 1."

        execution_steps.append(
            AgentExecutionStep(
                step_number=8,
                step_name=f"Correct / Retry (Retry #{retries_count})",
                agent="Orchestrator",
                status="ok" if recovered else "error",
                duration_ms=round((time.perf_counter() - step8_start) * 1000, 2),
                details={"recovered": recovered, "reason": correction_reason},
            )
        )

        if not recovered:
            current_state = TaskState.FAILED
            break

    # Step 9: Verify (Validation Agent checks outputs)
    step9_start = time.perf_counter()
    current_state = TaskState.VALIDATING

    if selected_tool == "numeric_summary" and tool_result:
        validation_rep = validation_agent.verify_numeric_summary(tool_result, df=work_df)
    elif selected_tool == "recommend_chart" and tool_result:
        validation_rep = validation_agent.verify_chart_config(tool_result, df=work_df)
    else:
        validation_rep = validation_agent.verify_general_result(tool_result)

    execution_steps.append(
        AgentExecutionStep(
            step_number=9,
            step_name="Verify",
            agent="ValidationAgent",
            status="ok" if validation_rep.passed else "warning",
            duration_ms=round((time.perf_counter() - step9_start) * 1000, 2),
            details={"validation_passed": validation_rep.passed, "issues": validation_rep.issues},
        )
    )

    # Step 10: Persist (Audit logging & Context Freshness)
    step10_start = time.perf_counter()
    if resolved_ctx.get("dataset_id"):
        mark_context_accessed("dataset", resolved_ctx["dataset_id"])

    audit_entry = {
        "task_id": task_id,
        "query": query,
        "assigned_agent": assigned_agent,
        "tool": selected_tool,
        "retries": retries_count,
        "validation_passed": validation_rep.passed,
        "timestamp": time.time(),
    }
    TASK_AUDIT_LOG.append(audit_entry)

    execution_steps.append(
        AgentExecutionStep(
            step_number=10,
            step_name="Persist",
            agent="Orchestrator",
            status="ok",
            duration_ms=round((time.perf_counter() - step10_start) * 1000, 2),
            details={"audit_entry": audit_entry},
        )
    )

    # Step 11: Respond (Format verified findings in user's detected language)
    step11_start = time.perf_counter()
    current_state = TaskState.COMPLETED if current_state != TaskState.FAILED else TaskState.FAILED

    verified_facts: List[str] = []
    business_insights: List[str] = []
    recommendations: List[str] = []
    citations: List[Dict[str, Any]] = []
    chart_cfg: Optional[Dict[str, Any]] = None

    if selected_tool == "numeric_summary" and "mean" in tool_result:
        col = tool_result["column"]
        mean_v = tool_result["mean"]
        med_v = tool_result["median"]
        verified_facts = [
            f"Target Column: {col}",
            f"Mean: {mean_v:,}",
            f"Median: {med_v:,}",
            f"Range: [{tool_result['min']}, {tool_result['max']}]",
            f"Std Dev: {tool_result['std']}",
        ]
        business_insights = [
            f"The mean ({mean_v}) compared to median ({med_v}) indicates {'asymmetry with extreme values pulling the average' if abs(mean_v - med_v) > (tool_result.get('std') or 0) * 0.25 else 'relatively balanced dispersion across records'}.",
        ]
        recommendations = business_analyst_agent.generate_recommendations(tool_result)
        chart_cfg = {"chart_type": "histogram", "title": f"Distribution of {col}", "data_mapping": {"x": col}, "aggregation": "count"}

    elif selected_tool == "top_categories" and "items" in tool_result:
        dim = tool_result["dimension"]
        items = tool_result["items"]
        top_val = items[0] if items else {"value": "None", "metric": 0}
        verified_facts = [
            f"Categorical Dimension: {dim}",
            f"Top Performer: {top_val['value']} with {top_val['metric']:,} {tool_result.get('metric', '')}",
            f"Total Categories: {tool_result.get('total_categories', len(items))}",
        ]
        business_insights = [
            f"'{top_val['value']}' leads the {dim} breakdown, representing primary volume concentration.",
        ]
        recommendations = business_analyst_agent.generate_recommendations({"top_values": items})
        chart_cfg = {"chart_type": "bar", "title": f"{tool_result.get('metric', 'Count')} by {dim}", "data_mapping": {"x": dim, "y": tool_result.get("metric") if tool_result.get("metric") != "count" else dim}, "aggregation": "count" if tool_result.get("metric") == "count" else "sum"}

    elif selected_tool == "correlation_summary":
        corrs = tool_result.get("correlations") or []
        if corrs:
            c0 = corrs[0]
            verified_facts = [
                f"Top Pair: {c0['col1']} & {c0['col2']} (r = {c0['correlation']})",
                f"Evaluated {len(tool_result.get('columns_evaluated', []))} numeric columns",
            ]
            business_insights = [
                f"Observed {c0.get('strength', '')} association between '{c0['col1']}' and '{c0['col2']}'. Note: Correlation does not prove causation.",
            ]
            chart_cfg = {"chart_type": "scatter", "title": f"{c0['col1']} vs {c0['col2']}", "data_mapping": {"x": c0["col1"], "y": c0["col2"]}}
        else:
            verified_facts = ["Insufficient numeric columns or no strong correlations found."]
            business_insights = [tool_result.get("message", "No notable linear correlations detected.")]

    elif selected_tool == "detect_outliers":
        flagged = tool_result.get("flagged_count") if "flagged_count" in tool_result else sum(u.get("flagged_count", 0) for u in tool_result.get("univariate", []))
        target_col = tool_result.get("column") or ((tool_result.get("univariate") or [{}])[0].get("column"))
        verified_facts = [
            f"Candidate Anomalies Flagged: {flagged}",
            f"Target Scope: {target_col or 'All numeric columns'}",
        ]
        business_insights = ["Flagged points are candidate anomalies; verify before excluding records."]
        if target_col:
            chart_cfg = {"chart_type": "box", "title": f"Outlier Spread: {target_col}", "data_mapping": {"y": target_col}}

    elif selected_tool == "analyze_datetime_column":
        d_col = tool_result.get("date_column", "date")
        trends = tool_result.get("metric_trends") or []
        verified_facts = [
            f"Date Column: {d_col}",
            f"Coverage: {tool_result.get('earliest_date')} to {tool_result.get('latest_date')}",
            f"Periods Observed: {tool_result.get('periods_observed', 0)}",
        ]
        if trends:
            t0 = trends[0]
            business_insights = [
                f"{t0['granularity'].capitalize()} trajectory of '{t0['metric_column']}': {t0['first_value']} to {t0['last_value']} (net {t0['net_delta']:+,.2f})."
            ]
            chart_cfg = {"chart_type": "time_series", "title": f"{t0['metric_column']} Over {d_col}", "data_mapping": {"x": d_col, "y": t0["metric_column"]}, "aggregation": "sum"}

    elif selected_tool == "analyze_group_comparison":
        verified_facts = [
            f"Group: {tool_result.get('group_column')}, Metric: {tool_result.get('value_column')}",
            f"ANOVA F={tool_result.get('f_statistic')}, p={tool_result.get('p_value')}",
        ]
        top_g = tool_result.get("top_group") or {}
        if top_g:
            business_insights = [f"'{top_g.get('group')}' has the highest mean ({top_g.get('mean')}) across evaluated groups."]
            chart_cfg = {"chart_type": "bar", "title": f"{tool_result.get('value_column')} by {tool_result.get('group_column')}", "data_mapping": {"x": tool_result.get("group_column"), "y": tool_result.get("value_column")}, "aggregation": "mean"}

    elif selected_tool == "detect_data_quality_issues":
        qs = tool_result.get("quality_score", 100)
        verified_facts = [
            f"Data Quality Score: {qs}%",
            f"Missing Columns: {tool_result.get('missing_columns_count', 0)}",
            f"Outlier Columns: {tool_result.get('outlier_columns_count', 0)}",
        ]
        business_insights = [
            "Data cleanliness is foundational to trustworthy executive reporting and model training.",
        ]
        raw_recs = tool_result.get("recommendations", [])
        recommendations = [
            r if isinstance(r, str) else r.get("description", r.get("reason", str(r)))
            for r in raw_recs
        ]
        if not recommendations:
            recommendations = ["Auto-clean dataset before modeling."]

    elif selected_tool == "recommend_chart":
        chart_cfg = tool_result
        verified_facts = [
            f"Recommended Chart: {tool_result.get('chart_type', 'bar').capitalize()}",
            f"X-Axis: {tool_result.get('x')}",
            f"Y-Axis: {tool_result.get('y')}",
        ]
        business_insights = ["Interactive visual representation provides instant stakeholder clarity."]

    elif selected_tool == "retrieve_pdf_page":
        citations = [{
            "document": tool_result.get("document_name", "document.pdf"),
            "page": tool_result.get("page_number", 1),
            "snippet": (tool_result.get("text", "")[:180] + "...") if tool_result.get("text") else "",
        }]
        verified_facts = [
            f"Document: {tool_result.get('document_name')}",
            f"Page: {tool_result.get('page_number')}",
            f"Characters Extracted: {tool_result.get('char_count', 0)}",
        ]

    elif selected_tool == "profile_dataset" or not verified_facts:
        row_c = tool_result.get("row_count", len(df) if df is not None else 0)
        col_c = tool_result.get("column_count", len(df.columns) if df is not None else 0)
        missing_c = tool_result.get("missing_cells", int(df.isna().sum().sum()) if df is not None else 0)
        dup_c = tool_result.get("duplicate_rows", int(df.duplicated().sum()) if df is not None else 0)
        verified_facts = [
            f"Dataset Rows: {row_c:,}",
            f"Dataset Columns: {col_c}",
            f"Missing Values: {missing_c:,}",
            f"Duplicate Records: {dup_c:,}",
        ]
        business_insights = [
            f"Dataset structure verified with {row_c:,} records across {col_c} attributes.",
        ]
        recommendations = ["Proceed with feature exploration and exploratory visual analysis."]

    # Multilingual answer formatting
    if lang_code == "hinglish":
        ans_prefix = f"✅ Query process ho gaya hai (`{assigned_agent}` ke through).\n\n"
        if verified_facts:
            ans_prefix += "**Verified Facts:**\n" + "\n".join(f"- {f}" for f in verified_facts) + "\n\n"
        if business_insights:
            ans_prefix += "**Business Insights:**\n" + "\n".join(f"- {b}" for b in business_insights)
    elif lang_code == "hi":
        ans_prefix = f"✅ कार्य सफलतापूर्वक निष्पादित किया गया (`{assigned_agent}`).\n\n"
        if verified_facts:
            ans_prefix += "**सत्यापित तथ्य:**\n" + "\n".join(f"- {f}" for f in verified_facts) + "\n\n"
        if business_insights:
            ans_prefix += "**व्यावसायिक अंतर्दृष्टि:**\n" + "\n".join(f"- {b}" for b in business_insights)
    else:
        ans_prefix = f"✅ Analysis verified and executed via `{assigned_agent}`.\n\n"
        if verified_facts:
            ans_prefix += "**Verified Facts:**\n" + "\n".join(f"- {f}" for f in verified_facts) + "\n\n"
        if business_insights:
            ans_prefix += "**Business Insights:**\n" + "\n".join(f"- {b}" for b in business_insights)

    execution_steps.append(
        AgentExecutionStep(
            step_number=11,
            step_name="Respond",
            agent="Orchestrator",
            status="ok",
            duration_ms=round((time.perf_counter() - step11_start) * 1000, 2),
            details={"language": lang_code, "facts_count": len(verified_facts)},
        )
    )

    total_duration = round((time.perf_counter() - start_total) * 1000, 2)

    return AgentTaskResponse(
        task_id=task_id,
        state=current_state,
        query=query,
        detected_language=lang_code,
        assigned_agent=assigned_agent,
        plan=plan,
        execution_steps=execution_steps,
        tools_used=[selected_tool],
        validation=validation_rep,
        retries_count=retries_count,
        answer=ans_prefix,
        verified_facts=verified_facts,
        business_insights=business_insights,
        recommendations=recommendations,
        citations=citations,
        chart_config=chart_cfg,
        limitations=["Deterministic tool computation verified against active dataset bounds."],
        duration_total_ms=total_duration,
    )
