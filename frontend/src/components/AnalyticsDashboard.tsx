import React, { useState } from 'react';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Line, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid, 
  Area 
} from 'recharts';
import { TrendingUp, Users, DollarSign, Activity, FileText, Table as TableIcon } from 'lucide-react';
import { ChartSpecification, PolicyReport } from '../types';

interface AnalyticsDashboardProps {
  charts: ChartSpecification[];
  report?: PolicyReport;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ charts, report }) => {
  const [activeTab, setActiveTab] = useState(0);

  if (!charts || charts.length === 0) {
    return null;
  }

  const metrics = report?.statistical_metrics || {
    tech_cagr: 10.3,
    net_jobs_added: 56700,
    peak_vacancies: 21300,
    reentry_rate_pct: 78.9,
    tech_median_wage: 7350,
    tech_premium_pct: 37.4,
    forecast_2025_q4_k: 184.2
  };

  const activeChart = charts[activeTab] || charts[0];

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      
      {/* 4 Primary Econometric KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 mb-6">
        
        <div className="bg-sky-50/60 border border-sky-100 rounded-xl p-4">
          <div className="flex items-center justify-between text-sky-700 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Tech Sector CAGR</span>
            <TrendingUp className="w-4 h-4" />
          </div>
          <div className="text-2xl font-bold text-slate-800 font-mono">
            +{metrics.tech_cagr || 10.3}%
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Outpaced national baseline (3.1%)
          </p>
        </div>

        <div className="bg-indigo-50/60 border border-indigo-100 rounded-xl p-4">
          <div className="flex items-center justify-between text-indigo-700 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Net Jobs Created</span>
            <Users className="w-4 h-4" />
          </div>
          <div className="text-2xl font-bold text-slate-800 font-mono">
            +{metrics.net_jobs_added ? metrics.net_jobs_added.toLocaleString() : '56,700'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            118.4k (2020) → 175.1k (2024)
          </p>
        </div>

        <div className="bg-emerald-50/60 border border-emerald-100 rounded-xl p-4">
          <div className="flex items-center justify-between text-emerald-700 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Median Tech Wage</span>
            <DollarSign className="w-4 h-4" />
          </div>
          <div className="text-2xl font-bold text-slate-800 font-mono">
            S${metrics.tech_median_wage ? metrics.tech_median_wage.toLocaleString() : '7,350'}
          </div>
          <p className="text-[11px] text-emerald-600 font-medium mt-0.5">
            +{metrics.tech_premium_pct || 37.4}% over National Median
          </p>
        </div>

        <div className="bg-purple-50/60 border border-purple-100 rounded-xl p-4">
          <div className="flex items-center justify-between text-purple-700 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">6-Mo Re-entry Rate</span>
            <Activity className="w-4 h-4" />
          </div>
          <div className="text-2xl font-bold text-slate-800 font-mono">
            {metrics.reentry_rate_pct || 78.9}%
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Labour market absorption resilience
          </p>
        </div>

      </div>

      {/* Chart Navigation Tabs */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-200 pb-3 mb-4 gap-2">
        <div className="flex space-x-1 sm:space-x-2">
          {charts.map((c, idx) => (
            <button
              key={c.chart_id}
              onClick={() => setActiveTab(idx)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === idx
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {c.title.split(':')[0]}
            </button>
          ))}
        </div>

        <span className="text-xs text-slate-500 font-mono hidden sm:inline">
          Format: {activeChart.chart_type.toUpperCase()} • Interactive Tooltip Enabled
        </span>
      </div>

      {/* Active Chart Visual Title */}
      <div className="mb-2">
        <h4 className="text-sm font-bold text-slate-800">{activeChart.title}</h4>
        {activeChart.annotations && activeChart.annotations.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-1.5">
            {activeChart.annotations.map((ann, i) => (
              <span key={i} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded border border-slate-200 font-mono">
                • {ann}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Interactive Chart Canvas */}
      <div className="h-80 w-full mt-4">
        <ResponsiveContainer width="100%" height="100%">
          {activeChart.chart_type === 'bar' ? (
            <ComposedChart data={activeChart.series} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey={activeChart.x_key} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} label={{ value: activeChart.y_axis_label, angle: -90, position: 'insideLeft', fontSize: 11 }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                itemStyle={{ color: '#93c5fd' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              <Bar dataKey="Tech_Industry_Median" fill="#0284c7" name="Tech Sector Median (SGD)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="National_Median" fill="#94a3b8" name="National Median (SGD)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="AI_Specialist" fill="#8b5cf6" name="AI Specialist (SGD)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Software_Engineer" fill="#06b6d4" name="Software Engineer (SGD)" radius={[4, 4, 0, 0]} />
            </ComposedChart>
          ) : (
            <ComposedChart data={activeChart.series} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey={activeChart.x_key} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} label={{ value: activeChart.y_axis_label, angle: -90, position: 'insideLeft', fontSize: 11 }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                itemStyle={{ color: '#93c5fd' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              
              {/* Optional elements based on chart id */}
              {activeChart.chart_id.includes('employment') ? (
                <>
                  <Area type="monotone" dataKey="Tech_Employment_K" fill="#e0f2fe" stroke="#0284c7" strokeWidth={2.5} name="Tech Employment (Thousands)" />
                  <Line type="monotone" dataKey="Trend_Line" stroke="#f59e0b" strokeDasharray="5 5" strokeWidth={2} name="Linear Trend" dot={false} />
                  <Line type="monotone" dataKey="Projected_Employment_K" stroke="#10b981" strokeWidth={2.5} strokeDasharray="3 3" name="2025 Projection Cone" />
                </>
              ) : (
                <>
                  <Bar dataKey="Job_Vacancies" fill="#3b82f6" name="Tech Job Vacancies" radius={[4, 4, 0, 0]} />
                  <Line type="monotone" dataKey="Retrenchments" stroke="#ef4444" strokeWidth={2.5} name="Quarterly Retrenchments" />
                </>
              )}
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>

    </div>
  );
};
