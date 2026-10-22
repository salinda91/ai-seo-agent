import {
  Website,
  TaskItem,
  CrawlPage,
  KeywordItem,
  RecommendationItem,
  ChangeRecordItem,
  AuditLogItem,
  SystemStatus,
  OnboardingState,
  PipelineStatus,
  BusinessProfileData,
  CodebaseValidationResult,
  CodebaseFixResult
} from '../types';

const DEFAULT_BASE_URL = 'http://127.0.0.1:8765';

export class ApiClient {
  private baseUrl: string = DEFAULT_BASE_URL;
  private token: string = '';

  constructor() {
    this.loadSettings();
  }

  async loadSettings(): Promise<void> {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      const data = await chrome.storage.local.get(['agent_token', 'agent_base_url']);
      if (data.agent_token) this.token = String(data.agent_token);
      if (data.agent_base_url) this.baseUrl = String(data.agent_base_url);
    }
  }

  async saveToken(token: string): Promise<void> {
    this.token = token;
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      await chrome.storage.local.set({ agent_token: token });
    }
  }

  getToken(): string {
    return this.token;
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private async fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    await this.loadSettings();
    const url = `${this.baseUrl}${endpoint}`;
    const headers = new Headers(options.headers || {});
    if (this.token) {
      headers.set('X-Agent-Token', this.token);
    }
    headers.set('Content-Type', 'application/json');

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorMsg = errJson.detail;
      } catch {}
      throw new Error(errorMsg);
    }
    return response.json();
  }

  // System
  async getStatus(): Promise<SystemStatus> {
    return this.fetchJson<SystemStatus>('/api/status');
  }

  // Websites
  async getWebsites(): Promise<Website[]> {
    return this.fetchJson<Website[]>('/api/websites');
  }

  async createWebsite(data: Partial<Website>): Promise<Website> {
    return this.fetchJson<Website>('/api/websites', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async updateWebsite(id: number, data: Partial<Website>): Promise<Website> {
    return this.fetchJson<Website>(`/api/websites/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async deleteWebsite(id: number): Promise<{ success: boolean }> {
    return this.fetchJson<{ success: boolean }>(`/api/websites/${id}`, {
      method: 'DELETE'
    });
  }

  // Crawler
  async startCrawl(websiteId: number, maxPages: number = 30): Promise<{ success: boolean; message: string }> {
    return this.fetchJson('/api/crawl', {
      method: 'POST',
      body: JSON.stringify({ website_id: websiteId, max_pages: maxPages })
    });
  }

  async getCrawlResults(websiteId: number): Promise<{
    total_pages: number;
    total_issues: number;
    critical_issues: number;
    high_issues: number;
    pages: CrawlPage[];
  }> {
    return this.fetchJson(`/api/crawl/${websiteId}`);
  }

  // Search Console
  async openGSC(): Promise<any> {
    return this.fetchJson('/api/gsc/open', { method: 'POST' });
  }

  async listGSCProperties(): Promise<{ properties: string[] }> {
    return this.fetchJson('/api/gsc/properties', { method: 'POST' });
  }

  async addGSCProperty(websiteId: number, isDomain: boolean = false): Promise<any> {
    return this.fetchJson('/api/gsc/add-property', {
      method: 'POST',
      body: JSON.stringify({ website_id: websiteId, is_domain: isDomain })
    });
  }

  async syncGSCPerformance(websiteId: number): Promise<any> {
    return this.fetchJson('/api/gsc/performance', {
      method: 'POST',
      body: JSON.stringify({ website_id: websiteId })
    });
  }

  async submitGSCSitemap(websiteId: number, sitemapUrl: string): Promise<any> {
    return this.fetchJson('/api/gsc/sitemaps', {
      method: 'POST',
      body: JSON.stringify({ website_id: websiteId, sitemap_url: sitemapUrl })
    });
  }

  async inspectGSCUrl(websiteId: number, targetUrl: string, requestIndexing: boolean = true): Promise<any> {
    return this.fetchJson('/api/gsc/inspect', {
      method: 'POST',
      body: JSON.stringify({ website_id: websiteId, target_url: targetUrl, request_indexing: requestIndexing })
    });
  }

  // Keywords
  async getKeywords(websiteId: number): Promise<KeywordItem[]> {
    return this.fetchJson(`/api/keywords/${websiteId}`);
  }

  async clusterKeywords(phrases: string[]): Promise<{ clusters: Record<string, string[]> }> {
    return this.fetchJson('/api/keywords/cluster', {
      method: 'POST',
      body: JSON.stringify({ phrases })
    });
  }

  async optimizeMeta(data: {
    url: string;
    current_title: string;
    current_description: string;
    target_keyword: string;
    page_snippet?: string;
  }): Promise<any> {
    return this.fetchJson('/api/keywords/optimize-meta', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // CMS & Recommendations
  async getRecommendations(websiteId: number): Promise<RecommendationItem[]> {
    return this.fetchJson(`/api/cms/recommendations/${websiteId}`);
  }

  async applyChange(data: {
    website_id: number;
    recommendation_id?: number;
    url: string;
    field_name: string;
    new_value: string;
  }): Promise<any> {
    return this.fetchJson('/api/cms/apply', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async rollbackChange(changeId: number): Promise<any> {
    return this.fetchJson(`/api/cms/rollback/${changeId}`, { method: 'POST' });
  }

  async getChanges(websiteId: number): Promise<ChangeRecordItem[]> {
    return this.fetchJson(`/api/cms/changes/${websiteId}`);
  }

  // 1-Click Auto-Fix All Audit Issues (WordPress Browser / Codebase Git Push)
  async autoFixAllCMS(websiteId: number): Promise<{
    success: boolean;
    fixed_count?: number;
    fixes_applied?: number;
    pushed?: boolean;
    commit_sha?: string;
    message?: string;
    details?: any[];
  }> {
    return this.fetchJson(`/api/cms/auto-fix-all/${websiteId}`, {
      method: 'POST'
    });
  }

  // Local Codebase & Git SEO Automation
  async validateLocalPath(path: string): Promise<CodebaseValidationResult> {
    return this.fetchJson<CodebaseValidationResult>('/api/codebase/validate', {
      method: 'POST',
      body: JSON.stringify({ path })
    });
  }

  async connectCodebase(data: {
    website_id: number;
    local_repo_path: string;
    git_branch?: string;
    git_remote?: string;
  }): Promise<{
    success: boolean;
    website_id: number;
    local_repo_path: string;
    git_branch: string;
    git_remote: string;
    is_git: boolean;
    remote_url: string;
    message: string;
  }> {
    return this.fetchJson('/api/codebase/connect', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async fixAndPushCodebase(data: {
    website_id: number;
    auto_push?: boolean;
    custom_branch?: string;
    custom_remote?: string;
  }): Promise<CodebaseFixResult> {
    return this.fetchJson<CodebaseFixResult>('/api/codebase/fix-and-push', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // Tasks & Audit
  async getTasks(limit: number = 50): Promise<TaskItem[]> {
    return this.fetchJson(`/api/tasks?limit=${limit}`);
  }

  async controlEngine(action: 'pause' | 'resume' | 'stop'): Promise<any> {
    return this.fetchJson('/api/tasks/control', {
      method: 'POST',
      body: JSON.stringify({ action })
    });
  }

  async approveTask(taskId: string): Promise<any> {
    return this.fetchJson(`/api/tasks/${taskId}/approve`, { method: 'POST' });
  }

  async rejectTask(taskId: string): Promise<any> {
    return this.fetchJson(`/api/tasks/${taskId}/reject`, { method: 'POST' });
  }

  async getAuditLogs(limit: number = 100): Promise<AuditLogItem[]> {
    return this.fetchJson(`/api/tasks/audit-logs?limit=${limit}`);
  }

  // Full Domain Onboarding Pipeline
  async startOnboarding(payload: {
    domain: string;
    name?: string;
    cms_type?: string;
    admin_url?: string;
    automation_mode?: string;
    is_domain_property?: boolean;
    local_repo_path?: string;
    git_branch?: string;
    git_remote?: string;
  }): Promise<{ success: boolean; job_id: string; domain: string; message: string }> {
    return this.fetchJson('/api/onboarding/start', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getOnboardingStatus(jobId: string): Promise<OnboardingState> {
    return this.fetchJson<OnboardingState>(`/api/onboarding/status/${encodeURIComponent(jobId)}`);
  }

  // 10-Stage Autonomous SEO Ranking Pipeline
  async runRankingPipeline(websiteId: number): Promise<{ success: boolean; job_id: string; domain: string; message: string }> {
    return this.fetchJson(`/api/pipeline/run/${websiteId}`, {
      method: 'POST'
    });
  }

  async getPipelineStatus(jobId: string): Promise<PipelineStatus> {
    return this.fetchJson<PipelineStatus>(`/api/pipeline/status/${encodeURIComponent(jobId)}`);
  }

  async getBusinessProfile(websiteId: number): Promise<BusinessProfileData> {
    return this.fetchJson<BusinessProfileData>(`/api/pipeline/business-profile/${websiteId}`);
  }
}

export const api = new ApiClient();
