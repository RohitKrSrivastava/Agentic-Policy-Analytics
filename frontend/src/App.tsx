import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { QueryInput } from './components/QueryInput';
import { AgentActivityMonitor } from './components/AgentActivityMonitor';
import { DataQualityCard } from './components/DataQualityCard';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { PolicyReportView } from './components/PolicyReportView';
import { HistoryDrawer } from './components/HistoryDrawer';
import { DataSourcesModal } from './components/DataSourcesModal';
import { SessionResponse, SystemHealthResponse, AgentStepLog, SessionStatus } from './types';
import { createAnalysis, getAnalysisSession, getSystemHealth } from './services/api';
import { SessionWebSocket } from './services/websocket';
import { Sparkles, Shield, Layers, HelpCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [currentSession, setCurrentSession] = useState<SessionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isDataSourcesOpen, setIsDataSourcesOpen] = useState(false);

  const wsRef = useRef<SessionWebSocket | null>(null);

  // Load system health on mount
  useEffect(() => {
    getSystemHealth()
      .then(setHealth)
      .catch(console.error);

    // Run initial analysis automatically on mount to show instant rich state!
    handleStartAnalysis("Analyse employment trends in the technology sector from 2020-2024", "auto");
  }, []);

  const handleStartAnalysis = async (query: string, provider: string) => {
    setIsLoading(true);
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const session = await createAnalysis(query, provider);
      setCurrentSession(session);

      // Connect WebSocket for streaming updates
      wsRef.current = new SessionWebSocket(session.session_id, (msg) => {
        handleWebSocketMessage(msg);
      });

      // Poll periodically as fallback
      const pollInterval = setInterval(async () => {
        try {
          const updated = await getAnalysisSession(session.session_id);
          setCurrentSession(updated);
          if (updated.status === 'completed' || updated.status === 'failed') {
            setIsLoading(false);
            clearInterval(pollInterval);
          }
        } catch (err) {
          clearInterval(pollInterval);
        }
      }, 1000);

    } catch (err) {
      console.error("Analysis creation failed:", err);
      setIsLoading(false);
    }
  };

  const handleWebSocketMessage = (msg: any) => {
    if (msg.type === 'agent_log') {
      setCurrentSession((prev) => {
        if (!prev) return prev;
        const exists = prev.logs.some((l) => l.id === msg.data.id);
        if (exists) return prev;
        return {
          ...prev,
          logs: [...prev.logs, msg.data]
        };
      });
    } else if (msg.type === 'status_update') {
      setCurrentSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: msg.status as SessionStatus,
          progress_pct: msg.progress_pct,
          current_agent: msg.current_agent,
          current_step: msg.current_step,
          llm_provider_used: msg.llm_provider_used || prev.llm_provider_used
        };
      });
      if (msg.status === 'completed' || msg.status === 'failed') {
        setIsLoading(false);
      }
    } else if (msg.type === 'workflow_completed') {
      setCurrentSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'completed',
          progress_pct: 100,
          charts: msg.charts || prev.charts,
          quality_reports: msg.quality_reports || prev.quality_reports,
          report: msg.report || prev.report
        };
      });
      setIsLoading(false);
    }
  };

  const handleSelectSessionFromHistory = async (sessionId: string) => {
    setIsLoading(true);
    try {
      const sess = await getAnalysisSession(sessionId);
      setCurrentSession(sess);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Navigation Header */}
      <Header 
        health={health} 
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenDataSources={() => setIsDataSourcesOpen(true)}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Research Query Input */}
        <QueryInput onSearch={handleStartAnalysis} isLoading={isLoading} />

        {/* Real-Time Agent Activity & ReAct Thought Trace */}
        {currentSession && (
          <AgentActivityMonitor
            logs={currentSession.logs}
            status={currentSession.status}
            progressPct={currentSession.progress_pct}
            currentAgent={currentSession.current_agent}
            currentStep={currentSession.current_step}
          />
        )}

        {/* Government Data Ingestion & Quality Card */}
        {currentSession && currentSession.quality_reports && currentSession.quality_reports.length > 0 && (
          <DataQualityCard qualityReports={currentSession.quality_reports} />
        )}

        {/* Interactive Econometric Visual Dashboard */}
        {currentSession && currentSession.charts && currentSession.charts.length > 0 && (
          <AnalyticsDashboard 
            charts={currentSession.charts} 
            report={currentSession.report}
          />
        )}

        {/* Synthesized Policy Report & Citations */}
        {currentSession?.report && (
          <PolicyReportView 
            report={currentSession.report} 
            sessionId={currentSession.session_id} 
          />
        )}

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <p>
            Agentic Policy Data Analytics Platform • Built for Singapore Public Sector Intelligence (DOS SingStat, MOM Statistics, Data.gov.sg) • Multi-Cloud LLM Resilient
          </p>
          <a
            href="https://github.com/RohitKrSrivastava/agentic-policy-analytics"
            target="_blank"
            rel="noreferrer"
            className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center space-x-1"
          >
            <span>RohitKrSrivastava/agentic-policy-analytics</span>
          </a>
        </div>
      </footer>

      {/* Slide-out History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectSession={handleSelectSessionFromHistory}
      />

      {/* Data Sources Catalog Modal */}
      <DataSourcesModal
        isOpen={isDataSourcesOpen}
        onClose={() => setIsDataSourcesOpen(false)}
      />
    </div>
  );
};

export default App;
