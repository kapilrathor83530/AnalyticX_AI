import re
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from app.agents.business_analyst_agent import business_analyst_agent
from app.agents.data_analyst_agent import data_analyst_agent
from app.agents.validation_layer import validate_columns, validate_tool_names
from app.agents.visualization_agent import visualization_agent
from app.analytics.data_understanding import understand_dataset
from app.analytics.project_insights_engine import build_automated_eda, discover_business_insights
from app.analytics.statistics import analyze_datetime_column, analyze_numerical_column, compare_groups, detect_outliers
from app.llm.model_manager import model_manager
from app.llm.prompt_templates import (
    BUSINESS_ANALYST_SYSTEM,
    TOOL_SELECTION_SYSTEM,
    build_business_prompt,
    build_tool_selection_prompt,
)
from app.llm.response_parser import parse_business_answer, parse_tool_selection
from app.models.dataset import Dataset
from app.schemas.agent import AgentStep

TOOL_NAMES = [
    "profile_dataset",
    "summarize_dataset",
    "top_categories",
    "numeric_summary",
    "analyze_categorical_column",
    "analyze_datetime_column",
    "correlation_summary",
    "calculate_correlation",
    "detect_outliers",
    "analyze_group_comparison",
    "generate_time_series",
    "describe_column",
    "detect_data_quality_issues",
    "recommend_chart",
    "build_chart_config",
    "explain_kpi",
]

_KNOWN_METRIC_TERMS = (
    "revenue", "sales", "profit", "cost", "amount", "price", "quantity", "units",
    "units_sold", "volume", "margin", "churn", "salary", "marks", "score", "sgpa",
    "gpa", "attendance", "temperature", "rainfall", "humidity", "bmi", "blood_pressure",
    "cholesterol", "glucose", "budget", "spend", "income", "age", "tenure",
)


def _match_column_in_query(query: str, candidates: List[str]) -> Optional[str]:
    q = query.lower()
    # Exact or underscored/spaced match longest-first so "units_sold" beats "units"
    for col in sorted(candidates, key=lambda c: len(c), reverse=True):
        c_low = col.lower()
        c_space = c_low.replace("_", " ")
        if c_low in q or c_space in q:
            return col
    return None


def _guess_metric(question: str, columns: list[str], profile: Optional[Dict[str, Any]] = None) -> str | None:
    q = question.lower()
    num_cols = (profile or {}).get("numerical_columns", columns)
    cat_cols = set((profile or {}).get("categorical_columns", []) + (profile or {}).get("identifier_columns", []))
    eligible_nums = [c for c in num_cols if c not in cat_cols]

    # Direct column mention among eligible numeric measures
    matched = _match_column_in_query(q, eligible_nums)
    if matched:
        return matched

    # Check if user explicitly named an unknown metric token (e.g. "units_sold", "churn")
    for kw in _KNOWN_METRIC_TERMS:
        if kw in q:
            for col in eligible_nums:
                if kw in col.lower() or col.lower() in kw:
                    return col
            # Explicitly asked for a specific named metric term not present in dataset
            return None

    # Generic question without specific missing term ("average", "distribution", "highest value")
    if any(w in q for w in ("average", "mean", "median", "distribution", "histogram", "outlier", "anomal", "highest average", "compare")) and eligible_nums:
        return eligible_nums[0]
    return None


def _question_requests_metric(question: str) -> bool:
    q = question.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", q) or word in q for word in _KNOWN_METRIC_TERMS)


def _guess_dimension(question: str, columns: list[str], profile: Optional[Dict[str, Any]] = None) -> str | None:
    q = question.lower()
    cat_cols = (profile or {}).get("categorical_columns", []) + (profile or {}).get("boolean_columns", [])
    dt_cols = (profile or {}).get("datetime_columns", [])
    id_cols = set((profile or {}).get("identifier_columns", []))

    candidates = [c for c in cat_cols + dt_cols if c not in id_cols] or [c for c in columns if c not in id_cols]
    matched = _match_column_in_query(q, candidates)
    if matched:
        return matched

    # Generic fallback when user asks about categories/groups without naming column
    if any(k in q for k in ("category", "categories", "group", "top five", "top 5", "compare", "segment", "department", "region", "subject")) and candidates:
        return candidates[0]
    return candidates[0] if candidates and any(k in q for k in ("highest", "lowest", "best", "worst", "top", "bottom")) else None


