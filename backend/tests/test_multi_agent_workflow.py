import pytest
import json
from backend.app.agents.orchestrator import WorkflowOrchestrator
from backend.app.core.database import SessionLocal, DBAnalysisSession
from backend.app.models.schemas import SessionStatus

@pytest.mark.asyncio
async def test_full_orchestrated_workflow_end_to_end():
    session_id = "test-e2e-88"
    db = SessionLocal()
    
    # Pre-create session in DB
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

    # Verify final state in DB
    db = SessionLocal()
    completed_sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    
    assert completed_sess is not None
    assert completed_sess.status == SessionStatus.COMPLETED.value
    assert completed_sess.progress_pct == 100
    assert len(completed_sess.logs) >= 8
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
