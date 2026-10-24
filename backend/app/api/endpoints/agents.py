import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db, DBAgentLog
from backend.app.models.schemas import AgentStepLog

router = APIRouter()

@router.get("/{session_id}/logs", response_model=List[AgentStepLog])
def get_session_logs(session_id: str, db: Session = Depends(get_db)):
    """
    Retrieves chronological reasoning steps (ReAct thoughts, actions, observations)
    for a specific research session.
    """
    logs = db.query(DBAgentLog).filter(DBAgentLog.session_id == session_id).order_by(DBAgentLog.timestamp.asc()).all()
    return [
        AgentStepLog(
            id=l.id,
            session_id=l.session_id,
            agent=l.agent,
            step_type=l.step_type,
            title=l.title,
            content=l.content,
            tool_name=l.tool_name,
            tool_input=json.loads(l.tool_input_json) if l.tool_input_json else None,
            tool_output=json.loads(l.tool_output_json) if l.tool_output_json else None,
            timestamp=l.timestamp
        )
        for l in logs
    ]
