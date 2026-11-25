import asyncio
from typing import Any, AsyncGenerator, Dict, List

from app.core.config import settings
from app.llm.ollama_client import OllamaClient, OllamaUnavailableError, ollama_client


class ModelManager:
    def __init__(self, client: OllamaClient | None = None):
        self.client = client or ollama_client
        self._semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT_REQUESTS)

    async def status(self) -> Dict[str, Any]:
        health = await self.client.health()
        active = settings.DEFAULT_MODEL
        available = active in health.get("models", []) or any(
            m.get("name", "").startswith(active.split(":")[0]) for m in health.get("models", [])
        )
        return {
            "available": health.get("available", False),
            "active_model": active,
            "active_model_installed": available,
            "installed_models": health.get("models", []),
            "error": health.get("error"),
        }

    async def list_models(self) -> List[str]:
        return await self.client.list_models()

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        format_json: bool | Dict[str, Any] = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        try:
            async with self._semaphore:
                return await self.client.generate(
                    prompt=prompt, system=system, format_json=format_json,
                    temperature=temperature, max_tokens=max_tokens,
                )
        except OllamaUnavailableError:
            return ""

    async def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        try:
            async with self._semaphore:
                async for chunk in self.client.generate_stream(
                    prompt=prompt, system=system,
                    temperature=temperature, max_tokens=max_tokens,
                ):
                    yield chunk
        except OllamaUnavailableError:
            return

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        try:
            async with self._semaphore:
                async for chunk in self.client.chat_stream(
                    messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                ):
                    yield chunk
        except OllamaUnavailableError:
            return


model_manager = ModelManager()
