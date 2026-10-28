import json
import logging
from datetime import datetime
from typing import Any

from backend.app.agents.analytics import AnalyticsAgent
from backend.app.agents.coordinator import DataCoordinatorAgent
from backend.app.agents.extractor import DataExtractionAgent
from backend.app.core.database import DBAgentLog, DBAnalysisSession, SessionLocal
from backend.app.core.websocket_manager import ws_manager
from backend.app.models.schemas import AgentStepLog, SessionStatus

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
        current_agent: str | None = None,
        current_step: str | None = None,
        charts: list | None = None,
        quality_reports: list | None = None,
        report: Any | None = None,
        provider_used: str | None = None,
        tokens_added: int = 0,
        error_message: str | None = None
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

            # Handle ambiguous queries or out-of-scope domain queries with domain guardrail
            if plan_res.get("is_out_of_scope"):
                from backend.app.models.schemas import PolicyFinding, PolicyReport
                is_ambig = plan_res.get("is_ambiguous", False)
                title = "Clarification Required: Ambiguous Research Query" if is_ambig else "Domain Guardrail Notice: Query Outside Policy Scope"
                step_title = "Clarification required: ambiguous query parameters" if is_ambig else "Domain guardrail applied: query out of scope"

                guardrail_report = PolicyReport(
                    session_id=self.session_id,
                    query=query,
                    title=title,
                    executive_summary=f"{plan_res.get('rejection_reason')} {plan_res.get('suggestion')}",
                    key_findings=[
                        PolicyFinding(
                            heading="Supported Data Repositories & Domain Scope",
                            body="This platform is specialized for Singapore Whole-of-Government (WOG) manpower and economic analytics. Integrated repositories include: DOS SingStat (Employment), MOM (Vacancies & Retrenchments), Data.gov.sg (Wages), and IMDA Policy DB.",
                            sentiment="neutral",
                            statistical_evidence="Authoritative coverage: Singapore labor market and wage dynamics (2020-2024) across ICT, Financial Services, and Overall Economy.",
                            citation_id="SCOPE-GUARDRAIL"
                        )
                    ],
                    statistical_metrics={},
                    policy_recommendations=[
                        "Select a supported Singapore sector: Information & Communications, Financial & Insurance Services, or Overall Economy.",
                        "Query Singapore labor metrics: employment trends, vacancies-to-unemployed ratio, retrenchments, or wage benchmarks.",
                        "Specify analysis periods within 2020-2024."
                    ],
                    citations=[],
                    quality_score=100.0,
                    hallucination_score=0.0
                )

                await self.update_session_state(
                    status=SessionStatus.COMPLETED,
                    progress_pct=100,
                    current_agent="Data Coordinator Agent",
                    current_step=step_title,
                    charts=[],
                    quality_reports=[],
                    report=guardrail_report,
                    provider_used=provider_used,
                    tokens_added=total_tokens
                )

                await ws_manager.broadcast_to_session(self.session_id, {
                    "type": "workflow_completed",
                    "session_id": self.session_id,
                    "charts": [],
                    "quality_reports": [],
                    "report": guardrail_report.model_dump(mode="json")
                })
                return

            # 2. Extraction & Data Quality Phase (Parameterized by Coordinator Plan)
            params = plan_res.get("parameters", {})
            sector_name = params.get("sector", "Information & Communications")
            start_yr = params.get("start_year", 2020)
            end_yr = params.get("end_year", 2024)

            await self.update_session_state(
                status=SessionStatus.EXTRACTING,
                progress_pct=35,
                current_agent="Data Extraction Agent",
                current_step=f"Extracting {sector_name} data ({start_yr}-{end_yr}) across selected repositories",
                provider_used=provider_used,
                tokens_added=total_tokens
            )

            extractor = DataExtractionAgent(self.session_id, self.log_step_db)
            extraction_res = await extractor.extract_sources(
                plan=plan_res.get("plan"),
                parameters=params
            )

            datasets = extraction_res["datasets"]
            quality_reports = extraction_res["quality_reports"]
            provenance = extraction_res.get("provenance", {})
            overall_quality = extraction_res.get("overall_quality_score", 0.0)

            # Save quality reports to DB & broadcast
            await self.update_session_state(
                status=SessionStatus.ANALYZING,
                progress_pct=65,
                current_agent="Analytics Agent",
                current_step=f"Running econometric models & policy synthesis for {sector_name}",
                quality_reports=quality_reports
            )

            # 3. Analytics, Synthesis & Hallucination Verification Phase
            analytics_agent = AnalyticsAgent(self.session_id, self.log_step_db)
            analysis_res = await analytics_agent.perform_analysis_and_synthesis(
                query=query,
                datasets=datasets,
                provider_preference=provider_preference,
                provenance=provenance,
                overall_quality_score=overall_quality,
                parameters=params
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
