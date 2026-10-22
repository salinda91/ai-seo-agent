import React, { useState, useEffect, useRef } from 'react';
import {
  Website,
  SystemStatus,
  TaskItem,
  RecommendationItem,
  KeywordItem
} from './types';
import { api } from './services/api';
import { Navbar, NavTab } from './components/Navbar';
import { LiveBrowserBar } from './components/LiveBrowserBar';
import { DashboardView } from './components/DashboardView';
import { DomainSetupView } from './components/DomainSetupView';
import { ConnectedWebsitesView } from './components/ConnectedWebsitesView';
import { SearchConsoleView } from './components/SearchConsoleView';
import { SiteAuditView } from './components/SiteAuditView';
import { KeywordResearchView } from './components/KeywordResearchView';
import { SEOOpportunitiesView } from './components/SEOOpportunitiesView';
import { ContentOptimizerView } from './components/ContentOptimizerView';
import { IndexingView } from './components/IndexingView';
import { AutomationRulesView } from './components/AutomationRulesView';
import { TaskQueueView } from './components/TaskQueueView';
import { ActivityLogsView } from './components/ActivityLogsView';
import { ReportsView } from './components/ReportsView';
import { SettingsView } from './components/SettingsView';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [websites, setWebsites] = useState<Website[]>([]);
  const [selectedWebsite, setSelectedWebsite] = useState<Website | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [keywords, setKeywords] = useState<KeywordItem[]>([]);
  const [isOffline, setIsOffline] = useState<boolean>(false);

  // Live Browser Feed state
  const [currentBrowserUrl, setCurrentBrowserUrl] = useState<string>('');
  const [manualTakeover, setManualTakeover] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);

  const loadAllData = async () => {
    try {
      const sysStatus = await api.getStatus();
      setStatus(sysStatus);
      setIsOffline(false);

      const siteList = await api.getWebsites();
      setWebsites(siteList);
      let activeSite = selectedWebsite;
      if (!activeSite && siteList.length > 0) {
        activeSite = siteList[0];
        setSelectedWebsite(activeSite);
      }

      const taskList = await api.getTasks(50);
      setTasks(taskList);

      if (activeSite) {
        const recs = await api.getRecommendations(activeSite.id);
        setRecommendations(recs);
        const kws = await api.getKeywords(activeSite.id);
        setKeywords(kws);
      }
    } catch {
      // Gracefully set offline without throwing unhandled console warnings
      setIsOffline(true);
      setStatus(null);
    }
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 12000);
    return () => clearInterval(interval);
  }, [selectedWebsite?.id]);

  // Connect WebSocket for live browser feedback
  useEffect(() => {
    let active = true;
    let timer: any = null;

    const connectWs = async () => {
      await api.loadSettings();
      if (!active) return;
      const token = api.getToken();
      const wsUrl = `ws://127.0.0.1:8765/ws/browser-feed${token ? `?token=${encodeURIComponent(token)}` : ''}`;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!active) {
            ws.close();
            return;
          }
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.url !== undefined) setCurrentBrowserUrl(data.url);
            if (data.event === 'navigated' && data.data?.url) setCurrentBrowserUrl(data.data.url);
            if (data.event === 'browser_stopped' || data.browser_running === false) setCurrentBrowserUrl('');
            if (data.manual_takeover !== undefined) setManualTakeover(data.manual_takeover);
          } catch {}
        };

        ws.onclose = () => {
          if (!active) return;
          setWsConnected(false);
          timer = setTimeout(connectWs, 5000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        if (active) timer = setTimeout(connectWs, 5000);
      }
    };

    connectWs();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const waitingCount = tasks.filter((t) => t.status === 'waiting_approval').length;

  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-100">
      {/* Top Header */}
      <header className="bg-slate-950 border-b border-slate-800 px-3 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white text-xs shadow-md">
            AI
          </div>
          <span className="font-bold text-xs tracking-wide text-white">AI SEO SPECIALIST</span>
        </div>

        {/* Website Selector Dropdown */}
        {websites.length > 0 && (
          <select
            value={selectedWebsite?.id ?? ''}
            onChange={(e) => {
              const site = websites.find((s) => s.id === Number(e.target.value));
              if (site) setSelectedWebsite(site);
            }}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 max-w-[160px] truncate"
          >
            {websites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.domain})
              </option>
            ))}
          </select>
        )}
      </header>

      {/* Live Browser Bar */}
      <LiveBrowserBar
        currentUrl={currentBrowserUrl}
        isPaused={status?.engine_paused ?? false}
        manualTakeover={manualTakeover}
        onRefresh={loadAllData}
        wsConnected={wsConnected}
      />

      {/* Offline Status Alert Banner */}
      {isOffline && (
        <div className="bg-rose-950 border-b border-rose-800/80 px-3 py-1.5 flex items-center justify-between text-xs shadow-sm">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-rose-200 font-semibold text-[11px]">Local Agent Offline</span>
            <span className="text-rose-400 text-[10px] hidden sm:inline">
              (Run <code className="bg-rose-900/60 px-1 rounded text-rose-200">scripts\start_agent.bat</code>)
            </span>
          </div>
          <button
            onClick={loadAllData}
            className="bg-rose-800 hover:bg-rose-700 text-white font-medium text-[10px] px-2 py-0.5 rounded transition shadow"
          >
            Reconnect
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} waitingCount={waitingCount} />

      {/* Main Tab Content */}
      <main className="flex-1 overflow-y-auto pb-6">
        {activeTab === 'dashboard' && (
          <DashboardView
            websites={websites}
            status={status}
            tasks={tasks}
            recommendations={recommendations}
            onNavigate={setActiveTab}
            onOpenGSC={() => setActiveTab('gsc')}
            onRefresh={loadAllData}
          />
        )}

        {activeTab === 'setup' && (
          <DomainSetupView
            websites={websites}
            onNavigate={setActiveTab}
            onDomainCreated={loadAllData}
          />
        )}

        {activeTab === 'websites' && (
          <ConnectedWebsitesView
            websites={websites}
            onRefresh={loadAllData}
            selectedWebsite={selectedWebsite}
            onSelectWebsite={setSelectedWebsite}
            onNavigateToSetup={() => setActiveTab('setup')}
          />
        )}

        {activeTab === 'gsc' && <SearchConsoleView website={selectedWebsite} />}

        {activeTab === 'audit' && <SiteAuditView website={selectedWebsite} />}

        {activeTab === 'keywords' && <KeywordResearchView website={selectedWebsite} />}

        {activeTab === 'opportunities' && (
          <SEOOpportunitiesView website={selectedWebsite} onRefreshStats={loadAllData} />
        )}

        {activeTab === 'optimizer' && <ContentOptimizerView website={selectedWebsite} />}

        {activeTab === 'indexing' && <IndexingView website={selectedWebsite} />}

        {activeTab === 'rules' && <AutomationRulesView website={selectedWebsite} />}

        {activeTab === 'tasks' && <TaskQueueView tasks={tasks} onRefresh={loadAllData} />}

        {activeTab === 'logs' && <ActivityLogsView />}

        {activeTab === 'reports' && (
          <ReportsView
            website={selectedWebsite}
            status={status}
            recommendations={recommendations}
            keywords={keywords}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView status={status} onRefreshStatus={loadAllData} />
        )}
      </main>
    </div>
  );
};
