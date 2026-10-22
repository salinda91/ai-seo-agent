import React from 'react';
import { Cpu, ShieldCheck, ShieldAlert, CheckCircle2, Lock } from 'lucide-react';
import { Website } from '../types';

interface Props {
  website: Website | null;
}

export const AutomationRulesView: React.FC<Props> = ({ website }) => {
  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
          <Cpu className="w-4 h-4 text-indigo-400" />
          <span>Automation Rules & Safety Governance</span>
        </h2>
        <p className="text-[11px] text-slate-400">
          Strict security boundaries and operational permission controls
        </p>
      </div>

      {/* Modes Explanation Cards */}
      <div className="space-y-2.5">
        <div className={`p-3 rounded-xl border transition ${
          website?.automation_mode === 'recommendation'
            ? 'bg-slate-800 border-indigo-500 ring-1 ring-indigo-500'
            : 'bg-slate-850 border-slate-700/60'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold text-white flex items-center space-x-1.5">
              <span>Recommendation Mode</span>
              {website?.automation_mode === 'recommendation' && (
                <span className="text-[9px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded font-medium">Active</span>
              )}
            </span>
            <ShieldCheck className="w-4 h-4 text-slate-400" />
          </div>
          <p className="text-[11px] text-slate-300">
            Read-only inspections. Audits websites, reads Search Console, and generates recommendations. Never makes automated changes to website CMS.
          </p>
        </div>

        <div className={`p-3 rounded-xl border transition ${
          website?.automation_mode === 'supervised'
            ? 'bg-slate-800 border-indigo-500 ring-1 ring-indigo-500'
            : 'bg-slate-850 border-slate-700/60'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold text-white flex items-center space-x-1.5">
              <span>Supervised Mode (Default)</span>
              {website?.automation_mode === 'supervised' && (
                <span className="text-[9px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded font-medium">Active</span>
              )}
            </span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-[11px] text-slate-300">
            Generates diffs and queues all proposed browser actions in the Task Queue. Execution occurs only after you click 'Approve'.
          </p>
        </div>

        <div className={`p-3 rounded-xl border transition ${
          website?.automation_mode === 'autonomous'
            ? 'bg-slate-800 border-indigo-500 ring-1 ring-indigo-500'
            : 'bg-slate-850 border-slate-700/60'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold text-white flex items-center space-x-1.5">
              <span>Autonomous Mode</span>
              {website?.automation_mode === 'autonomous' && (
                <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded font-medium">Active</span>
              )}
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-[11px] text-slate-300">
            Automatically executes verified low-risk optimizations (e.g. updating empty meta descriptions) within the daily action limit (50/day).
          </p>
        </div>
      </div>

      {/* High Risk Operations Gating */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-2.5">
        <h3 className="text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
          <Lock className="w-3.5 h-3.5 text-rose-400" />
          <span>High-Risk Operations (Mandatory Human Approval)</span>
        </h3>
        <p className="text-[10px] text-slate-400">
          The following operations are hardcoded to NEVER execute autonomously:
        </p>
        <ul className="space-y-1.5 text-[11px] text-slate-300">
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            <span>Deleting or unpublishing existing pages/posts</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            <span>Changing permalink / URL slug structures</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            <span>Modifying robots.txt or site-wide canonical tags</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            <span>Changing redirects (301 / 302 rules)</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            <span>Modifying user roles, credentials, or security settings</span>
          </li>
        </ul>
      </div>

      {/* Safety Interceptor Guarantees */}
      <div className="bg-slate-850 border border-slate-800 rounded-xl p-3 text-[11px] text-slate-400 space-y-1">
        <span className="font-semibold text-slate-200 block">🛑 Automatic Challenge Interception</span>
        <p>
          The agent automatically pauses when detecting CAPTCHA challenges, Google MFA/2FA, or expired login sessions, alerting you to take over manually.
        </p>
      </div>
    </div>
  );
};
