import json
import re
from typing import Any, Dict, Optional


JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = JSON_BLOCK_RE.search(text)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def parse_tool_selection(text: str) -> Dict[str, Any]:
    data = extract_json(text) or {}
    tools = data.get("tools") or []
    if not isinstance(tools, list):
        tools = []
    return {
        "tools": [str(t) for t in tools],
        "reason": str(data.get("reason") or ""),
        "missing_info": [str(m) for m in (data.get("missing_info") or [])],
    }


def parse_chart_command(text: str) -> Dict[str, Any]:
    data = extract_json(text) or {}
    mapping = data.get("data_mapping") or {}
    if not isinstance(mapping, dict):
        mapping = {}

    return {
        "action": str(data.get("action") or "unknown"),
        "chart_type": data.get("chart_type"),
        "data_mapping": {str(k): v for k, v in mapping.items() if v},
        "value": data.get("value"),
        "clarification_needed": bool(data.get("clarification_needed")),
        "clarification_question": data.get("clarification_question"),
    }


def parse_business_answer(text: str) -> str:
    return (text or "").strip()
