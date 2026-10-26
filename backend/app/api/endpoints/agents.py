import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import DBAgentLog, get_db
from backend.app.models.schemas import AgentStepLog

router = APIRouter()

@router.get("/{session_id}/logs", response_model=list[AgentStepLog])
def get_session_logs(session_id: str, db: Session = Depends(get_db)):
    """
    Retrieves chronological reasoning steps (ReAct thoughts, actions, observations)
    for a specific research session.
    """
    logs = db.query(DBAgentLog).filter(DBAgentLog.session_id == session_id).order_by(DBAgentLog.timestamp.asc()).all()
    return [
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
        for entry in logs
    ]
