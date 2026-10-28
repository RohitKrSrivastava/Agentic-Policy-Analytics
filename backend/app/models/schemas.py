from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    COORDINATOR = "Data Coordinator Agent"
    EXTRACTION = "Data Extraction Agent"
    ANALYTICS = "Analytics Agent"
    HALLUCINATION_GUARD = "Hallucination Verification Guard"

class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    SUMMARY = "summary"
    ERROR = "error"

class SessionStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentStepLog(BaseModel):
    id: str
    session_id: str
    agent: AgentType
    step_type: StepType
    title: str
    content: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DataQualityItem(BaseModel):
    dataset_name: str
    source_type: str
    total_records: int
    missing_values_handled: int
    outliers_identified: int
    completeness_score: float # 0.0 to 100.0%
    data_format: str
    cleaning_applied: list[str] = []

class ChartSeriesItem(BaseModel):
    name: str
    data: list[dict[str, Any]]

class ChartSpecification(BaseModel):
    chart_id: str
    title: str
    chart_type: str # 'line', 'bar', 'composed', 'area'
    x_key: str
    y_keys: list[str]
    series: list[dict[str, Any]]
    y_axis_label: str | None = None
    annotations: list[str] | None = []

class PolicyCitation(BaseModel):
    source_agency: str
    dataset_title: str
    time_period: str
    citation_id: str
    access_method: str # 'Data.gov.sg API v2', 'DOS SingStat Table M015661', 'MOM Labour Market Report'

class PolicyFinding(BaseModel):
    heading: str
    body: str
    sentiment: str # 'positive', 'neutral', 'cautionary'
    statistical_evidence: str
    citation_id: str

class PolicyReport(BaseModel):
    session_id: str
    query: str
    title: str
    executive_summary: str
    key_findings: list[PolicyFinding]
    statistical_metrics: dict[str, Any]
    policy_recommendations: list[str]
    citations: list[PolicyCitation]
    quality_score: float
    hallucination_score: float # 0 to 1.0 (lower is better; factual fidelity)
    verification_status: str = "verified" # 'verified', 'partially_verified', 'unverified', 'unverifiable'
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class QueryRequest(BaseModel):
    query: str = Field(..., example="Analyse employment trends in the technology sector from 2020-2024")
    provider_preference: str | None = Field("auto", example="auto") # auto, openai, gemini, bedrock, local_fallback
    include_forecasting: bool | None = True
    deep_verification: bool | None = True

class SessionResponse(BaseModel):
    session_id: str
    query: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    current_agent: str | None = None
    current_step: str | None = None
    progress_pct: int = 0
    logs: list[AgentStepLog] = []
    charts: list[ChartSpecification] = []
    quality_reports: list[DataQualityItem] = []
    report: PolicyReport | None = None
    error_message: str | None = None
    llm_provider_used: str | None = None
    tokens_consumed: int | None = 0

class ProviderHealth(BaseModel):
    provider_name: str
    status: str # 'active', 'standby', 'simulated', 'error'
    latency_ms: float
    model_name: str
    cost_per_1k_tokens: float
    is_fallback_available: bool

class SystemHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    active_providers: list[ProviderHealth]
    default_strategy: list[str]
    total_analyses_run: int
