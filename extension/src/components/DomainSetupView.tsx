import React, { useState, useEffect, useRef } from 'react';
import {
  Rocket,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Terminal,
  ArrowRight,
  ShieldAlert,
  Globe,
  Search,
  Sparkles,
  FileCheck,
  Zap,
  Target,
  Users,
  Compass,
  FileText,
  Link2,
  BarChart2,
  RefreshCw
} from 'lucide-react';
import { OnboardingState, OnboardingStep, Website, BusinessProfileData } from '../types';
import { api } from '../services/api';
import { NavTab } from './Navbar';

interface Props {
  websites?: Website[];
  onNavigate: (tab: NavTab) => void;
  onDomainCreated?: () => void;
}

export const DomainSetupView: React.FC<Props> = ({ websites = [], onNavigate, onDomainCreated }) => {
  const [activeMode, setActiveMode] = useState<'new_domain' | 'existing_site'>('new_domain');
  
  // New Domain Form State
  const [domain, setDomain] = useState('');
  const [name, setName] = useState('');
  const [cmsType, setCmsType] = useState('wordpress');
  const [adminUrl, setAdminUrl] = useState('');
  const [automationMode, setAutomationMode] = useState('supervised');
  const [isDomainProperty, setIsDomainProperty] = useState(false);
  const [localRepoPath, setLocalRepoPath] = useState('');
  const [gitBranch, setGitBranch] = useState('main');
  const [gitRemote, setGitRemote] = useState('origin');

  // Existing Site Form State
  const [selectedSiteId, setSelectedSiteId] = useState<number | ''>(websites[0]?.id || '');

  // Pipeline Execution State
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobType, setJobType] = useState<'onboarding' | 'pipeline'>('onboarding');
  const [steps, setSteps] = useState<Array<{ id: number; title: string; status: string; details: string; output?: string }>>([]);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [pipelineStatus, setPipelineStatus] = useState<string>('idle');
  const [activeDomain, setActiveDomain] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [businessProfile, setBusinessProfile] = useState<BusinessProfileData | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(true);
  const [showProfile, setShowProfile] = useState(true);
  const pollTimerRef = useRef<any>(null);

  // Poll status while job is in progress
  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        if (jobType === 'pipeline') {
          const state = await api.getPipelineStatus(jobId);
          setSteps(state.stages || []);
          setCurrentStep(state.current_stage || 1);
          setPipelineStatus(state.status);
          setActiveDomain(state.domain);
          setLogs(state.logs || []);

          if (state.status === 'completed' || state.status === 'failed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            if (state.website_id) {
              loadBusinessProfile(state.website_id);
            }
          }
        } else {
          const state = await api.getOnboardingStatus(jobId);
          setSteps(state.steps || []);
          setCurrentStep(state.current_step || 1);
          setPipelineStatus(state.status);
          setActiveDomain(state.domain);
          setLogs(state.logs || []);

          if (state.status === 'completed' || state.status === 'failed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            if (state.status === 'completed' && onDomainCreated) {
              onDomainCreated();
            }
            if (state.website_id) {
              loadBusinessProfile(state.website_id);
            }
          }
        }
      } catch (e: any) {
        console.debug('Polling pipeline status:', e);
      }
    };

    poll();
    pollTimerRef.current = setInterval(poll, 2500);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [jobId, jobType]);

  const loadBusinessProfile = async (siteId: number) => {
    try {
      const prof = await api.getBusinessProfile(siteId);
      if (prof && prof.business_name) {
        setBusinessProfile(prof);
      }
    } catch {}
  };

  const handleStartNewOnboarding = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanDomain = domain.replace(/^https?:\/\//i, '').replace(/\/$/, '').trim();
    if (!cleanDomain) {
      setErrorMsg('Please enter a valid domain name (e.g. example.com)');
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);
    setBusinessProfile(null);

    try {
      const res = await api.startOnboarding({
        domain: cleanDomain,
        name: name.trim() || cleanDomain,
        cms_type: cmsType,
        admin_url: adminUrl.trim() || undefined,
        automation_mode: automationMode,
        is_domain_property: isDomainProperty,
        local_repo_path: localRepoPath.trim() || undefined,
        git_branch: gitBranch.trim() || 'main',
        git_remote: gitRemote.trim() || 'origin'
      });

      if (res.job_id) {
        setJobType('onboarding');
        setActiveDomain(cleanDomain);
        setJobId(res.job_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start domain setup pipeline.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRunExistingSitePipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSiteId) {
      setErrorMsg('Please select a connected website.');
      return;
    }

    const site = websites.find((w) => w.id === Number(selectedSiteId));
    setSubmitting(true);
    setErrorMsg(null);
    setBusinessProfile(null);

    try {
      const res = await api.runRankingPipeline(Number(selectedSiteId));
      if (res.job_id) {
        setJobType('pipeline');
        setActiveDomain(site?.domain || 'Website');
        setJobId(res.job_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start 10-stage ranking workflow.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenGSC = async () => {
    try {
      await api.openGSC();
    } catch (e: any) {
      alert(`Could not open browser: ${e.message}`);
    }
  };

  const calculateProgress = (): number => {
    if (!steps || steps.length === 0) return 0;
    const completedCount = steps.filter((s) => s.status === 'completed').length;
    const runningCount = steps.filter((s) => s.status === 'running').length;
    return Math.min(100, Math.round(((completedCount + runningCount * 0.5) / steps.length) * 100));
  };

  const progressPercent = calculateProgress();
  const isRunning = pipelineStatus === 'in_progress';
  const isCompleted = pipelineStatus === 'completed';
  const isFailed = pipelineStatus === 'failed';

  const needsLogin = steps.some(
    (s) => s.status === 'warning' && s.details.toLowerCase().includes('login')
  );

  return (
    <div className="p-4 space-y-4 max-w-4xl mx-auto">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-indigo-950 via-slate-900 to-purple-950 border border-indigo-700/40 rounded-xl p-4 shadow-lg">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <Zap className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-wide">
                Complete Autonomous SEO Ranking Engine
              </h1>
              <p className="text-xs text-slate-300 mt-0.5">
                Executes the full 10-stage ranking workflow: Business intelligence, keywords, technical audit, page optimization, content gaps, internal links, GSC indexing, rankings, and continuous improvement.
              </p>
            </div>
          </div>
          {jobId && (
            <button
              onClick={() => {
                setJobId(null);
                setSteps([]);
                setPipelineStatus('idle');
              }}
              className="text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2.5 py-1 rounded transition"
            >
              + New Run
            </button>
          )}
        </div>
      </div>

      {/* Setup Mode Toggle (Shown when no active execution) */}
      {!jobId && (
        <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
          <button
            onClick={() => setActiveMode('new_domain')}
            className={`flex-1 py-1.5 rounded-md font-semibold transition flex items-center justify-center space-x-1.5 ${
              activeMode === 'new_domain'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Rocket className="w-3.5 h-3.5" />
            <span>Setup New Domain from Scratch</span>
          </button>
          <button
            onClick={() => setActiveMode('existing_site')}
            className={`flex-1 py-1.5 rounded-md font-semibold transition flex items-center justify-center space-x-1.5 ${
              activeMode === 'existing_site'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Run 10-Stage Ranking Workflow on Connected Website</span>
          </button>
        </div>
      )}

      {/* Form 1: Setup New Domain */}
      {!jobId && activeMode === 'new_domain' && (
        <form onSubmit={handleStartNewOnboarding} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3.5">
          <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
            <Globe className="w-4 h-4 text-indigo-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              New Domain & CMS Setup Parameters
            </h2>
          </div>

          {errorMsg && (
            <div className="bg-rose-950/50 border border-rose-800 text-rose-300 text-xs p-2.5 rounded flex items-center space-x-2">
              <XCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">
                Domain Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                placeholder="e.g. yourwebsite.com"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Do not include http:// or https:// (auto-normalized).
              </span>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">
                Site Friendly Label (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. My Online Store"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">CMS Platform</label>
              <select
                value={cmsType}
                onChange={(e) => setCmsType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="wordpress">WordPress / WooCommerce</option>
                <option value="shopify">Shopify</option>
                <option value="laravel">Laravel / Blade</option>
                <option value="custom">Custom Web Stack</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Admin Panel URL (Optional)</label>
              <input
                type="text"
                placeholder="https://example.com/wp-admin"
                value={adminUrl}
                onChange={(e) => setAdminUrl(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Automation Mode</label>
              <select
                value={automationMode}
                onChange={(e) => setAutomationMode(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="supervised">Supervised (Requires Human Approval)</option>
                <option value="autonomous">Autonomous (Auto-Apply Low Risk Fixes)</option>
                <option value="recommendation">Audit & Recommendations Only</option>
              </select>
            </div>
          </div>

          {cmsType !== 'wordpress' && (
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-2">
              <div className="text-xs font-semibold text-indigo-400">
                📁 Connect Local Codebase (Non-WordPress Auto-Fix & Git Push)
              </div>
              <p className="text-[10px] text-slate-400">
                Connect your local project folder so technical SEO audit fixes can be applied directly to your code templates and committed to Git.
              </p>
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">Absolute Local Project Path</label>
                <input
                  type="text"
                  placeholder="e.g. C:\Users\Dev\Projects\my-website"
                  value={localRepoPath}
                  onChange={(e) => setLocalRepoPath(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] text-slate-400 mb-0.5">Git Branch</label>
                  <input
                    type="text"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-400 mb-0.5">Git Remote</label>
                  <input
                    type="text"
                    value={gitRemote}
                    onChange={(e) => setGitRemote(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5 flex items-start space-x-2.5">
            <input
              type="checkbox"
              id="is_domain_prop"
              checked={isDomainProperty}
              onChange={(e) => setIsDomainProperty(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-0"
            />
            <label htmlFor="is_domain_prop" className="text-xs text-slate-300 cursor-pointer select-none">
              <span className="font-semibold text-white">Create as Domain Property (sc-domain:)</span>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Default unchecked uses URL-prefix (<code className="text-indigo-300">https://domain/</code>) for instant HTML tag/file verification.
              </p>
            </label>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg shadow-md transition flex items-center justify-center space-x-2"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Launching End-to-End Ranking Pipeline...</span>
              </>
            ) : (
              <>
                <Rocket className="w-4 h-4" />
                <span>Launch Complete 10-Stage SEO Ranking Pipeline</span>
              </>
            )}
          </button>
        </form>
      )}

      {/* Form 2: Run on Existing Site (Secondary Action) */}
      {!jobId && activeMode === 'existing_site' && (
        <form onSubmit={handleRunExistingSitePipeline} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-4">
          <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
            <Zap className="w-4 h-4 text-amber-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Run Complete 10-Stage Ranking Workflow on Existing Site
            </h2>
          </div>

          {errorMsg && (
            <div className="bg-rose-950/50 border border-rose-800 text-rose-300 text-xs p-2.5 rounded flex items-center space-x-2">
              <XCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {websites.length > 0 ? (
            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1.5">
                Select Website to Optimize
              </label>
              <select
                value={selectedSiteId}
                onChange={(e) => setSelectedSiteId(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
              >
                {websites.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.domain}) — {w.cms_type}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                Executes all 10 ranking stages: extracts business profile, categorizes keywords, runs full crawl, fixes technical barriers, optimizes meta & headings, outlines content gaps, graphs internal links, verifies GSC indexing, and schedules continuous improvements.
              </p>
            </div>
          ) : (
            <div className="p-4 bg-slate-900 border border-slate-800 rounded text-center text-xs text-slate-400">
              No websites connected yet. Switch to "Setup New Domain from Scratch" above.
            </div>
          )}

          {websites.length > 0 && (
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg shadow-md transition flex items-center justify-center space-x-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Starting Ranking Engine...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-amber-300" />
                  <span>Execute Complete 10-Stage Ranking Workflow Now</span>
                </>
              )}
            </button>
          )}
        </form>
      )}

      {/* Active Pipeline Status & Stepper */}
      {jobId && (
        <div className="space-y-4">
          {/* Progress Header Card */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Globe className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-white tracking-wide">{activeDomain}</span>
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${
                    isCompleted
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : isFailed
                      ? 'bg-rose-950 text-rose-400 border border-rose-800'
                      : 'bg-indigo-950 text-indigo-400 border border-indigo-800 animate-pulse'
                  }`}
                >
                  {pipelineStatus.replace('_', ' ')}
                </span>
              </div>
              <span className="text-xs font-mono font-semibold text-indigo-300">
                {progressPercent}% Complete
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  isFailed
                    ? 'bg-rose-500'
                    : isCompleted
                    ? 'bg-emerald-500'
                    : 'bg-gradient-to-r from-indigo-500 to-purple-500'
                }`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* Warning Callout */}
            {needsLogin && (
              <div className="mt-3 bg-amber-950/60 border border-amber-800/80 rounded-lg p-3 flex items-start justify-between space-x-3">
                <div className="flex items-start space-x-2.5">
                  <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-semibold text-amber-200">Google Authentication Required</h4>
                    <p className="text-[11px] text-amber-300/80 mt-0.5">
                      Please sign into Google in the open browser window so the agent can submit sitemaps and inspect indexation.
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleOpenGSC}
                  className="shrink-0 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-[11px] px-2.5 py-1.5 rounded transition flex items-center space-x-1"
                >
                  <span>Open Browser</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            )}

            {/* Success Shortcuts */}
            {isCompleted && (
              <div className="mt-3 bg-emerald-950/50 border border-emerald-800/80 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="text-xs font-medium text-emerald-200">
                    Complete 10-Stage Ranking Workflow finished! Business profile, keywords, and roadmap generated.
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => onNavigate('opportunities')}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-medium px-2.5 py-1 rounded transition flex items-center space-x-1"
                  >
                    <span>View Opportunities</span>
                    <Sparkles className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => onNavigate('keywords')}
                    className="bg-purple-600 hover:bg-purple-500 text-white text-[11px] font-medium px-2.5 py-1 rounded transition flex items-center space-x-1"
                  >
                    <span>Keywords</span>
                    <Target className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => onNavigate('audit')}
                    className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium px-2.5 py-1 rounded transition flex items-center space-x-1"
                  >
                    <span>Crawl Audit</span>
                    <FileCheck className="w-3 h-3" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Generated Business Profile Drawer (Stage 1 Output) */}
          {businessProfile && (
            <div className="bg-slate-950 border border-indigo-900/60 rounded-xl overflow-hidden shadow-sm">
              <button
                onClick={() => setShowProfile(!showProfile)}
                className="w-full px-3 py-2 bg-indigo-950/40 flex items-center justify-between text-xs text-indigo-300 font-semibold hover:bg-indigo-900/40 transition"
              >
                <div className="flex items-center space-x-2">
                  <Target className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Stage 1 Output: Business Profile & SEO Goals</span>
                </div>
                {showProfile ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              {showProfile && (
                <div className="p-3 text-xs space-y-2.5 bg-slate-950">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Summary</span>
                    <p className="text-slate-200 text-[11px] leading-relaxed">{businessProfile.summary}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[11px]">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Core Offerings</span>
                      <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                        {businessProfile.offerings.map((o, idx) => (
                          <li key={idx} className="truncate">{o}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Target Audience</span>
                      <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                        {businessProfile.target_audience.map((a, idx) => (
                          <li key={idx} className="truncate">{a}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-indigo-400 block mb-1">Prioritized SEO Goals</span>
                    <ul className="space-y-1 text-[11px] text-slate-300 font-mono">
                      {businessProfile.seo_goals.map((g, idx) => (
                        <li key={idx} className="flex items-start space-x-1.5">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{g}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Stepper Cards */}
          <div className="space-y-2">
            {steps.map((step) => {
              const isStepRunning = step.status === 'running';
              const isStepCompleted = step.status === 'completed';
              const isStepWarning = step.status === 'warning';
              const isStepFailed = step.status === 'failed';
              const isStepPending = step.status === 'pending';

              return (
                <div
                  key={step.id}
                  className={`border rounded-lg p-3 transition flex items-start space-x-3 ${
                    isStepRunning
                      ? 'bg-indigo-950/30 border-indigo-600/60 shadow-sm'
                      : isStepCompleted
                      ? 'bg-slate-950 border-emerald-900/40'
                      : isStepWarning
                      ? 'bg-amber-950/20 border-amber-800/50'
                      : isStepFailed
                      ? 'bg-rose-950/20 border-rose-800/50'
                      : 'bg-slate-950/60 border-slate-800 opacity-60'
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {isStepRunning && <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
                    {isStepCompleted && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                    {isStepWarning && <AlertTriangle className="w-4 h-4 text-amber-400" />}
                    {isStepFailed && <XCircle className="w-4 h-4 text-rose-400" />}
                    {isStepPending && <Clock className="w-4 h-4 text-slate-500" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-200">
                        {step.title}
                      </span>
                      <span
                        className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                          isStepRunning
                            ? 'text-indigo-400 bg-indigo-950/60'
                            : isStepCompleted
                            ? 'text-emerald-400 bg-emerald-950/60'
                            : isStepWarning
                            ? 'text-amber-400 bg-amber-950/60'
                            : isStepFailed
                            ? 'text-rose-400 bg-rose-950/60'
                            : 'text-slate-500 bg-slate-900'
                        }`}
                      >
                        {step.status}
                      </span>
                    </div>

                    {step.output && !step.details && (
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        Expected Output: {step.output}
                      </p>
                    )}

                    {step.details && (
                      <p className="text-[11px] text-slate-300 mt-1 leading-relaxed bg-slate-900/80 px-2 py-1 rounded border border-slate-800/60">
                        {step.details}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Activity Logs Drawer */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="w-full px-3 py-2 bg-slate-900 flex items-center justify-between text-xs text-slate-300 font-medium hover:bg-slate-850 transition"
            >
              <div className="flex items-center space-x-2">
                <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                <span>Execution Activity Logs ({logs.length})</span>
              </div>
              {showLogs ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showLogs && (
              <div className="p-3 bg-slate-950 font-mono text-[11px] text-slate-300 space-y-1 max-h-48 overflow-y-auto">
                {logs.map((log, index) => (
                  <div key={index} className="leading-snug">
                    <span className="text-slate-500 select-none mr-2">{index + 1}.</span>
                    <span
                      className={
                        log.includes('[ERROR]')
                          ? 'text-rose-400'
                          : log.includes('[WARNING]')
                          ? 'text-amber-300'
                          : log.includes('[COMPLETED]')
                          ? 'text-emerald-400'
                          : 'text-slate-300'
                      }
                    >
                      {log}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
