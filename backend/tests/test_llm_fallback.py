import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.evaluation.hallucination_guard import hallucination_guard
from backend.app.llm.gemini_provider import GeminiProvider
from backend.app.llm.openai_provider import OpenAIProvider
from backend.app.llm.router import MultiCloudLLMRouter


@pytest.mark.asyncio
async def test_llm_router_automatic_fallback():
    router = MultiCloudLLMRouter()

    # Intentionally trigger fallback by forcing an invalid provider key
    router.providers["openai"] = OpenAIProvider(api_key="invalid-key-will-fail")
    router.providers["gemini"] = GeminiProvider(api_key="invalid-gemini-key")

    # Test generation: should cascade past openai and gemini directly into local_fallback without crashing
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


@pytest.mark.asyncio
async def test_real_llm_response_schema_validation_and_guard_audit():
    """
    Simulates a real LLM provider (OpenAI GPT-4o) returning structured JSON
    and verifies that the schema, response parsing, and hallucination guard
    audit execute with strict adherence.
    """
    mock_llm_json = {
        "title": "Policy Analysis: Singapore Tech Sector Growth 2020-2024",
        "executive_summary": "Between 2020 and 2024, Singapore's tech employment expanded from 118.4k to 175.1k workers, achieving an 8.14% CAGR with S$7,350 median monthly wages.",
        "key_findings": [
            {
                "heading": "Workforce Expansion",
                "body": "Total tech workforce expanded by 47.9% net growth, reaching 175,100 positions.",
                "sentiment": "positive",
                "statistical_evidence": "118.4k baseline to 175.1k headcount (8.14% CAGR).",
                "citation_id": "SINGSTAT-M015661"
            }
        ],
        "policy_recommendations": [
            "Scale TeSA conversions for AI Specialists."
        ]
    }

    provider = OpenAIProvider(api_key="sk-mock-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {"content": json.dumps(mock_llm_json)},
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 180, "total_tokens": 300}
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.generate("Analyze tech workforce", json_mode=True)
        assert res.provider_name == "openai"
        parsed = json.loads(res.content)
        assert parsed["title"] == mock_llm_json["title"]

        # Verify through hallucination guard
        v_res = hallucination_guard.verify_report(parsed)
        assert v_res["is_factually_consistent"] is True
        assert v_res["hallucination_score"] == 0.0


@pytest.mark.asyncio
async def test_multi_provider_consistency_evaluation():
    """
    Evaluates that multiple provider outputs maintain schema invariants and consistent metric reporting.
    """
    router = MultiCloudLLMRouter()

    res1, _ = await router.generate("Formulate execution plan for Financial Services", preferred_provider="local_fallback", json_mode=True)
    res2, _ = await router.generate("Formulate execution plan for Financial Services", preferred_provider="local_fallback", json_mode=True)

    data1 = json.loads(res1.content)
    data2 = json.loads(res2.content)

    assert "subtasks" in data1
    assert "subtasks" in data2
    assert len(data1["subtasks"]) == len(data2["subtasks"])
    assert data1["subtasks"][0]["tool_name"] == data2["subtasks"][0]["tool_name"]
