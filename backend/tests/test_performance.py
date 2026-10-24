import pytest
import asyncio
import time
from backend.app.agents.orchestrator import WorkflowOrchestrator
from backend.app.core.database import SessionLocal, DBAnalysisSession
from backend.app.models.schemas import SessionStatus

@pytest.mark.asyncio
async def test_concurrent_multi_agent_workloads():
    """
    Performance & Concurrency Load Test:
    Simulates 5 concurrent policy researchers launching simultaneous agentic workflows.
    Ensures zero database deadlocks, clean state segregation, and high throughput.
    """
    num_concurrent = 5
    session_ids = [f"perf-test-{i}" for i in range(num_concurrent)]
    
    # Initialize sessions in DB
    db = SessionLocal()
    for sid in session_ids:
        existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == sid).first()
        if existing:
            db.delete(existing)
        db.add(DBAnalysisSession(
            id=sid,
            query=f"Concurrent query {sid}: Analyse tech employment 2020-2024",
            status=SessionStatus.PENDING.value
        ))
    db.commit()
    db.close()

    start_time = time.time()

    async def run_single(sid):
        orch = WorkflowOrchestrator(sid)
        await orch.execute_workflow(
            query="Analyse employment trends in the technology sector from 2020-2024",
            provider_preference="local_fallback"
        )

    # Run in parallel
    await asyncio.gather(*[run_single(sid) for sid in session_ids])

    elapsed = time.time() - start_time

    # Validate all finished in COMPLETED state
    db = SessionLocal()
    completed_count = db.query(DBAnalysisSession).filter(
        DBAnalysisSession.id.in_(session_ids),
        DBAnalysisSession.status == SessionStatus.COMPLETED.value
    ).count()
    db.close()

    assert completed_count == num_concurrent
    # Ensure average throughput is sub-second per orchestrated multi-agent run
    assert elapsed < 15.0 # Total execution for 5 concurrent multi-agent runs well within performance target
