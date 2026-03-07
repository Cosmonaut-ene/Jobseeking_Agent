import axios from 'axios'

// In production (served by FastAPI), API is on the same origin.
// In dev, Vite proxies /api → localhost:8000.
export const api = axios.create({
  baseURL: '',
})

// ── Types ────────────────────────────────────────────────────────────────────

export interface GapAnalysis {
  strong_matches: string[]
  missing_skills: string[]
  notes: string
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
}

export interface ResumeVersion {
  id: string
  job_id: string
  content_json: Record<string, unknown>
  ats_score: number
  changes_summary: string
  created_at: string
}

export interface Application {
  id: string
  job_id: string
  resume_version_id: string
  channel: string
  status: string
  applied_at: string
  follow_up_date: string | null
  notes: string
  cover_letter_path?: string | null
}

export interface Skill {
  name: string
  level: string
  years: number
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
