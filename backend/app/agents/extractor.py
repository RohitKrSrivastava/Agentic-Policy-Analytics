import logging
from collections.abc import Callable
from typing import Any

from backend.app.agents.base_agent import BaseAgent
from backend.app.models.schemas import AgentType, DataQualityItem, StepType
from backend.app.tools.data_quality import quality_engine
from backend.app.tools.government_sources import data_connector

logger = logging.getLogger("extractor_agent")

class DataExtractionAgent(BaseAgent):
    """
    Data Extraction Agent:
    - Receives parameterized execution plan from Coordinator Agent.
    - Dynamically extracts datasets from multiple Singapore government sources:
      1. DOS SingStat (CSV)
      2. MOM Labour Market Indicators (JSON)
      3. Data.gov.sg Wages (REST API / Schema Validated JSON)
      4. MOM Labour Turnover Survey (Excel .xlsx)
      5. Internal Policy DB (SQLite)
    - Applies schema normalization, IQR outlier capping, and empirical completeness assessment.
    - Transparently reports individual source success, partial failures, and exact data provenance.
    """
    def __init__(self, session_id: str, log_callback: Callable | None = None):
        super().__init__(AgentType.EXTRACTION, session_id, log_callback)

    async def extract_sources(self, plan: dict[str, Any] | None = None, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Executes parameterized data extraction using parameters derived from the user query.
        """
        params = parameters or (plan.get("parameters") if plan else {}) or {}
        start_year = params.get("start_year", 2020)
        end_year = params.get("end_year", 2024)
        sector = params.get("sector", "Information & Communications")

        datasets: dict[str, Any] = {}
        quality_reports: list[DataQualityItem] = []
        source_provenance: dict[str, str] = {}

        # -------------------------------------------------------------
        # 1. DOS SingStat (CSV)
        # -------------------------------------------------------------
        await self.log_step(
            step_type=StepType.THOUGHT,
            title="Reasoning: Extracting DOS SingStat Employment Time Series",
            content=f"Connecting to DOS SingStat Table 14.1 for '{sector}' employment time series ({start_year} to {end_year})."
        )

        singstat_res = await data_connector.fetch_singstat_employment(
            sector=sector,
            start_year=start_year,
            end_year=end_year
        )
        source_provenance["singstat"] = singstat_res.get("source", "DOS SingStat CSV")

        await self.log_step(
            step_type=StepType.ACTION,
            title="Tool Call: query_singstat_table",
            content=f"Invoking query_singstat_table: sector='{sector}', start_year={start_year}, end_year={end_year}.",
            tool_name="query_singstat_table",
            tool_input={"format": "CSV", "sector": sector, "start_year": start_year, "end_year": end_year},
            tool_output={"records_retrieved": singstat_res.get("total_records", 0), "status": singstat_res.get("status")}
        )

        if singstat_res.get("status") == "success" and singstat_res.get("data"):
            cleaned_singstat, sq_report = quality_engine.audit_and_clean(
                data=singstat_res.get("data", []),
                dataset_name=f"DOS SingStat Employment ({sector})",
                source_type="Department of Statistics Singapore",
                data_format="CSV",
                numeric_columns=["employment_thousands", "growth_rate_yoy", "local_workforce_pct", "productivity_index"]
            )
            datasets["singstat"] = cleaned_singstat
            quality_reports.append(sq_report)

            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Observation: DOS SingStat Quality Audit",
                content=f"Acquired {sq_report.total_records} quarterly records. Empirical Completeness: {sq_report.completeness_score}%. Handled {sq_report.missing_values_handled} nulls and {sq_report.outliers_identified} outliers."
            )
        else:
            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Observation: DOS SingStat Acquisition Warning",
                content=f"SingStat query returned 0 records or error: {singstat_res.get('error', 'No matching records for specified filter')}."
            )

        # -------------------------------------------------------------
        # 2. MOM Labour Market Indicators (JSON)
        # -------------------------------------------------------------
        await self.log_step(
            step_type=StepType.THOUGHT,
            title="Reasoning: Extracting MOM Labour Market Dynamics",
            content=f"Requesting quarterly job vacancies, retrenchments, and unemployment ratios from Ministry of Manpower (MOM) for {start_year}-{end_year}."
        )

        mom_res = await data_connector.fetch_mom_labour_indicators(
            start_year=start_year,
            end_year=end_year
        )
        source_provenance["mom"] = mom_res.get("source", "MOM Statistics JSON")

        await self.log_step(
            step_type=StepType.ACTION,
            title="Tool Call: query_mom_statistics",
            content=f"Invoking query_mom_statistics for series {start_year}-{end_year}.",
            tool_name="query_mom_statistics",
            tool_input={"format": "JSON", "start_year": start_year, "end_year": end_year},
            tool_output={"records_retrieved": mom_res.get("total_records", 0)}
        )

        if mom_res.get("status") == "success" and mom_res.get("data"):
            cleaned_mom, mq_report = quality_engine.audit_and_clean(
                data=mom_res.get("data", []),
                dataset_name="MOM Labour Market Report (Vacancies & Retrenchments)",
                source_type="Ministry of Manpower Singapore",
                data_format="JSON",
                numeric_columns=["tech_job_vacancies", "tech_retrenchments", "vacancy_to_unemployed_ratio", "reentry_rate_pct"]
            )
            datasets["mom"] = cleaned_mom
            quality_reports.append(mq_report)

            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Observation: MOM Statistics Quality Audit",
                content=f"Acquired {mq_report.total_records} quarterly records. Empirical Completeness: {mq_report.completeness_score}%. Integrity verified."
            )
        else:
            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Observation: MOM Statistics Notice",
                content=f"MOM query notice: {mom_res.get('error', 'No records found')}."
            )

        # -------------------------------------------------------------
        # 3. Data.gov.sg Wages (REST API / Schema-Validated JSON)
        # -------------------------------------------------------------
        await self.log_step(
            step_type=StepType.THOUGHT,
            title="Reasoning: Querying Data.gov.sg Salary Benchmarks",
            content=f"Connecting to Data.gov.sg API v2 to retrieve gross monthly wages for '{sector}' vs National Median."
        )

        wage_res = await data_connector.fetch_datagovsg_wages(industry=sector)
        source_provenance["wages"] = wage_res.get("access_method", "Data.gov.sg API")

        await self.log_step(
            step_type=StepType.ACTION,
            title="Tool Call: query_datagovsg_api",
            content=f"Invoking query_datagovsg_api via {wage_res.get('access_method')}.",
            tool_name="query_datagovsg_api",
            tool_input={"industry": sector, "access_method": wage_res.get("access_method")},
            tool_output={"records_retrieved": wage_res.get("total_records", 0)}
        )

        if wage_res.get("status") == "success" and wage_res.get("data"):
            cleaned_wages, wq_report = quality_engine.audit_and_clean(
                data=wage_res.get("data", []),
                dataset_name=f"Data.gov.sg Monthly Gross Income ({sector})",
                source_type=wage_res.get("source", "Data.gov.sg"),
                data_format=wage_res.get("format", "JSON"),
                numeric_columns=["median_gross_wage_sgd", "p25_gross_wage_sgd", "p75_gross_wage_sgd"]
            )
            datasets["wages"] = cleaned_wages
            quality_reports.append(wq_report)

            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Observation: Data.gov.sg Wage Benchmark Audit",
                content=f"Extracted {wq_report.total_records} validated observations via {wage_res.get('access_method')}. Completeness: {wq_report.completeness_score}%."
            )

        # -------------------------------------------------------------
        # 4. MOM Labour Turnover (Excel .xlsx)
        # -------------------------------------------------------------
        await self.log_step(
            step_type=StepType.THOUGHT,
            title="Reasoning: Extracting Excel File for Labour Turnover Rates",
            content=f"Parsing MOM Excel spreadsheet (.xlsx) for '{sector}' recruitment, resignation, and net turnover indicators."
        )

        excel_res = await data_connector.fetch_mom_turnover_excel(sector=sector)
        source_provenance["excel_turnover"] = excel_res.get("source", "MOM Excel Survey")

        if excel_res.get("status") == "success" and excel_res.get("data"):
            cleaned_excel, eq_report = quality_engine.audit_and_clean(
                data=excel_res.get("data", []),
                dataset_name=f"MOM Labour Turnover Survey ({sector})",
                source_type="Ministry of Manpower Singapore",
                data_format="Excel (.xlsx)",
                numeric_columns=["Job_Vacancies", "Recruitment_Rate_Pct", "Resignation_Rate_Pct", "Net_Turnover_Rate"]
            )
            datasets["excel_turnover"] = cleaned_excel
            quality_reports.append(eq_report)

            await self.log_step(
                step_type=StepType.OBSERVATION,
                title="Observation: MOM Excel Survey Parsed",
                content=f"Extracted {eq_report.total_records} sector rows from Excel spreadsheet. Completeness: {eq_report.completeness_score}%."
            )

        # -------------------------------------------------------------
        # 5. Internal Policy DB (SQLite)
        # -------------------------------------------------------------
        policy_db_res = await data_connector.fetch_internal_policy_kpis()
        datasets["policy_kpis"] = policy_db_res
        source_provenance["policy_kpis"] = policy_db_res.get("source", "Internal Policy DB")

        # Compute empirical overall completeness score across active datasets
        if quality_reports:
            avg_completeness = round(sum(q.completeness_score for q in quality_reports) / len(quality_reports), 1)
        else:
            avg_completeness = 0.0

        await self.log_step(
            step_type=StepType.REFLECTION,
            title="Extraction Reflection & Cross-Source Synthesis",
            content=f"Acquired {len(datasets)} dataset groups for '{sector}' ({start_year}-{end_year}). Measured average empirical completeness: {avg_completeness}%. Provenance: Data.gov.sg ({wage_res.get('access_method')}), DOS SingStat ({singstat_res.get('source')})."
        )

        return {
            "datasets": datasets,
            "quality_reports": quality_reports,
            "provenance": source_provenance,
            "overall_quality_score": avg_completeness
        }

    # Backward compatibility alias
    async def extract_all_sources(self) -> dict[str, Any]:
        return await self.extract_sources()
