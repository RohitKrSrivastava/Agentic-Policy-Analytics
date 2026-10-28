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
    - Interprets query intent, domain validity, geographic boundary, and temporal coverage.
    - Handles ambiguity and prompts user for clarification when query lacks analytical direction.
    - Formulates structured, tool-selected execution plans based on target metrics.
    - Delegates specific subtasks with parameters to the Data Extraction Agent.
    """
    def __init__(self, session_id: str, log_callback: Callable | None = None):
        super().__init__(AgentType.COORDINATOR, session_id, log_callback)

    def evaluate_query_scope(self, query: str) -> dict[str, Any]:
        """
        Determines if the query is within Singapore public sector manpower & policy domain.
        Catches:
        1. Ambiguous/generic queries ("tell me something", "help", "analyze").
        2. Unsupported geographies (e.g. Malaysia, US).
        3. Unrelated topics (weather, recipes, crypto).
        4. Unsupported sectors (retail, manufacturing, construction, healthcare).
        5. Out-of-bounds year windows (< 2020 or > 2024).
        """
        q_lower = query.lower().strip()

        # 1. Ambiguity / Generic Query Detection
        ambiguous_exact = [
            "tell me something", "hello", "hi", "hey", "help", "what can you do",
            "show me data", "analyze", "analyse", "run", "do analysis", "test",
            "report", "singapore", "singapore data", "tell me", "give me data",
            "show report", "policy"
        ]
        if q_lower in ambiguous_exact or re.match(r'^(tell\s+me\s+something|what\s+is\s+happening|what\s+can\s+you\s+do|show\s+me\s+something)[\.\?\!]?$', q_lower):
            return {
                "is_out_of_scope": True,
                "is_ambiguous": True,
                "reason": "The query lacks specific analytical parameters (target sector, timeframe, or policy metrics).",
                "suggestion": "Please clarify your research parameters: 1) Target Sector (Information & Communications, Financial Services, Overall Economy), 2) Timeframe (within 2020-2024), and 3) Metrics of interest (employment trends, vacancies, retrenchments, or wage benchmarks)."
            }

        # 2. Geographic Boundary Check
        unsupported_geos = [
            "malaysia", "indonesia", "thailand", "vietnam", "philippines",
            "united states", "usa", "uk", "britain", "europe", "india", "china", "japan"
        ]
        for geo in unsupported_geos:
            if re.search(r'\b' + re.escape(geo) + r'\b', q_lower):
                return {
                    "is_out_of_scope": True,
                    "is_ambiguous": False,
                    "reason": f"Geographic domain boundary: Query targets '{geo.title()}', but this platform is specialized for Singapore Public Sector (WOG/IMDA/MOM/DOS) data repositories.",
                    "suggestion": "Please refine your query to Singapore policy domains (e.g. Singapore technology employment, MOM labor market dynamics, or national wage benchmarks)."
                }

        # 3. Topic / Domain Check
        unsupported_topics = [
            "weather", "forecast tomorrow", "temperature", "rain", "recipe",
            "cook", "horoscope", "crypto price", "bitcoin", "sports score",
            "movie", "celebrity", "joke"
        ]
        for topic in unsupported_topics:
            if re.search(r'\b' + re.escape(topic) + r'\b', q_lower):
                return {
                    "is_out_of_scope": True,
                    "is_ambiguous": False,
                    "reason": f"Topic domain mismatch: '{topic}' is outside the scope of Singapore manpower, wage economics, and public policy analytics.",
                    "suggestion": "This platform analyzes Singapore employment trends, workforce transitions, wage distributions, and policy initiatives."
                }

        # 4. Unsupported Sector Check
        unsupported_sectors = [
            "retail", "manufacturing", "construction", "healthcare", "hospitality",
            "aviation", "f&b", "food and beverage", "agriculture", "mining", "transport"
        ]
        for unsup in unsupported_sectors:
            if re.search(r'\b' + re.escape(unsup) + r'\b', q_lower):
                return {
                    "is_out_of_scope": True,
                    "is_ambiguous": False,
                    "reason": f"Sector data boundary: The '{unsup.title()}' sector is not present in the current Singapore WOG demonstration datasets.",
                    "suggestion": "Integrated repositories currently cover: Information & Communications (SSIC J), Financial & Insurance Services (SSIC K), and Overall Economy (2020-2024). Please query one of these supported sectors."
                }

        # 5. Out-of-bounds Year Window Check
        years = [int(y) for y in re.findall(r'\b(20[0-2][0-9]|19[0-9]{2})\b', query)]
        if years and all(y < 2020 or y > 2024 for y in years):
            return {
                "is_out_of_scope": True,
                "is_ambiguous": False,
                "reason": f"Time horizon boundary: Requested years ({min(years)}-{max(years)}) fall outside public sector dataset coverage.",
                "suggestion": "Authoritative Singapore government datasets in this platform cover the five-year window 2020–2024. Please specify an analytical timeframe within 2020-2024."
            }

        return {
            "is_out_of_scope": False,
            "is_ambiguous": False,
            "reason": "Query is within Singapore public policy and labor market domain."
        }

    def extract_query_parameters(self, query: str) -> dict[str, Any]:
        q_lower = query.lower()

        # Extract years (clamped to 2020-2024 coverage)
        years = [int(y) for y in re.findall(r'\b(20[1-2][0-9])\b', query)]
        if len(years) >= 2:
            start_year = max(2020, min(years))
            end_year = min(2024, max(years))
        elif len(years) == 1:
            start_year = max(2020, min(years[0], 2024))
            end_year = 2024
        else:
            start_year = 2020
            end_year = 2024

        # Extract sector focus
        if any(w in q_lower for w in ["finance", "banking", "financial", "insurance"]):
            sector = "Financial & Insurance Services"
        elif any(w in q_lower for w in ["overall", "economy", "all sector", "national"]):
            sector = "Overall Economy"
        else:
            sector = "Information & Communications"

        # Determine metric focus
        focus_metrics = []
        if any(w in q_lower for w in ["wage", "salary", "income", "compensation", "remuneration"]):
            focus_metrics.append("wages")
        if any(w in q_lower for w in ["vacancy", "vacancies", "opening", "openings"]):
            focus_metrics.append("vacancies")
        if any(w in q_lower for w in ["retrench", "layoff", "redundancy"]):
            focus_metrics.append("retrenchments")
        if any(w in q_lower for w in ["employ", "workforce", "headcount", "jobs", "hiring"]):
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
            title="Reasoning: Interpreting Query Intent, Domain Scope & Ambiguity",
            content=f"Evaluating user request: '{query}'. Checking geographic boundary, sector availability, time horizon (2020-2024), and clarity."
        )

        scope_result = self.evaluate_query_scope(query)
        if scope_result["is_out_of_scope"]:
            guardrail_title = "Clarification Required: Ambiguous Query" if scope_result.get("is_ambiguous") else "Domain Guardrail Triggered: Data Scope Boundary"
            await self.log_step(
                step_type=StepType.OBSERVATION,
                title=guardrail_title,
                content=f"Notice: {scope_result['reason']} Recommendation: {scope_result['suggestion']}"
            )
            return {
                "is_out_of_scope": True,
                "is_ambiguous": scope_result.get("is_ambiguous", False),
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

        # Step 3: Tool Selection & LLM Dynamic Planning
        selected_tools = []
        if "employment" in params["focus_metrics"] or len(params["focus_metrics"]) > 2:
            selected_tools.append({
                "task_id": "ST-01",
                "source": "DOS SingStat",
                "tool_name": "query_singstat_table",
                "reasoning": f"Extract quarterly {params['sector']} employment time series ({params['start_year']}-{params['end_year']}) to model CAGR and workforce trajectory.",
                "parameters": {"sector": params["sector"], "start_year": params["start_year"], "end_year": params["end_year"]}
            })
        if "vacancies" in params["focus_metrics"] or "retrenchments" in params["focus_metrics"] or len(params["focus_metrics"]) > 2:
            selected_tools.append({
                "task_id": "ST-02",
                "source": "MOM Statistics",
                "tool_name": "query_mom_statistics",
                "reasoning": f"Acquire MOM quarterly job vacancies, retrenchments, and vacancy-to-unemployed ratio for {params['start_year']}-{params['end_year']}.",
                "parameters": {"sector": params["sector"], "start_year": params["start_year"], "end_year": params["end_year"]}
            })
        if "wages" in params["focus_metrics"] or len(params["focus_metrics"]) > 2:
            selected_tools.append({
                "task_id": "ST-03",
                "source": "Data.gov.sg",
                "tool_name": "query_datagovsg_api",
                "reasoning": f"Connect to Data.gov.sg wage benchmarks to assess {params['sector']} salary distribution and wage premium over national median.",
                "parameters": {"industry": params["sector"]}
            })
        if "vacancies" in params["focus_metrics"] or len(params["focus_metrics"]) > 2:
            selected_tools.append({
                "task_id": "ST-04",
                "source": "MOM Excel",
                "tool_name": "fetch_mom_turnover_excel",
                "reasoning": f"Extract recruitment and resignation rates from MOM Labour Turnover Survey for {params['sector']}.",
                "parameters": {"sector": params["sector"]}
            })
        selected_tools.append({
            "task_id": f"ST-0{len(selected_tools)+1}",
            "source": "Internal Policy DB",
            "tool_name": "fetch_internal_policy_kpis",
            "reasoning": "Retrieve strategic policy initiatives, funding allocations, and TeSA / AI Strategy 2.0 KPI benchmarks.",
            "parameters": {}
        })

        planning_prompt = f"""
