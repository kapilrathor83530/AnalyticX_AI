"""Business Decision Scenario Forecasting Module."""
from typing import Any, Dict, List, Optional
import numpy as np


def generate_forecast_scenarios(
    forecast_values: List[float],
    intervals: Dict[str, List[float]],
    target_metric: str,
    custom_assumptions: Optional[Dict[str, Any]] = None,
    is_non_negative: bool = True,
) -> Dict[str, Any]:
    """
    Computes comparative business scenarios:
    1. Baseline Scenario: The statistical model's point estimate.
    2. Optimistic Scenario: Upper 80% prediction interval combined with favorable market momentum (+5%).
    3. Pessimistic Scenario: Lower 80% prediction interval combined with market headwind (-5%).
    4. Custom Scenario: User-defined assumptions (price adjustments, marketing budget, growth factor).
    """
    n = len(forecast_values)
    baseline = [round(float(v), 2) for v in forecast_values]
    u80 = intervals.get("upper_80", baseline)
    l80 = intervals.get("lower_80", baseline)

    # 1. Optimistic Scenario (Upper Bound + 5% positive market drift)
    optimistic = []
    for step, (val, upper) in enumerate(zip(baseline, u80)):
        drift = 1.0 + (0.05 * (step + 1) / max(1, n))
        opt_val = max(val, upper) * drift
        optimistic.append(round(float(opt_val), 2))

    # 2. Pessimistic Scenario (Lower Bound - 5% downside headwind)
    pessimistic = []
    for step, (val, lower) in enumerate(zip(baseline, l80)):
        drift = max(0.0, 1.0 - (0.05 * (step + 1) / max(1, n)))
        pes_val = min(val, lower) * drift
        if is_non_negative:
            pes_val = max(0.0, pes_val)
        pessimistic.append(round(float(pes_val), 2))

    # 3. Custom What-If Scenario
    custom_assumptions = custom_assumptions or {}
    growth_pct = float(custom_assumptions.get("growth_rate_pct", 0.0))
    price_pct = float(custom_assumptions.get("price_change_pct", 0.0))
    elasticity = float(custom_assumptions.get("price_elasticity", -1.2))
    mktg_pct = float(custom_assumptions.get("marketing_budget_pct", 0.0))
    mktg_elasticity = float(custom_assumptions.get("marketing_elasticity", 0.35))

    # Calculate net multiplier
    # Growth effect: (1 + growth_pct / 100)
    # Price effect via elasticity: (1 + elasticity * (price_pct / 100))
    # Marketing effect: (1 + mktg_elasticity * (mktg_pct / 100))
    growth_mult = 1.0 + (growth_pct / 100.0)
    price_mult = max(0.1, 1.0 + elasticity * (price_pct / 100.0))
    mktg_mult = max(0.1, 1.0 + mktg_elasticity * (mktg_pct / 100.0))
    net_multiplier = growth_mult * price_mult * mktg_mult

    custom_values = []
    for val in baseline:
        c_val = val * net_multiplier
        if is_non_negative:
            c_val = max(0.0, c_val)
        custom_values.append(round(float(c_val), 2))

    base_sum = sum(baseline)
    opt_sum = sum(optimistic)
    pes_sum = sum(pessimistic)
    cust_sum = sum(custom_values)

    return {
        "target_metric": target_metric,
        "scenarios": {
            "baseline": {
                "name": "Statistical Baseline",
                "description": "Pure statistical point forecast from champion model with 0 external assumptions.",
                "values": baseline,
                "total": round(base_sum, 2),
                "delta_vs_baseline": 0.0,
                "delta_pct_vs_baseline": 0.0,
            },
            "optimistic": {
                "name": "Optimistic Case (+80% Upper Bound + Momentum)",
                "description": "Favorable market conditions tracking the 80% upper prediction interval.",
                "values": optimistic,
                "total": round(opt_sum, 2),
                "delta_vs_baseline": round(opt_sum - base_sum, 2),
                "delta_pct_vs_baseline": round(((opt_sum - base_sum) / max(1e-4, base_sum)) * 100, 1),
            },
            "pessimistic": {
                "name": "Conservative / Risk Case (80% Lower Bound)",
                "description": "Adverse market contraction tracking the 80% lower uncertainty fence.",
                "values": pessimistic,
                "total": round(pes_sum, 2),
                "delta_vs_baseline": round(pes_sum - base_sum, 2),
                "delta_pct_vs_baseline": round(((pes_sum - base_sum) / max(1e-4, base_sum)) * 100, 1),
            },
            "custom": {
                "name": "User What-If Simulation",
                "description": (
                    f"Assumptions applied: Growth = {growth_pct:+g}%, Price = {price_pct:+g}% (Elasticity {elasticity}), "
                    f"Marketing = {mktg_pct:+g}% (Elasticity {mktg_elasticity})."
                ),
                "assumptions": {
                    "growth_rate_pct": growth_pct,
                    "price_change_pct": price_pct,
                    "price_elasticity": elasticity,
                    "marketing_budget_pct": mktg_pct,
                    "marketing_elasticity": mktg_elasticity,
                    "net_demand_multiplier": round(net_multiplier, 3),
                },
                "values": custom_values,
                "total": round(cust_sum, 2),
                "delta_vs_baseline": round(cust_sum - base_sum, 2),
                "delta_pct_vs_baseline": round(((cust_sum - base_sum) / max(1e-4, base_sum)) * 100, 1),
            },
        },
    }
