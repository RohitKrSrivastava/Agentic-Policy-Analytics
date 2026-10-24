import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.models.schemas import SessionStatus, SessionResponse, AgentStepLog
from backend.app.agents.coordinator import DataCoordinatorAgent
from backend.app.agents.extractor import DataExtractionAgent
from backend.app.agents.analytics import AnalyticsAgent
from backend.app.core.database import SessionLocal, DBAnalysisSession, DBAgentLog
from backend.app.core.websocket_manager import ws_manager

logger = logging.getLogger("orchestrator")

class WorkflowOrchestrator:
    """
    Multi-Agent Collaborative Workflow Orchestrator.
    Manages session lifecycle, shared blackboard state, agent coordination,
    and DB persistence.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def log_step_db(self, step: AgentStepLog):
        db = SessionLocal()
        try:
            db_log = DBAgentLog(
                id=step.id,
                session_id=self.session_id,
                agent=step.agent.value,
                step_type=step.step_type.value,
                title=step.title,
                content=step.content,
                tool_name=step.tool_name,
                tool_input_json=json.dumps(step.tool_input) if step.tool_input else None,
                tool_output_json=json.dumps(step.tool_output) if step.tool_output else None,
                timestamp=step.timestamp
            )
            db.add(db_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist agent log to DB: {e}")
            db.rollback()
        finally:
            db.close()

    async def update_session_state(
        self,
        status: SessionStatus,
        progress_pct: int,
        current_agent: Optional[str] = None,
        current_step: Optional[str] = None,
        charts: Optional[list] = None,
        quality_reports: Optional[list] = None,
        report: Optional[Any] = None,
        provider_used: Optional[str] = None,
        tokens_added: int = 0,
        error_message: Optional[str] = None
    ):
        db = SessionLocal()
        try:
            db_session = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == self.session_id).first()
            if db_session:
                db_session.status = status.value
                db_session.progress_pct = progress_pct
                if current_agent:
                    db_session.current_agent = current_agent
                if current_step:
                    db_session.current_step = current_step
                if provider_used:
                    db_session.llm_provider_used = provider_used
                if tokens_added:
                    db_session.tokens_consumed = (db_session.tokens_consumed or 0) + tokens_added
                if charts is not None:
                    db_session.charts_json = json.dumps([c.model_dump(mode="json") if hasattr(c, "model_dump") else c for c in charts])
                if quality_reports is not None:
                    db_session.quality_json = json.dumps([q.model_dump(mode="json") if hasattr(q, "model_dump") else q for q in quality_reports])
                if report is not None:
                    db_session.report_json = json.dumps(report.model_dump(mode="json") if hasattr(report, "model_dump") else report)
                if error_message:
                    db_session.error_message = error_message
                db_session.updated_at = datetime.utcnow()
                db.commit()

            # Broadcast status update via WebSocket
            await ws_manager.broadcast_to_session(self.session_id, {
                "type": "status_update",
                "session_id": self.session_id,
                "status": status.value,
                "progress_pct": progress_pct,
                "current_agent": current_agent,
                "current_step": current_step,
                "llm_provider_used": provider_used,
                "error_message": error_message
            })
        except Exception as e:
            logger.error(f"Failed to update session state in DB: {e}")
            db.rollback()
        finally:
            db.close()

    async def execute_workflow(self, query: str, provider_preference: str = "auto"):
        """
        Executes end-to-end multi-agent research workflow:
        Coordinator (Planning) -> Extractor (Multi-Source Acquisition & Cleaning) -> Analytics (Modeling, RAG, Synthesis & Verification)
        """
        try:
            # 1. Planning Phase
            await self.update_session_state(
                status=SessionStatus.PLANNING,
                progress_pct=10,
                current_agent="Data Coordinator Agent",
                current_step="Formulating multi-source research plan"
            )

            coordinator = DataCoordinatorAgent(self.session_id, self.log_step_db)
            plan_res = await coordinator.plan_research_workflow(query, provider_preference=provider_preference)
            
            provider_used = plan_res.get("provider_used", "local_fallback")
            total_tokens = plan_res.get("tokens", 0)

            # 2. Extraction & Data Quality Phase
            await self.update_session_state(
                status=SessionStatus.EXTRACTING,
                progress_pct=35,
                current_agent="Data Extraction Agent",
                current_step="Querying SingStat, MOM, and Data.gov.sg portals",
                provider_used=provider_used,
                tokens_added=total_tokens
            )

            extractor = DataExtractionAgent(self.session_id, self.log_step_db)
            extraction_res = await extractor.extract_all_sources()
            
            datasets = extraction_res["datasets"]
            quality_reports = extraction_res["quality_reports"]

            # Save quality reports to DB & broadcast
            await self.update_session_state(
                status=SessionStatus.ANALYZING,
                progress_pct=65,
                current_agent="Analytics Agent",
                current_step="Running econometric regressions & RAG policy synthesis",
                quality_reports=quality_reports
            )

            # 3. Analytics, Synthesis & Hallucination Verification Phase
            analytics_agent = AnalyticsAgent(self.session_id, self.log_step_db)
            analysis_res = await analytics_agent.perform_analysis_and_synthesis(
                query=query,
                datasets=datasets,
                provider_preference=provider_preference
            )

            final_report = analysis_res["report"]
            charts = analysis_res["charts"]
            total_tokens += analysis_res.get("tokens", 0)

            # 4. Final Completion
            await self.update_session_state(
                status=SessionStatus.COMPLETED,
                progress_pct=100,
                current_agent="System Orchestrator",
                current_step="Analysis completed & verified",
                charts=charts,
                quality_reports=quality_reports,
                report=final_report,
                provider_used=provider_used,
                tokens_added=analysis_res.get("tokens", 0)
            )

            # Broadcast final completion event with all artifacts
            await ws_manager.broadcast_to_session(self.session_id, {
                "type": "workflow_completed",
                "session_id": self.session_id,
                "charts": [c.model_dump(mode="json") for c in charts],
                "quality_reports": [q.model_dump(mode="json") for q in quality_reports],
                "report": final_report.model_dump(mode="json")
            })

            logger.info(f"Session {self.session_id} successfully completed.")

        except Exception as e:
            logger.error(f"Workflow execution failed for session {self.session_id}: {e}", exc_info=True)
            await self.update_session_state(
                status=SessionStatus.FAILED,
                progress_pct=100,
                current_agent="System Orchestrator",
                current_step="Execution halted due to error",
                error_message=str(e)
            )