You are the Lead Data Coordinator Agent for Singapore public policy research.
User Query: "{query}"
Extracted Parameters:
- Target Sector: {params['sector']}
- Time Horizon: {params['start_year']} to {params['end_year']}
- Key Metrics: {', '.join(params['focus_metrics'])}

Selected Tools for Execution:
{json.dumps(selected_tools, indent=2)}

Formulate a prioritized multi-source extraction plan. Return valid JSON:
{{
  "thought": string,
  "subtasks": list of objects with "task_id", "source", "tool_name", "reasoning", "parameters",
  "expected_hypotheses": list of strings
}}
"""
        response, attempts = await llm_router.generate(
            prompt=planning_prompt,
            system_prompt="You are an expert government research coordinator. Output actionable, valid JSON plans.",
            json_mode=True,
            preferred_provider=provider_preference
        )

        try:
            plan_data = json.loads(response.content)
            # Ensure each subtask has valid tool_name and parameters
            if not plan_data.get("subtasks"):
                plan_data["subtasks"] = selected_tools
            else:
                for st in plan_data.get("subtasks", []):
                    if "parameters" not in st or not st["parameters"]:
                        st["parameters"] = {
                            "sector": params["sector"],
                            "start_year": params["start_year"],
                            "end_year": params["end_year"]
                        }
        except Exception:
            plan_data = {
                "thought": f"Formulating dynamic tool execution plan for {params['sector']} ({params['start_year']}-{params['end_year']}).",
                "subtasks": selected_tools,
                "expected_hypotheses": [
                    f"Employment in {params['sector']} demonstrated positive structural expansion between {params['start_year']} and {params['end_year']}.",
                    "Wage premiums and local workforce share remained resilient despite macroeconomic normalization."
                ]
            }

        await self.log_step(
            step_type=StepType.ACTION,
            title="Tool Selection: Dynamic Execution Plan",
            content=f"Selected {len(plan_data.get('subtasks', []))} targeted tools across Singapore government repositories. Delegating plan to Data Extraction Agent.",
            tool_name="workflow_planner",
            tool_input={"parameters": params, "selected_tools": [t["tool_name"] for t in plan_data.get("subtasks", [])]},
            tool_output=plan_data
        )

        await self.log_step(
            step_type=StepType.OBSERVATION,
            title="Research Plan Confirmed",
            content=f"Plan confirmed for {params['sector']} ({params['start_year']}-{params['end_year']}) using {response.provider_name}. {len(plan_data.get('subtasks', []))} subtasks ready for execution."
        )

        return {
            "is_out_of_scope": False,
            "parameters": params,
            "plan": plan_data,
            "provider_used": response.provider_name,
            "tokens": response.total_tokens
        }
