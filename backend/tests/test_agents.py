import pytest

from backend.app.agents.analytics import AnalyticsAgent
from backend.app.agents.coordinator import DataCoordinatorAgent
from backend.app.agents.extractor import DataExtractionAgent
from backend.app.models.schemas import StepType


@pytest.mark.asyncio
async def test_coordinator_agent_planning():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    coordinator = DataCoordinatorAgent(session_id="test-sess-01", log_callback=dummy_callback)
    plan_res = await coordinator.plan_research_workflow("Analyse employment trends in the technology sector from 2020-2024")

    assert plan_res["is_out_of_scope"] is False
    assert "plan" in plan_res
    assert len(plan_res["plan"]["subtasks"]) >= 3
    assert len(logged_steps) >= 3
    assert any(s.step_type == StepType.THOUGHT for s in logged_steps)
    assert any(s.step_type == StepType.ACTION for s in logged_steps)
    assert any(s.step_type == StepType.OBSERVATION for s in logged_steps)


@pytest.mark.asyncio
async def test_coordinator_domain_guardrail_out_of_scope():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    coordinator = DataCoordinatorAgent(session_id="test-sess-guard", log_callback=dummy_callback)

    # 1. Geographic mismatch
    malaysia_res = await coordinator.plan_research_workflow("construction sector wages in Malaysia 1995-2005")
    assert malaysia_res["is_out_of_scope"] is True
    assert "Malaysia" in malaysia_res["rejection_reason"]

    # 2. Topic mismatch
    weather_res = await coordinator.plan_research_workflow("What is the weather today?")
    assert weather_res["is_out_of_scope"] is True
    assert "weather" in weather_res["rejection_reason"].lower()

    # 3. Ambiguous query
    ambig_res = await coordinator.plan_research_workflow("tell me something")
    assert ambig_res["is_out_of_scope"] is True
    assert ambig_res["is_ambiguous"] is True
    assert "clarify" in ambig_res["suggestion"].lower()

    # 4. Unsupported sector
    unsupported_sector_res = await coordinator.plan_research_workflow("retail employment 2021-2023")
    assert unsupported_sector_res["is_out_of_scope"] is True
    assert "Retail" in unsupported_sector_res["rejection_reason"]

    # 5. Out of bounds years
    years_out_res = await coordinator.plan_research_workflow("tech employment 2015-2018")
    assert years_out_res["is_out_of_scope"] is True
    assert "Time horizon boundary" in years_out_res["rejection_reason"]


@pytest.mark.asyncio
async def test_coordinator_parameter_extraction():
    coordinator = DataCoordinatorAgent(session_id="test-sess-params")
    params = coordinator.extract_query_parameters("Analyze financial sector tech wages and vacancies from 2021 to 2023")
    assert params["start_year"] == 2021
    assert params["end_year"] == 2023
    assert "Financial" in params["sector"]
    assert "wages" in params["focus_metrics"]
    assert "vacancies" in params["focus_metrics"]


@pytest.mark.asyncio
async def test_extraction_agent_multi_source():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-02", log_callback=dummy_callback)
    res = await extractor.extract_sources(parameters={"start_year": 2020, "end_year": 2024, "sector": "Information & Communications"})

    assert "singstat" in res["datasets"]
    assert "mom" in res["datasets"]
    assert "wages" in res["datasets"]
    assert "excel_turnover" in res["datasets"]
    assert len(res["quality_reports"]) >= 4
    assert len(logged_steps) >= 5
    assert "provenance" in res
    assert res["overall_quality_score"] > 80.0


@pytest.mark.asyncio
async def test_analytics_agent_synthesis():
    logged_steps = []
    async def dummy_callback(step):
        logged_steps.append(step)

    extractor = DataExtractionAgent(session_id="test-sess-03", log_callback=dummy_callback)
    extracted = await extractor.extract_sources()

    analytics = AnalyticsAgent(session_id="test-sess-03", log_callback=dummy_callback)
    analysis_res = await analytics.perform_analysis_and_synthesis(
        query="Analyse employment trends in the technology sector from 2020-2024",
        datasets=extracted["datasets"],
        provenance=extracted.get("provenance"),
        overall_quality_score=extracted.get("overall_quality_score")
    )

    report = analysis_res["report"]
    assert report.session_id == "test-sess-03"
    assert len(report.key_findings) >= 1
    assert len(report.citations) >= 3
    assert report.quality_score >= 80.0
    assert report.hallucination_score <= 0.05
    assert len(analysis_res["charts"]) >= 2
