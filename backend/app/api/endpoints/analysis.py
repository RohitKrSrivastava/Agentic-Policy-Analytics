import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agents.orchestrator import WorkflowOrchestrator
from backend.app.core.database import DBAnalysisSession, get_db
from backend.app.models.schemas import (
    AgentStepLog,
    ChartSpecification,
    DataQualityItem,
    PolicyReport,
    QueryRequest,
    SessionResponse,
    SessionStatus,
)

router = APIRouter()

@router.post("", response_model=SessionResponse)
@router.post("/query", response_model=SessionResponse)
async def create_analysis(request: QueryRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Submits a natural language policy query and launches autonomous multi-agent analysis in background.
    """
    session_id = str(uuid.uuid4())[:8]

    # Initialize DB record
    new_session = DBAnalysisSession(
        id=session_id,
        query=request.query,
        status=SessionStatus.PENDING.value,
        progress_pct=0,
        current_agent="System Initializer",
        current_step="Queued for multi-agent dispatch",
        llm_provider_used=request.provider_preference or "auto",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Launch workflow asynchronously in background task
    orchestrator = WorkflowOrchestrator(session_id)
    background_tasks.add_task(orchestrator.execute_workflow, request.query, request.provider_preference or "auto")

    return SessionResponse(
        session_id=session_id,
        query=request.query,
        status=SessionStatus.PENDING,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
        current_agent="System Initializer",
        current_step="Queued for multi-agent dispatch",
        progress_pct=0,
        llm_provider_used=request.provider_preference
    )

@router.get("/{session_id}", response_model=SessionResponse)
def get_analysis_session(session_id: str, db: Session = Depends(get_db)):
    """
    Fetches full analysis session details, including ReAct thought logs,
    generated charts, data quality audits, and synthesized policy report.
    """
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Analysis session not found.")

    # Parse nested JSON
    charts = [ChartSpecification(**c) for c in json.loads(sess.charts_json)] if sess.charts_json else []
    quality_reports = [DataQualityItem(**q) for q in json.loads(sess.quality_json)] if sess.quality_json else []
    report = PolicyReport(**json.loads(sess.report_json)) if sess.report_json else None

    # Parse logs
    logs = [
        AgentStepLog(
            id=entry.id,
            session_id=entry.session_id,
            agent=entry.agent,
            step_type=entry.step_type,
            title=entry.title,
            content=entry.content,
            tool_name=entry.tool_name,
            tool_input=json.loads(entry.tool_input_json) if entry.tool_input_json else None,
            tool_output=json.loads(entry.tool_output_json) if entry.tool_output_json else None,
            timestamp=entry.timestamp
        )
        for entry in sess.logs
    ]

    return SessionResponse(
        session_id=sess.id,
        query=sess.query,
        status=SessionStatus(sess.status),
        created_at=sess.created_at,
        updated_at=sess.updated_at,
        current_agent=sess.current_agent,
        current_step=sess.current_step,
        progress_pct=sess.progress_pct,
        logs=logs,
        charts=charts,
        quality_reports=quality_reports,
        report=report,
        error_message=sess.error_message,
        llm_provider_used=sess.llm_provider_used,
        tokens_consumed=sess.tokens_consumed
    )

@router.get("", response_model=list[SessionResponse])
def list_analysis_sessions(limit: int = 20, db: Session = Depends(get_db)):
    """
    Returns history of research analyses for the history viewer.
    """
    sessions = db.query(DBAnalysisSession).order_by(DBAnalysisSession.created_at.desc()).limit(limit).all()
    results = []
    for s in sessions:
        results.append(SessionResponse(
            session_id=s.id,
            query=s.query,
            status=SessionStatus(s.status),
            created_at=s.created_at,
            updated_at=s.updated_at,
            current_agent=s.current_agent,
            current_step=s.current_step,
            progress_pct=s.progress_pct,
            llm_provider_used=s.llm_provider_used,
            tokens_consumed=s.tokens_consumed
        ))
    return results

@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    db.delete(sess)
    db.commit()
    return {"message": f"Session {session_id} successfully deleted."}
