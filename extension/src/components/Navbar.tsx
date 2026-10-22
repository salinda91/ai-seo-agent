import React from 'react';
import {
  LayoutDashboard,
  Rocket,
  Globe,
  Search,
  CheckCircle2,
  Key,
  Sparkles,
  FileEdit,
  Send,
  Cpu,
  ListOrdered,
  History,
  BarChart3,
  Settings
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'setup'
  | 'websites'
  | 'gsc'
  | 'audit'
  | 'keywords'
  | 'opportunities'
  | 'optimizer'
  | 'indexing'
  | 'rules'
  | 'tasks'
  | 'logs'
  | 'reports'
  | 'settings';

interface Props {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  waitingCount: number;
}

export const Navbar: React.FC<Props> = ({ activeTab, onTabChange, waitingCount }) => {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'setup', label: 'Domain Setup', icon: Rocket },
    { id: 'websites', label: 'Websites', icon: Globe },
    { id: 'gsc', label: 'Search Console', icon: Search },
    { id: 'audit', label: 'Site Audit', icon: CheckCircle2 },
    { id: 'keywords', label: 'Keywords', icon: Key },
    { id: 'opportunities', label: 'Opportunities', icon: Sparkles },
    { id: 'optimizer', label: 'Optimizer', icon: FileEdit },
    { id: 'indexing', label: 'Indexing', icon: Send },
    { id: 'rules', label: 'Rules', icon: Cpu },
    { id: 'tasks', label: 'Tasks', icon: ListOrdered, badge: waitingCount },
    { id: 'logs', label: 'Logs', icon: History },
    { id: 'reports', label: 'Reports', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="bg-slate-950 border-b border-slate-800 px-2 py-1.5 overflow-x-auto">
      <div className="flex space-x-1 min-w-max">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id as NavTab)}
              className={`flex items-center space-x-1 px-2.5 py-1.5 rounded text-xs font-medium transition ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {!!tab.badge && tab.badge > 0 && (
                <span className="bg-amber-500 text-slate-950 text-[10px] font-bold px-1.5 py-0.2 rounded-full ml-1">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
