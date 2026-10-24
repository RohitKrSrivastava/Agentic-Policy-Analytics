import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from backend.app.models.schemas import AgentType, StepType, AgentStepLog
from backend.app.core.websocket_manager import ws_manager

logger = logging.getLogger("agent")

class BaseAgent:
    def __init__(self, agent_type: AgentType, session_id: str, log_callback: Optional[Callable] = None):
        self.agent_type = agent_type
        self.session_id = session_id
        self.log_callback = log_callback

    async def log_step(
        self,
        step_type: StepType,
        title: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Dict[str, Any]] = None
    ) -> AgentStepLog:
        """
        Emits a ReAct step (Thought, Action, Observation, Reflection)
        simultaneously to DB callback and real-time WebSocket clients.
        """
        step = AgentStepLog(
            id=str(uuid.uuid4())[:8],
            session_id=self.session_id,
            agent=self.agent_type,
            step_type=step_type,
            title=title,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            timestamp=datetime.utcnow()
        )

        logger.info(f"[{self.agent_type.value}] [{step_type.value.upper()}] {title}: {content[:100]}...")

        # Broadcast through WebSocket
        await ws_manager.broadcast_to_session(self.session_id, {
            "type": "agent_log",
            "session_id": self.session_id,
            "data": step.model_dump(mode="json")
        })

        # Save to DB via callback
        if self.log_callback:
            await self.log_callback(step)

        return step
