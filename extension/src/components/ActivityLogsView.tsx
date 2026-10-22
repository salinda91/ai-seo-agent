import React, { useState, useEffect } from 'react';
import { History, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';
import { AuditLogItem } from '../types';
import { api } from '../services/api';

export const ActivityLogsView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs(100);
      setLogs(data);
    } catch (e) {
      console.warn('Error fetching logs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
            <History className="w-4 h-4 text-indigo-400" />
            <span>Activity & Audit Trail</span>
          </h2>
          <p className="text-[11px] text-slate-400">Tamper-evident chronological execution log</p>
        </div>

        <button
          onClick={loadLogs}
          disabled={loading}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
          title="Refresh Logs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-2">
        {logs.map((log) => {
          const isError = log.status === 'failure' || log.status === 'error';
          const isWarning = log.status === 'warning' || log.status === 'paused';

          return (
            <div key={log.id} className="bg-slate-850 border border-slate-700/60 rounded-xl p-3 space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5">
                  {isError ? (
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                  ) : isWarning ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  )}
                  <span className="font-semibold text-white">{log.action}</span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
              </div>

              {log.details && Object.keys(log.details).length > 0 && (
                <div className="bg-slate-900/80 p-2 rounded text-[11px] font-mono text-slate-300 overflow-x-auto">
                  {JSON.stringify(log.details)}
                </div>
              )}
            </div>
          );
        })}

        {logs.length === 0 && (
          <div className="text-center py-8 text-slate-500 text-xs">
            No activity logs recorded yet.
          </div>
        )}
      </div>
    </div>
  );
};
