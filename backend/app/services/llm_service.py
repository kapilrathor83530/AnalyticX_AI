from typing import Any, Dict, List

from app.llm.model_manager import model_manager
from app.llm.prompt_templates import BUSINESS_ANALYST_SYSTEM, CHART_COMMAND_SYSTEM, build_business_prompt, build_chart_command_prompt
from app.llm.ollama_client import OllamaUnavailableError
from app.llm.response_parser import parse_business_answer, parse_chart_command
from app.visualization.chart_registry import list_charts


async def chat(messages: List[Dict[str, str]], context: str | None = None, temperature: float = 0.2) -> Dict[str, Any]:
    status = await model_manager.status()
    if not status.get("available"):
        return {
            "answer": "Local LLM is not available. Please start Ollama and pull the default model.",
            "model": status.get("active_model", ""),
            "available": False,
            "error": status.get("error"),
        }

    full_messages = [{"role": "system", "content": BUSINESS_ANALYST_SYSTEM}]
    if context:
        full_messages.append({"role": "system", "content": f"Context:\n{context}"})
    full_messages.extend(messages)

    try:
        answer = await model_manager.client.chat(full_messages, temperature=temperature)
    except OllamaUnavailableError as exc:
        return {"answer": "", "model": status["active_model"], "available": False, "error": str(exc)}

    return {"answer": parse_business_answer(answer), "model": status["active_model"], "available": True}


async def parse_command(command: str, columns: List[str]) -> Dict[str, Any]:
    status = await model_manager.status()
    if not status.get("available"):
        return {
            "action": "unknown",
            "chart_type": None,
            "data_mapping": {},
            "value": None,
            "clarification_needed": True,
            "clarification_question": "Local LLM is not available. Please start Ollama.",
            "available": False,
        }

    chart_ids = [c.id for c in list_charts()]
    prompt = build_chart_command_prompt(command, columns, chart_ids)
    raw = await model_manager.generate(prompt=prompt, system=CHART_COMMAND_SYSTEM, format_json=True)
    parsed = parse_chart_command(raw)
    parsed["available"] = True
    return parsed
