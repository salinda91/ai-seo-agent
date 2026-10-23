import React, { useState, useEffect } from 'react';
import { Play, AlertCircle, CheckCircle2, ChevronDown, ChevronRight, RefreshCw, Filter, Zap, GitCommit, Loader2, AlertTriangle, Sparkles } from 'lucide-react';
import { Website, CrawlPage, SitemapStatusResponse } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
}

export const SiteAuditView: React.FC<Props> = ({ website }) => {
  const [loading, setLoading] = useState(false);
  const [autoFixing, setAutoFixing] = useState(false);
  const [creatingSitemap, setCreatingSitemap] = useState(false);
  const [sitemapStatus, setSitemapStatus] = useState<SitemapStatusResponse | null>(null);
  const [fixResultMsg, setFixResultMsg] = useState<{ text: string; error?: boolean } | null>(null);
  const [crawlData, setCrawlData] = useState<{
    total_pages: number;
    total_issues: number;
    critical_issues: number;
    high_issues: number;
    pages: CrawlPage[];
  } | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [expandedPage, setExpandedPage] = useState<number | null>(null);

  const loadAudit = async () => {
    if (!website) return;
    try {
      const data = await api.getCrawlResults(website.id);
      setCrawlData(data);
    } catch (err: any) {
      console.warn('Could not load audit data:', err);
    }
  };

  const loadSitemapStatus = async () => {
    if (!website) return;
    try {
      const status = await api.getSitemapStatus(website.id);
      setSitemapStatus(status);
    } catch (err: any) {
      console.warn('Could not load sitemap status in audit:', err);
    }
  };

  useEffect(() => {
    loadAudit();
    loadSitemapStatus();
  }, [website]);

  const handleCreateAndUploadSitemap = async () => {
    if (!website) return;
    setCreatingSitemap(true);
    setFixResultMsg({ text: 'Creating XML sitemap, pushing to Git, and submitting to GSC...' });
    try {
      const res = await api.createAndUploadSitemap(website.id);
      if (res.success) {
        setFixResultMsg({ text: res.message || 'Sitemap created and uploaded successfully!', error: false });
        await loadSitemapStatus();
        await loadAudit();
      } else {
        setFixResultMsg({ text: res.error || 'Failed to create sitemap.', error: true });
      }
    } catch (err: any) {
      setFixResultMsg({ text: `Failed: ${err.message}`, error: true });
    } finally {
      setCreatingSitemap(false);
    }
  };

  const handleStartCrawl = async () => {
    if (!website) return;
    setLoading(true);
    try {
      await api.startCrawl(website.id, 25);
      alert('SEO crawler started in background. Refreshing results in 5 seconds...');
      setTimeout(loadAudit, 5000);
    } catch (err: any) {
      alert(`Error starting crawl: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoFixAll = async () => {
    if (!website) return;
    const isWP = website.cms_type === 'wordpress' || website.cms_type === 'woocommerce';
    if (!isWP && !website.local_repo_path) {
      alert('Please connect your local codebase folder in Connected Websites first to auto-fix and push code to Git.');
      return;
    }

    setAutoFixing(true);
    setFixResultMsg({ text: 'Applying automated fixes across audited pages...' });

    try {
      const res = await api.autoFixAllCMS(website.id);
      const fixes = res.fixes_applied ?? res.fixed_count ?? 0;
      let msg = '';
      if (isWP) {
        msg = fixes > 0
          ? `Auto-fixed ${fixes} issues in WordPress!`
          : res.message || 'No pending WordPress fixes found or changes already applied.';
      } else {
        const commit = res.commit_sha ? ` (Commit ${res.commit_sha})` : '';
        const pushMsg = res.pushed ? ' and pushed to Git remote!' : ' and committed locally.';
        msg = fixes > 0
          ? `Auto-fixed ${fixes} issues in local files${commit}${pushMsg}`
          : res.message || 'No pending issues found to fix in codebase.';
      }
      setFixResultMsg({ text: msg, error: false });
      loadAudit();
    } catch (err: any) {
      setFixResultMsg({ text: `Auto-fix failed: ${err.message}`, error: true });
    } finally {
      setAutoFixing(false);
    }
  };

  if (!website) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        Please select a connected website to view the site audit.
      </div>
    );
  }

  const isWP = website.cms_type === 'wordpress' || website.cms_type === 'woocommerce';
  const filteredPages = (crawlData?.pages || []).filter((page) => {
    if (selectedSeverity === 'all') return true;
    return page.issues.some((iss) => iss.severity === selectedSeverity);
  });

  return (
    <div className="p-4 space-y-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold text-white">Technical SEO Audit</h2>
          <p className="text-[11px] text-slate-400">Auditing {website.domain}</p>
        </div>
        <div className="flex items-center space-x-1.5">
          <button
            onClick={loadAudit}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleStartCrawl}
            disabled={loading}
            className="flex items-center space-x-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold transition"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{loading ? 'Crawling...' : 'Run Audit'}</span>
          </button>
          <button
            onClick={handleAutoFixAll}
            disabled={autoFixing}
            className={`flex items-center space-x-1 px-2.5 py-1.5 rounded text-xs font-semibold transition shadow ${
              isWP
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white'
            }`}
            title={
              isWP
                ? 'Auto-fix audit issues in WordPress'
                : 'Auto-fix audit issues in local templates and push to Git'
            }
          >
            {autoFixing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : isWP ? (
              <Zap className="w-3.5 h-3.5 text-amber-300" />
            ) : (
              <GitCommit className="w-3.5 h-3.5" />
            )}
            <span>{autoFixing ? 'Fixing...' : isWP ? 'Auto-Fix (WP)' : 'Auto-Fix & Push'}</span>
          </button>
        </div>
      </div>

      {/* Auto-Fix Feedback Toast */}
      {fixResultMsg && (
        <div
          className={`p-2.5 rounded-lg text-xs flex items-center space-x-2 ${
            fixResultMsg.error
              ? 'bg-rose-950/60 border border-rose-800 text-rose-300'
              : 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
          }`}
        >
          {fixResultMsg.error ? (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          )}
          <span>{fixResultMsg.text}</span>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-4 gap-2 text-center text-xs">
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-lg p-2">
          <span className="text-[10px] text-slate-400 block">Pages</span>
          <span className="text-base font-bold text-white">{crawlData?.total_pages ?? 0}</span>
        </div>
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-lg p-2">
          <span className="text-[10px] text-slate-400 block">Critical</span>
          <span className="text-base font-bold text-rose-400">{crawlData?.critical_issues ?? 0}</span>
        </div>
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-lg p-2">
          <span className="text-[10px] text-slate-400 block">High</span>
          <span className="text-base font-bold text-amber-400">{crawlData?.high_issues ?? 0}</span>
        </div>
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-lg p-2">
          <span className="text-[10px] text-slate-400 block">Total Issues</span>
          <span className="text-base font-bold text-indigo-400">{crawlData?.total_issues ?? 0}</span>
        </div>
      </div>

      {/* Missing XML Sitemap Warning & Create/Upload Button */}
      {sitemapStatus && !sitemapStatus.available && (
        <div className="bg-gradient-to-r from-amber-950/60 via-slate-900 to-indigo-950/40 border border-amber-800/80 rounded-xl p-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <div>
              <div className="text-xs font-bold text-white flex items-center space-x-1.5">
                <span>XML Sitemap Not Available</span>
                <span className="text-[10px] bg-rose-500/20 text-rose-300 px-1.5 py-0.2 rounded font-mono">
                  HTTP {sitemapStatus.status_code || 404}
                </span>
              </div>
              <p className="text-[11px] text-amber-200/80 mt-0.5">
                No valid XML sitemap detected. Search engines cannot index your pages reliably.
              </p>
            </div>
          </div>
          <button
            onClick={handleCreateAndUploadSitemap}
            disabled={creatingSitemap}
            className="shrink-0 ml-3 px-3 py-1.5 bg-gradient-to-r from-amber-600 to-indigo-600 hover:from-amber-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow transition"
          >
            {creatingSitemap ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-amber-200" />
            )}
            <span>{creatingSitemap ? 'Creating...' : 'Create & Upload Sitemap'}</span>
          </button>
        </div>
      )}

      {/* Severity Filter Pills */}
      <div className="flex items-center space-x-1 overflow-x-auto text-[11px]">
        {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
          <button
            key={sev}
            onClick={() => setSelectedSeverity(sev)}
            className={`px-2 py-0.5 rounded capitalize font-medium transition ${
              selectedSeverity === sev
                ? 'bg-slate-700 text-white ring-1 ring-slate-500'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Pages List */}
      <div className="space-y-2">
        {filteredPages.map((page) => {
          const isExpanded = expandedPage === page.id;
          return (
            <div
              key={page.id}
              className="bg-slate-850 border border-slate-700/60 rounded-xl overflow-hidden transition"
            >
              <div
                onClick={() => setExpandedPage(isExpanded ? null : page.id)}
                className="p-3 cursor-pointer hover:bg-slate-800/60 flex items-start justify-between space-x-2"
              >
                <div className="flex items-start space-x-2 truncate">
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="truncate">
                    <p className="text-xs font-semibold text-slate-200 truncate">{page.title || '(No Title)'}</p>
                    <p className="text-[10px] text-slate-400 font-mono truncate">{page.url}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 flex-shrink-0">
                  <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-700">
                    HTTP {page.status_code}
                  </span>
                  {page.issues.length > 0 ? (
                    <span className="text-[10px] px-1.5 py-0.5 bg-rose-500/20 text-rose-300 rounded font-bold">
                      {page.issues.length} issue{page.issues.length > 1 ? 's' : ''}
                    </span>
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  )}
                </div>
              </div>

              {isExpanded && (
                <div className="p-3 bg-slate-900 border-t border-slate-800 space-y-2 text-xs">
                  <div className="space-y-1 text-[11px]">
                    <p className="text-slate-400"><strong className="text-slate-300">Meta Description:</strong> {page.meta_description || 'Missing'}</p>
                    <p className="text-slate-400"><strong className="text-slate-300">H1:</strong> {page.h1 || 'Missing'}</p>
                    <p className="text-slate-400"><strong className="text-slate-300">Canonical:</strong> {page.canonical || 'None'}</p>
                    <p className="text-slate-400"><strong className="text-slate-300">Images without Alt:</strong> {page.images_without_alt}</p>
                  </div>

                  {page.issues.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-800 space-y-1.5">
                      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Detected Defects</p>
                      {page.issues.map((iss, idx) => (
                        <div
                          key={idx}
                          className="flex items-start space-x-2 bg-slate-850 p-2 rounded border border-slate-800 text-[11px]"
                        >
                          <AlertCircle
                            className={`w-3.5 h-3.5 flex-shrink-0 mt-0.5 ${
                              iss.severity === 'critical'
                                ? 'text-rose-400'
                                : iss.severity === 'high'
                                ? 'text-amber-400'
                                : 'text-indigo-400'
                            }`}
                          />
                          <div>
                            <span className="font-semibold text-slate-200 uppercase text-[9px] mr-1.5">
                              [{iss.severity}]
                            </span>
                            <span className="text-slate-300">{iss.message}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filteredPages.length === 0 && (
          <div className="text-center py-8 text-slate-500 text-xs">
            No audit records found. Click "Run Audit" to crawl this site.
          </div>
        )}
      </div>
    </div>
  );
};
