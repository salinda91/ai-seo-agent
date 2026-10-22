import React from 'react';
import { Play, Pause, Square, ExternalLink, ShieldAlert, Monitor } from 'lucide-react';
import { api } from '../services/api';

interface Props {
  currentUrl: string;
  isPaused: boolean;
  manualTakeover: boolean;
  onRefresh: () => void;
  wsConnected: boolean;
}

export const LiveBrowserBar: React.FC<Props> = ({
  currentUrl,
  isPaused,
  manualTakeover,
  onRefresh,
  wsConnected
}) => {
  const handleTogglePause = async () => {
    try {
      await api.controlEngine(isPaused ? 'resume' : 'pause');
      onRefresh();
    } catch (e: any) {
      alert(`Control error: ${e.message}`);
    }
  };

  const handleStop = async () => {
    if (confirm('Stop all current browser automation tasks?')) {
      await api.controlEngine('stop');
      onRefresh();
    }
  };

  return (
    <div className="bg-slate-800 border-b border-slate-700 px-3 py-2 flex items-center justify-between text-xs">
      <div className="flex items-center space-x-2 truncate flex-1 mr-2">
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} title={wsConnected ? 'Connected to Agent' : 'Agent Offline'} />
        <Monitor className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        <span className="text-slate-400 font-medium">Browser:</span>
        <span className="text-slate-200 truncate font-mono max-w-xs" title={currentUrl || 'Browser idle'}>
          {currentUrl || 'Idle / Ready'}
        </span>
      </div>

      <div className="flex items-center space-x-1.5 flex-shrink-0">
        {manualTakeover && (
          <span className="flex items-center space-x-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded text-[10px] font-semibold">
            <ShieldAlert className="w-3 h-3 text-amber-400" />
            <span>Human Takeover</span>
          </span>
        )}

        <button
          onClick={handleTogglePause}
          className={`flex items-center space-x-1 px-2 py-1 rounded font-medium transition ${
            isPaused
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
              : 'bg-amber-600 hover:bg-amber-500 text-white'
          }`}
          title={isPaused ? 'Resume Automation' : 'Pause Automation'}
        >
          {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
          <span>{isPaused ? 'Resume' : 'Pause'}</span>
        </button>

        <button
          onClick={handleStop}
          className="flex items-center space-x-1 px-2 py-1 rounded bg-rose-600/80 hover:bg-rose-500 text-white transition font-medium"
          title="Emergency Stop"
        >
          <Square className="w-3 h-3" />
          <span>Stop</span>
        </button>
      </div>
    </div>
  );
};
