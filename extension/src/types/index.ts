export interface Website {
  id: number;
  domain: string;
  name: string;
  cms_type: 'wordpress' | 'woocommerce' | 'laravel' | 'custom';
  admin_url?: string;
  is_active: boolean;
  gsc_property_id?: string;
  gsc_verified: boolean;
  automation_mode: 'recommendation' | 'supervised' | 'autonomous';
  local_repo_path?: string;
  git_branch?: string;
  git_remote?: string;
  created_at: string;
}

export interface TaskItem {
  id: string;
  website_id: number;
  task_type: string;
  status: 'pending' | 'running' | 'paused_captcha' | 'paused_mfa' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled';
  risk_level: 'low' | 'medium' | 'high';
  payload: Record<string, any>;
  result?: Record<string, any>;
  error_message?: string;
  requires_human_approval: boolean;
  created_at: string;
}

export interface CrawlPage {
  id: number;
  url: string;
  status_code: number;
  title: string | null;
  meta_description: string | null;
  h1: string | null;
  canonical: string | null;
  images_without_alt: number;
  issues: Array<{ severity: 'critical' | 'high' | 'medium' | 'low'; type: string; message: string }>;
}

export interface KeywordItem {
  id: number;
  phrase: string;
  target_page: string | null;
  search_intent: string;
  impressions: number;
  clicks: number;
  ctr: number;
  position: number;
  opportunity_score: number;
  source: string;
}

export interface RecommendationItem {
  id: number;
  url: string;
  issue_title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  evidence: string;
  proposed_fix: string;
  proposed_change_data: Record<string, any>;
  expected_benefit: string;
  risk_level: 'low' | 'medium' | 'high';
  automation_eligible: boolean;
  status: 'suggested' | 'approved' | 'rejected' | 'applied';
}

export interface ChangeRecordItem {
  id: number;
  url: string;
  field_name: string;
  before_value: string | null;
  after_value: string | null;
  status: 'pending' | 'applied' | 'verified' | 'rolled_back';
  applied_at: string;
  verified_at: string | null;
}

export interface AuditLogItem {
  id: number;
  website_id: number;
  task_id: string | null;
  action: string;
  details: Record<string, any>;
  status: string;
  created_at: string;
}

export interface SystemStatus {
  status: string;
  app_name: string;
  version: string;
  browser_running: boolean;
  manual_takeover: boolean;
  chrome_profile: string;
  gemini_configured: boolean;
  engine_paused: boolean;
  stats: {
    websites: number;
    active_tasks: number;
    recommendations: number;
    daily_actions: number;
    daily_limit: number;
  };
}

export interface OnboardingStep {
  id: number;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'warning' | 'failed';
  details: string;
}

export interface OnboardingState {
  job_id: string;
  domain: string;
  status: 'in_progress' | 'completed' | 'failed';
  current_step: number;
  total_steps: number;
  steps: OnboardingStep[];
  logs: string[];
  website_id?: number | null;
  error?: string | null;
}

export interface BusinessProfileData {
  business_name: string | null;
  summary: string;
  offerings: string[];
  target_audience: string[];
  service_locations: string[];
  languages: string[];
  competitors: string[];
  seo_goals: string[];
  content_gaps: string[];
  internal_linking_plan: Array<{
    source_page: string;
    target_page: string;
    suggested_anchor: string;
    reason: string;
  }>;
  authority_roadmap: Array<{
    strategy: string;
    description: string;
    difficulty: string;
    expected_impact: string;
  }>;
}

export interface PipelineStage {
  id: number;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'warning' | 'failed';
  details: string;
  output: string;
}

export interface PipelineStatus {
  job_id: string;
  website_id: number;
  domain: string;
  status: 'in_progress' | 'completed' | 'failed';
  current_stage: number;
  total_stages: number;
  stages: PipelineStage[];
  logs: string[];
  error?: string | null;
}

export interface CodebaseValidationResult {
  valid: boolean;
  path?: string;
  is_git_repo?: boolean;
  current_branch?: string;
  remote_url?: string;
  error?: string;
}

export interface CodebaseFixResult {
  success: boolean;
  fixes_applied: number;
  pushed: boolean;
  commit_sha?: string;
  push_output?: string;
  details?: Array<{
    recommendation_id: number;
    url: string;
    file: string;
    status: string;
  }>;
  error?: string;
}

export interface SitemapStatusResponse {
  website_id: number;
  domain: string;
  available: boolean;
  sitemap_url: string;
  status_code: number;
  details: string;
  has_local_file: boolean;
  local_path: string | null;
  has_missing_recommendation: boolean;
  can_create_and_upload: boolean;
  cms_type: string;
}

export interface CreateSitemapResponse {
  success: boolean;
  message: string;
  sitemap_url: string;
  urls_count: number;
  urls?: string[];
  target_file?: string;
  commit_sha?: string;
  pushed_to_git?: boolean;
  gsc_submitted?: boolean;
  gsc_message?: string;
  error?: string;
}


