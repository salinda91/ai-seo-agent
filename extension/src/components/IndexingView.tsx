import React, { useState } from 'react';
import { Send, CheckCircle2, Clock, AlertCircle, RefreshCw } from 'lucide-react';
import { Website } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
}

export const IndexingView: React.FC<Props> = ({ website }) => {
  const [url, setUrl] = useState('');
  const [requestIndexing, setRequestIndexing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!website || !url) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.inspectGSCUrl(website.id, url, requestIndexing);
      setResult(res);
    } catch (err: any) {
      alert(`URL inspection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!website) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        Please select a connected website to inspect URLs.
      </div>
    );
  }

  const inspection = result?.inspection;
  const indexingReq = result?.indexing_request;

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
          <Send className="w-4 h-4 text-indigo-400" />
          <span>URL Inspection & Indexing</span>
        </h2>
        <p className="text-[11px] text-slate-400">
          Direct Googlebot inspection & indexing requests via Search Console UI
        </p>
      </div>

      <form onSubmit={handleInspect} className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-3">
        <div>
          <label className="text-[10px] text-slate-400 block mb-1">Target URL to Inspect</label>
          <input
            type="text"
            placeholder={`https://${website.domain}/new-page`}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="request_indexing"
            checked={requestIndexing}
            onChange={(e) => setRequestIndexing(e.target.checked)}
            className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
          />
          <label htmlFor="request_indexing" className="text-xs text-slate-300">
            Automatically click "Request Indexing" if eligible
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Inspecting in Search Console...' : 'Inspect URL'}</span>
        </button>
      </form>

      {/* Result Card */}
      {result && (
        <div className="bg-slate-850 border border-slate-700 rounded-xl p-3.5 space-y-3 text-xs">
          <h3 className="font-bold text-white flex items-center space-x-1.5">
            {inspection?.is_on_google ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-amber-400" />
            )}
            <span>{inspection?.is_on_google ? 'URL is on Google' : 'URL is not on Google'}</span>
          </h3>

          <div className="space-y-1 text-[11px] text-slate-300">
            <p><strong className="text-slate-400">Inspected URL:</strong> {inspection?.target_url}</p>
            <p><strong className="text-slate-400">Index Status:</strong> {inspection?.is_indexed ? 'Page is indexed' : 'Not indexed or pending'}</p>
            {inspection?.status_details?.length > 0 && (
              <div>
                <strong className="text-slate-400 block">Identified Issues:</strong>
                <ul className="list-disc list-inside text-amber-300">
                  {inspection.status_details.map((d: string, i: number) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {indexingReq && (
            <div className={`p-2.5 rounded-lg border text-[11px] ${
              indexingReq.success
                ? 'bg-emerald-950/40 border-emerald-600/40 text-emerald-200'
                : 'bg-amber-950/40 border-amber-600/40 text-amber-200'
            }`}>
              <span className="font-bold block mb-0.5">Indexing Request Result:</span>
              <span>{indexingReq.message}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
