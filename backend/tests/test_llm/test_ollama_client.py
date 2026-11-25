import pytest

from app.llm.ollama_client import OllamaClient, OllamaUnavailableError


@pytest.mark.asyncio
async def test_health_returns_dict_when_unavailable():
    client = OllamaClient(base_url="http://127.0.0.1:1", timeout=0.5)
    health = await client.health()
    assert health["available"] is False


@pytest.mark.asyncio
async def test_generate_raises_when_unavailable():
    client = OllamaClient(base_url="http://127.0.0.1:1", timeout=0.5)
    with pytest.raises(OllamaUnavailableError):
        await client.generate("hello")
