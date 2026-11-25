import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.core.config import settings


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT_SECONDS

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return {"available": True, "models": response.json().get("models", [])}
        except Exception as exc:
            return {"available": False, "error": str(exc), "models": []}

    async def list_models(self) -> List[str]:
        health = await self.health()
        return [m.get("name", "") for m in health.get("models", []) if m.get("name")]

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        format_json: bool | Dict[str, Any] = False,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model or settings.DEFAULT_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": settings.LLM_ENABLE_THINKING,
            "keep_alive": settings.LLM_KEEP_ALIVE,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": settings.LLM_CONTEXT_TOKENS,
            },
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = format_json if isinstance(format_json, dict) else "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"Ollama request failed: {exc}") from exc

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        payload: Dict[str, Any] = {
            "model": model or settings.DEFAULT_MODEL,
            "prompt": prompt,
            "stream": True,
            "think": settings.LLM_ENABLE_THINKING,
            "keep_alive": settings.LLM_KEEP_ALIVE,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": settings.LLM_CONTEXT_TOKENS,
            },
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                            if data.get("done", False):
                                break
                        except Exception:
                            continue
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"Ollama stream failed: {exc}") from exc

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        format_json: bool | Dict[str, Any] = False,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model or settings.DEFAULT_MODEL,
            "messages": messages,
            "stream": False,
            "think": settings.LLM_ENABLE_THINKING,
            "keep_alive": settings.LLM_KEEP_ALIVE,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": settings.LLM_CONTEXT_TOKENS,
            },
        }
        if format_json:
            payload["format"] = format_json if isinstance(format_json, dict) else "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"Ollama chat failed: {exc}") from exc

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        payload: Dict[str, Any] = {
            "model": model or settings.DEFAULT_MODEL,
            "messages": messages,
            "stream": True,
            "think": settings.LLM_ENABLE_THINKING,
            "keep_alive": settings.LLM_KEEP_ALIVE,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": settings.LLM_CONTEXT_TOKENS,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                            if data.get("done", False):
                                break
                        except Exception:
                            continue
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"Ollama chat stream failed: {exc}") from exc


ollama_client = OllamaClient()
