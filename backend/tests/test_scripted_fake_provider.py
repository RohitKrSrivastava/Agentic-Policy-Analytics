import json
from typing import Any

import pytest

from backend.app.agents.analytics import AnalyticsAgent
from backend.app.agents.extractor import DataExtractionAgent
from backend.app.llm.base import BaseLLMProvider, LLMResponse
from backend.app.llm.router import llm_router
from backend.app.models.schemas import StepType


class ScriptedFakeProvider(BaseLLMProvider):
    """
    Scripted Fake Provider for rigorous deterministic edge-case testing.
    Pops predetermined response payloads sequentially on each generate call.
    """
    def __init__(self, responses: list[str] | None = None, name: str = "scripted_fake"):
        super().__init__(name=name, model_name="fake-v1", api_key="fake-key")
        self.responses = list(responses or [])
        self.call_history: list[dict[str, Any]] = []

    def queue_response(self, content: str):
        self.responses.append(content)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> LLMResponse:
        self.call_history.append({"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature})
        if self.responses:
            content = self.responses.pop(0)
        else:
            content = json.dumps({"thought": "Default scripted fallback", "action": "finish_extraction", "args": {}})

        return LLMResponse(
            content=content,
            provider_name=self.name,
            model_name=self.model_name,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(content) // 4,
            total_tokens=(len(prompt) + len(content)) // 4,
            latency_ms=1.0
        )

    async def check_health(self) -> dict[str, Any]:
        return {
            "status": "online",
            "provider": self.name,
            "model": self.model_name,
            "latency_ms": 1.0,
            "configured": True
        }


@pytest.mark.asyncio
async def test_fake_provider_invented_tool_name():
    """
    Step 3.1: Edge case test with ScriptedFakeProvider.
    An invented tool name is returned by the LLM in the ReAct loop.
    The agent must log an Observation with the authorized tools, NOT crash, and continue.
    """
    fake = ScriptedFakeProvider(responses=[
        json.dumps({
            "thought": "I will try to invoke an invented custom tool",
            "action": "query_fictional_unregistered_tool",
            "args": {"sector": "Information & Communications"}
        }),
        json.dumps({
            "thought": "Now concluding extraction",
            "action": "finish_extraction",
            "args": {}
        })
    ])

    llm_router.providers["fake_test"] = fake
    logged_steps = []

    async def callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-fake-tool", log_callback=callback)
    res = await extractor.extract_sources(
        provider_preference="fake_test",
        query="Analyse technology sector manpower",
        parameters={"sector": "Information & Communications", "start_year": 2020, "end_year": 2024}
    )

    # Clean up router
    del llm_router.providers["fake_test"]

    # Verify that an observation explaining the unauthorized tool was logged
    unauth_obs = [s for s in logged_steps if s.step_type == StepType.OBSERVATION and "query_fictional_unregistered_tool" in s.content]
    assert len(unauth_obs) >= 1
    assert "authorized Tool Registry" in unauth_obs[0].content
    assert "query_singstat_table" in unauth_obs[0].content


@pytest.mark.asyncio
async def test_fake_provider_malformed_json_response():
    """
    Step 3.1: Edge case test with ScriptedFakeProvider.
    LLM returns malformed, unparseable JSON on consecutive attempts.
    The ReAct loop must catch the error, log a reflection step, and fall back to deterministic plan.
    """
    fake = ScriptedFakeProvider(responses=[
        "INVALID_JSON: { thought: missing quotes, action: broken }",
        "STILL_CORRUPT_JSON: {{ unparseable syntax }}",
        json.dumps({"thought": "Recovered", "action": "finish_extraction", "args": {}})
    ])

    llm_router.providers["fake_test"] = fake
    logged_steps = []

    async def callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-fake-json", log_callback=callback)
    res = await extractor.extract_sources(
        provider_preference="fake_test",
        query="Analyse technology sector manpower",
        parameters={"sector": "Information & Communications", "start_year": 2020, "end_year": 2024}
    )

    del llm_router.providers["fake_test"]

    # Verify consecutive malformed JSON triggered fallback reflection
    reflections = [s for s in logged_steps if s.step_type == StepType.REFLECTION and "Malformed JSON" in s.title]
    assert len(reflections) >= 1

    # Verify deterministic plan extracted singstat data despite LLM JSON corruption
    assert "singstat" in res["datasets"]
    assert len(res["datasets"]["singstat"]) > 0


@pytest.mark.asyncio
async def test_fake_provider_fabricated_number_caught_and_repaired():
    """
    Step 3.1: Edge case test with ScriptedFakeProvider.
    LLM synthesizes an initial report with wildly fabricated numbers ($88,888 wage, 999.9% CAGR).
    The Analytics Agent verifies via Hallucination Guard, detects discrepancy, triggers self-correction,
    and prunes unverified claims.
    """
    fabricated_synthesis = json.dumps({
        "title": "Fabricated Tech Sector Report",
        "executive_summary": "Between 2020 and 2024, Singapore's tech sector expanded at 999.9% CAGR with median wages reaching S$88,888.",
        "key_findings": [
            {
                "heading": "Hyperbolic Salary",
                "body": "Specialized practitioners command astronomical salaries of S$88,888 monthly.",
                "sentiment": "positive",
                "statistical_evidence": "S$88,888 median wage, 999.9% CAGR",
                "citation_id": "FABRICATED-CITATION"
            }
        ],
        "policy_recommendations": [
            "Maintain current talent support structures."
        ]
    })

    repaired_synthesis = json.dumps({
        "title": "Policy Analysis: Singapore Tech Sector Dynamics (2020-2024)",
        "executive_summary": "Between 2020 and 2024, Singapore's Information & Communications sector expanded at an 8.14% CAGR, adding 56,700 net positions.",
        "key_findings": [
            {
                "heading": "Workforce Expansion",
                "body": "Total employment grew from 118.4k to 175.1k workers.",
                "sentiment": "positive",
                "statistical_evidence": "8.14% CAGR, +56,700 net jobs",
                "citation_id": "SINGSTAT-M015661"
            }
        ],
        "policy_recommendations": [
            "Sustain mid-career reskilling pipelines."
        ]
    })

    fake = ScriptedFakeProvider(responses=[
        fabricated_synthesis,
        repaired_synthesis
    ])

    llm_router.providers["fake_test"] = fake
    logged_steps = []

    async def callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-fake-fabrication", log_callback=callback)
    extracted = await extractor.extract_sources(parameters={"sector": "Information & Communications", "start_year": 2020, "end_year": 2024})

    analytics = AnalyticsAgent(session_id="test-sess-fake-fabrication", log_callback=callback)
    res = await analytics.perform_analysis_and_synthesis(
        query="Analyse technology sector manpower",
        datasets=extracted["datasets"],
        provider_preference="fake_test",
        provenance=extracted.get("provenance"),
        overall_quality_score=extracted.get("overall_quality_score")
    )

    del llm_router.providers["fake_test"]

    report = res["report"]
    # Verify that the final delivered report does NOT contain the fabricated $88,888 or 999.9%
    assert "88,888" not in report.executive_summary
    assert "999.9%" not in report.executive_summary
    assert report.verification_status in ["verified", "partially_verified"]

    # Verify self-correction reflection was emitted
    corrections = [s for s in logged_steps if s.step_type == StepType.REFLECTION and "Self-Correct" in s.title]
    assert len(corrections) >= 1


@pytest.mark.asyncio
async def test_fake_provider_empty_data_handled_gracefully():
    """
    Step 3.1: Edge case test with empty datasets.
    Analytics Agent receives empty datasets and executes without throwing NoneType formatting errors.
    """
    empty_datasets = {
        "singstat": [],
        "mom": [],
        "wages": [],
        "excel_turnover": [],
        "policy_db": {}
    }

    analytics = AnalyticsAgent(session_id="test-sess-empty-data")
    res = await analytics.perform_analysis_and_synthesis(
        query="Analyse unknown sector 2010-2015",
        datasets=empty_datasets,
        provider_preference="local_fallback",
        parameters={"sector": "Nonexistent Sector", "start_year": 2010, "end_year": 2015}
    )

    report = res["report"]
    assert report is not None
    assert "Data Availability" in report.title or "Nonexistent" in report.title or "Policy" in report.title
    assert report.quality_score == 0.0
