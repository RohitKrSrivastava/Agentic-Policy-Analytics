import json
import pytest

from backend.app.agents.orchestrator import WorkflowOrchestrator
from backend.app.core.database import DBAnalysisSession, SessionLocal
from backend.app.models.schemas import SessionStatus


@pytest.mark.asyncio
async def test_full_orchestrated_workflow_end_to_end():
    session_id = "test-e2e-88"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="Analyse employment trends in the technology sector from 2020-2024",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)
    await orchestrator.execute_workflow(
        query="Analyse employment trends in the technology sector from 2020-2024",
        provider_preference="auto"
    )

    db = SessionLocal()
    completed_sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()

    assert completed_sess is not None
    assert completed_sess.status == SessionStatus.COMPLETED.value
    assert completed_sess.progress_pct == 100
    assert len(completed_sess.logs) >= 5
    assert completed_sess.report_json is not None
    assert completed_sess.charts_json is not None
    assert "Tech_Employment_K" in completed_sess.charts_json

    db.close()


@pytest.mark.asyncio
async def test_orchestrated_workflow_out_of_scope_guardrail():
    session_id = "test-e2e-guardrail"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="What is the weather today?",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)
    await orchestrator.execute_workflow(
        query="What is the weather today?",
        provider_preference="auto"
    )

    db = SessionLocal()
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    assert sess is not None
    assert sess.status == SessionStatus.COMPLETED.value
    assert "weather" in sess.current_step.lower() or "guardrail" in sess.current_step.lower()

    report_data = json.loads(sess.report_json)
    assert "Domain Guardrail" in report_data.get("title", "")
    assert "weather" in report_data.get("executive_summary", "").lower()
    db.close()


@pytest.mark.asyncio
async def test_orchestrated_workflow_years_outside_range_no_crash():
    """
    Edge case: Queries for 2015-2019 or 2018-2019 must NOT crash with NoneType formatting errors.
    Must complete gracefully with a transparent data boundary notice.
    """
    session_id = "test-e2e-years-out-of-range"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="Compare tech employment in 2018 and 2019",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)
    await orchestrator.execute_workflow(
        query="Compare tech employment in 2018 and 2019",
        provider_preference="auto"
    )

    db = SessionLocal()
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    assert sess is not None
    assert sess.status == SessionStatus.COMPLETED.value

    report_data = json.loads(sess.report_json)
    assert "boundary" in report_data.get("executive_summary", "").lower() or "guardrail" in report_data.get("title", "").lower()
    db.close()


@pytest.mark.asyncio
async def test_orchestrated_workflow_unsupported_sector_no_silent_fallback():
    """
    Edge case: Querying an unsupported sector (e.g. 'manufacturing 2021-2023' or 'healthcare wages')
    must NOT silently return an ICT report or crash.
    """
    session_id = "test-e2e-unsupported-sector"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="manufacturing 2021-2023 employment",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)
    await orchestrator.execute_workflow(
        query="manufacturing 2021-2023 employment",
        provider_preference="auto"
    )

    db = SessionLocal()
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    assert sess is not None
    assert sess.status == SessionStatus.COMPLETED.value

    report_data = json.loads(sess.report_json)
    assert "Sector data boundary" in report_data.get("executive_summary", "") or "Manufacturing" in report_data.get("executive_summary", "")
    # Must NOT have returned an unrelated Financial or ICT report
    assert "Financial & Insurance Services (2020-2026)" not in report_data.get("title", "")
    db.close()


@pytest.mark.asyncio
async def test_orchestrated_workflow_ambiguous_query_asks_for_clarification():
    """
    Edge case: Ambiguous query 'tell me something' must NOT silently execute the default ICT pipeline.
    It must ask for clarification on sector and metrics.
    """
    session_id = "test-e2e-ambiguous"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="tell me something",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)
    await orchestrator.execute_workflow(
        query="tell me something",
        provider_preference="auto"
    )

    db = SessionLocal()
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    assert sess is not None
    assert sess.status == SessionStatus.COMPLETED.value

    report_data = json.loads(sess.report_json)
    assert "Clarification Required" in report_data.get("title", "")
    assert "clarify" in report_data.get("executive_summary", "").lower() or "lacks specific" in report_data.get("executive_summary", "").lower()
    db.close()


@pytest.mark.asyncio
async def test_financial_services_sector_query_targets_financial_services():
    """
    Verifies that querying Financial Services correctly targets Financial & Insurance Services,
    instead of defaulting to ICT.
    """
    session_id = "test-e2e-finance"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="Analyse financial services employment trends and wages 2020-2024",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)
    await orchestrator.execute_workflow(
        query="Analyse financial services employment trends and wages 2020-2024",
        provider_preference="auto"
    )

    db = SessionLocal()
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    assert sess is not None
    assert sess.status == SessionStatus.COMPLETED.value

    report_data = json.loads(sess.report_json)
    assert "Financial" in report_data.get("title", "")
    db.close()


@pytest.mark.asyncio
async def test_replan_node_on_empty_data():
    """
    Finding 1 & 4: ReAct Agent Replanning Node.
    When primary time series data is empty (coverage gap), Orchestrator dynamically
    invokes Coordinator reflection, adjusts the plan to Overall Economy, and re-executes.
    """
    session_id = "test-e2e-replan-node"
    db = SessionLocal()

    existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_sess = DBAnalysisSession(
        id=session_id,
        query="Analyse tech sector employment dynamics",
        status=SessionStatus.PENDING.value
    )
    db.add(new_sess)
    db.commit()
    db.close()

    orchestrator = WorkflowOrchestrator(session_id)

    # Mock the first extraction call to simulate an unexpected empty dataset
    original_extract = orchestrator.execute_workflow

    from unittest.mock import patch
    from backend.app.agents.extractor import DataExtractionAgent

    real_extract = DataExtractionAgent.extract_sources
    call_count = 0

    async def mock_extract(self, plan=None, parameters=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First pass: empty singstat
            return {
                "datasets": {"singstat": [], "mom": [], "wages": []},
                "quality_reports": [],
                "provenance": {},
                "overall_quality_score": 0.0,
                "missing_sources": ["query_singstat_table"]
            }
        else:
            # Replan pass: return real data
            return await real_extract(self, plan=plan, parameters=parameters)

    with patch.object(DataExtractionAgent, "extract_sources", side_effect=mock_extract, autospec=True):
        await orchestrator.execute_workflow(
            query="Analyse tech sector employment dynamics",
            provider_preference="auto"
        )

    db = SessionLocal()
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    assert sess is not None
    assert sess.status == SessionStatus.COMPLETED.value
    assert call_count >= 2  # Replanning executed extraction twice!

    # Check that a reflection step for replanning was persisted
    replan_logs = [log for log in sess.logs if "Replanning Data Strategy" in log.title]
    assert len(replan_logs) >= 1
    assert "Overall Economy" in replan_logs[0].content
    db.close()
