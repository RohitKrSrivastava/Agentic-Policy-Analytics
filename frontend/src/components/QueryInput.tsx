import React, { useState } from 'react';
import { Sparkles, ArrowRight, Compass, ShieldAlert, Cpu } from 'lucide-react';

interface QueryInputProps {
  onSearch: (query: string, provider: string) => void;
  isLoading: boolean;
}

const PRESET_QUERIES = [
  {
    label: "Tech Sector Employment 2020-2024",
    query: "Analyse employment trends in the technology sector from 2020-2024"
  },
  {
    label: "Wage Benchmarks: Tech vs National",
    query: "Compare tech sector wages with financial services and national median"
  },
  {
    label: "Labour Market Tightness & Vacancies",
    query: "Evaluate job vacancy rates and retrenchment patterns 2020-2024"
  },
  {
    label: "IMDA TeSA & National AI Strategy KPIs",
    query: "Review TeSA and National AI Strategy 2.0 KPI progress"
  }
];

export const QueryInput: React.FC<QueryInputProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState("Analyse employment trends in the technology sector from 2020-2024");
  const [provider, setProvider] = useState("auto");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSearch(query.trim(), provider);
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        
        {/* Label & Provider Config */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <label className="text-sm font-semibold text-slate-800 flex items-center space-x-2">
            <Compass className="w-4 h-4 text-sky-600" />
            <span>Policy Research Objective</span>
          </label>

          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-500 font-medium">LLM Engine:</span>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="bg-slate-50 border border-slate-300 text-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500 font-medium"
            >
              <option value="auto">Auto-Failover (Multi-Cloud Safe)</option>
              <option value="openai">OpenAI (GPT-4o-mini)</option>
              <option value="gemini">Google Cloud Gemini (1.5 Flash)</option>
              <option value="bedrock">AWS Bedrock (Claude 3.5)</option>
              <option value="local_fallback">Local Heuristic Engine (Offline)</option>
            </select>
          </div>
        </div>

        {/* Search Input Bar */}
        <div className="relative flex items-center">
          <textarea
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="E.g., Analyse employment trends in the technology sector from 2020-2024..."
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition resize-none pr-32 font-medium"
          />

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className={`absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white shadow-sm transition ${
              isLoading || !query.trim()
                ? 'bg-slate-400 cursor-not-allowed'
                : 'bg-sky-600 hover:bg-sky-700 active:scale-95'
            }`}
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>Run Analysis</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

        {/* Suggestion Pills */}
        <div className="pt-1">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500 mb-2 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            <span>Recommended Research Inquiries:</span>
          </div>

          <div className="flex flex-wrap gap-2">
            {PRESET_QUERIES.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setQuery(p.query)}
                className="text-xs bg-slate-100 hover:bg-sky-50 hover:text-sky-700 hover:border-sky-200 border border-slate-200 px-3 py-1.5 rounded-lg text-slate-600 transition text-left"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

      </form>
    </div>
  );
};
