import React, { useState } from 'react';
import {
  Globe,
  Plus,
  Trash2,
  CheckCircle,
  ExternalLink,
  Shield,
  Zap,
  Loader2,
  Folder,
  GitBranch,
  GitCommit,
  UploadCloud,
  Check,
  AlertCircle,
  Edit3,
  Wrench,
  ChevronDown,
  ChevronUp,
  X,
  Save
} from 'lucide-react';
import { Website } from '../types';
import { api } from '../services/api';

interface Props {
  websites: Website[];
  onRefresh: () => void;
  selectedWebsite: Website | null;
  onSelectWebsite: (site: Website) => void;
  onNavigateToSetup?: () => void;
}

export const ConnectedWebsitesView: React.FC<Props> = ({
  websites,
  onRefresh,
  selectedWebsite,
  onSelectWebsite,
  onNavigateToSetup
}) => {
  const [showAdd, setShowAdd] = useState(false);
  const [domain, setDomain] = useState('');
  const [name, setName] = useState('');
  const [cmsType, setCmsType] = useState<'wordpress' | 'woocommerce' | 'laravel' | 'custom'>('wordpress');
  const [adminUrl, setAdminUrl] = useState('');
  const [automationMode, setAutomationMode] = useState<'recommendation' | 'supervised' | 'autonomous'>('supervised');
  const [localRepoPath, setLocalRepoPath] = useState('');
  const [gitBranch, setGitBranch] = useState('main');
  const [gitRemote, setGitRemote] = useState('origin');
  const [loading, setLoading] = useState(false);
  const [pipelineRunningId, setPipelineRunningId] = useState<number | null>(null);

  // Auto-Fix State
  const [fixingSiteId, setFixingSiteId] = useState<number | null>(null);
  const [fixFeedback, setFixFeedback] = useState<{ [siteId: number]: { text: string; error?: boolean } }>({});

  // Codebase Connection Drawer / Form per site
  const [connectingSiteId, setConnectingSiteId] = useState<number | null>(null);
  const [folderPathInput, setFolderPathInput] = useState('');
  const [branchInput, setBranchInput] = useState('main');
  const [remoteInput, setRemoteInput] = useState('origin');
  const [validatingFolder, setValidatingFolder] = useState(false);
  const [folderError, setFolderError] = useState<string | null>(null);
  const [folderSuccess, setFolderSuccess] = useState<string | null>(null);

  // Edit Website State
  const [editingSiteId, setEditingSiteId] = useState<number | null>(null);
  const [editDomain, setEditDomain] = useState('');
  const [editName, setEditName] = useState('');
  const [editCmsType, setEditCmsType] = useState<'wordpress' | 'woocommerce' | 'laravel' | 'custom'>('wordpress');
  const [editAdminUrl, setEditAdminUrl] = useState('');
  const [editAutomationMode, setEditAutomationMode] = useState<'recommendation' | 'supervised' | 'autonomous'>('supervised');
  const [editLocalRepoPath, setEditLocalRepoPath] = useState('');
  const [editGitBranch, setEditGitBranch] = useState('main');
  const [editGitRemote, setEditGitRemote] = useState('origin');
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const handleOpenEdit = (site: Website, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editingSiteId === site.id) {
      setEditingSiteId(null);
      return;
    }
    setEditingSiteId(site.id);
    setEditDomain(site.domain);
    setEditName(site.name || site.domain);
    setEditCmsType(site.cms_type);
    setEditAdminUrl(site.admin_url || '');
    setEditAutomationMode(site.automation_mode);
    setEditLocalRepoPath(site.local_repo_path || '');
    setEditGitBranch(site.git_branch || 'main');
    setEditGitRemote(site.git_remote || 'origin');
    setEditError(null);
  };

  const handleSaveEdit = async (siteId: number, e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!editDomain.trim()) {
      setEditError('Domain cannot be empty.');
      return;
    }
    setSavingEdit(true);
    setEditError(null);
    try {
      const updated = await api.updateWebsite(siteId, {
        domain: editDomain.trim(),
        name: editName.trim() || editDomain.trim(),
        cms_type: editCmsType,
        admin_url: editAdminUrl.trim() || undefined,
        automation_mode: editAutomationMode,
        local_repo_path: editLocalRepoPath.trim() || undefined,
        git_branch: editGitBranch.trim() || 'main',
        git_remote: editGitRemote.trim() || 'origin'
      });
      setEditingSiteId(null);
      if (selectedWebsite?.id === siteId) {
        onSelectWebsite(updated);
      }
      onRefresh();
    } catch (err: any) {
      setEditError(err.message || 'Failed to update website.');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleRunPipeline = async (site: Website, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectWebsite(site);
    setPipelineRunningId(site.id);
    try {
      await api.runRankingPipeline(site.id);
      if (onNavigateToSetup) {
        onNavigateToSetup();
      } else {
        alert(`10-Stage Ranking Workflow initiated for ${site.domain}!`);
      }
    } catch (err: any) {
      alert(`Error starting pipeline: ${err.message}`);
    } finally {
      setPipelineRunningId(null);
    }
  };

  const handleAutoFixAll = async (site: Website, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectWebsite(site);

    const isWP = site.cms_type === 'wordpress' || site.cms_type === 'woocommerce';
    if (!isWP && !site.local_repo_path) {
      setConnectingSiteId(site.id);
      setFolderPathInput('');
      setBranchInput(site.git_branch || 'main');
      setRemoteInput(site.git_remote || 'origin');
      setFolderError('Please connect your local project folder first before auto-fixing and pushing to Git.');
      return;
    }

    setFixingSiteId(site.id);
    setFixFeedback((prev) => ({ ...prev, [site.id]: { text: 'Running automated SEO audit fixes...' } }));

    try {
      const res = await api.autoFixAllCMS(site.id);
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
          ? `Auto-fixed ${fixes} issues in local templates${commit}${pushMsg}`
          : res.message || 'No pending issues found to fix in codebase.';
      }
      setFixFeedback((prev) => ({ ...prev, [site.id]: { text: msg, error: false } }));
      onRefresh();
    } catch (err: any) {
      setFixFeedback((prev) => ({
        ...prev,
        [site.id]: { text: `Fix failed: ${err.message}`, error: true }
      }));
    } finally {
      setFixingSiteId(null);
    }
  };

  const handleValidateAndConnectFolder = async (site: Website, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!folderPathInput.trim()) {
      setFolderError('Please enter a valid local directory path.');
      return;
    }

    setValidatingFolder(true);
    setFolderError(null);
    setFolderSuccess(null);

    try {
      const val = await api.validateLocalPath(folderPathInput.trim());
      if (!val.valid) {
        setFolderError(val.error || 'Invalid directory path.');
        setValidatingFolder(false);
        return;
      }

      await api.connectCodebase({
        website_id: site.id,
        local_repo_path: val.path || folderPathInput.trim(),
        git_branch: branchInput.trim() || val.current_branch || 'main',
        git_remote: remoteInput.trim() || 'origin'
      });

      setFolderSuccess(`Connected! ${val.is_git_repo ? `Git repo detected (${val.current_branch || 'main'}).` : 'Directory saved.'}`);
      setTimeout(() => {
        setConnectingSiteId(null);
        setFolderSuccess(null);
        onRefresh();
      }, 1200);
    } catch (err: any) {
      setFolderError(err.message || 'Failed to connect codebase.');
    } finally {
      setValidatingFolder(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!domain) return;
    setLoading(true);
    try {
      await api.createWebsite({
        domain,
        name: name || domain,
        cms_type: cmsType,
        admin_url: adminUrl,
        automation_mode: automationMode,
        local_repo_path: localRepoPath.trim() || undefined,
        git_branch: gitBranch.trim() || 'main',
        git_remote: gitRemote.trim() || 'origin'
      });
      setDomain('');
      setName('');
      setAdminUrl('');
      setLocalRepoPath('');
      setShowAdd(false);
      onRefresh();
    } catch (err: any) {
      alert(`Error creating website: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this website?')) {
      try {
        await api.deleteWebsite(id);
        onRefresh();
      } catch (err: any) {
        alert(`Error: ${err.message}`);
      }
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white">Connected Websites</h2>
          <p className="text-[11px] text-slate-400">Select an authorized website to manage</p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center space-x-1 px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>{showAdd ? 'Cancel' : 'Add Website'}</span>
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleSubmit} className="bg-slate-800/90 border border-slate-700 rounded-xl p-3.5 space-y-3">
          <h3 className="text-xs font-semibold text-white">Add New Website</h3>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Domain or Homepage URL</label>
            <input
              type="text"
              placeholder="example.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              required
              className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Site Label / Name</label>
            <input
              type="text"
              placeholder="My Store / Agency Blog"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-400 block mb-1">CMS Platform</label>
              <select
                value={cmsType}
                onChange={(e: any) => setCmsType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="wordpress">WordPress</option>
                <option value="woocommerce">WooCommerce</option>
                <option value="laravel">Laravel / PHP</option>
                <option value="custom">Custom (Next.js / HTML / Astro)</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">Automation Mode</label>
              <select
                value={automationMode}
                onChange={(e: any) => setAutomationMode(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="recommendation">Recommendation</option>
                <option value="supervised">Supervised (Approval)</option>
                <option value="autonomous">Autonomous (Auto-Fix)</option>
              </select>
            </div>
          </div>

          {cmsType === 'wordpress' || cmsType === 'woocommerce' ? (
            <div>
              <label className="text-[10px] text-slate-400 block mb-1">WordPress Admin Panel URL (Optional)</label>
              <input
                type="text"
                placeholder="https://example.com/wp-admin"
                value={adminUrl}
                onChange={(e) => setAdminUrl(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          ) : (
            <div className="p-2.5 bg-slate-900/80 border border-slate-700/80 rounded-lg space-y-2">
              <div className="flex items-center space-x-1.5 text-indigo-400 text-xs font-semibold">
                <Folder className="w-3.5 h-3.5" />
                <span>Local Codebase Folder (Git Auto-Push)</span>
              </div>
              <p className="text-[10px] text-slate-400">
                Connect your local codebase so audit issues can be auto-fixed directly in your templates and pushed to Git.
              </p>
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Absolute Local Folder Path</label>
                <input
                  type="text"
                  placeholder="e.g. C:\Users\Dev\Projects\my-site or /var/www/site"
                  value={localRepoPath}
                  onChange={(e) => setLocalRepoPath(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">Git Branch</label>
                  <input
                    type="text"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">Git Remote</label>
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

          <button
            type="submit"
            disabled={loading}
            className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold transition"
          >
            {loading ? 'Adding...' : 'Connect Website'}
          </button>
        </form>
      )}

      {/* Website Cards List */}
      <div className="space-y-3">
        {websites.map((site) => {
          const isSelected = selectedWebsite?.id === site.id;
          const isWP = site.cms_type === 'wordpress' || site.cms_type === 'woocommerce';
          const isFixing = fixingSiteId === site.id;
          const isConnectingCodebase = connectingSiteId === site.id;
          const isEditing = editingSiteId === site.id;
          const feedback = fixFeedback[site.id];

          return (
            <div
              key={site.id}
              onClick={() => onSelectWebsite(site)}
              className={`p-3 rounded-xl border cursor-pointer transition ${
                isSelected
                  ? 'bg-slate-800 border-indigo-500 shadow-md ring-1 ring-indigo-500/50'
                  : 'bg-slate-850 hover:bg-slate-800 border-slate-700/70'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300'}`}>
                    <Globe className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
                      <span>{site.name}</span>
                      {isSelected && <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded font-medium">Active</span>}
                    </h3>
                    <p className="text-[11px] text-slate-400 font-mono">{site.domain}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-1">
                  <button
                    onClick={(e) => handleOpenEdit(site, e)}
                    className={`p-1 rounded transition ${
                      isEditing
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-indigo-300 hover:bg-slate-700'
                    }`}
                    title={isEditing ? 'Close editor' : 'Edit website settings'}
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(site.id, e)}
                    className="p-1 text-slate-500 hover:text-rose-400 rounded hover:bg-slate-700 transition"
                    title="Remove website"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Inline Edit Form */}
              {isEditing ? (
                <form
                  onSubmit={(e) => handleSaveEdit(site.id, e)}
                  onClick={(e) => e.stopPropagation()}
                  className="mt-3 p-3 bg-slate-900 border border-indigo-500/60 rounded-xl space-y-2.5 text-xs"
                >
                  <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                    <span className="font-semibold text-white flex items-center space-x-1.5 text-xs">
                      <Edit3 className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Edit Website Settings</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setEditingSiteId(null)}
                      className="text-slate-400 hover:text-white p-0.5 rounded hover:bg-slate-800"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Domain</label>
                      <input
                        type="text"
                        value={editDomain}
                        onChange={(e) => setEditDomain(e.target.value)}
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Site Name / Label</label>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">CMS Platform</label>
                      <select
                        value={editCmsType}
                        onChange={(e: any) => setEditCmsType(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="wordpress">WordPress</option>
                        <option value="woocommerce">WooCommerce</option>
                        <option value="laravel">Laravel / PHP</option>
                        <option value="custom">Custom (Next.js / HTML / Astro)</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Automation Mode</label>
                      <select
                        value={editAutomationMode}
                        onChange={(e: any) => setEditAutomationMode(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="recommendation">Recommendation</option>
                        <option value="supervised">Supervised (Approval)</option>
                        <option value="autonomous">Autonomous (Auto-Fix)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 block mb-0.5">Admin Panel URL (Optional)</label>
                    <input
                      type="text"
                      placeholder="https://example.com/wp-admin"
                      value={editAdminUrl}
                      onChange={(e) => setEditAdminUrl(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>

                  <div className="p-2 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5">
                    <div className="text-[10px] font-semibold text-slate-300 flex items-center space-x-1">
                      <Folder className="w-3 h-3 text-indigo-400" />
                      <span>Local Codebase Folder (for non-WordPress Git push)</span>
                    </div>
                    <input
                      type="text"
                      placeholder="e.g. C:\Users\...\my-website"
                      value={editLocalRepoPath}
                      onChange={(e) => setEditLocalRepoPath(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                    <div className="grid grid-cols-2 gap-2 pt-0.5">
                      <div>
                        <label className="text-[9px] text-slate-400 block">Git Branch</label>
                        <input
                          type="text"
                          value={editGitBranch}
                          onChange={(e) => setEditGitBranch(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-xs text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] text-slate-400 block">Git Remote</label>
                        <input
                          type="text"
                          value={editGitRemote}
                          onChange={(e) => setEditGitRemote(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-xs text-white font-mono"
                        />
                      </div>
                    </div>
                  </div>

                  {editError && (
                    <p className="text-[10px] text-rose-400 flex items-center space-x-1">
                      <AlertCircle className="w-3 h-3 shrink-0" />
                      <span>{editError}</span>
                    </p>
                  )}

                  <div className="flex justify-end space-x-1.5 pt-1">
                    <button
                      type="button"
                      onClick={() => setEditingSiteId(null)}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={savingEdit}
                      className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold flex items-center space-x-1 shadow transition"
                    >
                      {savingEdit ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>Saving...</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-3 h-3" />
                          <span>Save Changes</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  {/* Status and CMS badges */}
                  <div className="mt-2.5 pt-2 border-t border-slate-700/50 flex items-center justify-between text-[10px]">
                    <div className="flex items-center space-x-2">
                      <span className="capitalize bg-slate-700/60 text-slate-300 px-1.5 py-0.5 rounded">
                        {site.cms_type}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded font-medium ${
                        site.automation_mode === 'autonomous'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : site.automation_mode === 'supervised'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-slate-700 text-slate-300'
                      }`}>
                        {site.automation_mode}
                      </span>
                    </div>
                    <div className="flex items-center space-x-1 text-slate-400">
                      {site.gsc_verified ? (
                        <span className="text-emerald-400 flex items-center space-x-0.5">
                          <CheckCircle className="w-3 h-3" />
                          <span>GSC Verified</span>
                        </span>
                      ) : (
                        <span>GSC Pending</span>
                      )}
                    </div>
                  </div>

                  {/* Non-WP Codebase Details Bar */}
                  {!isWP && (
                    <div className="mt-2 p-2 bg-slate-900/70 border border-slate-700/60 rounded-lg text-[10px]">
                      {site.local_repo_path ? (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-1.5 truncate">
                            <Folder className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                            <span className="text-slate-300 truncate font-mono" title={site.local_repo_path}>
                              {site.local_repo_path}
                            </span>
                            <span className="bg-slate-800 px-1.5 py-0.2 rounded text-slate-400 font-mono shrink-0">
                              {site.git_branch || 'main'}
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConnectingSiteId(isConnectingCodebase ? null : site.id);
                              setFolderPathInput(site.local_repo_path || '');
                              setBranchInput(site.git_branch || 'main');
                              setRemoteInput(site.git_remote || 'origin');
                              setFolderError(null);
                            }}
                            className="text-indigo-400 hover:text-indigo-300 underline font-medium ml-2 shrink-0"
                          >
                            {isConnectingCodebase ? 'Close' : 'Edit'}
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between">
                          <span className="text-amber-400/90 flex items-center space-x-1">
                            <AlertCircle className="w-3 h-3 shrink-0" />
                            <span>No local folder connected</span>
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConnectingSiteId(isConnectingCodebase ? null : site.id);
                              setFolderPathInput('');
                              setBranchInput('main');
                              setRemoteInput('origin');
                              setFolderError(null);
                            }}
                            className="text-xs bg-indigo-600/80 hover:bg-indigo-600 text-white px-2 py-0.5 rounded font-medium transition"
                          >
                            {isConnectingCodebase ? 'Cancel' : 'Connect Folder'}
                          </button>
                        </div>
                      )}

                      {/* Expandable Folder Connect Form */}
                      {isConnectingCodebase && (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          className="mt-2 pt-2 border-t border-slate-800 space-y-2"
                        >
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">Local Directory Path</label>
                            <input
                              type="text"
                              placeholder="C:\Users\...\my-website"
                              value={folderPathInput}
                              onChange={(e) => setFolderPathInput(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">Git Branch</label>
                              <input
                                type="text"
                                value={branchInput}
                                onChange={(e) => setBranchInput(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">Git Remote</label>
                              <input
                                type="text"
                                value={remoteInput}
                                onChange={(e) => setRemoteInput(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                              />
                            </div>
                          </div>

                          {folderError && (
                            <p className="text-[10px] text-rose-400 flex items-center space-x-1">
                              <AlertCircle className="w-3 h-3 shrink-0" />
                              <span>{folderError}</span>
                            </p>
                          )}
                          {folderSuccess && (
                            <p className="text-[10px] text-emerald-400 flex items-center space-x-1">
                              <Check className="w-3 h-3 shrink-0" />
                              <span>{folderSuccess}</span>
                            </p>
                          )}

                          <div className="flex justify-end space-x-1.5 pt-1">
                            <button
                              type="button"
                              onClick={() => setConnectingSiteId(null)}
                              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px]"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              disabled={validatingFolder}
                              onClick={(e) => handleValidateAndConnectFolder(site, e)}
                              className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-[10px] font-semibold flex items-center space-x-1"
                            >
                              {validatingFolder && <Loader2 className="w-3 h-3 animate-spin" />}
                              <span>Save & Verify</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Feedback Alert if auto-fix just ran */}
                  {feedback && (
                    <div
                      className={`mt-2 p-2 rounded-lg text-[10px] flex items-center space-x-1.5 ${
                        feedback.error
                          ? 'bg-rose-950/60 border border-rose-800 text-rose-300'
                          : 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
                      }`}
                    >
                      {feedback.error ? (
                        <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                      ) : (
                        <CheckCircle className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                      )}
                      <span className="truncate">{feedback.text}</span>
                    </div>
                  )}

                  {/* Dual Action Buttons: Auto-Fix All Audit Issues & 10-Stage Ranking */}
                  <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      onClick={(e) => handleAutoFixAll(site, e)}
                      disabled={isFixing}
                      className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold transition flex items-center justify-center space-x-1.5 border shadow ${
                        isWP
                          ? 'bg-emerald-950/70 hover:bg-emerald-900/80 border-emerald-700/60 text-emerald-200'
                          : 'bg-cyan-950/70 hover:bg-cyan-900/80 border-cyan-700/60 text-cyan-200'
                      }`}
                      title={
                        isWP
                          ? 'Automatically fix audit issues directly in WordPress'
                          : 'Auto-fix audit issues in local templates and push to Git'
                      }
                    >
                      {isFixing ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Auto-Fixing...</span>
                        </>
                      ) : isWP ? (
                        <>
                          <Zap className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>⚡ Auto-Fix (WordPress)</span>
                        </>
                      ) : (
                        <>
                          <GitCommit className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span>🛠️ Auto-Fix & Push Git</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={(e) => handleRunPipeline(site, e)}
                      disabled={pipelineRunningId === site.id}
                      className="py-1.5 px-2 bg-gradient-to-r from-indigo-900/60 to-purple-900/60 hover:from-indigo-850 hover:to-purple-850 disabled:opacity-50 border border-indigo-700/50 rounded-lg text-white font-medium text-[11px] transition flex items-center justify-center space-x-1.5 shadow"
                    >
                      {pipelineRunningId === site.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                          <span>Running Pipeline...</span>
                        </>
                      ) : (
                        <>
                          <Wrench className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          <span>10-Stage Ranking Workflow</span>
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}

        {websites.length === 0 && (
          <div className="text-center py-8 text-slate-500 text-xs">
            No websites connected yet. Click "+ Add Website" to begin.
          </div>
        )}
      </div>
    </div>
  );
};
