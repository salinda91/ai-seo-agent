import React, { useState, useEffect } from 'react';
import { Sparkles, Check, X, RotateCcw, ShieldCheck, ArrowRight, RefreshCw, AlertCircle, Zap, GitCommit, Loader2 } from 'lucide-react';
import { Website, RecommendationItem, ChangeRecordItem } from '../types';
import { api } from '../services/api';

interface Props {
  website: Website | null;
  onRefreshStats: () => void;
}

export const SEOOpportunitiesView: React.FC<Props> = ({ website, onRefreshStats }) => {
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [changes, setChanges] = useState<ChangeRecordItem[]>([]);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [batchFixing, setBatchFixing] = useState(false);
  const [batchFeedback, setBatchFeedback] = useState<{ text: string; error?: boolean } | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'pending' | 'history'>('pending');

  const loadData = async () => {
    if (!website) return;
    try {
      const recs = await api.getRecommendations(website.id);
      const chg = await api.getChanges(website.id);
      setRecommendations(recs);
      setChanges(chg);
    } catch (e) {
      console.warn('Error loading recommendations:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, [website]);

  const handleApply = async (rec: RecommendationItem) => {
    if (!website) return;
    const isWP = website.cms_type === 'wordpress' || website.cms_type === 'woocommerce';
    if (!isWP && !website.local_repo_path) {
      alert('This website is configured as custom/codebase. Please connect its local codebase folder path in Connected Websites first so the agent can apply changes to code and push to Git.');
      return;
    }

    setLoadingId(rec.id);
    try {
      const changeData = rec.proposed_change_data || {};
      const field = changeData.field || 'meta_description';
      const newVal = changeData.proposed_value || rec.proposed_fix;

      const res = await api.applyChange({
        website_id: website.id,
        recommendation_id: rec.id,
        url: rec.url,
        field_name: field,
        new_value: newVal
      });

      if (res.success) {
        if (res.applied_to === 'code' || res.file) {
          alert(`Success! ${res.message || `Applied change directly to code file ${res.file} and pushed to Git!`}`);
        } else if (res.verified_live) {
          alert('Success! Change applied and verified directly on the live website HTML!');
        } else {
          alert(res.message || 'Change applied to CMS. Live verification will confirm during next cycle.');
        }
        loadData();
        onRefreshStats();
      } else {
        alert(`Apply error: ${res.error || 'Failed to apply'}`);
      }
    } catch (err: any) {
      alert(`Error applying change: ${err.message}`);
    } finally {
      setLoadingId(null);
    }
  };

  const handleRollback = async (changeId: number) => {
    if (!confirm('Revert this change and restore the previous value on the website?')) return;
    try {
      const res = await api.rollbackChange(changeId);
      if (res.success) {
        alert('Change successfully rolled back and previous state restored!');
        loadData();
      } else {
        alert(`Rollback error: ${res.error || 'Failed'}`);
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleAutoFixAll = async () => {
    if (!website) return;
    const isWP = website.cms_type === 'wordpress' || website.cms_type === 'woocommerce';
    if (!isWP && !website.local_repo_path) {
      alert('Please connect your local codebase folder in Connected Websites first to auto-fix and push code to Git.');
      return;
    }

    setBatchFixing(true);
    setBatchFeedback({ text: 'Applying automated fixes across all recommendations...' });

    try {
      const res = await api.autoFixAllCMS(website.id);
      const fixes = res.fixes_applied ?? res.fixed_count ?? 0;
      let msg = '';
      if (isWP) {
        msg = fixes > 0
          ? `Successfully auto-fixed ${fixes} issues directly in WordPress!`
          : res.message || 'No pending WordPress fixes found or changes already applied.';
      } else {
        const commit = res.commit_sha ? ` (Commit ${res.commit_sha})` : '';
        const pushMsg = res.pushed ? ' and pushed to Git remote!' : ' and committed locally.';
        msg = fixes > 0
          ? `Successfully auto-fixed ${fixes} issues in local files${commit}${pushMsg}`
          : res.message || 'No pending issues found to fix in codebase.';
      }
      setBatchFeedback({ text: msg, error: false });
      loadData();
      onRefreshStats();
    } catch (err: any) {
      setBatchFeedback({ text: `Auto-fix failed: ${err.message}`, error: true });
    } finally {
      setBatchFixing(false);
    }
  };

  if (!website) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs">
        Please select a connected website to view SEO opportunities.
      </div>
    );
  }

  const pendingRecs = recommendations.filter((r) => r.status === 'suggested');
  const isWP = website.cms_type === 'wordpress' || website.cms_type === 'woocommerce';

  return (
    <div className="p-4 space-y-4">
      {/* Header and Sub-tabs */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold text-white flex items-center space-x-1.5">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>SEO Opportunities</span>
          </h2>
          <p className="text-[11px] text-slate-400">{pendingRecs.length} actionable improvements</p>
        </div>

        <div className="flex bg-slate-800 p-0.5 rounded-lg text-xs">
          <button
            onClick={() => setActiveSubTab('pending')}
            className={`px-2 py-1 rounded font-medium transition ${
              activeSubTab === 'pending' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Pending ({pendingRecs.length})
          </button>
          <button
            onClick={() => setActiveSubTab('history')}
            className={`px-2 py-1 rounded font-medium transition ${
              activeSubTab === 'history' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            History ({changes.length})
          </button>
        </div>
      </div>

      {/* Auto-Fix All Audit Issues Header Action Bar */}
      {pendingRecs.length > 0 && activeSubTab === 'pending' && (
        <div className="p-3 bg-gradient-to-r from-slate-900 to-indigo-950/60 border border-indigo-900/60 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-white flex items-center space-x-1.5">
              <span>Auto-Fix Engine</span>
              <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded font-medium">
                {isWP ? 'WordPress Direct' : website.local_repo_path ? 'Local Git Push' : 'Codebase Setup Needed'}
              </span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {isWP
                ? 'Applies meta titles, descriptions, and headings automatically in WordPress.'
                : website.local_repo_path
                ? `Injects fixes into templates at ${website.local_repo_path} & pushes to ${website.git_branch || 'main'}.`
                : 'Connect your local repository folder in Connected Websites to auto-fix and push code.'}
            </p>
          </div>

          <button
            onClick={handleAutoFixAll}
            disabled={batchFixing}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0 transition flex items-center space-x-1.5 border shadow ${
              isWP
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white border-cyan-500'
            }`}
          >
            {batchFixing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Fixing Issues...</span>
              </>
            ) : isWP ? (
              <>
                <Zap className="w-3.5 h-3.5 text-amber-300" />
                <span>Auto-Fix All in WordPress</span>
              </>
            ) : (
              <>
                <GitCommit className="w-3.5 h-3.5" />
                <span>Auto-Fix All & Push to Git</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Batch Feedback Banner */}
      {batchFeedback && (
        <div
          className={`p-2.5 rounded-lg text-xs flex items-center space-x-2 ${
            batchFeedback.error
              ? 'bg-rose-950/60 border border-rose-800 text-rose-300'
              : 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
          }`}
        >
          {batchFeedback.error ? (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          ) : (
            <Check className="w-4 h-4 shrink-0 text-emerald-400" />
          )}
          <span>{batchFeedback.text}</span>
        </div>
      )}

      {activeSubTab === 'pending' ? (
        <div className="space-y-3">
          {pendingRecs.map((rec) => {
            const isLoading = loadingId === rec.id;
            const changeData = rec.proposed_change_data || {};
            const beforeVal = changeData.current_value;
            const afterVal = changeData.proposed_value;

            return (
              <div
                key={rec.id}
                className="bg-slate-850 border border-slate-700/60 rounded-xl p-3.5 space-y-2.5 transition"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded mr-2">
                      {rec.severity}
                    </span>
                    <span className="text-xs font-bold text-white">{rec.issue_title}</span>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5 truncate max-w-xs">{rec.url}</p>
                  </div>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
                    Risk: {rec.risk_level}
                  </span>
                </div>

                <p className="text-[11px] text-slate-300 leading-relaxed">{rec.proposed_fix}</p>

                {/* Before vs After Diff Preview */}
                {afterVal && (
                  <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-[11px] space-y-1.5">
                    {beforeVal && (
                      <div className="text-slate-400">
                        <strong className="text-rose-400 block text-[10px]">CURRENT VALUE:</strong>
                        <span className="line-through">{beforeVal}</span>
                      </div>
                    )}
                    <div className="text-slate-200">
                      <strong className="text-emerald-400 block text-[10px]">PROPOSED VALUE:</strong>
                      <span>{afterVal}</span>
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2 truncate mr-2">
                    <span className="text-[10px] text-slate-400 truncate">{rec.expected_benefit}</span>
                    <span className={`text-[9px] px-1.5 py-0.2 rounded font-medium flex items-center space-x-1 shrink-0 ${
                      isWP
                        ? 'bg-emerald-500/10 text-emerald-300'
                        : website.local_repo_path
                        ? 'bg-cyan-500/10 text-cyan-300'
                        : 'bg-amber-500/10 text-amber-300'
                    }`}>
                      {isWP ? (
                        <>
                          <Zap className="w-2.5 h-2.5 text-amber-300" />
                          <span>WordPress CMS</span>
                        </>
                      ) : website.local_repo_path ? (
                        <>
                          <GitCommit className="w-2.5 h-2.5 text-cyan-400" />
                          <span>Codebase ({website.git_branch || 'main'})</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-2.5 h-2.5 text-amber-400" />
                          <span>Needs Folder Link</span>
                        </>
                      )}
                    </span>
                  </div>
                  <div className="flex space-x-1.5 shrink-0">
                    <button
                      onClick={() => handleApply(rec)}
                      disabled={isLoading}
                      className={`flex items-center space-x-1 px-3 py-1 rounded text-xs font-semibold transition shadow disabled:opacity-50 ${
                        isWP
                          ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                          : 'bg-cyan-600 hover:bg-cyan-500 text-white'
                      }`}
                      title={
                        isWP
                          ? 'Apply this change to WordPress via browser automation'
                          : 'Apply this fix directly to your code template and push to Git'
                      }
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Applying...</span>
                        </>
                      ) : isWP ? (
                        <>
                          <Zap className="w-3.5 h-3.5 text-amber-300" />
                          <span>Apply in WordPress</span>
                        </>
                      ) : (
                        <>
                          <GitCommit className="w-3.5 h-3.5 text-white" />
                          <span>Apply to Code & Push</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {pendingRecs.length === 0 && (
            <div className="text-center py-8 text-slate-500 text-xs">
              No pending opportunities. Run a Site SEO Crawl to generate new recommendations.
            </div>
          )}
        </div>
      ) : (
        /* History & Single-Click Rollback Tab */
        <div className="space-y-2">
          {changes.map((chg) => (
            <div key={chg.id} className="bg-slate-850 border border-slate-700/60 rounded-xl p-3 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-200 uppercase text-[10px] mr-2">
                    {chg.field_name}
                  </span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                    chg.status === 'verified'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : chg.status === 'rolled_back'
                      ? 'bg-slate-700 text-slate-400'
                      : 'bg-amber-500/20 text-amber-300'
                  }`}>
                    {chg.status}
                  </span>
                </div>
                {chg.status !== 'rolled_back' && (
                  <button
                    onClick={() => handleRollback(chg.id)}
                    className="flex items-center space-x-1 px-2 py-0.5 bg-rose-600/30 hover:bg-rose-600 text-rose-300 hover:text-white rounded text-[11px] font-medium transition"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Rollback</span>
                  </button>
                )}
              </div>

              <p className="text-[10px] text-slate-400 font-mono truncate">{chg.url}</p>

              <div className="bg-slate-900 p-2 rounded text-[11px] space-y-1">
                <p className="text-slate-400"><strong className="text-slate-300">New Value:</strong> {chg.after_value}</p>
                {chg.before_value && (
                  <p className="text-slate-500"><strong className="text-slate-400">Previous:</strong> {chg.before_value}</p>
                )}
              </div>
            </div>
          ))}

          {changes.length === 0 && (
            <div className="text-center py-8 text-slate-500 text-xs">
              No changes have been executed yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
