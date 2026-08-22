import axios from 'axios'

// In production (served by FastAPI), API is on the same origin.
// In dev, Vite proxies /api → localhost:8000.
export const api = axios.create({
  baseURL: '',
})

// ── Types ────────────────────────────────────────────────────────────────────

export interface GapAnalysis {
  ats_pct?: number
  strong_matches: string[]
  missing_skills: string[]
  unmet_requirements?: string[]
  notes: string
  skills_improvements?: {
    technical?: string[]
    certifications?: string[]
    soft_skills?: string[]
    tools?: string[]
  }
  resume_improvements?: {
    bullet_strength?: string[]
    achievements_feedback?: string
    metrics_suggestions?: string[]
    ats_keywords?: string[]
  }
  formatting_improvements?: {
    tone_clarity?: string[]
    action_verbs?: string[]
    layout?: string[]
  }
  recommendations?: {
    top_5?: string[]
    quick_wins?: string[]
    deeper_improvements?: string[]
    estimated_improvement_pct?: number
  }
}

export interface Job {
  id: string
  source: string
  raw_jd: string
  title: string
  company: string
  location: string
  salary_range: string
  skills_required: string[]
  match_score: number
  gap_analysis: GapAnalysis
  source_url: string
  status: string
  created_at: string
  updated_at: string
  resume_versions?: ResumeVersion[]
  application?: Application | null
}

export interface ResumeVersion {
  id: string
  job_id: string
  content_json: Record<string, unknown>
  ats_score: number
  changes_summary: string
  deterministic_ats_score?: number
  ats_report?: AtsSimulationReport | null
  created_at: string
}

// ── ATS Simulation (确定性评分，SPEC 附录 F.5) ─────────────────────────────────

export interface ParseabilityReport {
  score: number
  extracted_char_count: number
  missing_fields: string[]
  warnings: string[]
}

export interface KeywordMatchReport {
  score: number
  hits: string[]
  misses: string[]
  alias_hits: [string, string][]
}

export interface AtsSimulationReport {
  deterministic_ats_score: number
  parseability: ParseabilityReport
  keyword_match: KeywordMatchReport
  diagnosis: string[]
}

export async function simulateAts(resumeVersionId: string): Promise<AtsSimulationReport> {
  const r = await api.post('/api/ats/simulate', { resume_version_id: resumeVersionId })
  return r.data
}

// ── Tailor Resume as a background task (UX 打磨: 单趟耗时可超过 90 秒，
// 需要按轮次展示真实进度，而不是一个死的 "Tailoring…") ────────────────────────

export interface TailorTask {
  status: 'pending' | 'running' | 'done' | 'error'
  progress: string
  round?: number
  max_iterations?: number
  deterministic_ats_score?: number
  result?: ResumeVersion & { pdf_download_url?: string }
  error?: string
}

export async function startTailor(jobId: string): Promise<{ task_id: string }> {
  const r = await api.post(`/api/jobs/${jobId}/tailor`)
  return r.data
}

export async function getTailorTask(jobId: string, taskId: string): Promise<TailorTask> {
  const r = await api.get(`/api/jobs/${jobId}/tailor/tasks/${taskId}`)
  return r.data
}

// ready(AI 已备好) -> applied(人类已投递) -> responded/interview/rejected
// 见 SPEC 附录 F.6 TASK-D01；流转规则由后端 APPLICATION_STATUS_TRANSITIONS 强制。
export type ApplicationStatus = 'ready' | 'applied' | 'responded' | 'interview' | 'rejected'

export interface Application {
  id: string
  job_id: string
  resume_version_id: string
  channel: string
  status: ApplicationStatus
  applied_at: string
  follow_up_date: string | null
  notes: string
  cover_letter_path?: string | null
}

export interface ReadyToConfirmEntry {
  application: Application
  job: Job | null
}

export async function listReadyToConfirm(): Promise<ReadyToConfirmEntry[]> {
  const r = await api.get('/api/dashboard/ready-to-confirm')
  return r.data
}

export async function confirmApplicationApplied(applicationId: string): Promise<Application> {
  const r = await api.put(`/api/applications/${applicationId}/status`, { status: 'applied' })
  return r.data
}

export interface Skill {
  name: string
  level: string
  years: number
}

// ── GitHub profile sync (SPEC 附录 F.7 TASK-B03) ───────────────────────────────
// diff 提议 -> 人工逐项确认 -> apply。合并规则跟 Resume.tsx 的 mergeSkills 一致
// （years 只增不减），这里只负责触发/展示/确认，不在前端重新实现合并逻辑。

export interface SkillDiffEntry {
  name: string
  change_type: 'new' | 'years_increase'
  proposed_years: number
  current_years: number | null
  source_repos: string[]
  first_seen: string
  last_active: string
}

export interface GitHubSyncTask {
  status: 'pending' | 'running' | 'done' | 'error'
  progress: string
  diff?: SkillDiffEntry[]
  error?: string
}

export async function startGithubSync(username?: string, excludeForks = true): Promise<{ task_id: string }> {
  const r = await api.post('/api/profile/github-sync', { username: username || null, exclude_forks: excludeForks })
  return r.data
}

export async function getGithubSyncTask(taskId: string): Promise<GitHubSyncTask> {
  const r = await api.get(`/api/profile/github-sync/tasks/${taskId}`)
  return r.data
}

export async function applyGithubSync(taskId: string, acceptedSkillNames: string[]): Promise<{ saved: boolean; profile: UserProfile }> {
  const r = await api.post('/api/profile/github-sync/apply', { task_id: taskId, accepted_skill_names: acceptedSkillNames })
  return r.data
}

export interface Bullet {
  raw: string
  tech: string[]
  metric: string
}

export interface Experience {
  company: string
  role: string
  duration: string
  bullets: Bullet[]
}

export interface Project {
  name: string
  description: string
  tech_stack: string[]
  bullets: Bullet[]
}

export interface Education {
  institution: string
  degree: string
  field: string
  duration: string
  gpa: string
}

export interface SalaryRange {
  min: number
  max: number
  currency: string
}

export interface Preferences {
  locations: string[]
  salary_range: SalaryRange | null
  job_types: string[]
}

export interface UserProfile {
  name: string
  target_roles: string[]
  skills: Skill[]
  experience: Experience[]
  projects: Project[]
  preferences: Preferences
  education: Education[]
}

export interface TaskStatus {
  status: 'pending' | 'running' | 'done' | 'error'
  progress: string
  results?: Job[]
  error?: string
}

export interface DashboardStats {
  by_status: Record<string, number>
  total_jobs: number
  high_score_count?: number
  mid_score_count?: number
  recent_jobs_7d?: number
  by_source?: Record<string, number>
}

export interface AdvisorReport {
  generated_at: string
  total_jobs_analysed: number
  top_missing_skills: { skill: string; count: number }[]
  top_present_skills: { skill: string; count: number }[]
  app_stats: Record<string, unknown>
  market_summary: string
  skill_gap_analysis: string
  recommended_actions: string[]
}
