import React, { useState } from 'react';
import { Sparkles, Check, ArrowRight, FileEdit, Send } from 'lucide-react';
import { Website } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
}

export const ContentOptimizerView: React.FC<Props> = ({ website }) => {
  const [url, setUrl] = useState('');
  const [targetKeyword, setTargetKeyword] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contentSnippet, setContentSnippet] = useState('');
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);

  // Suggested values from Gemini
  const [suggestedTitle, setSuggestedTitle] = useState('');
  const [suggestedDesc, setSuggestedDesc] = useState('');
  const [suggestedH1, setSuggestedH1] = useState('');
  const [rationale, setRationale] = useState('');

  const handleOptimize = async () => {
    if (!targetKeyword) {
      alert('Please enter a target keyword.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.optimizeMeta({
        url: url || `https://${website?.domain || 'example.com'}`,
        current_title: title,
        current_description: description,
        target_keyword: targetKeyword,
        page_snippet: contentSnippet
      });

      const after = res.after || {};
      setSuggestedTitle(after.title || '');
      setSuggestedDesc(after.meta_description || '');
      setSuggestedH1(after.h1 || '');
      setRationale(res.rationale || res.expected_benefit || '');
    } catch (err: any) {
      alert(`Optimization error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyToCMS = async () => {
    if (!website) return;
    if (!url) {
      alert('Please enter target URL to update in CMS.');
      return;
    }
    setApplying(true);
    try {
      if (suggestedDesc) {
        await api.applyChange({
          website_id: website.id,
          url: url,
          field_name: 'meta_description',
          new_value: suggestedDesc
        });
      }
      alert('SEO updates submitted to browser automation engine!');
    } catch (err: any) {
      alert(`Failed to apply: ${err.message}`);
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
          <FileEdit className="w-4 h-4 text-indigo-400" />
          <span>Content & Meta Optimizer</span>
        </h2>
        <p className="text-[11px] text-slate-400">AI-driven Title Tag & Meta Description engineering</p>
      </div>

      <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-3">
        <div>
          <label className="text-[10px] text-slate-400 block mb-1">Target Page URL</label>
          <input
            type="text"
            placeholder={`https://${website?.domain || 'example.com'}/blog/post`}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="text-[10px] text-slate-400 block mb-1">Primary Target Keyword *</label>
          <input
            type="text"
            placeholder="e.g. best enterprise seo software"
            value={targetKeyword}
            onChange={(e) => setTargetKeyword(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] text-slate-400">Current Title Tag</label>
            <span className={`text-[10px] ${title.length > 60 ? 'text-amber-400' : 'text-slate-400'}`}>
              {title.length} / 60 chars
            </span>
          </div>
          <input
            type="text"
            placeholder="Current title..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] text-slate-400">Current Meta Description</label>
            <span className={`text-[10px] ${description.length > 160 ? 'text-amber-400' : 'text-slate-400'}`}>
              {description.length} / 160 chars
            </span>
          </div>
          <textarea
            rows={2}
            placeholder="Current meta description..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <button
          onClick={handleOptimize}
          disabled={loading || !targetKeyword}
          className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          <span>{loading ? 'Analyzing with Gemini...' : 'Generate AI Meta Optimization'}</span>
        </button>
      </div>

      {/* Suggested Results */}
      {suggestedTitle && (
        <div className="bg-slate-850 border border-emerald-500/40 rounded-xl p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-emerald-300 flex items-center space-x-1">
              <Check className="w-4 h-4 text-emerald-400" />
              <span>Optimized Output</span>
            </h3>
            {rationale && <span className="text-[10px] text-slate-400">{rationale}</span>}
          </div>

          <div>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[10px] text-slate-400">Optimized Title:</span>
              <span className="text-[10px] text-emerald-400 font-mono">{suggestedTitle.length} chars (Optimal: 45-60)</span>
            </div>
            <p className="bg-slate-900 border border-slate-800 rounded p-2 text-xs font-semibold text-white">
              {suggestedTitle}
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[10px] text-slate-400">Optimized Meta Description:</span>
              <span className="text-[10px] text-emerald-400 font-mono">{suggestedDesc.length} chars (Optimal: 130-160)</span>
            </div>
            <p className="bg-slate-900 border border-slate-800 rounded p-2 text-xs text-slate-200">
              {suggestedDesc}
            </p>
          </div>

          {suggestedH1 && (
            <div>
              <span className="text-[10px] text-slate-400 block mb-0.5">H1 Suggestion:</span>
              <p className="bg-slate-900 border border-slate-800 rounded p-2 text-xs text-slate-300">
                {suggestedH1}
              </p>
            </div>
          )}

          <button
            onClick={handleApplyToCMS}
            disabled={applying}
            className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-semibold flex items-center justify-center space-x-1 transition"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{applying ? 'Updating CMS...' : 'Push to CMS via Browser Automation'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
