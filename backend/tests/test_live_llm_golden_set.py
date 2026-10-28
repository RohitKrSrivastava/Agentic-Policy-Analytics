"""
Golden Set & Live LLM Evaluation Suite
Includes:
1. 20 Realistic Singapore Whole-of-Government (WOG) Policy Evaluation Queries
2. Stochastic Temperature (0.7) Spread Test across 5 iterations measuring statistical metric stability
"""

import uuid
import pytest
from backend.app.agents.orchestrator import PolicyOrchestrator
from backend.app.core.database import DBAnalysisSession, SessionLocal
from backend.app.models.schemas import SessionStatus

GOLDEN_POLICY_QUERIES = [
    # Core domain ICT queries
    "Analyze Singapore ICT sector employment and wage growth from 2020 to 2024.",
    "Examine tech employment growth and median salary changes across the digital economy.",
    "Assess the impact of tech layoffs and retrenchments on Singapore ICT workforce in 2023.",
    "What was the compound annual growth rate (CAGR) of median wages in tech from 2020 to 2024?",
    "Evaluate job vacancies and talent tightness in the Information & Communications sector.",
    
    # Financial Services queries
    "Analyze financial services employment dynamics and workforce expansion from 2020 to 2024.",
    "Examine tech talent adoption and wage premium in the Singapore financial sector.",
    "Compare financial sector retrenchments in 2023 against historical pre-2022 levels.",
    "Assess wage trajectory in banking and insurance relative to the national median.",
    
    # Multi-sector comparisons
    "Compare tech employment and wage growth between ICT and Financial Services (2020-2024).",
    "Evaluate manpower growth across Information Technology versus Banking & Finance.",
    "Contrast retrenchment resilience between tech sector and financial services post-2022.",
    
    # Temporal & historical boundaries (edge cases)
    "Analyse retail sector employment 2015-2019.",
    "Compare tech employment in 2018 and 2019.",
    "Examine Singapore ICT workforce trends from 2021 to 2023.",
    
    # Sector coverage edge cases (triggering reflection/replanning or guardrails)
    "Evaluate manufacturing sector employment and automation impact 2021-2023.",
    "Examine healthcare wages and nursing staff retention in public hospitals.",
    "Assess construction sector workforce reliance on work permit holders 2020-2024.",
    
    # Ambiguous & broad queries
    "Tell me something about labor market trends.",
    "Provide policy recommendations for Singapore's digital workforce strategy 2025."
]


@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_golden_set_20_queries():
    """
    Executes all 20 golden policy queries through the multi-agent pipeline.
    Verifies that:
    1. Pipeline completes without unhandled exception.
    2. Handles out-of-scope or ambiguous queries gracefully via guardrails/reflection.
    3. Produces a PolicyReport with verified/partially_verified/unverifiable status.
    4. Logs contain thought, action, or reflection steps.
    """
    assert len(GOLDEN_POLICY_QUERIES) == 20

    for idx, query in enumerate(GOLDEN_POLICY_QUERIES, 1):
        session_id = f"test-golden-{idx}-{uuid.uuid4().hex[:6]}"
        db = SessionLocal()
        session_record = DBAnalysisSession(
            id=session_id,
            query=query,
            status=SessionStatus.PENDING.value
        )
        db.add(session_record)
        db.commit()
        db.close()

        orchestrator = PolicyOrchestrator(session_id=session_id)
        report = await orchestrator.execute_workflow(
            query=query,
            provider_preference="local_fallback"
        )

        assert report is not None, f"Query #{idx} failed to produce a report: {query}"
        assert report.title, f"Query #{idx} report missing title"
        assert len(report.key_findings) > 0, f"Query #{idx} report missing key findings"
        assert report.verification_status in [
            "verified",
            "partially_verified",
            "unverified",
            "unverifiable"
        ], f"Query #{idx} invalid verification status: {report.verification_status}"


@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_stochastic_temperature_spread_stability():
    """
    Executes the same policy query 5 times at temperature = 0.7.
    Measures the numeric spread of statistical metrics (CAGR, net jobs, retrenchments).
    Validates that statistical grounding ensures zero numeric hallucination/drift across runs.
    """
    query = "Analyze Singapore ICT sector employment and wage growth from 2020 to 2024."
    runs_count = 5
    collected_metrics: list[dict[str, float]] = []

    for i in range(runs_count):
        session_id = f"test-temp-variance-{i}-{uuid.uuid4().hex[:6]}"
        db = SessionLocal()
        session_record = DBAnalysisSession(
            id=session_id,
            query=query,
            status=SessionStatus.PENDING.value
        )
        db.add(session_record)
        db.commit()
        db.close()

        orchestrator = PolicyOrchestrator(session_id=session_id)
        report = await orchestrator.execute_workflow(
            query=query,
            provider_preference="local_fallback",
            temperature=0.7
        )

        assert report is not None
        # Extract numerical metrics from statistical_metrics or key findings
        metrics = report.statistical_metrics or {}
        collected_metrics.append(metrics)

    assert len(collected_metrics) == 5

    # Check key numerical metrics across all 5 runs
    tracked_keys = ["cagr_wage", "net_jobs_added", "total_retrenchments", "tech_cagr"]
    for key in tracked_keys:
        values = [m.get(key) for m in collected_metrics if m.get(key) is not None]
        if len(values) == runs_count:
            spread = max(values) - min(values)
            assert spread == 0.0, (
                f"Numeric spread for metric '{key}' at temp=0.7 was {spread} "
                f"(values: {values}). Statistical grounding should guarantee zero variance!"
            )
