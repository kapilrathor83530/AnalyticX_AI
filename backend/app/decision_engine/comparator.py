from typing import Any, Dict, List


def compare_scenarios(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not scenarios:
        return {"error": "No scenarios provided"}

    keys = set()
    for scenario in scenarios:
        keys.update(scenario.get("scenario", {}).keys())

    comparison: Dict[str, Any] = {"metrics": {}, "scenarios": []}

    for scenario in scenarios:
        comparison["scenarios"].append(
            {
                "id": scenario.get("id"),
                "name": scenario.get("name"),
                "scenario": scenario.get("scenario", {}),
            }
        )

    for key in keys:
        row = {}
        for scenario in scenarios:
            row[scenario.get("name", str(scenario.get("id")))] = scenario.get("scenario", {}).get(key)
        comparison["metrics"][key] = row

    return comparison
