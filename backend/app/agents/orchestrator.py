import json
import logging
from datetime import datetime
from typing import Any

from backend.app.agents.analytics import AnalyticsAgent
from backend.app.agents.coordinator import DataCoordinatorAgent
from backend.app.agents.extractor import DataExtractionAgent, _merge_record_lists
from backend.app.agents.state_graph import StateGraph
from backend.app.core.database import DBAgentLog, DBAnalysisSession, SessionLocal
from backend.app.core.websocket_manager import ws_manager
from backend.app.models.schemas import AgentStepLog, PolicyFinding, PolicyReport, SessionStatus

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

    async def execute_workflow(self, query: str, provider_preference: str = "auto", temperature: float = 0.2):
        """
        Executes end-to-end multi-agent research workflow modeled directly on LangGraph's StateGraph:
        Nodes:
          1. 'plan': Evaluates query scope and formulates multi-source research plan.
          2. 'extract': Executes autonomous ReAct or deterministic data acquisition.
          3. 'check_coverage': Inspects datasets for coverage gaps across critical repositories.
          4. 'replan': LLM-driven autonomous recovery node for missing data (substitutions & window widening).
          5. 'analyze': Runs econometric modeling, cross-sector comparisons, and synthesis.
          6. 'publish': Enforces transparent data substitution disclosures, audits factuality, and broadcasts.
        """
        try:
            coordinator = DataCoordinatorAgent(self.session_id, self.log_step_db)
            extractor = DataExtractionAgent(self.session_id, self.log_step_db)
            analytics_agent = AnalyticsAgent(self.session_id, self.log_step_db)

            # Node 1: Plan
            async def node_plan(state: dict[str, Any]) -> dict[str, Any]:
                await self.update_session_state(
                    status=SessionStatus.PLANNING,
                    progress_pct=10,
                    current_agent="Data Coordinator Agent",
                    current_step="Formulating multi-source research plan"
                )
                plan_res = await coordinator.plan_research_workflow(query, provider_preference=provider_preference)
                provider_used = plan_res.get("provider_used", "local_fallback")
                total_tokens = plan_res.get("tokens", 0)

                if plan_res.get("is_out_of_scope"):
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
                    return {
                        "is_out_of_scope": True,
                        "guardrail_report": guardrail_report,
                        "guardrail_step_title": step_title,
                        "provider_used": provider_used,
                        "total_tokens": total_tokens
                    }

                params = plan_res.get("parameters", {})
                return {
                    "is_out_of_scope": False,
                    "plan_res": plan_res,
                    "parameters": params,
                    "original_parameters": dict(params),
                    "provider_used": provider_used,
                    "total_tokens": total_tokens
                }

            # Node 2: Extract
            async def node_extract(state: dict[str, Any]) -> dict[str, Any]:
                params = state["parameters"]
                sec = params.get("sector", "Information & Communications")
                start_yr = params.get("start_year", 2020)
                end_yr = params.get("end_year", 2024)

                await self.update_session_state(
                    status=SessionStatus.EXTRACTING,
                    progress_pct=35,
                    current_agent="Data Extraction Agent",
                    current_step=f"Extracting {sec} data ({start_yr}-{end_yr}) across selected repositories",
                    provider_used=state.get("provider_used"),
                    tokens_added=state.get("total_tokens", 0)
                )

                extraction_res = await extractor.extract_sources(
                    plan=state.get("plan_res", {}).get("plan"),
                    parameters=params,
                    provider_preference=provider_preference,
                    query=query
                )
                return {
                    "datasets": extraction_res.get("datasets", {}),
                    "quality_reports": extraction_res.get("quality_reports", []),
                    "provenance": extraction_res.get("provenance", {}),
                    "overall_quality_score": extraction_res.get("overall_quality_score", 0.0)
                }

            # Node 3: Check Coverage
            async def node_check_coverage(state: dict[str, Any]) -> dict[str, Any]:
                datasets = state.get("datasets", {})
                empty = []
                if not datasets.get("singstat"):
                    empty.append("singstat")
                if not datasets.get("mom"):
                    empty.append("mom")
                if not datasets.get("wages"):
                    empty.append("wages")
                return {"empty_sources": empty}

            # Node 4: Replan (LLM-driven recovery decision)
            async def node_replan(state: dict[str, Any]) -> dict[str, Any]:
                replans = state.get("replans", 0) + 1
                empty_sources = state.get("empty_sources", [])
                params = dict(state.get("parameters", {}))
                substitutions = list(state.get("substitutions", []))

                # LLM autonomously evaluates gap and determines recovery action
                replan_decision = await coordinator.decide_replan_action(
                    query=query,
                    current_params=params,
                    empty_sources=empty_sources,
                    replan_iteration=replans,
                    provider_preference=provider_preference
                )

                replanned_subtasks = []

                if replan_decision.get("substituted_sector"):
                    orig_sec = params.get("sector", "Unknown Sector")
                    sub_sec = replan_decision["substituted_sector"]
                    params["sector"] = sub_sec
                    if params.get("sectors"):
                        params["sectors"] = [sub_sec if s == orig_sec else s for s in params["sectors"]]
                    substitutions.append({
                        "type": "sector",
                        "original": orig_sec,
                        "substituted": sub_sec,
                        "reason": replan_decision.get("remediation_summary", "Sector unavailable in authoritative datasets")
                    })

                if replan_decision.get("substituted_years"):
                    y = replan_decision["substituted_years"]
                    orig_span = f"{params.get('start_year')}-{params.get('end_year')}"
                    params["start_year"] = y.get("start_year", 2020)
                    params["end_year"] = y.get("end_year", 2024)
                    substitutions.append({
                        "type": "window",
                        "original": orig_span,
                        "substituted": f"{params['start_year']}-{params['end_year']}",
                        "reason": replan_decision.get("remediation_summary", "Observation window adjusted to 2020-2024 boundary")
                    })

                if "singstat" in empty_sources:
                    replanned_subtasks.append({
                        "task_id": f"REPLAN-SING-{replans}",
                        "source": "DOS SingStat",
                        "tool_name": "query_singstat_table",
                        "reasoning": f"Acquire {params['sector']} employment baseline ({params['start_year']}-{params['end_year']}).",
                        "parameters": params
                    })
                if "mom" in empty_sources:
                    replanned_subtasks.append({
                        "task_id": f"REPLAN-MOM-{replans}",
                        "source": "MOM Statistics",
                        "tool_name": "query_mom_statistics",
                        "reasoning": f"Acquire MOM vacancies and retrenchments ({params['start_year']}-{params['end_year']}).",
                        "parameters": params
                    })
                if "wages" in empty_sources:
                    wage_params = dict(params)
                    wage_params["industry"] = params["sector"]
                    replanned_subtasks.append({
                        "task_id": f"REPLAN-WAGE-{replans}",
                        "source": "Data.gov.sg",
                        "tool_name": "query_datagovsg_api",
                        "reasoning": f"Acquire salary benchmarks for {params['sector']}.",
                        "parameters": wage_params
                    })

                replanned_plan = {
                    "thought": replan_decision.get("thought", "Autonomous replanning on coverage gap."),
                    "subtasks": replanned_subtasks,
                    "expected_hypotheses": ["Replanned empirical benchmarks establish valid grounding baseline."]
                }

                await self.update_session_state(
                    status=SessionStatus.EXTRACTING,
                    progress_pct=40 + replans * 10,
                    current_agent="Data Extraction Agent",
                    current_step=f"Executing replanned data acquisition ({', '.join(empty_sources)})"
                )

                replan_res = await extractor.extract_sources(
                    plan=replanned_plan,
                    parameters=params,
                    provider_preference="local_fallback",
                    query=query
                )

                datasets = dict(state.get("datasets", {}))
                for k, v in replan_res.get("datasets", {}).items():
                    if v:
                        datasets[k] = _merge_record_lists(datasets.get(k), v) if isinstance(v, list) else v

                quality_reports = list(state.get("quality_reports", []))
                quality_reports.extend(replan_res.get("quality_reports", []))
                provenance = dict(state.get("provenance", {}))
                provenance.update(replan_res.get("provenance", {}))

                return {
                    "replans": replans,
                    "parameters": params,
                    "substitutions": substitutions,
                    "datasets": datasets,
                    "quality_reports": quality_reports,
                    "provenance": provenance
                }

            # Node 5: Analyze
            async def node_analyze(state: dict[str, Any]) -> dict[str, Any]:
                params = dict(state.get("parameters", {}))
                params["substitutions"] = state.get("substitutions", [])
                sec = params.get("sector", "Information & Communications")

                await self.update_session_state(
                    status=SessionStatus.ANALYZING,
                    progress_pct=65,
                    current_agent="Analytics Agent",
                    current_step=f"Running econometric models & policy synthesis for {sec}",
                    quality_reports=state.get("quality_reports", [])
                )

                analysis_res = await analytics_agent.perform_analysis_and_synthesis(
                    query=query,
                    datasets=state.get("datasets", {}),
                    provider_preference=provider_preference,
                    provenance=state.get("provenance", {}),
                    overall_quality_score=state.get("overall_quality_score", 0.0),
                    parameters=params,
                    temperature=temperature
                )
                return {
                    "report": analysis_res["report"],
                    "charts": analysis_res["charts"],
                    "verification": analysis_res["verification"],
                    "total_tokens": state.get("total_tokens", 0) + analysis_res.get("tokens", 0)
                }

            # Node 6: Publish
            async def node_publish(state: dict[str, Any]) -> dict[str, Any]:
                if state.get("is_out_of_scope"):
                    guardrail_report = state["guardrail_report"]
                    await self.update_session_state(
                        status=SessionStatus.COMPLETED,
                        progress_pct=100,
                        current_agent="Data Coordinator Agent",
                        current_step=state.get("guardrail_step_title", "Domain guardrail applied"),
                        charts=[],
                        quality_reports=[],
                        report=guardrail_report,
                        provider_used=state.get("provider_used"),
                        tokens_added=state.get("total_tokens", 0)
                    )
                    await ws_manager.broadcast_to_session(self.session_id, {
                        "type": "workflow_completed",
                        "session_id": self.session_id,
                        "charts": [],
                        "quality_reports": [],
                        "report": guardrail_report.model_dump(mode="json")
                    })
                    return {"final_report": guardrail_report}

                final_report = state["report"]
                charts = state.get("charts", [])
                quality_reports = state.get("quality_reports", [])

                await self.update_session_state(
                    status=SessionStatus.COMPLETED,
                    progress_pct=100,
                    current_agent="System Orchestrator",
                    current_step="Analysis completed & verified",
                    charts=charts,
                    quality_reports=quality_reports,
                    report=final_report,
                    provider_used=state.get("provider_used"),
                    tokens_added=state.get("total_tokens", 0)
                )

                await ws_manager.broadcast_to_session(self.session_id, {
                    "type": "workflow_completed",
                    "session_id": self.session_id,
                    "charts": [c.model_dump(mode="json") for c in charts],
                    "quality_reports": [q.model_dump(mode="json") for q in quality_reports],
                    "report": final_report.model_dump(mode="json")
                })
                return {"final_report": final_report}

            # Assemble LangGraph StateGraph
            g = StateGraph()
            g.add_node("plan", node_plan)
            g.add_node("extract", node_extract)
            g.add_node("check_coverage", node_check_coverage)
            g.add_node("replan", node_replan)
            g.add_node("analyze", node_analyze)
            g.add_node("publish", node_publish)

            g.set_entry_point("plan")

            def route_plan(s: dict[str, Any]) -> str:
                return "publish" if s.get("is_out_of_scope") else "extract"

            def route_coverage(s: dict[str, Any]) -> str:
                if s.get("empty_sources") and s.get("replans", 0) < s.get("max_replans", 2):
                    return "replan"
                return "analyze"

            g.add_conditional_edges("plan", route_plan)
            g.add_edge("extract", "check_coverage")
            g.add_conditional_edges("check_coverage", route_coverage)
            g.add_edge("replan", "check_coverage")
            g.add_edge("analyze", "publish")

            compiled_graph = g.compile()

            initial_state = {
                "session_id": self.session_id,
                "query": query,
                "provider_preference": provider_preference,
                "temperature": temperature,
                "replans": 0,
                "max_replans": 2,
                "substitutions": [],
                "datasets": {},
                "provenance": {},
                "quality_reports": [],
                "total_tokens": 0
            }

            final_state = await compiled_graph.ainvoke(initial_state)
            logger.info(f"Session {self.session_id} successfully completed via StateGraph.")
            return final_state.get("final_report")

        except Exception as e:
            logger.error(f"Workflow execution failed for session {self.session_id}: {e}", exc_info=True)
            await self.update_session_state(
                status=SessionStatus.FAILED,
                progress_pct=100,
                current_agent="System Orchestrator",
                current_step="Execution halted due to error",
                error_message=str(e)
            )
            return None

        except Exception as e:
            logger.error(f"Workflow execution failed for session {self.session_id}: {e}", exc_info=True)
            await self.update_session_state(
                status=SessionStatus.FAILED,
                progress_pct=100,
                current_agent="System Orchestrator",
                current_step="Execution halted due to error",
                error_message=str(e)
            )
            return None


# Backward-compatible alias
PolicyOrchestrator = WorkflowOrchestrator
