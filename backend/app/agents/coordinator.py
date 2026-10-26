import json
import logging
import re
from collections.abc import Callable
from typing import Any

from backend.app.agents.base_agent import BaseAgent
from backend.app.llm.router import llm_router
from backend.app.models.schemas import AgentType, StepType

logger = logging.getLogger("coordinator_agent")

class DataCoordinatorAgent(BaseAgent):
    """
    Data Coordinator Agent:
    - Interprets query intent, domain validity, and geographic boundary.
    - Handles ambiguity and applies domain guardrails for out-of-scope requests.
    - Formulates structured, parameterized multi-source research execution plans.
    - Delegates specific tool invocations with extracted parameters to the Data Extraction Agent.
    """
    def __init__(self, session_id: str, log_callback: Callable | None = None):
        super().__init__(AgentType.COORDINATOR, session_id, log_callback)

    def evaluate_query_scope(self, query: str) -> dict[str, Any]:
        """
        Determines if the query is within Singapore public sector manpower & policy domain.
        Catches unsupported geographies (e.g. Malaysia, US) and unrelated domains (weather, recipes).
        """
        q_lower = query.lower()

        # 1. Geographic Boundary Check
        unsupported_geos = [
            "malaysia", "indonesia", "thailand", "vietnam", "philippines",
            "united states", "usa", "uk", "britain", "europe", "india", "china", "japan"
        ]
        for geo in unsupported_geos:
            if re.search(r'\b' + re.escape(geo) + r'\b', q_lower):
                return {
                    "is_out_of_scope": True,
                    "reason": f"Geographic domain mismatch: Query targets '{geo.title()}', but this platform is specialized for Singapore Public Sector (WOG/IMDA/MOM/DOS) data repositories.",
                    "suggestion": "Please refine your query to Singapore policy domains (e.g. Singapore technology employment, MOM labor market dynamics, or national wage benchmarks)."
                }

        # 2. Topic / Domain Check
        unsupported_topics = [
            "weather", "forecast tomorrow", "temperature", "rain", "recipe",
            "cook", "horoscope", "crypto price", "bitcoin", "sports score",
            "movie", "celebrity", "joke"
        ]
        for topic in unsupported_topics:
            if re.search(r'\b' + re.escape(topic) + r'\b', q_lower):
                return {
                    "is_out_of_scope": True,
                    "reason": f"Topic domain mismatch: '{topic}' is outside the scope of Singapore manpower, wage economics, and public policy analytics.",
                    "suggestion": "This platform analyzes Singapore employment trends, workforce transitions, wage distributions, and policy initiatives."
                }

        return {
            "is_out_of_scope": False,
            "reason": "Query is within Singapore public policy and labor market domain."
        }

    def extract_query_parameters(self, query: str) -> dict[str, Any]:
        """
        Extracts execution parameters (years, sector, metrics) from natural language query.
        """
        q_lower = query.lower()

        # Extract years (e.g., 2021 to 2023, 2020-2024, in 2022)
        years = [int(y) for y in re.findall(r'\b(20[1-2][0-9])\b', query)]
        if len(years) >= 2:
            start_year = min(years)
            end_year = max(years)
        elif len(years) == 1:
            start_year = years[0]
            end_year = 2024
        else:
            start_year = 2020
            end_year = 2024

        # Extract sector focus
        if any(w in q_lower for w in ["finance", "banking", "financial"]):
            sector = "Financial & Insurance Services"
        elif any(w in q_lower for w in ["manufacturing", "factory", "industrial"]):
            sector = "Manufacturing"
        elif any(w in q_lower for w in ["construction", "building"]):
            sector = "Construction"
        else:
            sector = "Information & Communications"

        # Determine metric focus
        focus_metrics = []
        if any(w in q_lower for w in ["wage", "salary", "income", "compensation"]):
            focus_metrics.append("wages")
        if any(w in q_lower for w in ["vacancy", "vacancies", "opening", "openings"]):
            focus_metrics.append("vacancies")
        if any(w in q_lower for w in ["retrench", "layoff", "redundancy"]):
            focus_metrics.append("retrenchments")
        if any(w in q_lower for w in ["employ", "workforce", "headcount", "jobs"]):
            focus_metrics.append("employment")
        if not focus_metrics:
            focus_metrics = ["employment", "vacancies", "retrenchments", "wages"]

        return {
            "start_year": start_year,
            "end_year": end_year,
            "sector": sector,
            "focus_metrics": focus_metrics
        }

    async def plan_research_workflow(self, query: str, provider_preference: str = "auto") -> dict[str, Any]:
        # Step 1: Query Scope Evaluation & Domain Guardrails
        await self.log_step(
            step_type=StepType.THOUGHT,
            title="Reasoning: Interpreting Query Intent & Geographic Scope",
            content=f"Evaluating user request: '{query}'. Checking geographic boundaries (Singapore public sector) and domain alignment."
        )

        scope_result = self.evaluate_query_scope(query)
        if scope_result["is_out_of_scope"]:
            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Domain Guardrail Triggered: Out of Scope",
                content=f"Rejected query: {scope_result['reason']}. Recommendation: {scope_result['suggestion']}"
            )
            return {
                "is_out_of_scope": True,
                "rejection_reason": scope_result["reason"],
                "suggestion": scope_result["suggestion"],
                "plan": None,
                "provider_used": "guardrail_engine",
                "tokens": 0
            }

        # Step 2: Parameter Extraction
        params = self.extract_query_parameters(query)
        await self.log_step(
            step_type=StepType.ACTION,
            title="Tool Call: query_parameter_extractor",
            content=f"Parsed parameters: Sector='{params['sector']}', Period={params['start_year']}-{params['end_year']}, Focus={', '.join(params['focus_metrics'])}.",
            tool_name="parameter_extractor",
            tool_input={"query": query},
            tool_output=params
        )

        # Step 3: LLM Dynamic Planning
        planning_prompt = f"""
You are the Lead Data Coordinator Agent for Singapore public policy research.
User Query: "{query}"
Extracted Parameters:
- Target Sector: {params['sector']}
- Time Horizon: {params['start_year']} to {params['end_year']}
- Key Metrics: {', '.join(params['focus_metrics'])}

Formulate a prioritized multi-source extraction and analysis plan across Singapore government repositories:
1. DOS SingStat (Employment time series)
2. MOM Statistics (Job vacancies & retrenchments)
3. Data.gov.sg (Salary benchmarks)
4. MOM Turnover Survey (Excel recruitment & turnover)
5. Internal Policy DB (TeSA and AI targets)

Return JSON with keys:
- "thought": string
- "subtasks": list of objects with "task_id", "source", "tool_name", "parameters"
- "expected_hypotheses": list of strings
"""
        response, attempts = await llm_router.generate(
            prompt=planning_prompt,
            system_prompt="You are an expert government research coordinator. Output actionable, valid JSON plans.",
            json_mode=True,
            preferred_provider=provider_preference
        )

        try:
            plan_data = json.loads(response.content)
            # Ensure parameters are attached to subtasks
            for st in plan_data.get("subtasks", []):
                st["parameters"] = {
                    "sector": params["sector"],
                    "start_year": params["start_year"],
                    "end_year": params["end_year"],
                    "focus_metrics": params["focus_metrics"]
                }
        except Exception:
            plan_data = {
                "thought": f"Executing structured research for {params['sector']} ({params['start_year']}-{params['end_year']}).",
                "subtasks": [
                    {
                        "task_id": "ST-01",
                        "source": "DOS SingStat",
                        "tool_name": "query_singstat_table",
                        "parameters": {"sector": params["sector"], "start_year": params["start_year"], "end_year": params["end_year"]}
                    },
                    {
                        "task_id": "ST-02",
                        "source": "MOM Statistics",
                        "tool_name": "query_mom_statistics",
                        "parameters": {"sector": params["sector"], "start_year": params["start_year"], "end_year": params["end_year"]}
                    },
                    {
                        "task_id": "ST-03",
                        "source": "Data.gov.sg",
                        "tool_name": "query_datagovsg_api",
                        "parameters": {"industry": params["sector"]}
                    },
                    {
                        "task_id": "ST-04",
                        "source": "MOM Excel",
                        "tool_name": "fetch_mom_turnover_excel",
                        "parameters": {"sector": params["sector"]}
                    },
                    {
                        "task_id": "ST-05",
                        "source": "Internal Policy DB",
                        "tool_name": "fetch_internal_policy_kpis",
                        "parameters": {}
                    }
                ],
                "expected_hypotheses": [
                    f"Employment in {params['sector']} demonstrated resilience between {params['start_year']} and {params['end_year']}.",
                    "Wage premiums and local workforce share remained stable despite macroeconomic headwinds."
                ]
            }

        await self.log_step(
            step_type=StepType.ACTION,
            title="Workflow Delegation: Parameterized Plan",
            content=f"Delegating {len(plan_data.get('subtasks', []))} parameterized subtasks to Data Extraction Agent.",
            tool_name="workflow_planner",
            tool_input={"parameters": params, "provider": response.provider_name},
            tool_output=plan_data
        )

        await self.log_step(
            step_type=StepType.OBSERVATION,
            title="Research Plan Confirmed",
            content=f"Research plan confirmed for {params['sector']} ({params['start_year']}-{params['end_year']}) using {response.provider_name}. Ready for data acquisition."
        )

        return {
            "is_out_of_scope": False,
            "parameters": params,
            "plan": plan_data,
            "provider_used": response.provider_name,
            "tokens": response.total_tokens
        }
