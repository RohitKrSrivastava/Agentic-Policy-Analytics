from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

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
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DataQualityItem(BaseModel):
    dataset_name: str
    source_type: str
    total_records: int
    missing_values_handled: int
    outliers_identified: int
    completeness_score: float # 0.0 to 100.0%
    data_format: str
    cleaning_applied: List[str] = []

class ChartSeriesItem(BaseModel):
    name: str
    data: List[Dict[str, Any]]

class ChartSpecification(BaseModel):
    chart_id: str
    title: str
    chart_type: str # 'line', 'bar', 'composed', 'area'
    x_key: str
    y_keys: List[str]
    series: List[Dict[str, Any]]
    y_axis_label: Optional[str] = None
    annotations: Optional[List[str]] = []

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
    key_findings: List[PolicyFinding]
    statistical_metrics: Dict[str, Any]
    policy_recommendations: List[str]
    citations: List[PolicyCitation]
    quality_score: float
    hallucination_score: float # 0 to 1.0 (lower is better; factual fidelity)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class QueryRequest(BaseModel):
    query: str = Field(..., example="Analyse employment trends in the technology sector from 2020-2024")
    provider_preference: Optional[str] = Field("auto", example="auto") # auto, openai, gemini, bedrock, local_fallback
    include_forecasting: Optional[bool] = True
    deep_verification: Optional[bool] = True

class SessionResponse(BaseModel):
    session_id: str
    query: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    current_agent: Optional[str] = None
    current_step: Optional[str] = None
    progress_pct: int = 0
    logs: List[AgentStepLog] = []
    charts: List[ChartSpecification] = []
    quality_reports: List[DataQualityItem] = []
    report: Optional[PolicyReport] = None
    error_message: Optional[str] = None
    llm_provider_used: Optional[str] = None
    tokens_consumed: Optional[int] = 0

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
    active_providers: List[ProviderHealth]
    default_strategy: List[str]
    total_analyses_run: int
