import React, { useEffect, useState } from 'react';
import { X, Database, Globe, FileSpreadsheet, Layers, CheckCircle2 } from 'lucide-react';
import { listDatasets } from '../services/api';

interface DataSourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DataSourcesModal: React.FC<DataSourcesModalProps> = ({ isOpen, onClose }) => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedPreview, setSelectedPreview] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    try {
      const data = await listDatasets();
      setDatasets(data);
    } catch (err) {
      console.error(err);
    }
  };

  const inspectDataset = async (id: string) => {
    setPreviewLoading(true);
    try {
      const res = await fetch(`/api/v1/datasets/${id}/preview`);
      const json = await res.json();
      setSelectedPreview({ id, data: json });
    } catch (e) {
      console.error(e);
    } finally {
      setPreviewLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <Database className="w-5 h-5 text-sky-600" />
            <div>
              <h3 className="font-bold text-slate-900 text-base">Integrated Singapore Government Data Catalog</h3>
              <p className="text-xs text-slate-500">Official repositories connected to the Data Extraction Agent</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Catalog List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {datasets.map((d) => (
              <div 
                key={d.id} 
                className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col justify-between hover:border-sky-300 transition"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-bold text-sm text-slate-900">{d.name}</span>
                    <span className="text-[10px] font-mono bg-white border border-slate-200 px-2 py-0.5 rounded font-semibold text-slate-700">
                      {d.format}
                    </span>
                  </div>
                  <p className="text-xs text-sky-700 font-medium mb-2">{d.agency}</p>
                  
                  <div className="text-[11px] text-slate-600 space-y-1">
                    <p><b>Time Range:</b> {d.time_range}</p>
                    <p><b>Cadence:</b> {d.update_cadence}</p>
                    <p><b>Attributes:</b> <span className="font-mono text-[10px] text-slate-500">{d.key_attributes.join(', ')}</span></p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => inspectDataset(d.id)}
                  className="mt-3.5 text-xs text-sky-600 hover:text-sky-800 font-semibold border-t border-slate-200/80 pt-2 flex items-center justify-between"
                >
                  <span>Preview Raw Schema & Records</span>
                  <span>→</span>
                </button>
              </div>
            ))}
          </div>

          {/* Interactive Preview Drawer */}
          {selectedPreview && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-xs text-slate-800">
                  Live Snapshot Preview: <code>{selectedPreview.id}</code>
                </span>
                <button
                  onClick={() => setSelectedPreview(null)}
                  className="text-xs text-slate-400 hover:text-slate-600"
                >
                  Close Preview
                </button>
              </div>
              <pre className="bg-slate-900 text-slate-200 p-4 rounded-xl text-xs font-mono max-h-60 overflow-y-auto">
                {JSON.stringify(selectedPreview.data, null, 2)}
              </pre>
            </div>
          )}

        </div>

      </div>
    </div>
  );
};
