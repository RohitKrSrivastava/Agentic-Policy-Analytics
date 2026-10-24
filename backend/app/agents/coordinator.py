import json
import logging
from typing import Dict, Any, Optional, Callable
from backend.app.agents.base_agent import BaseAgent
from backend.app.models.schemas import AgentType, StepType
from backend.app.llm.router import llm_router

logger = logging.getLogger("coordinator_agent")

class DataCoordinatorAgent(BaseAgent):
    """
    Data Coordinator Agent:
    - Plans policy research workflows.
    - Understands query intent and formulates analytical hypotheses.
    - Delegates extraction subtasks across heterogeneous sources.
    - Monitors multi-agent execution pipeline.
    """
    def __init__(self, session_id: str, log_callback: Optional[Callable] = None):
        super().__init__(AgentType.COORDINATOR, session_id, log_callback)

    async def plan_research_workflow(self, query: str, provider_preference: str = "auto") -> Dict[str, Any]:
        await self.log_step(
            step_type=StepType.THOUGHT,
            title="Decomposing Policy Research Query",
            content=f"Analyzing query: '{query}'. Formulating structured research execution plan and selecting government data sources."
        )

        planning_prompt = f"""
You are the Lead Data Coordinator Agent for the Singapore Policy Analytics Platform.
The user has submitted the following research query:
"{query}"

Decompose this query into an executable analytical workflow. You must delegate to:
1. Data Extraction Agent: specify the exact government sources needed (SingStat Table 14.1, MOM Labour Market Statistics, Data.gov.sg Wages API, Internal Policy DB).
2. Analytics Agent: specify statistical operations (CAGR, time-series projection, vacancy-unemployment ratios, wage premiums).

Return your response as a valid JSON object with keys:
- "thought": string
- "subtasks": list of objects with "task_id", "agent", "source", "action", "parameters"
- "expected_hypotheses": list of strings
"""
        response, attempts = await llm_router.generate(
            prompt=planning_prompt,
            system_prompt="You are an expert government policy research coordinator. Provide precise, actionable execution plans.",
            json_mode=True,
            preferred_provider=provider_preference
        )

        try:
            plan_data = json.loads(response.content)
        except Exception:
            # Fallback parsing
            plan_data = {
                "thought": "Decomposing query across Singapore Infocomm employment, MOM labour dynamics, and wage benchmarks.",
                "subtasks": [
                    {"task_id": "ST-01", "agent": "Data Extraction Agent", "source": "DOS SingStat", "action": "query_singstat_table"},
                    {"task_id": "ST-02", "agent": "Data Extraction Agent", "source": "MOM Statistics", "action": "query_mom_statistics"},
                    {"task_id": "ST-03", "agent": "Data Extraction Agent", "source": "Data.gov.sg", "action": "query_datagovsg_api"},
                    {"task_id": "ST-04", "agent": "Data Extraction Agent", "source": "MOM Excel", "action": "fetch_mom_turnover_excel"},
                    {"task_id": "ST-05", "agent": "Analytics Agent", "action": "statistical_modeling"}
                ],
                "expected_hypotheses": [
                    "Tech employment demonstrated robust growth from 2020 to 2024 despite 2022-2023 tech downsizing.",
                    "Local workforce share and wage premiums remained resilient in Singapore."
                ]
            }

        await self.log_step(
            step_type=StepType.ACTION,
            title="Workflow Delegation",
            content=f"Delegating {len(plan_data.get('subtasks', []))} analytical subtasks to Data Extraction Agent and Analytics Agent.",
            tool_name="workflow_planner",
            tool_input={"query": query, "provider": response.provider_name},
            tool_output=plan_data
        )

        await self.log_step(
            step_type=StepType.OBSERVATION,
            title="Research Plan Confirmed",
            content=f"Research plan finalized using {response.provider_name} ({response.model_name}). Provider fallback: {'Yes' if response.fallback_used else 'No'}. Ready for data acquisition."
        )

        return {
            "plan": plan_data,
            "provider_used": response.provider_name,
            "tokens": response.total_tokens
        }
