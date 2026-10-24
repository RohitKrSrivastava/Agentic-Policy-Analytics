import React from 'react';
import { CheckCircle, AlertTriangle, FileSpreadsheet, Database, Globe, Layers } from 'lucide-react';
import { DataQualityItem } from '../types';

interface DataQualityCardProps {
  qualityReports: DataQualityItem[];
}

export const DataQualityCard: React.FC<DataQualityCardProps> = ({ qualityReports }) => {
  if (!qualityReports || qualityReports.length === 0) {
    return null;
  }

  const avgCompleteness = (
    qualityReports.reduce((acc, q) => acc + q.completeness_score, 0) / qualityReports.length
  ).toFixed(1);

  const totalRecords = qualityReports.reduce((acc, q) => acc + q.total_records, 0);
  const totalImputed = qualityReports.reduce((acc, q) => acc + q.missing_values_handled, 0);
  const totalOutliers = qualityReports.reduce((acc, q) => acc + q.outliers_identified, 0);

  const getFormatIcon = (format: string) => {
    if (format.includes('CSV')) return <Layers className="w-4 h-4 text-emerald-600" />;
    if (format.includes('Excel')) return <FileSpreadsheet className="w-4 h-4 text-emerald-600" />;
    if (format.includes('API')) return <Globe className="w-4 h-4 text-sky-600" />;
    return <Database className="w-4 h-4 text-indigo-600" />;
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      
      {/* Title & Metric Overview */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="font-bold text-slate-800 text-base">Government Data Ingestion & Quality Audit</h3>
            <span className="bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded-full font-semibold border border-emerald-200">
              Verified Pipeline
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-source validation across CSV, Excel, JSON, and REST APIs with automated outlier capping and imputation.
          </p>
        </div>

        {/* Global Score Badges */}
        <div className="flex items-center space-x-4 bg-slate-50 px-4 py-2 rounded-xl border border-slate-200">
          <div>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Completeness</span>
            <span className="text-base font-bold text-emerald-600 font-mono">{avgCompleteness}%</span>
          </div>
          <div className="h-6 w-px bg-slate-200" />
          <div>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Total Records</span>
            <span className="text-base font-bold text-slate-800 font-mono">{totalRecords}</span>
          </div>
          <div className="h-6 w-px bg-slate-200" />
          <div>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Imputations</span>
            <span className="text-base font-bold text-sky-600 font-mono">{totalImputed}</span>
          </div>
        </div>
      </div>

      {/* Dataset Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-4">
        {qualityReports.map((q, idx) => (
          <div key={idx} className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-1 mb-2">
                <div className="flex items-center space-x-1.5">
                  {getFormatIcon(q.data_format)}
                  <span className="text-[11px] font-bold text-slate-800 truncate" title={q.dataset_name}>
                    {q.dataset_name.split('(')[0].trim()}
                  </span>
                </div>
                <span className="text-[10px] font-mono bg-white border border-slate-200 text-slate-600 px-1.5 py-0.5 rounded">
                  {q.data_format}
                </span>
              </div>
              
              <p className="text-[10px] text-slate-500 truncate mb-3">{q.source_type}</p>

              <div className="space-y-1.5 text-[11px] font-medium text-slate-600">
                <div className="flex justify-between">
                  <span className="text-slate-500">Quality Score:</span>
                  <span className="font-mono text-emerald-600 font-bold">{q.completeness_score}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Records Audited:</span>
                  <span className="font-mono text-slate-800">{q.total_records}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Outliers Capped:</span>
                  <span className="font-mono text-slate-800">{q.outliers_identified}</span>
                </div>
              </div>
            </div>

            {/* Cleaning Actions applied */}
            <div className="mt-3 pt-2 border-t border-slate-200/60">
              <span className="text-[10px] text-slate-400 block mb-1">Cleansing Operations:</span>
              <ul className="text-[10px] text-slate-600 space-y-0.5 list-disc list-inside">
                {q.cleaning_applied.slice(0, 2).map((c, i) => (
                  <li key={i} className="truncate" title={c}>{c}</li>
                ))}
              </ul>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
};
