import React from 'react';
import {
  Globe,
  Rocket,
  AlertTriangle,
  Key,
  ShieldCheck,
  Search,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Activity
} from 'lucide-react';
import { Website, SystemStatus, TaskItem, RecommendationItem } from '../types';

interface Props {
  websites: Website[];
  status: SystemStatus | null;
  tasks: TaskItem[];
  recommendations: RecommendationItem[];
  onNavigate: (tab: any) => void;
  onOpenGSC: () => void;
  onRefresh?: () => void;
}

export const DashboardView: React.FC<Props> = ({
  websites,
  status,
  tasks,
  recommendations,
  onNavigate,
  onOpenGSC,
  onRefresh
}) => {
  const pendingApprovals = tasks.filter((t) => t.status === 'waiting_approval');
  const criticalCount = recommendations.filter((r) => r.severity === 'critical').length;
  const highCount = recommendations.filter((r) => r.severity === 'high').length;

  // Calculate dynamic health score
  const totalIssues = recommendations.length;
  const healthScore = Math.max(20, Math.min(100, Math.round(100 - (criticalCount * 15 + highCount * 5))));

  return (
    <div className="p-4 space-y-4">
      {/* Offline Agent Card */}
      {!status && (
        <div className="bg-slate-950 border border-rose-800/80 rounded-xl p-4 space-y-3 shadow-lg">
          <div className="flex items-center space-x-2 text-rose-400">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <h3 className="text-xs font-bold text-white">Local Python Agent Server Offline</h3>
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            The Chrome extension communicates with your local Python automation engine running on <code className="text-indigo-300">http://127.0.0.1:8765</code>. Please ensure the local agent process is started.
          </p>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 font-mono text-[11px] text-slate-300 space-y-1.5">
            <div className="text-slate-400 text-[10px] uppercase font-sans font-bold">To Start Local Agent:</div>
            <div>&gt; Double-click <span className="text-emerald-400 font-semibold">scripts\start_agent.bat</span></div>
            <div className="text-slate-500 text-[10px] font-sans">Or run in your project terminal:</div>
            <div className="text-cyan-300 select-all">&gt; .\venv\Scripts\python.exe -m agent.run_agent --port 8765</div>
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition shadow flex items-center justify-center space-x-1"
            >
              <span>Check Connection Now</span>
            </button>
          )}
        </div>
      )}

      {/* Pending Approvals Alert Banner */}
      {pendingApprovals.length > 0 && (
        <div className="bg-amber-950/60 border border-amber-600/50 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <div>
              <p className="text-xs font-semibold text-amber-200">
                {pendingApprovals.length} Action{pendingApprovals.length > 1 ? 's' : ''} Awaiting Approval
              </p>
              <p className="text-[11px] text-amber-300/80">
                Supervised Mode requires your verification before executing browser modifications.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('tasks')}
            className="px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-medium transition flex items-center space-x-1"
          >
            <span>Review</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Top Metric Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* Health Score Card */}
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">SEO Health Score</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">{healthScore}</span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-1.5 mt-2">
            <div
              className={`h-1.5 rounded-full ${
                healthScore > 75 ? 'bg-emerald-500' : healthScore > 50 ? 'bg-amber-500' : 'bg-rose-500'
              }`}
              style={{ width: `${healthScore}%` }}
            />
          </div>
        </div>

        {/* Websites & Daily Actions */}
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Daily Actions</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">
              {status?.stats.daily_actions ?? 0}
            </span>
            <span className="text-xs text-slate-400">/ {status?.stats.daily_limit ?? 50}</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-2">
            {websites.length} website{websites.length !== 1 ? 's' : ''} connected
          </p>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-slate-800/50 border border-slate-700/40 rounded-lg p-2.5">
          <span className="text-[10px] text-slate-400 block">Critical Issues</span>
          <span className="text-lg font-bold text-rose-400">{criticalCount}</span>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/40 rounded-lg p-2.5">
          <span className="text-[10px] text-slate-400 block">High Priority</span>
          <span className="text-lg font-bold text-amber-400">{highCount}</span>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/40 rounded-lg p-2.5">
          <span className="text-[10px] text-slate-400 block">Total Issues</span>
          <span className="text-lg font-bold text-indigo-400">{totalIssues}</span>
        </div>
      </div>

      {/* Quick Workflows Grid */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
          Autonomous Workflows
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onNavigate('setup')}
            className="col-span-2 flex items-center space-x-3 p-3 bg-gradient-to-r from-indigo-950/70 to-slate-800 hover:from-indigo-900/80 hover:to-slate-750 border border-indigo-700/50 rounded-lg text-left transition group shadow-sm"
          >
            <div className="p-2.5 bg-indigo-600 text-white rounded-lg group-hover:scale-105 transition shadow">
              <Rocket className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-1.5">
                <p className="text-xs font-bold text-white">Full Domain Setup</p>
                <span className="text-[9px] bg-indigo-500/30 text-indigo-200 px-1.5 py-0.2 rounded font-mono font-semibold">FROM SCRATCH</span>
              </div>
              <p className="text-[10px] text-slate-300 truncate">Automate GSC setup, sitemap indexing, crawl audit & roadmap</p>
            </div>
            <ArrowRight className="w-4 h-4 text-indigo-400 group-hover:translate-x-1 transition" />
          </button>

          <button
            onClick={onOpenGSC}
            className="flex items-center space-x-2 p-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg text-left transition group"
          >
            <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-md group-hover:bg-indigo-600 group-hover:text-white transition">
              <Search className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Search Console</p>
              <p className="text-[10px] text-slate-400">Launch browser UI</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('audit')}
            className="flex items-center space-x-2 p-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg text-left transition group"
          >
            <div className="p-2 bg-emerald-600/20 text-emerald-400 rounded-md group-hover:bg-emerald-600 group-hover:text-white transition">
              <TrendingUp className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Site SEO Crawl</p>
              <p className="text-[10px] text-slate-400">Audit all pages</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('opportunities')}
            className="flex items-center space-x-2 p-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg text-left transition group"
          >
            <div className="p-2 bg-amber-600/20 text-amber-400 rounded-md group-hover:bg-amber-600 group-hover:text-white transition">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Opportunities</p>
              <p className="text-[10px] text-slate-400">Review & apply</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('websites')}
            className="flex items-center space-x-2 p-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg text-left transition group"
          >
            <div className="p-2 bg-cyan-600/20 text-cyan-400 rounded-md group-hover:bg-cyan-600 group-hover:text-white transition">
              <Globe className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Add Website</p>
              <p className="text-[10px] text-slate-400">Connect new CMS</p>
            </div>
          </button>
        </div>
      </div>

      {/* Operating Principle Reminder */}
      <div className="bg-slate-850 border border-slate-800 rounded-lg p-3 text-[11px] text-slate-400 leading-relaxed">
        <span className="font-semibold text-slate-200 block mb-0.5">🔒 Browser UI First Architecture</span>
        Operates directly via your dedicated Chrome session without Search Console API dependencies. Sessions persist safely inside the local Chrome profile.
      </div>
    </div>
  );
};
