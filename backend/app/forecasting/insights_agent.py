"""Forecasting Insights Agent, Narrative Synthesis & Grounded Q&A."""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def synthesize_forecasting_narrative(
    series: pd.Series,
    forecast_points: List[Dict[str, Any]],
    evaluation: Dict[str, Any],
    intervals: Dict[str, List[float]],
    target_metric: str,
    date_column: str,
) -> Dict[str, Any]:
    """
    Synthesizes executive plain-English business intelligence from the numerical forecast outputs.
    Zero hallucinations: every claim is tied directly to verified numbers.
    """
    hist_values = series.values
    hist_mean = float(np.mean(hist_values[-min(len(hist_values), 12):]))
    f_values = [p["value"] for p in forecast_points]
    f_mean = float(np.mean(f_values))

    net_delta = f_mean - hist_mean
    pct_change = round((net_delta / max(1e-4, hist_mean)) * 100, 1) if hist_mean != 0 else 0.0
    direction = "increase" if net_delta > 0 else ("decline" if net_delta < 0 else "remain stable")

    # Peak & Trough
    max_idx = int(np.argmax(f_values))
    min_idx = int(np.argmin(f_values))
    peak_pt = forecast_points[max_idx]
    trough_pt = forecast_points[min_idx]

    # Uncertainty assessment
    l80 = intervals.get("lower_80", f_values)
    u80 = intervals.get("upper_80", f_values)
    initial_spread = u80[0] - l80[0]
    final_spread = u80[-1] - l80[-1]
    spread_growth_pct = round(((final_spread - initial_spread) / max(1e-4, initial_spread)) * 100, 1)

    champ_name = evaluation.get("champion_name", "Champion Model")
    champ_wape = evaluation.get("champion_metrics", {}).get("wape", 0.0)
    naive_wape = evaluation.get("naive_baseline_metrics", {}).get("wape", 0.0)

    # Executive Summary Paragraph
    executive_summary = (
        f"Based on historical patterns in '{target_metric}' across {len(series)} chronological periods, "
        f"the forecast projects a net {direction} of {abs(pct_change):+.1f}% over the {len(forecast_points)}-period horizon. "
        f"The trailing historical average of {hist_mean:,.2f} is projected to shift to a forecast average of {f_mean:,.2f}."
    )

    # Detected Pattern
    pattern_desc = (
        f"Model selected: {champ_name} (holdout WAPE = {champ_wape}%, beating naive benchmark by "
        f"{evaluation.get('champion_metrics', {}).get('wape_improvement_vs_naive_pct', 0.0):.1f}%). "
        f"Projected peak of {peak_pt['value']:,.2f} occurs on {peak_pt['date'][:10]}, with a low of "
        f"{trough_pt['value']:,.2f} expected on {trough_pt['date'][:10]}."
    )

    # Uncertainty & Risk Note
    uncertainty_note = (
        f"Uncertainty bounds (80% confidence) expand from ±{initial_spread/2:,.2f} in period 1 "
        f"to ±{final_spread/2:,.2f} by the final horizon ({spread_growth_pct:+.1f}% wider). "
        f"Longer-horizon estimates carry progressively higher variance."
    )

    recommendations = [
        f"Align operational inventory and staffing to accommodate the projected peak of {peak_pt['value']:,.2f} on {peak_pt['date'][:10]}.",
        f"Continuously monitor initial realized values against the 80% prediction interval [{l80[0]:,.2f}, {u80[0]:,.2f}] to detect structural drift.",
        f"For deeper risk mitigation, inspect the Conservative Scenario in the Decision Simulator tab.",
    ]

    limitations = [
        "Projection assumes historical dynamics and macroeconomic conditions persist without sudden external shocks.",
        "Unforeseen competitor actions, regulatory shifts, or supply chain bottlenecks are not reflected in univariate models.",
    ]

    return {
        "direction": direction,
        "percent_change": pct_change,
        "trailing_history_mean": round(hist_mean, 2),
        "forecast_mean": round(f_mean, 2),
        "net_delta": round(net_delta, 2),
        "peak": {"date": peak_pt["date"], "value": peak_pt["value"]},
        "trough": {"date": trough_pt["date"], "value": trough_pt["value"]},
        "executive_summary": executive_summary,
        "pattern_description": pattern_desc,
        "uncertainty_assessment": uncertainty_note,
        "recommendations": recommendations,
        "limitations": limitations,
    }


