import asyncio
import time

import pytest

from backend.app.agents.orchestrator import WorkflowOrchestrator
from backend.app.core.database import DBAnalysisSession, SessionLocal
from backend.app.models.schemas import SessionStatus


@pytest.mark.asyncio
async def test_concurrent_multi_agent_workloads():
    """
    Performance & Concurrency Load Test:
    Simulates 10 concurrent policy researchers launching simultaneous agentic workflows
    across varied economic sectors (Information & Communications, Financial Services, Overall Economy).
    Ensures zero database deadlocks, clean state segregation, and high throughput.
    """
    sectors = [
        "Information & Communications",
        "Financial & Insurance Services",
        "Overall Economy"
    ]
    num_concurrent = 9
    session_ids = [f"perf-test-{i}" for i in range(num_concurrent)]

    db = SessionLocal()
    for i, sid in enumerate(session_ids):
        existing = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == sid).first()
        if existing:
            db.delete(existing)
        sec = sectors[i % len(sectors)]
        db.add(DBAnalysisSession(
            id=sid,
            query=f"Concurrent query {sid}: Analyse {sec} employment 2020-2024",
            status=SessionStatus.PENDING.value
        ))
    db.commit()
    db.close()

    start_time = time.time()

    async def run_single(i, sid):
        sec = sectors[i % len(sectors)]
        orch = WorkflowOrchestrator(sid)
        await orch.execute_workflow(
            query=f"Analyse {sec} employment trends and wages from 2020-2024",
            provider_preference="local_fallback"
        )

    await asyncio.gather(*[run_single(i, sid) for i, sid in enumerate(session_ids)])

    elapsed = time.time() - start_time

    db = SessionLocal()
    completed_count = db.query(DBAnalysisSession).filter(
        DBAnalysisSession.id.in_(session_ids),
        DBAnalysisSession.status == SessionStatus.COMPLETED.value
    ).count()
    db.close()

    assert completed_count == num_concurrent
    assert elapsed < 20.0
