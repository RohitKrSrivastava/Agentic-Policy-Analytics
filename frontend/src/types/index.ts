export type AgentType = 
  | 'Data Coordinator Agent'
  | 'Data Extraction Agent'
  | 'Analytics Agent'
  | 'Hallucination Verification Guard';

export type StepType = 'thought' | 'action' | 'observation' | 'reflection' | 'summary' | 'error';

export type SessionStatus = 
  | 'pending'
  | 'planning'
  | 'extracting'
  | 'analyzing'
  | 'verifying'
  | 'completed'
  | 'failed';

export interface AgentStepLog {
  id: string;
  session_id: string;
  agent: AgentType;
  step_type: StepType;
  title: string;
  content: string;
  tool_name?: string;
  tool_input?: any;
  tool_output?: any;
  timestamp: string;
}

export interface DataQualityItem {
  dataset_name: string;
  source_type: string;
  total_records: number;
  missing_values_handled: number;
  outliers_identified: number;
  completeness_score: number;
  data_format: string;
  cleaning_applied: string[];
}

export interface ChartSpecification {
  chart_id: string;
  title: string;
  chart_type: 'line' | 'bar' | 'composed' | 'area';
  x_key: string;
  y_keys: string[];
  series: any[];
  y_axis_label?: string;
  annotations?: string[];
}

export interface PolicyCitation {
  source_agency: string;
  dataset_title: string;
  time_period: string;
  citation_id: string;
  access_method: string;
}

export interface PolicyFinding {
  heading: string;
  body: string;
  sentiment: 'positive' | 'neutral' | 'cautionary';
  statistical_evidence: string;
  citation_id: string;
}

export interface PolicyReport {
  session_id: string;
  query: string;
  title: string;
  executive_summary: string;
  key_findings: PolicyFinding[];
  statistical_metrics: Record<string, any>;
  policy_recommendations: string[];
  citations: PolicyCitation[];
  quality_score: number;
  hallucination_score: number;
  generated_at: string;
}

export interface SessionResponse {
  session_id: string;
  query: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  current_agent?: string;
  current_step?: string;
  progress_pct: number;
  logs: AgentStepLog[];
  charts: ChartSpecification[];
  quality_reports: DataQualityItem[];
  report?: PolicyReport;
  error_message?: string;
  llm_provider_used?: string;
  tokens_consumed?: number;
}

export interface ProviderHealth {
  provider_name: string;
  status: 'active' | 'standby' | 'simulated' | 'unconfigured' | 'error';
  latency_ms: number;
  model_name: string;
  cost_per_1k_tokens: number;
  is_fallback_available: boolean;
}

export interface SystemHealthResponse {
  status: string;
  timestamp: string;
  active_providers: ProviderHealth[];
  default_strategy: string[];
  total_analyses_run: number;
}
