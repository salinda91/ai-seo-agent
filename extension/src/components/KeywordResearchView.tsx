import React, { useState, useEffect } from 'react';
import { Key, Sparkles, TrendingUp, Layers, RefreshCw } from 'lucide-react';
import { Website, KeywordItem } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
}

export const KeywordResearchView: React.FC<Props> = ({ website }) => {
  const [keywords, setKeywords] = useState<KeywordItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [clusters, setClusters] = useState<Record<string, string[]> | null>(null);

  const loadKeywords = async () => {
    if (!website) return;
    try {
      const data = await api.getKeywords(website.id);
      setKeywords(data);
    } catch (e) {
      console.warn('Could not load keywords:', e);
    }
  };

  useEffect(() => {
    loadKeywords();
  }, [website]);

  const handleCluster = async () => {
    if (keywords.length === 0) return;
    setLoading(true);
    try {
      const phrases = keywords.map((k) => k.phrase);
      const res = await api.clusterKeywords(phrases);
      setClusters(res.clusters);
    } catch (err: any) {
      alert(`Error clustering: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!website) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        Please select a connected website to view keyword research.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
            <Key className="w-4 h-4 text-indigo-400" />
            <span>Keyword Intelligence</span>
          </h2>
          <p className="text-[11px] text-slate-400">{keywords.length} tracked phrases</p>
        </div>

        <div className="flex space-x-1.5">
          <button
            onClick={loadKeywords}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleCluster}
            disabled={loading || keywords.length === 0}
            className="flex items-center space-x-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span>{loading ? 'Clustering...' : 'AI Topic Clusters'}</span>
          </button>
        </div>
      </div>

      {/* Clusters View Modal / Section */}
      {clusters && (
        <div className="bg-slate-800/90 border border-indigo-500/40 rounded-xl p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>Semantic Topic Clusters</span>
            </h3>
            <button
              onClick={() => setClusters(null)}
              className="text-[10px] text-slate-400 hover:text-white"
            >
              Close
            </button>
          </div>

          <div className="space-y-2">
            {Object.entries(clusters).map(([clusterName, phrases], i) => (
              <div key={i} className="bg-slate-900 p-2.5 rounded-lg border border-slate-750">
                <span className="text-xs font-semibold text-indigo-300 block mb-1">
                  {clusterName} ({phrases.length})
                </span>
                <div className="flex flex-wrap gap-1">
                  {phrases.map((p, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Keywords Table */}
      <div className="bg-slate-850 border border-slate-700/60 rounded-xl overflow-hidden">
        <table className="w-full text-left text-[11px]">
          <thead className="bg-slate-800 text-slate-400 font-semibold border-b border-slate-700">
            <tr>
              <th className="p-2">Keyword Phrase</th>
              <th className="p-2">Intent</th>
              <th className="p-2 text-right">Score</th>
              <th className="p-2 text-right">Pos</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {keywords.map((kw) => (
              <tr key={kw.id} className="hover:bg-slate-800/50 transition">
                <td className="p-2">
                  <span className="font-semibold text-slate-200 block truncate max-w-[140px]">{kw.phrase}</span>
                  <span className="text-[10px] text-slate-400">
                    {kw.clicks} clicks • {kw.impressions} impr
                  </span>
                </td>
                <td className="p-2">
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                      kw.search_intent === 'transactional'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : kw.search_intent === 'commercial'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-indigo-500/20 text-indigo-300'
                    }`}
                  >
                    {kw.search_intent}
                  </span>
                </td>
                <td className="p-2 text-right">
                  <span className="font-bold text-emerald-400">{kw.opportunity_score}</span>
                  <span className="text-[9px] text-slate-500">/100</span>
                </td>
                <td className="p-2 text-right text-slate-300 font-mono">
                  {kw.position > 0 ? kw.position.toFixed(1) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {keywords.length === 0 && (
          <div className="text-center py-8 text-slate-500 text-xs">
            No keywords recorded yet. Sync Google Search Console or run a crawl to discover keyword opportunities.
          </div>
        )}
      </div>
    </div>
  );
};
