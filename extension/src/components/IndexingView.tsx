import React, { useState, useEffect } from 'react';
import { Send, CheckCircle2, Clock, AlertCircle, RefreshCw, AlertTriangle, Sparkles, Loader2 } from 'lucide-react';
import { Website, SitemapStatusResponse } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
}

export const IndexingView: React.FC<Props> = ({ website }) => {
  const [url, setUrl] = useState('');
  const [requestIndexing, setRequestIndexing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  // Sitemap status & creation state
  const [sitemapStatus, setSitemapStatus] = useState<SitemapStatusResponse | null>(null);
  const [creatingSitemap, setCreatingSitemap] = useState(false);
  const [sitemapMsg, setSitemapMsg] = useState<{ text: string; error?: boolean } | null>(null);

  const loadSitemap = async () => {
    if (!website) return;
    try {
      const res = await api.getSitemapStatus(website.id);
      setSitemapStatus(res);
    } catch (e) {
      console.warn('Could not load sitemap status in indexing:', e);
    }
  };

  useEffect(() => {
    loadSitemap();
  }, [website]);

  const handleCreateSitemap = async () => {
    if (!website) return;
    setCreatingSitemap(true);
    setSitemapMsg({ text: 'Creating XML sitemap and submitting to GSC...' });
    try {
      const res = await api.createAndUploadSitemap(website.id);
      if (res.success) {
        setSitemapMsg({ text: res.message || 'Sitemap created and uploaded successfully!', error: false });
        await loadSitemap();
      } else {
        setSitemapMsg({ text: res.error || 'Failed to create sitemap.', error: true });
      }
    } catch (err: any) {
      setSitemapMsg({ text: `Failed: ${err.message}`, error: true });
    } finally {
      setCreatingSitemap(false);
    }
  };

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

      {/* Sitemap Feedback Toast */}
      {sitemapMsg && (
        <div
          className={`p-2.5 rounded-lg text-xs flex items-center space-x-2 ${
            sitemapMsg.error
              ? 'bg-rose-950/60 border border-rose-800 text-rose-300'
              : 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
          }`}
        >
          {sitemapMsg.error ? (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          )}
          <span>{sitemapMsg.text}</span>
        </div>
      )}

      {/* Missing Sitemap Warning Banner */}
      {sitemapStatus && !sitemapStatus.available && (
        <div className="bg-gradient-to-r from-amber-950/50 via-slate-900 to-indigo-950/40 border border-amber-800/80 rounded-xl p-3 flex items-center justify-between shadow-sm">
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
                No sitemap found at sitemap.xml. Generating a sitemap ensures all URLs are discovered.
              </p>
            </div>
          </div>
          <button
            onClick={handleCreateSitemap}
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
