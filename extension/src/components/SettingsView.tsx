import React, { useState, useEffect } from 'react';
import { Settings, Key, Shield, Check, RefreshCw, Folder } from 'lucide-react';
import { SystemStatus } from '../types';
import { api } from '../services/api';

interface Props {
  status: SystemStatus | null;
  onRefreshStatus: () => void;
}

export const SettingsView: React.FC<Props> = ({ status, onRefreshStatus }) => {
  const [tokenInput, setTokenInput] = useState('');
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    setTokenInput(api.getToken());
  }, []);

  const handleSaveToken = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.saveToken(tokenInput.trim());
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
    onRefreshStatus();
  };

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
          <Settings className="w-4 h-4 text-indigo-400" />
          <span>Agent Configuration & Security</span>
        </h2>
        <p className="text-[11px] text-slate-400">Manage pairing tokens and local automation settings</p>
      </div>

      {/* Pairing Token Form */}
      <form onSubmit={handleSaveToken} className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-white flex items-center space-x-1.5">
            <Key className="w-3.5 h-3.5 text-indigo-400" />
            <span>Agent Pairing Token (X-Agent-Token)</span>
          </label>
          {savedSuccess && <span className="text-[10px] text-emerald-400 flex items-center space-x-0.5"><Check className="w-3 h-3" /> Saved</span>}
        </div>
        <p className="text-[11px] text-slate-400">
          Required to authenticate Chrome extension requests against the local Python server. Found in your agent console or <code className="bg-slate-900 px-1 py-0.5 rounded text-slate-300">agent/data/.agent_token</code>.
        </p>

        <input
          type="password"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          placeholder="Paste 32-character secret token here..."
          className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-indigo-500"
        />

        <button
          type="submit"
          className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold transition"
        >
          Save & Pair Extension
        </button>
      </form>

      {/* Dedicated Chrome Profile Status */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-2 text-xs">
        <h3 className="font-semibold text-white flex items-center space-x-1.5">
          <Folder className="w-3.5 h-3.5 text-cyan-400" />
          <span>Dedicated Chrome Profile</span>
        </h3>
        <p className="text-[11px] text-slate-300">
          Your automation operates in a persistent, isolated Chrome profile separate from your personal profile.
        </p>
        <div className="bg-slate-900 p-2 rounded text-[10px] font-mono text-slate-300 break-all select-all border border-slate-800">
          {status?.chrome_profile || '%LOCALAPPDATA%\\AI_SEO_Agent\\ChromeProfile'}
        </div>
        <div className="pt-1 text-[11px] text-amber-300/90 leading-relaxed">
          💡 <strong>One-time Login:</strong> Open Google Search Console or WordPress through the extension and sign in normally. Your session cookies remain securely stored in this dedicated directory.
        </div>
      </div>

      {/* Security Architecture Guarantees */}
      <div className="bg-slate-850 border border-slate-800 rounded-xl p-3 space-y-2 text-xs">
        <h3 className="font-semibold text-slate-200 flex items-center space-x-1.5">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Security & Isolation Principles</span>
        </h3>
        <ul className="space-y-1 text-[11px] text-slate-400">
          <li>• Bound strictly to localhost (<code className="text-slate-300">127.0.0.1:8765</code>). Never exposed to public internet.</li>
          <li>• Full SSRF filtering: Blocks private IPs, local networks, and cloud metadata.</li>
          <li>• Web crawled text is treated as untrusted data to prevent prompt injection.</li>
          <li>• No Google passwords stored; uses browser session authentication directly.</li>
        </ul>
      </div>
    </div>
  );
};