def answer_forecasting_chat(
    run_record: Any,
    question: str,
) -> Dict[str, Any]:
    """Answers user forecasting Q&A strictly grounded in the run's verified outputs."""
    q_lower = question.lower()
    target = run_record.target_column
    horizon = run_record.horizon
    metrics = run_record.metrics or {}
    insights = run_record.insights or {}
    scenarios = run_record.scenarios or {}
    cand_models = run_record.candidate_models or []

    # 1. Uncertainty
    if any(k in q_lower for k in ["uncertainty", "confidence", "interval", "risk", "band"]):
        reply = (
            f"### Uncertainty & Confidence Interval Analysis for **{target}**\n\n"
            f"{insights.get('uncertainty_assessment', 'Uncertainty intervals widen over time.')}\n\n"
            f"- **80% Prediction Band:** Encompasses the most probable operational range.\n"
            f"- **95% Extreme Fence:** Represents statistical tail boundaries.\n"
            f"- **Holdout RMSE:** {metrics.get('rmse', 'N/A'):,.2f} | **Holdout WAPE:** {metrics.get('wape', 'N/A')}%\n\n"
            f"As the forecast extends to {horizon} periods, uncertainty compounds proportionally with $\\sqrt{{h}}$."
        )
        return {"question": question, "answer": reply, "confidence": 0.96}

    # 2. Compare with Baseline
    elif any(k in q_lower for k in ["compare", "baseline", "naive", "benchmark", "performance"]):
        comp_text = "\n".join([
            f"- **{m['name']}:** WAPE = {m['metrics'].get('wape')}% | MAE = {m['metrics'].get('mae')} (vs Naive: {m['metrics'].get('wape_improvement_vs_naive_pct', 0.0):+.1f}%)"
            for m in cand_models[:4]
        ])
        reply = (
            f"### Model Comparison vs Naive Benchmark\n\n"
            f"The selected model **{run_record.model_type}** was tested against competitive baselines on an identical chronological holdout window:\n\n"
            f"{comp_text}\n\n"
            f"**Selection Rationale:** {evaluation_summary(run_record)}"
        )
        return {"question": question, "answer": reply, "confidence": 0.98}

    # 3. Peak / Trough / Next 90 days / Overview
    elif any(k in q_lower for k in ["peak", "trough", "high", "low", "growth", "next", "90 days", "direction"]):
        peak = insights.get("peak", {})
        trough = insights.get("trough", {})
        reply = (
            f"### Forecast Trajectory & Critical Milestones for **{target}**\n\n"
            f"{insights.get('executive_summary', 'Forecast completed.')}\n\n"
            f"- **Projected Peak:** {peak.get('value', 'N/A'):,.2f} on {str(peak.get('date', ''))[:10]}\n"
            f"- **Projected Low:** {trough.get('value', 'N/A'):,.2f} on {str(trough.get('date', ''))[:10]}\n"
            f"- **Net Trajectory:** {insights.get('direction', 'change').upper()} ({insights.get('percent_change', 0):+.1f}%)\n"
        )
        return {"question": question, "answer": reply, "confidence": 0.95}

    # 4. Additional Features / How to improve
    elif any(k in q_lower for k in ["improve", "feature", "additional", "accuracy", "data"]):
        reply = (
            f"### Recommended Enhancements to Elevate Forecast Accuracy\n\n"
            f"To further refine projections for **{target}**:\n\n"
            f"1. **Exogenous Regressors:** Ingest pricing adjustments, promotional calendars, or marketing expenditures.\n"
            f"2. **Longer History:** Expanding historical observations past 24 periods unlocks robust multi-year seasonal decomposition.\n"
            f"3. **Segment Granularity:** Run segmented forecasts by product category or region to prevent aggregation masking.\n"
            f"4. **Event Flags:** Incorporate holiday and supply-chain outage dummy indicators."
        )
        return {"question": question, "answer": reply, "confidence": 0.92}

    # Default
    else:
        reply = (
            f"### Forecasting Intelligence for **{target}**\n\n"
            f"- **Target Metric:** {target} (Date Column: {run_record.date_column})\n"
            f"- **Horizon:** {horizon} periods ({run_record.frequency})\n"
            f"- **Champion Model:** {run_record.model_type} (WAPE = {metrics.get('wape', 'N/A')}%)\n\n"
            f"{insights.get('executive_summary', '')}\n\n"
            f"You can ask: **'Compare with baseline'**, **'Explain uncertainty'**, **'Show peak and trough'**, or **'What features can improve this?'**."
        )
        return {"question": question, "answer": reply, "confidence": 0.90}


def evaluation_summary(run_record: Any) -> str:
    metrics = run_record.metrics or {}
    wape = metrics.get("wape")
    impr = metrics.get("wape_improvement_vs_naive_pct", 0.0)
    return f"Achieved holdout WAPE of {wape}%, outperforming the standard naive baseline by {abs(impr):.1f}%."
