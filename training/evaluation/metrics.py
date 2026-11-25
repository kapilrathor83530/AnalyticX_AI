"""Structured tool-selection accuracy and JSON validity metrics."""
import json
import re
from typing import Any, Dict, List


JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        match = JSON_BLOCK.search(text)
        if not match:
            return False
        try:
            json.loads(match.group(0))
            return True
        except json.JSONDecodeError:
            return False


def tool_selection_accuracy(predictions: List[Dict[str, Any]]) -> float:
    correct = 0
    for item in predictions:
        expected = set(item.get("expected_tools", []))
        actual = set(item.get("actual_tools", []))
        if expected == actual:
            correct += 1
    return correct / max(len(predictions), 1)


def json_validity_rate(outputs: List[str]) -> float:
    if not outputs:
        return 0.0
    return sum(is_valid_json(o) for o in outputs) / len(outputs)
