import React, { useState } from 'react';
import { ListOrdered, Check, X, Clock, Play, AlertCircle, RefreshCw } from 'lucide-react';
import { TaskItem } from '../types';
import { api } from '../services/api';

interface Props {
  tasks: TaskItem[];
  onRefresh: () => void;
}

export const TaskQueueView: React.FC<Props> = ({ tasks, onRefresh }) => {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleApprove = async (taskId: string) => {
    setLoadingId(taskId);
    try {
      await api.approveTask(taskId);
      onRefresh();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setLoadingId(null);
    }
  };

  const handleReject = async (taskId: string) => {
    setLoadingId(taskId);
    try {
      await api.rejectTask(taskId);
      onRefresh();
    } catch (err: any) {
      alert(`Reject error: ${err.message}`);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
            <ListOrdered className="w-4 h-4 text-indigo-400" />
            <span>Task Queue & Approval Pipeline</span>
          </h2>
          <p className="text-[11px] text-slate-400">{tasks.length} tasks in history</p>
        </div>

        <button
          onClick={onRefresh}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
          title="Refresh Queue"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-2.5">
        {tasks.map((task) => {
          const isWaiting = task.status === 'waiting_approval';
          const isBusy = loadingId === task.id;

          return (
            <div
              key={task.id}
              className={`p-3 rounded-xl border transition ${
                isWaiting
                  ? 'bg-amber-950/30 border-amber-500/50 ring-1 ring-amber-500/30'
                  : 'bg-slate-850 border-slate-700/60'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-white uppercase">{task.task_type.replace('_', ' ')}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                        task.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : task.status === 'waiting_approval'
                          ? 'bg-amber-500/20 text-amber-300'
                          : task.status === 'running'
                          ? 'bg-indigo-500/20 text-indigo-300 animate-pulse'
                          : task.status === 'failed'
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {task.status.replace('_', ' ')}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                    ID: {task.id.slice(0, 8)}... • Risk: {task.risk_level}
                  </span>
                </div>

                {isWaiting && (
                  <div className="flex space-x-1.5">
                    <button
                      onClick={() => handleApprove(task.id)}
                      disabled={isBusy}
                      className="flex items-center space-x-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold transition"
                    >
                      <Check className="w-3 h-3" />
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => handleReject(task.id)}
                      disabled={isBusy}
                      className="p-1 bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white rounded text-xs transition"
                      title="Reject task"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>

              {task.error_message && (
                <div className="mt-2 p-2 bg-rose-950/40 border border-rose-600/30 rounded text-[11px] text-rose-200">
                  {task.error_message}
                </div>
              )}

              {task.payload && Object.keys(task.payload).length > 0 && (
                <div className="mt-2 text-[10px] font-mono text-slate-400 bg-slate-900/60 p-1.5 rounded truncate">
                  Payload: {JSON.stringify(task.payload)}
                </div>
              )}
            </div>
          );
        })}

        {tasks.length === 0 && (
          <div className="text-center py-8 text-slate-500 text-xs">
            Task queue is currently empty.
          </div>
        )}
      </div>
    </div>
  );
};
