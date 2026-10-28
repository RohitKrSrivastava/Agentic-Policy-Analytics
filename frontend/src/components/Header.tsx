import React from 'react';
import { Activity, ShieldCheck, Database, History, ExternalLink, Cpu, GitBranch } from 'lucide-react';
import { SystemHealthResponse } from '../types';

interface HeaderProps {
  health: SystemHealthResponse | null;
  onOpenHistory: () => void;
  onOpenDataSources: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, onOpenHistory, onOpenDataSources }) => {
  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand & Emblem */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-white">GovPolicy<span className="text-sky-400">AI</span></span>
              <span className="bg-sky-500/10 text-sky-400 text-xs px-2 py-0.5 rounded-full border border-sky-500/20 font-medium">Research Prototype v1.0</span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Agentic Policy Data Analytics Platform • Singapore Government Focus</p>
          </div>
        </div>

        {/* Multi-Cloud Provider Health Pills */}
        <div className="hidden lg:flex items-center space-x-2 bg-slate-800/60 p-1.5 rounded-xl border border-slate-700/60 text-xs">
          <span className="text-slate-400 px-2 flex items-center font-medium">
            <Cpu className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
            Multi-Cloud LLMs:
          </span>

          {health?.active_providers.map((p) => {
            const isOnline = p.status === 'active' || p.status === 'standby';
            const isFallback = p.provider_name === 'local_fallback';
            return (
              <div 
                key={p.provider_name}
                className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-900/60 border border-slate-700/50"
                title={`${p.model_name} (${p.status}) - ${p.latency_ms}ms`}
              >
                <span className={`w-2 h-2 rounded-full ${isFallback ? 'bg-emerald-400 animate-pulse' : isOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className="capitalize font-medium text-slate-200">
                  {p.provider_name === 'local_fallback' ? 'Local Safety Engine' : p.provider_name}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {p.latency_ms ? `${p.latency_ms.toFixed(0)}ms` : 'offline'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          <button
            onClick={onOpenDataSources}
            className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg transition border border-slate-700"
          >
            <Database className="w-4 h-4 text-sky-400" />
            <span className="hidden sm:inline">Data Sources</span>
          </button>

          <button
            onClick={onOpenHistory}
            className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg transition border border-slate-700"
          >
            <History className="w-4 h-4 text-indigo-400" />
            <span>History</span>
          </button>

          <a
            href="https://github.com/RohitKrSrivastava/agentic-policy-analytics"
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg transition border border-slate-700"
            title="GitHub Repository: RohitKrSrivastava/agentic-policy-analytics"
          >
            <GitBranch className="w-3.5 h-3.5 text-sky-400" />
            <span className="hidden sm:inline">GitHub</span>
          </a>

          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white px-2 py-2 transition"
            title="FastAPI Swagger OpenAPI Docs"
          >
            <span className="hidden md:inline">API</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

      </div>
    </header>
  );
};