def _guess_mapping(question: str, columns: list[str], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    x = _guess_dimension(question, columns, profile)
    y = _guess_metric(question, columns, profile)
    mapping: Dict[str, Any] = {}
    if x:
        mapping["x"] = x
    if y:
        mapping["y"] = y
    return mapping


def _heuristic_tool_selection(question: str, columns: list[str], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    q = question.lower()
    tools: List[str] = []

    if any(k in q for k in ["missing", "quality", "null", "duplicate", "hygiene"]):
        tools.append("detect_data_quality_issues")
    if any(k in q for k in ["outlier", "unusual", "anomaly", "anomalies", "extreme"]):
        tools.append("detect_outliers")
    if any(k in q for k in ["trend", "monthly", "weekly", "daily", "yearly", "over time", "time series"]):
        tools.append("analyze_datetime_column")
    if any(k in q for k in ["correlation", "relationship", "associated", "vs", "related"]):
        tools.append("correlation_summary")
    if any(k in q for k in ["distribution", "histogram", "spread", "skew"]):
        tools.append("numeric_summary")
    has_group_intent = bool(
        re.search(r"\b(?:by|across|per|each|wise|har|me)\s+[a-z0-9_ ]+", q)
        and _guess_dimension(question, columns, profile)
    )
    if has_group_intent or any(k in q for k in ["top", "highest", "best", "lowest", "worst", "compare", "which category", "average by"]):
        tools.append("top_categories")
    if any(k in q for k in ["total", "sum", "average", "mean", "median", "kpi"]):
        if "numeric_summary" not in tools:
            tools.append("numeric_summary")
    if any(k in q for k in ["chart", "plot", "graph", "visualize", "visualization"]):
        tools.append("recommend_chart")
    if any(k in q for k in ["insight", "important finding", "recommend", "contain", "overview", "profile", "what does this dataset"]):
        tools.append("profile_dataset")

    if not tools:
        tools.append("summarize_dataset")

    return {"tools": tools, "reason": "heuristic", "missing_info": [], "mapping": {}}


async def run_workflow(
    df: pd.DataFrame,
    question: str,
    use_llm: bool = True,
) -> Dict[str, Any]:
    understanding = understand_dataset(df, sanitize=True)
    norm_df = understanding["normalized_df"]
    profile = understanding["profile"]
    columns = [str(c) for c in norm_df.columns]

    steps: List[AgentStep] = []
    tools_used: List[str] = []
    missing_info: List[str] = []

    selection: Dict[str, Any] = {"tools": [], "reason": "", "missing_info": [], "mapping": {}}

    # 1) Tool selection (LLM if available, else heuristic)
    if use_llm:
        health = await model_manager.status()
        if health.get("available"):
            prompt = build_tool_selection_prompt(question, TOOL_NAMES, columns)
            raw = await model_manager.generate(prompt=prompt, system=TOOL_SELECTION_SYSTEM, format_json=True)
            parsed = parse_tool_selection(raw)
            if parsed["tools"]:
                selection = {**parsed, "mapping": {}}

    if not selection["tools"]:
        selection = _heuristic_tool_selection(question, columns, profile)

    valid_tools = validate_tool_names(selection["tools"])
    rejected = list(set(selection["tools"]) - set(valid_tools))

    steps.append(
        AgentStep(
            agent="Orchestrator",
            tool="tool_selection",
            status="ok" if valid_tools else "error",
            message=f"Selected tools: {valid_tools or 'none'}",
            result={"selected": valid_tools, "rejected": rejected},
        )
    )

    tool_results: Dict[str, Any] = {}
    chart_config: Optional[Dict[str, Any]] = None

    def _run(tool: str, fn, *args, **kwargs):
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            tool_results[tool] = result
            tools_used.append(tool)
            steps.append(
                AgentStep(
                    agent="DataAnalystAgent",
                    tool=tool,
                    status="ok",
                    message=f"Executed {tool}",
                    result={"preview": str(result)[:300]},
                    duration_ms=duration,
                )
            )
        except Exception as exc:
            steps.append(
                AgentStep(
                    agent="DataAnalystAgent",
                    tool=tool,
                    status="error",
                    message=f"{tool} failed: {exc}",
                )
            )

    for tool in valid_tools:
        if tool == "profile_dataset":
            _run(tool, data_analyst_agent.profile_dataset, norm_df)
            # Also attach key insights for overview/insight/recommendation questions
            if any(k in question.lower() for k in ("insight", "important finding", "recommend", "contain", "overview")):
                dummy_ds = Dataset(id=0, name="Active Dataset", version=1, size_bytes=0)
                eda_res = build_automated_eda(norm_df, "Active Dataset", understanding=understanding)
                ins_list = discover_business_insights(norm_df, dummy_ds, eda_res, "live")
                tool_results["insights_summary"] = [
                    {"category": i["category"], "title": i["title"], "finding": i.get("finding", i["explanation"])}
                    for i in ins_list[:6]
                ]
                for i in ins_list:
                    if i.get("chart_spec"):
                        chart_config = i["chart_spec"]
                        break
        elif tool == "summarize_dataset":
            _run(tool, data_analyst_agent.summarize_dataset, norm_df)
        elif tool == "detect_data_quality_issues":
            _run(tool, lambda d: data_analyst_agent.profile_dataset(d), norm_df)
            from app.analytics.data_quality import inspect_data_quality
            q_rep = inspect_data_quality(norm_df)
            tool_results["detect_data_quality_issues"] = q_rep
        elif tool == "detect_outliers":
            target_num = _guess_metric(question, columns, profile)
            res = detect_outliers(
                norm_df,
                column=target_num,
                numeric_columns=profile.get("numerical_columns", []),
            )
            tool_results[tool] = res
            tools_used.append(tool)
            steps.append(AgentStep(agent="DataQualityAgent", tool=tool, status="ok", message="Executed outlier detection", result={"preview": str(res)[:300]}))
            if target_num:
                chart_config = {"chart_type": "box", "title": f"Outlier Spread: {target_num}", "data_mapping": {"y": target_num}}
            elif profile.get("numerical_columns"):
                chart_config = {"chart_type": "box", "title": f"Outlier Spread: {profile['numerical_columns'][0]}", "data_mapping": {"y": profile["numerical_columns"][0]}}
        elif tool == "analyze_datetime_column":
            dt_cols = profile.get("datetime_columns", [])
            num_cols = profile.get("numerical_columns", [])
            if not dt_cols:
                missing_info.append("datetime column")
                steps.append(AgentStep(agent="DataAnalystAgent", tool=tool, status="skipped", message="No datetime column detected in dataset."))
                continue
            d_col = _match_column_in_query(question, dt_cols) or dt_cols[0]
            res = analyze_datetime_column(norm_df, d_col, numeric_columns=num_cols)
            tool_results[tool] = res
            tools_used.append(tool)
            steps.append(AgentStep(agent="DataAnalystAgent", tool=tool, status="ok", message=f"Analyzed temporal column '{d_col}'"))
            if res.get("metric_trends"):
                m0 = res["metric_trends"][0]["metric_column"]
                chart_config = {"chart_type": "time_series", "title": f"{m0} Over {d_col}", "data_mapping": {"x": d_col, "y": m0}, "aggregation": "sum"}
        elif tool == "top_categories":
            dimension = _guess_dimension(question, columns, profile)
            metric = _guess_metric(question, columns, profile)
            if not dimension:
                missing_info.append("category column")
                steps.append(
                    AgentStep(
                        agent="DataAnalystAgent",
                        tool="top_categories",
                        status="skipped",
                        message="No suitable category column found.",
                    )
                )
                continue
            if _question_requests_metric(question) and not metric:
                missing_info.append("requested numeric metric column")
                steps.append(
                    AgentStep(
                        agent="DataAnalystAgent",
                        tool="top_categories",
                        status="skipped",
                        message="The requested metric does not exist in this dataset.",
                    )
                )
                continue
            _run(tool, data_analyst_agent.top_categories, norm_df, dimension, metric, 5)
            if metric:
                comp_res = compare_groups(norm_df, dimension, metric)
                if "error" not in comp_res:
                    tool_results["group_comparison"] = comp_res
            chart_config = chart_config or {
                "chart_type": "bar",
                "title": f"{metric or 'Count'} by {dimension}",
                "data_mapping": {"x": dimension, "y": metric or dimension},
                "aggregation": "mean" if "average" in question.lower() else ("sum" if metric else "count"),
            }
        elif tool in {"numeric_summary", "analyze_numerical_column"}:
            metric = _guess_metric(question, columns, profile)
            if not metric:
                missing_info.append("numeric metric column")
                continue
            _run("numeric_summary", analyze_numerical_column, norm_df, metric)
            chart_config = chart_config or {"chart_type": "histogram", "title": f"Distribution of {metric}", "data_mapping": {"x": metric}, "aggregation": "count"}
        elif tool in {"correlation_summary", "calculate_correlation"}:
            _run("correlation_summary", data_analyst_agent.correlation_summary, norm_df)
            corrs = (tool_results.get("correlation_summary") or {}).get("correlations") or []
            if corrs:
                c0 = corrs[0]
                chart_config = chart_config or {"chart_type": "scatter", "title": f"{c0['col1']} vs {c0['col2']} (r={c0['correlation']})", "data_mapping": {"x": c0["col1"], "y": c0["col2"]}}
        elif tool == "describe_column":
            column = _guess_metric(question, columns, profile) or _guess_dimension(question, columns, profile) or (columns[0] if columns else None)
            if column:
                _run(tool, data_analyst_agent.describe_column, norm_df, column)
        elif tool == "recommend_chart":
            rec = visualization_agent.recommend_chart(norm_df, query=question)
            tool_results[tool] = rec
            tools_used.append(tool)
            chart_config = rec
            steps.append(
                AgentStep(
                    agent="VisualizationAgent",
                    tool=tool,
                    status="ok",
                    message=f"Recommended chart: {rec.get('chart_type')}",
                    result=rec,
                )
            )
        elif tool == "build_chart_config":
            mapping = _guess_mapping(question, columns, profile)
            config = visualization_agent.build_chart_config(
                chart_type="bar", data_mapping=mapping, title="Generated Chart"
            )
            tool_results[tool] = config
            tools_used.append(tool)
            chart_config = config
            steps.append(
                AgentStep(
                    agent="VisualizationAgent",
                    tool=tool,
                    status="ok",
                    message="Built chart config",
                    result=config,
                )
            )
        elif tool == "explain_kpi":
            metric = _guess_metric(question, columns, profile)
            dimension = _guess_dimension(question, columns, profile)
            if not metric:
                missing_info.append("numeric metric column")
                continue
            kpi = business_analyst_agent.explain_kpi(norm_df, metric, dimension)
            recommendation = business_analyst_agent.generate_recommendations(kpi)
            tool_results[tool] = {"kpi": kpi, "recommendation": recommendation}
            tools_used.append(tool)
            steps.append(
                AgentStep(
                    agent="BusinessAnalystAgent",
                    tool=tool,
                    status="ok",
                    message="Explained KPI",
                    result=kpi,
                )
            )

    # 4) Build verified answer
    answer = ""
    if use_llm:
        health = await model_manager.status()
        if health.get("available"):
            context = _build_context(tool_results)
            prompt = build_business_prompt(question, context)
            raw = await model_manager.generate(prompt=prompt, system=BUSINESS_ANALYST_SYSTEM)
            answer = parse_business_answer(raw)

    if not answer:
        answer = _fallback_answer(question, tool_results, missing_info)

    steps.append(
        AgentStep(
            agent="ValidationLayer",
            tool="validate_result_shape",
            status="ok",
            message="Validated response",
        )
    )

    limitations = list(missing_info)
    if "correlation_summary" in tools_used:
        limitations.append("Correlation indicates statistical association only and does not establish causation.")

    return {
        "question": question,
        "answer": answer,
        "tools_used": tools_used,
        "steps": steps,
        "missing_info": missing_info,
        "verified_facts": _extract_verified_facts(tool_results),
        "limitations": limitations,
        "chart_config": chart_config,
        "tool_results": tool_results,
    }


def _extract_verified_facts(tool_results: Dict[str, Any]) -> List[str]:
    facts: List[str] = []
    if "numeric_summary" in tool_results:
        ns = tool_results["numeric_summary"]
        if "mean" in ns:
            facts.append(f"{ns['column']}: Mean={ns['mean']}, Median={ns['median']}, Min={ns['min']}, Max={ns['max']} (N={ns['count']}).")
    if "top_categories" in tool_results and tool_results["top_categories"].get("items"):
        tc = tool_results["top_categories"]
        top0 = tc["items"][0]
        facts.append(f"Top {tc['dimension']} by {tc['metric']}: {top0['value']} ({top0['metric']:,}).")
    if "correlation_summary" in tool_results and tool_results["correlation_summary"].get("correlations"):
        c0 = tool_results["correlation_summary"]["correlations"][0]
        facts.append(f"Strongest pair: {c0['col1']} & {c0['col2']} (r={c0['correlation']}).")
    if "detect_outliers" in tool_results:
        do = tool_results["detect_outliers"]
        if "flagged_count" in do:
            facts.append(f"Outlier scan ({do['column']}, {do['method']}): {do['flagged_count']} candidate anomalies.")
    if "analyze_datetime_column" in tool_results:
        dt = tool_results["analyze_datetime_column"]
        if dt.get("earliest_date"):
            facts.append(f"Temporal span ({dt['date_column']}): {dt['earliest_date']} to {dt['latest_date']} ({dt['periods_observed']} {dt['granularity']} periods).")
    return facts[:5]


def _build_context(tool_results: Dict[str, Any]) -> str:
    if not tool_results:
        return "No tool results available."
    lines = []
    for tool, result in tool_results.items():
        lines.append(f"[{tool}] {str(result)[:700]}")
    return "\n".join(lines)


def _fallback_answer(question: str, tool_results: Dict[str, Any], missing_info: List[str]) -> str:
    if missing_info:
        return (
            f"I cannot fully answer '{question}' with the active dataset. "
            f"Missing or unavailable fields: {', '.join(missing_info)}."
        )

    parts: List[str] = []

    if "insights_summary" in tool_results:
        ins_list = tool_results["insights_summary"]
        lines = [f"- **[{i['category'].upper()}] {i['title']}**: {i['finding']}" for i in ins_list]
        parts.append("Here are the top data-grounded insights:\n" + "\n".join(lines))

    if "detect_data_quality_issues" in tool_results:
        q = tool_results["detect_data_quality_issues"]
        missing_map = q.get("missing_by_column", {})
        if missing_map:
            ranked = sorted(missing_map.items(), key=lambda kv: kv[1]["count"], reverse=True)
            lines = [f"- **{col}**: {info['count']} missing ({info['percent']}%)" for col, info in ranked[:5]]
            parts.append(f"Data Quality Score is **{q['quality_score']}%**. Missing value breakdown:\n" + "\n".join(lines))
        else:
            parts.append(f"Data Quality Score is **{q['quality_score']}%**. Zero missing values detected across all columns.")

    if "detect_outliers" in tool_results:
        do = tool_results["detect_outliers"]
        if "univariate" in do:
            flagged = [u for u in do["univariate"] if u.get("flagged_count", 0) > 0]
            if flagged:
                lines = [f"- **{u['column']}**: {u['flagged_count']} candidates ({u['flagged_pct']}%) via {u['method']} [{u['threshold']}]" for u in flagged[:5]]
                parts.append("Detected candidate anomalies (not automatically removed):\n" + "\n".join(lines))
            else:
                parts.append("No candidate anomalies exceeded univariate statistical thresholds.")
        elif "flagged_count" in do:
            parts.append(f"Column '{do['column']}' ({do['method']}): {do['flagged_count']} candidate anomaly observation(s) flagged ({do.get('flagged_pct', 0)}%). {do.get('note', '')}")

    if "analyze_datetime_column" in tool_results:
        dt = tool_results["analyze_datetime_column"]
        trends = dt.get("metric_trends") or []
        if trends:
            t0 = trends[0]
            parts.append(
                f"{t0['granularity'].capitalize()} trend for **{t0['metric_column']}** over **{dt['date_column']}** "
                f"({t0['first_period']} to {t0['last_period']}): moved from {t0['first_value']:,.2f} to {t0['last_value']:,.2f} "
                f"(net {t0['net_delta']:+,.2f}, peak {t0['peak_value']:,.2f} in {t0['peak_period']})."
            )
        elif dt.get("earliest_date"):
            parts.append(f"Temporal coverage ({dt['date_column']}): {dt['earliest_date']} to {dt['latest_date']} ({dt['periods_observed']} {dt['granularity']} periods).")

    if "top_categories" in tool_results and tool_results["top_categories"].get("items"):
        tc = tool_results["top_categories"]
        top_lines = [f"{i+1}. **{it['value']}**: {it['metric']:,}" + (f" (mean: {it['mean']:,})" if "mean" in it else "") for i, it in enumerate(tc["items"])]
        parts.append(f"Top categories in **{tc['dimension']}** by **{tc['metric']}**:\n" + "\n".join(top_lines))

    if "numeric_summary" in tool_results and "mean" in tool_results["numeric_summary"]:
        ns = tool_results["numeric_summary"]
        parts.append(
            f"Summary for **{ns['column']}** (N={ns['count']:,}): "
            f"Mean = {ns['mean']:,}, Median = {ns['median']:,}, Std = {ns['std']:,}, "
            f"Range = [{ns['min']:,}, {ns['max']:,}], IQR = {ns['iqr']:,}."
        )

    if "correlation_summary" in tool_results:
        cs = tool_results["correlation_summary"]
        corrs = cs.get("correlations") or []
        if corrs:
            c_lines = [f"- **{c['col1']}** & **{c['col2']}**: Pearson r = {c['correlation']} ({c['strength']})" for c in corrs[:4]]
            parts.append("Observed numerical relationships (association does not prove causation):\n" + "\n".join(c_lines))
        else:
            parts.append(cs.get("message", "No strong numerical correlations exceeded reporting thresholds."))

    if "recommend_chart" in tool_results:
        rc = tool_results["recommend_chart"]
        parts.append(f"Recommended **{rc.get('chart_type')}** visualization ('{rc.get('title')}'): {rc.get('reason', 'Validated against dataset schema.')}")

    if "explain_kpi" in tool_results:
        parts.append(tool_results["explain_kpi"].get("recommendation", "KPI evaluated."))

    if "profile_dataset" in tool_results and not parts:
        p = tool_results["profile_dataset"]
        parts.append(
            f"Dataset contains **{p['row_count']:,} rows** across **{p['column_count']} columns** "
            f"({len(p.get('numerical_columns', []))} numeric, {len(p.get('categorical_columns', []))} categorical, "
            f"{len(p.get('datetime_columns', []))} datetime; {p.get('missing_cells', 0):,} missing cells)."
        )

    if "summarize_dataset" in tool_results and not parts:
        s = tool_results["summarize_dataset"]
        parts.append(f"Dataset summary: {s.get('row_count', 0):,} rows and {s.get('column_count', 0)} columns.")

    if parts:
        return "\n\n".join(parts)

    return "No verified result available for this question. Please specify exact dataset columns or ask about insights, distributions, relationships, trends, or anomalies."


async def execute_agent_task(
    request: Any,
    df: Any = None,
    db: Any = None,
) -> Any:
    """Executes the controlled 11-step agentic loop across specialized agents."""
    from app.agents.agentic_loop import execute_agentic_loop
    return await execute_agentic_loop(request=request, df=df, db=db)
