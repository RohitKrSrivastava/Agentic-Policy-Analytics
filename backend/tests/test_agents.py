import pytest
from backend.app.agents.coordinator import DataCoordinatorAgent
from backend.app.agents.extractor import DataExtractionAgent
from backend.app.agents.analytics import AnalyticsAgent
from backend.app.models.schemas import StepType

@pytest.mark.asyncio
async def test_coordinator_agent_planning():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    coordinator = DataCoordinatorAgent(session_id="test-sess-01", log_callback=dummy_callback)
    plan_res = await coordinator.plan_research_workflow("Analyse employment trends in the technology sector from 2020-2024")

    assert "plan" in plan_res
    assert len(plan_res["plan"]["subtasks"]) >= 3
    assert len(logged_steps) >= 3
    assert any(s.step_type == StepType.THOUGHT for s in logged_steps)
    assert any(s.step_type == StepType.ACTION for s in logged_steps)
    assert any(s.step_type == StepType.OBSERVATION for s in logged_steps)

@pytest.mark.asyncio
async def test_extraction_agent_multi_source():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-02", log_callback=dummy_callback)
    res = await extractor.extract_all_sources()

    assert "singstat" in res["datasets"]
    assert "mom" in res["datasets"]
    assert "wages" in res["datasets"]
    assert "excel_turnover" in res["datasets"]
    assert len(res["quality_reports"]) >= 4
    assert len(logged_steps) >= 5

@pytest.mark.asyncio
async def test_analytics_agent_synthesis():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-03", log_callback=dummy_callback)
    extracted = await extractor.extract_all_sources()

    analytics = AnalyticsAgent(session_id="test-sess-03", log_callback=dummy_callback)
    analysis_res = await analytics.perform_analysis_and_synthesis(
        query="Analyse employment trends in the technology sector from 2020-2024",
        datasets=extracted["datasets"]
    )

    report = analysis_res["report"]
    assert report.session_id == "test-sess-03"
    assert len(report.key_findings) >= 2
    assert len(report.citations) >= 3
    assert report.quality_score >= 90.0
    assert report.hallucination_score <= 0.05
    assert len(analysis_res["charts"]) >= 2
