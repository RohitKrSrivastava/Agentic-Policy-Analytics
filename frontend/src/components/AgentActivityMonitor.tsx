import React, { useState } from 'react';
import { 
  Bot, 
  Search, 
  BarChart3, 
  ShieldCheck, 
  BrainCircuit, 
  Wrench, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp, 
  Clock, 
  AlertCircle 
} from 'lucide-react';
import { AgentStepLog, SessionStatus, AgentType, StepType } from '../types';

interface AgentActivityMonitorProps {
  logs: AgentStepLog[];
  status: SessionStatus;
  progressPct: number;
  currentAgent?: string;
  currentStep?: string;
}

export const AgentActivityMonitor: React.FC<AgentActivityMonitorProps> = ({
  logs,
  status,
  progressPct,
  currentAgent,
  currentStep
}) => {
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  const getAgentBadge = (agent: AgentType) => {
    switch (agent) {
      case 'Data Coordinator Agent':
        return {
          icon: BrainCircuit,
          color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
          dot: 'bg-indigo-500'
        };
      case 'Data Extraction Agent':
        return {
          icon: Search,
          color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
          dot: 'bg-emerald-500'
        };
      case 'Analytics Agent':
        return {
          icon: BarChart3,
          color: 'text-sky-600 bg-sky-50 border-sky-200',
          dot: 'bg-sky-500'
        };
      case 'Hallucination Verification Guard':
        return {
          icon: ShieldCheck,
          color: 'text-purple-600 bg-purple-50 border-purple-200',
          dot: 'bg-purple-500'
        };
      default:
        return {
          icon: Bot,
          color: 'text-slate-600 bg-slate-50 border-slate-200',
          dot: 'bg-slate-500'
        };
    }
  };

  const getStepTypeBadge = (type: StepType) => {
    switch (type) {
      case 'thought':
        return <span className="bg-amber-100 text-amber-800 border border-amber-200 text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider">Thought (Reasoning)</span>;
      case 'action':
        return <span className="bg-sky-100 text-sky-800 border border-sky-200 text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider">Action (Tool Execution)</span>;
      case 'observation':
        return <span className="bg-emerald-100 text-emerald-800 border border-emerald-200 text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider">Observation (Result)</span>;
      case 'reflection':
        return <span className="bg-purple-100 text-purple-800 border border-purple-200 text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider">Reflection (Audit)</span>;
      case 'error':
        return <span className="bg-rose-100 text-rose-800 border border-rose-200 text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider">Error</span>;
      default:
        return <span className="bg-slate-100 text-slate-700 text-[10px] font-semibold px-2 py-0.5 rounded uppercase">{type}</span>;
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      
      {/* Header & Agent Flow Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="font-bold text-slate-800 text-base">Autonomous Multi-Agent Activity</h3>
            <span className="bg-slate-100 text-slate-600 font-mono text-xs px-2 py-0.5 rounded">
              ReAct Orchestration
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time trace of autonomous agent deliberation, tool invocation, and factuality verification.
          </p>
        </div>

        {/* Progress Bar & Status Chip */}
        <div className="w-full md:w-64">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="font-semibold text-slate-700 capitalize flex items-center">
              {status === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mr-1" />}
              {status}
            </span>
            <span className="font-mono text-slate-500 font-medium">{progressPct}%</span>
          </div>
          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${
                status === 'completed' ? 'bg-emerald-500' : 'bg-sky-500'
              }`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* 4 Agent Collaboration Architecture Status Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 my-4">
        {[
          { name: "Coordinator Agent", role: "Plans workflow & delegates", icon: BrainCircuit, activeAt: ["planning", "extracting", "analyzing", "completed"] },
          { name: "Extraction Agent", role: "SingStat, MOM, Data.gov.sg", icon: Search, activeAt: ["extracting", "analyzing", "completed"] },
          { name: "Analytics Agent", role: "Econometric models & RAG", icon: BarChart3, activeAt: ["analyzing", "completed"] },
          { name: "Hallucination Guard", role: "Factuality & Grounding Audit", icon: ShieldCheck, activeAt: ["completed"] },
        ].map((ag, i) => {
          const isActive = ag.activeAt.includes(status);
          const isCurrent = currentAgent?.includes(ag.name.split(" ")[0]);
          return (
            <div 
              key={i}
              className={`p-3 rounded-xl border transition ${
                isCurrent 
                  ? 'bg-sky-50/80 border-sky-300 ring-2 ring-sky-100' 
                  : isActive
                  ? 'bg-slate-50/70 border-slate-200'
                  : 'bg-slate-50/30 border-slate-100 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <ag.icon className={`w-4 h-4 ${isCurrent ? 'text-sky-600 animate-bounce' : isActive ? 'text-slate-700' : 'text-slate-400'}`} />
                <span className="text-xs font-bold text-slate-800">{ag.name}</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 truncate">{ag.role}</p>
            </div>
          );
        })}
      </div>

      {/* ReAct Thought Timeline */}
      <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
        {logs.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs flex flex-col items-center">
            <Clock className="w-6 h-6 mb-2 opacity-50" />
            <span>Awaiting query submission. The multi-agent coordinator will commence here.</span>
          </div>
        ) : (
          logs.map((log) => {
            const badge = getAgentBadge(log.agent);
            const isExpanded = expandedLogId === log.id;

            return (
              <div 
                key={log.id}
                className="bg-slate-50/80 hover:bg-slate-50 border border-slate-200 rounded-xl p-3.5 transition text-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className={`w-2 h-2 rounded-full ${badge.dot}`} />
                    <span className="font-semibold text-slate-800">{log.agent}</span>
                    {getStepTypeBadge(log.step_type)}
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>

                <div className="mt-2 text-slate-700 font-medium">
                  {log.title}
                </div>

                <p className="mt-1 text-slate-600 leading-relaxed whitespace-pre-wrap">
                  {log.content}
                </p>

                {/* Tool Call Payload Accordion */}
                {(log.tool_name || log.tool_input || log.tool_output) && (
                  <div className="mt-2 pt-2 border-t border-slate-200/60">
                    <button
                      type="button"
                      onClick={() => toggleExpand(log.id)}
                      className="flex items-center space-x-1.5 text-[11px] text-sky-600 hover:text-sky-800 font-semibold"
                    >
                      <Wrench className="w-3 h-3" />
                      <span>Tool Details: <code>{log.tool_name || 'Generic Tool'}</code></span>
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {isExpanded && (
                      <div className="mt-2 bg-slate-900 text-slate-200 p-3 rounded-lg font-mono text-[11px] overflow-x-auto space-y-2">
                        {log.tool_input && (
                          <div>
                            <span className="text-sky-400 font-semibold">Input Parameters:</span>
                            <pre className="mt-1 text-slate-300">{JSON.stringify(log.tool_input, null, 2)}</pre>
                          </div>
                        )}
                        {log.tool_output && (
                          <div className="pt-2 border-t border-slate-800">
                            <span className="text-emerald-400 font-semibold">Output Result:</span>
                            <pre className="mt-1 text-slate-300">{JSON.stringify(log.tool_output, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
