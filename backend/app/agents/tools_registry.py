from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.app.tools.government_sources import data_connector


class SectorWindowArgs(BaseModel):
    sector: str = Field(
        default="Information & Communications",
        description="Target Singapore sector: 'Information & Communications', 'Financial & Insurance Services', or 'Overall Economy'"
    )
    start_year: int = Field(default=2020, ge=2020, le=2024, description="Start year of observation (2020-2024)")
    end_year: int = Field(default=2024, ge=2020, le=2024, description="End year of observation (2020-2024)")

    @field_validator("sector", mode="before")
    @classmethod
    def normalize_sector(cls, v: Any) -> str:
        s = str(v).lower()
        if any(k in s for k in ["fin", "bank", "insur"]):
            return "Financial & Insurance Services"
        elif any(k in s for k in ["overall", "economy", "national"]):
            return "Overall Economy"
        elif any(k in s for k in ["tech", "ict", "info", "software", "digital"]):
            return "Information & Communications"
        return str(v)

    @field_validator("end_year")
    @classmethod
    def validate_year_order(cls, v: int, info) -> int:
        if "start_year" in info.data and v < info.data["start_year"]:
            raise ValueError(f"end_year ({v}) cannot precede start_year ({info.data['start_year']})")
        return v


class YearWindowArgs(BaseModel):
    start_year: int = Field(default=2020, ge=2020, le=2024, description="Start year of observation (2020-2024)")
    end_year: int = Field(default=2024, ge=2020, le=2024, description="End year of observation (2020-2024)")

    @field_validator("end_year")
    @classmethod
    def validate_year_order(cls, v: int, info) -> int:
        if "start_year" in info.data and v < info.data["start_year"]:
            raise ValueError(f"end_year ({v}) cannot precede start_year ({info.data['start_year']})")
        return v


class IndustryWageArgs(BaseModel):
    industry: str = Field(
        default="Information & Communications",
        description="Target industry sector for wage distribution benchmark"
    )

    @field_validator("industry", mode="before")
    @classmethod
    def normalize_industry(cls, v: Any) -> str:
        s = str(v).lower()
        if any(k in s for k in ["fin", "bank", "insur"]):
            return "Financial & Insurance Services"
        elif any(k in s for k in ["overall", "economy", "national"]):
            return "Overall Economy"
        elif any(k in s for k in ["tech", "ict", "info", "software", "digital"]):
            return "Information & Communications"
        return str(v)


class SectorTurnoverArgs(BaseModel):
    sector: str = Field(
        default="Information & Communications",
        description="Target industry sector for labour turnover analysis"
    )

    @field_validator("sector", mode="before")
    @classmethod
    def normalize_sector(cls, v: Any) -> str:
        s = str(v).lower()
        if any(k in s for k in ["fin", "bank", "insur"]):
            return "Financial & Insurance Services"
        elif any(k in s for k in ["overall", "economy", "national"]):
            return "Overall Economy"
        elif any(k in s for k in ["tech", "ict", "info", "software", "digital"]):
            return "Information & Communications"
        return str(v)


class EmptyArgs(BaseModel):
    pass


@dataclass
class AgentTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    func: Callable[..., Awaitable[dict[str, Any]]]


TOOL_REGISTRY: dict[str, AgentTool] = {
    "query_singstat_table": AgentTool(
        name="query_singstat_table",
        description="Query Singapore Department of Statistics (DOS) Table 14.1 for quarterly employment headcount, YoY growth, and resident workforce share.",
        args_schema=SectorWindowArgs,
        func=data_connector.fetch_singstat_employment
    ),
    "query_mom_statistics": AgentTool(
        name="query_mom_statistics",
        description="Query Ministry of Manpower (MOM) Labour Market Indicators for quarterly job vacancies, retrenchments, vacancy-to-unemployed ratio, and 6-month re-entry rate.",
        args_schema=YearWindowArgs,
        func=data_connector.fetch_mom_labour_indicators
    ),
    "query_datagovsg_api": AgentTool(
        name="query_datagovsg_api",
        description="Query Data.gov.sg API v2 for annual sector median gross monthly wages, 25th/75th percentiles, and specialized occupation benchmarks.",
        args_schema=IndustryWageArgs,
        func=data_connector.fetch_datagovsg_wages
    ),
    "fetch_mom_turnover_excel": AgentTool(
        name="fetch_mom_turnover_excel",
        description="Query MOM Labour Turnover Survey from Excel spreadsheet for sector recruitment, resignation, and net turnover rates.",
        args_schema=SectorTurnoverArgs,
        func=data_connector.fetch_mom_turnover_excel
    ),
    "fetch_internal_policy_kpis": AgentTool(
        name="fetch_internal_policy_kpis",
        description="Query Internal Policy Database in SQLite for TeSA and National AI Strategy 2.0 KPI targets, actuals, and budget tracking.",
        args_schema=EmptyArgs,
        func=data_connector.fetch_internal_policy_kpis
    )
}
