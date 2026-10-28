import React from 'react';
import { 
  FileText, 
  Download, 
  FileCode, 
  FileSpreadsheet, 
  ShieldCheck, 
  CheckCircle, 
  Lightbulb, 
  ExternalLink, 
  BookOpen 
} from 'lucide-react';
import { PolicyReport } from '../types';

interface PolicyReportViewProps {
  report: PolicyReport;
  sessionId: string;
}

export const PolicyReportView: React.FC<PolicyReportViewProps> = ({ report, sessionId }) => {
  if (!report) return null;

  const handleDownload = (format: 'pdf' | 'markdown' | 'json') => {
    const url = `/api/v1/export/${sessionId}/${format}`;
    window.open(url, '_blank');
  };

  const getSentimentTag = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Positive Indicator</span>;
      case 'cautionary':
        return <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Cautionary Note</span>;
      default:
        return <span className="bg-slate-100 text-slate-800 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Structural Insight</span>;
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 sm:p-8 mb-6">
      
      {/* Title & Export Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-200 gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1.5">
            <span className="bg-sky-50 text-sky-700 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-sky-200">
              Government Policy Brief
            </span>
            <span className="text-slate-400 text-xs font-mono">Session ID: {sessionId}</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            {report.title}
          </h2>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleDownload('pdf')}
            className="flex items-center space-x-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium px-3.5 py-2 rounded-lg transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export PDF</span>
          </button>

          <button
            onClick={() => handleDownload('markdown')}
            className="flex items-center space-x-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium px-3.5 py-2 rounded-lg transition border border-slate-200"
          >
            <FileCode className="w-3.5 h-3.5 text-slate-500" />
            <span>Markdown</span>
          </button>

          <button
            onClick={() => handleDownload('json')}
            className="flex items-center space-x-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium px-3.5 py-2 rounded-lg transition border border-slate-200"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-slate-500" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {/* Hallucination Verification Guard Certification Strip */}
      {(() => {
        const vStatus = report.verification_status || (report.hallucination_score === 0 ? "verified" : report.hallucination_score < 0.2 ? "partially_verified" : "unverified");
        const discrepancies = report.discrepancy_count ?? (vStatus === "verified" ? 0 : Math.max(1, Math.round(report.hallucination_score * 10)));

        let badgeColor = "bg-emerald-500 text-white";
        let badgeText = "VERIFIED";
        let guardTitle = "Hallucination Verification Guard: Grounded";
        let guardDesc = "Quantitative claims and econometric metrics verified against underlying public sector datasets with zero discrepancies.";
        let riskColor = "text-emerald-600";
        let riskText = "0.00 (Zero)";

        if (vStatus === "partially_verified") {
          badgeColor = "bg-amber-500 text-white";
          badgeText = `PARTIALLY VERIFIED (${discrepancies} ${discrepancies === 1 ? 'discrepancy' : 'discrepancies'})`;
          guardTitle = "Hallucination Verification Guard: Partially Verified";
          guardDesc = `Core findings verified; ${discrepancies} claim(s) required repair or had missing ground-truth coverage.`;
          riskColor = "text-amber-600";
          riskText = `${report.hallucination_score.toFixed(2)} (Low)`;
        } else if (vStatus === "unverified" || vStatus === "unverifiable") {
          badgeColor = "bg-rose-500 text-white";
          badgeText = vStatus === "unverifiable" ? "UNVERIFIABLE" : "UNVERIFIED";
          guardTitle = `Hallucination Verification Guard: ${vStatus === "unverifiable" ? "Unverifiable" : "Discrepancies Flagged"}`;
          guardDesc = "Ground truth verification could not fully confirm reported figures against source repositories.";
          riskColor = "text-rose-600";
          riskText = `${report.hallucination_score.toFixed(2)} (High)`;
        }

        return (
          <div className="my-6 bg-gradient-to-r from-purple-50/70 to-indigo-50/70 border border-purple-200/80 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3" data-testid="verification-strip">
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-lg ${vStatus === 'verified' ? 'bg-purple-600' : vStatus === 'partially_verified' ? 'bg-amber-600' : 'bg-rose-600'} flex items-center justify-center text-white shrink-0 shadow-sm`}>
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-bold text-slate-900">{guardTitle}</span>
                  <span className={`${badgeColor} text-[10px] font-bold px-1.5 py-0.5 rounded font-mono`} data-testid="verification-badge">{badgeText}</span>
                </div>
                <p className="text-xs text-slate-600 mt-0.5">
                  {guardDesc}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-lg border border-purple-100 shrink-0 font-mono text-xs">
              <div>
                <span className="text-[10px] text-slate-400 uppercase block font-sans">Hallucination Risk</span>
                <span className={`font-bold ${riskColor}`}>{riskText}</span>
              </div>
              <div className="h-6 w-px bg-slate-200" />
              <div>
                <span className="text-[10px] text-slate-400 uppercase block font-sans">Data Quality</span>
                <span className="font-bold text-sky-600">{report.quality_score}%</span>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Section 1: Executive Summary */}
      <div className="mb-8">
        <h3 className="text-base font-bold text-slate-900 mb-2.5 flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-sky-600" />
          <span>Executive Summary</span>
        </h3>
        <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200/70">
          {report.executive_summary}
        </p>
      </div>

      {/* Section 2: Key Findings */}
      <div className="mb-8">
        <h3 className="text-base font-bold text-slate-900 mb-3">
          Empirical Findings & Evidence Base
        </h3>

        <div className="grid grid-cols-1 gap-4">
          {report.key_findings.map((f, idx) => (
            <div key={idx} className="bg-slate-50/60 border border-slate-200 rounded-xl p-4 transition hover:bg-slate-50">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="text-sm font-bold text-slate-900">{f.heading}</h4>
                {getSentimentTag(f.sentiment)}
              </div>

              <p className="text-xs text-slate-700 leading-relaxed mb-3">
                {f.body}
              </p>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between pt-2 border-t border-slate-200/60 text-xs text-slate-500 gap-1 font-mono">
                <span className="text-slate-600 font-sans">
                  <b>Statistical Evidence:</b> {f.statistical_evidence}
                </span>
                <span className="bg-white border border-slate-200 px-2 py-0.5 rounded text-sky-700 text-[11px] font-semibold">
                  Source: {f.citation_id}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Strategic Recommendations */}
      <div className="mb-8">
        <h3 className="text-base font-bold text-slate-900 mb-3 flex items-center space-x-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          <span>Strategic Policy Recommendations</span>
        </h3>

        <div className="space-y-2.5">
          {report.policy_recommendations.map((rec, idx) => (
            <div key={idx} className="flex items-start space-x-3 bg-amber-50/40 border border-amber-200/60 p-3.5 rounded-xl text-xs text-slate-800">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-white font-bold text-[10px] shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <p className="leading-relaxed font-medium">{rec}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Section 4: Authoritative Data Citations */}
      <div>
        <h3 className="text-base font-bold text-slate-900 mb-3">
          Authoritative Citations & Data Audit Trail
        </h3>

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-mono">Citation ID</th>
                <th className="py-2.5 px-3">Lead Agency</th>
                <th className="py-2.5 px-3">Dataset Reference</th>
                <th className="py-2.5 px-3">Time Horizon</th>
                <th className="py-2.5 px-3">Access Protocol</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-600">
              {report.citations.map((c, i) => (
                <tr key={i} className="hover:bg-slate-50 transition">
                  <td className="py-2.5 px-3 font-mono font-bold text-sky-700">{c.citation_id}</td>
                  <td className="py-2.5 px-3 font-medium text-slate-900">{c.source_agency}</td>
                  <td className="py-2.5 px-3">{c.dataset_title}</td>
                  <td className="py-2.5 px-3 font-mono text-[11px]">{c.time_period}</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">{c.access_method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
