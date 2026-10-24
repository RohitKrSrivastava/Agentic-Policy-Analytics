import pytest
from backend.app.llm.router import MultiCloudLLMRouter
from backend.app.llm.openai_provider import OpenAIProvider
from backend.app.llm.gemini_provider import GeminiProvider

@pytest.mark.asyncio
async def test_llm_router_automatic_fallback():
    router = MultiCloudLLMRouter()
    
    # Intentionally trigger fallback by forcing an invalid provider key
    router.providers["openai"] = OpenAIProvider(api_key="invalid-key-will-fail")
    router.providers["gemini"] = GeminiProvider(api_key="invalid-gemini-key")
    
    # Test generation: should cascade past openai and gemini directly into local_fallback without crashing!
    response, attempted = await router.generate(
        prompt="Synthesize policy analysis",
        preferred_provider="openai"
    )

    assert response is not None
    assert response.provider_name == "local_fallback"
    assert response.fallback_used is True
    assert "openai" in attempted
    assert "local_fallback" in attempted

@pytest.mark.asyncio
async def test_llm_providers_health_check():
    router = MultiCloudLLMRouter()
    health = await router.get_providers_health()
    
    assert len(health) >= 4
    provider_names = [p.provider_name for p in health]
    assert "openai" in provider_names
    assert "gemini" in provider_names
    assert "bedrock" in provider_names
    assert "local_fallback" in provider_names
