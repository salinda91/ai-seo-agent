import React, { useState } from 'react';
import { Search, RefreshCw, Plus, Send, ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react';
import { Website } from '../types';
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
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3 space-y-2">
        <h3 className="text-xs font-semibold text-slate-200">Submit Sitemap via UI</h3>
        <div className="flex space-x-1.5">
          <input
            type="text"
            value={sitemapInput}
            onChange={(e) => setSitemapInput(e.target.value)}
            placeholder="sitemap.xml"
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            onClick={handleSubmitSitemap}
            disabled={loading}
            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-medium flex items-center space-x-1 transition"
          >
            <Send className="w-3 h-3" />
            <span>Submit</span>
          </button>
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
