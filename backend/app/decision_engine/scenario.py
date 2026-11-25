from typing import Any, Dict, List

from app.analytics.profiling import to_python
from app.decision_engine.baseline import compute_baseline


def apply_adjustments(
    baseline: Dict[str, Any],
    adjustments: List[Dict[str, Any]],
    elasticity: float | None = None,
) -> Dict[str, Any]:
    totals = dict(baseline.get("totals", {}))
    means = dict(baseline.get("means", {}))
    applied: List[Dict[str, Any]] = []

    for adj in adjustments:
        field = adj.get("field")
        mode = adj.get("mode", "percent")
        value = float(adj.get("value", 0))

        if mode == "percent":
            factor = 1 + value / 100
        elif mode == "absolute":
            factor = None
        else:
            continue

        if field in totals and totals[field] is not None:
            if factor is not None:
                totals[field] = totals[field] * factor
            else:
                totals[field] = totals[field] + value
            applied.append({"field": field, "mode": mode, "value": value})
        elif field in means and means[field] is not None:
            if factor is not None:
                means[field] = means[field] * factor
            else:
                means[field] = means[field] + value
            applied.append({"field": field, "mode": mode, "value": value})

    revenue = totals.get("revenue")
    cost = totals.get("cost")

    # Price elasticity handling for revenue (if price adjusted and elasticity provided)
    if elasticity is not None:
        for adj in adjustments:
            if adj.get("field") == "price":
                pct_change = adj.get("value", 0) / 100 if adj.get("mode") == "percent" else 0
                volume_change = elasticity * pct_change
                if revenue is not None:
                    totals["revenue"] = revenue * (1 + pct_change) * (1 + volume_change)
                    revenue = totals["revenue"]
                if cost is not None:
                    totals["cost"] = cost * (1 + volume_change)
                    cost = totals["cost"]

    if revenue is not None and cost is not None:
        totals["profit"] = revenue - cost
        totals["margin_percent"] = (revenue - cost) / revenue * 100 if revenue else None

    return {
        "totals": {k: to_python(v) for k, v in totals.items()},
        "means": {k: to_python(v) for k, v in means.items()},
        "applied_adjustments": applied,
    }


def run_scenario(
    baseline: Dict[str, Any],
    adjustments: List[Dict[str, Any]],
    elasticity: float | None = None,
) -> Dict[str, Any]:
    scenario = apply_adjustments(baseline, adjustments, elasticity=elasticity)

    diffs: Dict[str, Any] = {}
    for key, new_value in scenario["totals"].items():
        old_value = baseline["totals"].get(key)
        if old_value is None or new_value is None:
            continue
        diff = new_value - old_value
        pct = (diff / old_value * 100) if old_value else None
        diffs[key] = {
            "baseline": to_python(old_value),
            "scenario": to_python(new_value),
            "diff": to_python(diff),
            "diff_percent": to_python(pct),
        }

    return {
        "scenario": scenario["totals"],
        "baseline": baseline.get("totals", {}),
        "differences": diffs,
        "applied_adjustments": scenario["applied_adjustments"],
    }
