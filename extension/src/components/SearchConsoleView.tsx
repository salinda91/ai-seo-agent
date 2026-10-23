import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Plus, Send, ExternalLink, ShieldCheck, AlertCircle, AlertTriangle, CheckCircle2, Sparkles, Loader2, FileCode } from 'lucide-react';
import { Website, SitemapStatusResponse } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
}

export const SearchConsoleView: React.FC<Props> = ({ website }) => {
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<{
    total_clicks: string;
    total_impressions: string;
    average_ctr: string;
    average_position: string;
  } | null>(null);
  const [queries, setQueries] = useState<any[]>([]);
  const [sitemapInput, setSitemapInput] = useState('sitemap.xml');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Sitemap management state
  const [sitemapStatus, setSitemapStatus] = useState<SitemapStatusResponse | null>(null);
  const [checkingSitemap, setCheckingSitemap] = useState(false);
  const [creatingSitemap, setCreatingSitemap] = useState(false);
  const [sitemapFeedback, setSitemapFeedback] = useState<{ text: string; error?: boolean } | null>(null);

  const loadSitemapStatus = async () => {
    if (!website) return;
    setCheckingSitemap(true);
    try {
      const res = await api.getSitemapStatus(website.id);
      setSitemapStatus(res);
      if (res.available && res.sitemap_url) {
        const slug = res.sitemap_url.split('/').pop() || 'sitemap.xml';
        setSitemapInput(slug);
      }
    } catch (err: any) {
      console.warn('Could not inspect sitemap status:', err);
    } finally {
      setCheckingSitemap(false);
    }
  };

  useEffect(() => {
    loadSitemapStatus();
  }, [website]);

  if (!website) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        Please select a connected website from the top bar or Websites tab.
      </div>
    );
  }

  const handleOpenGSC = async () => {
    setLoading(true);
    try {
      const res = await api.openGSC();
      if (res.needs_login) {
        setStatusMessage('Google login required. Please sign into Google in the opened browser window.');
      } else {
        setStatusMessage('Search Console opened in dedicated browser profile.');
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAddProperty = async () => {
    setLoading(true);
    setStatusMessage('Automating Add Property workflow in Search Console...');
    try {
      const res = await api.addGSCProperty(website.id);
      setStatusMessage(res.instructions || 'Add property initiated.');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncPerformance = async () => {
    setLoading(true);
    setStatusMessage('Reading Performance scorecards and queries from Search Console UI...');
    try {
      const res = await api.syncGSCPerformance(website.id);
      if (res.metrics) setMetrics(res.metrics);
      if (res.queries) setQueries(res.queries);
      setStatusMessage(`Synced ${res.queries_count || 0} queries and ${res.pages_count || 0} pages from GSC UI.`);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitSitemap = async () => {
    if (!sitemapInput) return;
    setLoading(true);
    try {
      const res = await api.submitGSCSitemap(website.id, sitemapInput);
      setStatusMessage(res.message || 'Sitemap submitted in GSC.');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAndUploadSitemap = async () => {
    if (!website) return;
    setCreatingSitemap(true);
    setSitemapFeedback({ text: 'Generating XML sitemap with all indexable URLs, deploying to codebase, and submitting to GSC...' });
    try {
      const res = await api.createAndUploadSitemap(website.id);
      if (res.success) {
        setSitemapFeedback({ text: res.message || 'XML sitemap created, deployed to website, and submitted to Search Console!', error: false });
        setSitemapInput('sitemap.xml');
        await loadSitemapStatus();
      } else {
        setSitemapFeedback({ text: res.error || 'Failed to create and upload sitemap.', error: true });
      }
    } catch (err: any) {
      setSitemapFeedback({ text: `Failed: ${err.message}`, error: true });
    } finally {
      setCreatingSitemap(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header & Browser Workflow Triggers */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
              <span>Google Search Console</span>
              <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded font-medium">Browser First</span>
            </h2>
            <p className="text-[11px] text-slate-400">Target Property: {website.gsc_property_id || website.domain}</p>
          </div>
          <button
            onClick={handleOpenGSC}
            disabled={loading}
            className="flex items-center space-x-1 px-2.5 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded text-xs font-medium transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open in Chrome</span>
          </button>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={handleSyncPerformance}
            disabled={loading}
            className="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold flex items-center justify-center space-x-1 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Performance</span>
          </button>

          <button
            onClick={handleAddProperty}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white rounded text-xs font-medium flex items-center space-x-1 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Property</span>
          </button>
        </div>

        {statusMessage && (
          <div className="bg-slate-900/90 border border-slate-700 rounded p-2 text-[11px] text-slate-300 flex items-start space-x-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      {/* Scorecards */}
      {metrics && (
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-2.5">
            <span className="text-[10px] text-slate-400 block">Total Clicks</span>
            <span className="text-xl font-extrabold text-indigo-400">{metrics.total_clicks}</span>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-2.5">
            <span className="text-[10px] text-slate-400 block">Total Impressions</span>
            <span className="text-xl font-extrabold text-cyan-400">{metrics.total_impressions}</span>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-2.5">
            <span className="text-[10px] text-slate-400 block">Average CTR</span>
            <span className="text-xl font-extrabold text-emerald-400">{metrics.average_ctr}</span>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-2.5">
            <span className="text-[10px] text-slate-400 block">Average Position</span>
            <span className="text-xl font-extrabold text-amber-400">{metrics.average_position}</span>
          </div>
        </div>
      )}

      {/* Sitemaps Manager Bar */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileCode className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold text-slate-200">XML Sitemap & Indexation</h3>
          </div>
          <button
            onClick={loadSitemapStatus}
            disabled={checkingSitemap}
            className="flex items-center space-x-1 text-[11px] text-slate-400 hover:text-slate-200 transition"
            title="Re-check sitemap availability"
          >
            <RefreshCw className={`w-3 h-3 ${checkingSitemap ? 'animate-spin' : ''}`} />
            <span>Check Status</span>
          </button>
        </div>

        {/* Feedback message */}
        {sitemapFeedback && (
          <div
            className={`p-2.5 rounded-lg text-xs flex items-center space-x-2 ${
              sitemapFeedback.error
                ? 'bg-rose-950/60 border border-rose-800 text-rose-300'
                : 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
            }`}
          >
            {sitemapFeedback.error ? (
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            ) : (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            )}
            <span>{sitemapFeedback.text}</span>
          </div>
        )}

        {/* Condition 1: Sitemap is NOT available */}
        {sitemapStatus && !sitemapStatus.available ? (
          <div className="bg-gradient-to-br from-amber-950/50 to-slate-900 border border-amber-800/80 rounded-xl p-3 space-y-3">
            <div className="flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-bold text-white">XML Sitemap Not Available</span>
                  <span className="text-[10px] bg-rose-500/20 text-rose-300 px-1.5 py-0.2 rounded font-mono">
                    HTTP {sitemapStatus.status_code || 404}
                  </span>
                </div>
                <p className="text-[11px] text-amber-200/90 leading-relaxed">
                  No valid XML sitemap was detected at <span className="font-mono text-amber-100 bg-amber-900/60 px-1 py-0.5 rounded">https://{website.domain}/sitemap.xml</span>.
                  Search engines need an XML sitemap to discover and rank all your pages.
                </p>
              </div>
            </div>

            <button
              onClick={handleCreateAndUploadSitemap}
              disabled={creatingSitemap}
              className="w-full py-2 px-3 bg-gradient-to-r from-amber-600 via-orange-600 to-indigo-600 hover:from-amber-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold flex items-center justify-center space-x-2 shadow-lg transition"
            >
              {creatingSitemap ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-amber-200" />
              )}
              <span>{creatingSitemap ? 'Generating & Uploading Sitemap...' : 'Create and Upload Sitemap'}</span>
            </button>
          </div>
        ) : sitemapStatus?.available ? (
          /* Condition 2: Sitemap IS live and available */
          <div className="bg-emerald-950/30 border border-emerald-800/60 rounded-xl p-2.5 flex items-center justify-between">
            <div className="flex items-center space-x-2 truncate">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <div className="truncate">
                <span className="text-[10px] text-emerald-300 font-semibold block">Live XML Sitemap Verified</span>
                <span className="text-[11px] text-slate-300 font-mono truncate">{sitemapStatus.sitemap_url}</span>
              </div>
            </div>
            <div className="flex items-center space-x-1.5 shrink-0 ml-2">
              <a
                href={sitemapStatus.sitemap_url}
                target="_blank"
                rel="noreferrer"
                className="p-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] flex items-center space-x-1 px-2 transition"
              >
                <ExternalLink className="w-3 h-3" />
                <span>View</span>
              </a>
              <button
                onClick={handleCreateAndUploadSitemap}
                disabled={creatingSitemap}
                className="p-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded text-[11px] flex items-center space-x-1 px-2 transition"
                title="Re-generate and push latest URLs"
              >
                {creatingSitemap ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                <span>Update</span>
              </button>
            </div>
          </div>
        ) : null}

        {/* Manual GSC Submission Form */}
        <div className="pt-1">
          <label className="text-[10px] text-slate-400 block mb-1">Submit Sitemap to Search Console</label>
          <div className="flex space-x-1.5">
            <input
              type="text"
              value={sitemapInput}
              onChange={(e) => setSitemapInput(e.target.value)}
              placeholder="sitemap.xml"
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
            <button
              onClick={handleSubmitSitemap}
              disabled={loading}
              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-medium flex items-center space-x-1 transition"
            >
              <Send className="w-3 h-3" />
              <span>Submit to GSC</span>
            </button>
          </div>
        </div>
      </div>

      {/* Queries Table */}
      {queries.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-slate-300">Top Queries ({queries.length})</h3>
          <div className="bg-slate-850 border border-slate-700/60 rounded-xl overflow-hidden">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-800 text-slate-400 font-semibold border-b border-slate-700">
                <tr>
                  <th className="p-2">Query</th>
                  <th className="p-2 text-right">Clicks</th>
                  <th className="p-2 text-right">Impr</th>
                  <th className="p-2 text-right">Pos</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {queries.map((q, i) => (
                  <tr key={i} className="hover:bg-slate-800/50 transition">
                    <td className="p-2 font-medium text-slate-200 truncate max-w-[150px]">{q.query}</td>
                    <td className="p-2 text-right text-indigo-300">{q.clicks}</td>
                    <td className="p-2 text-right text-slate-400">{q.impressions}</td>
                    <td className="p-2 text-right text-amber-300">{q.position}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
