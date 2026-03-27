import { useEffect, useState } from 'react'
import {
  CheckCircle, XCircle, Scissors, Download, Mail,
  ExternalLink, ChevronDown, ChevronUp, Copy, Check, Loader2,
} from 'lucide-react'
import { api } from '../api/client'
import type { Job, ResumeVersion } from '../api/client'
import JobCard from '../components/JobCard'
import EvaluationReport from '../components/EvaluationReport'
import { useT } from '../contexts/LanguageContext'

const STATUSES = ['all', 'new', 'reviewed', 'dismissed', 'applied', 'interview', 'rejected', 'offer']

const STATUS_COLORS: Record<string, string> = {
  new:       'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  reviewed:  'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  dismissed: 'bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400',
  applied:   'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  interview: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  rejected:  'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  offer:     'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
}

interface TailoredBullet { rewritten: string; source_raw: string }
interface TailoredProject { name: string; bullets: TailoredBullet[] }
interface TailoredExperience { company: string; role: string; duration: string; bullets: string[] }
interface TailoredContent {
  name?: string; summary?: string; skills?: string[]
  projects?: TailoredProject[]; experience?: TailoredExperience[]
}

function CopyBtn({ text }: { text: string }) {
  const t = useT()
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800) })
  }
  return (
    <button onClick={copy} className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-md bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400 hover:bg-amber-100 dark:hover:bg-amber-900/40 hover:text-amber-700 dark:hover:text-amber-300 transition-colors">
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? t('copy_btn_done') : t('copy_btn')}
    </button>
  )
}

function ResumePanel({ resume }: { resume: ResumeVersion }) {
  const t = useT()
  const content = resume.content_json as TailoredContent
  const atsPct = Math.round(resume.ats_score * 100)
  return (
    <div className="glass-card text-sm divide-theme overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 glass-section rounded-t-xl">
        <span className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
          <Scissors size={13} className="text-amber-500" />{t('resume_panel_title')}
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {t('resume_ats_match')} <strong className={atsPct >= 70 ? 'text-emerald-700 dark:text-emerald-400' : atsPct >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'}>{atsPct}%</strong>
        </span>
      </div>
      <div className="p-4 space-y-4">
        {resume.changes_summary && <p className="text-xs text-slate-500 dark:text-slate-400 italic border-l-2 border-amber-300 pl-2">{resume.changes_summary}</p>}
        {content.summary && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-zinc-500 mb-1 flex items-center">
              {t('resume_section_summary')}<CopyBtn text={content.summary} />
            </h4>
            <p className="text-slate-700 dark:text-slate-300 leading-relaxed">{content.summary}</p>
          </section>
        )}
        {content.skills && content.skills.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-zinc-500 mb-1.5 flex items-center">
              {t('resume_section_skills')}<CopyBtn text={content.skills.join(', ')} />
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {content.skills.map((s, i) => <span key={i} className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-md text-xs">{s}</span>)}
            </div>
          </section>
        )}
        {content.projects && content.projects.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-zinc-500 mb-2">{t('resume_section_projects')}</h4>
            <div className="space-y-3">
              {content.projects.map((proj, i) => (
                <div key={i}>
                  <p className="font-medium text-slate-800 dark:text-slate-200 mb-1 flex items-center">
                    {proj.name}<CopyBtn text={proj.bullets.map(b => `• ${b.rewritten}`).join('\n')} />
                  </p>
                  <ul className="space-y-1.5 pl-2">
                    {proj.bullets.map((b, j) => (
                      <li key={j} className="text-slate-700 dark:text-slate-300 leading-snug">
                        <span className="text-slate-400 dark:text-zinc-500 mr-1">•</span>{b.rewritten}
                        {b.source_raw && b.source_raw !== b.rewritten && (
                          <details className="mt-0.5">
                            <summary className="text-xs text-slate-400 dark:text-zinc-500 cursor-pointer hover:text-slate-600 dark:hover:text-zinc-300 list-none">{t('resume_original_label')}</summary>
                            <p className="text-xs text-slate-400 dark:text-zinc-500 italic mt-0.5 pl-2">{b.source_raw}</p>
                          </details>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}
        {content.experience && content.experience.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-zinc-500 mb-2">{t('resume_section_experience')}</h4>
            <div className="space-y-2">
              {content.experience.map((exp, i) => (
                <div key={i}>
                  <p className="font-medium text-slate-800 dark:text-slate-200 flex items-center">
                    {exp.role}<span className="text-slate-500 dark:text-slate-400 font-normal ml-1">@ {exp.company}</span>
                    <CopyBtn text={(exp.bullets ?? []).map(b => `• ${b}`).join('\n')} />
                  </p>
                  <p className="text-xs text-slate-400 dark:text-zinc-500 mb-1">{exp.duration}</p>
                  <ul className="space-y-0.5 pl-2">
                    {(exp.bullets ?? []).map((b, j) => (
                      <li key={j} className="text-slate-600 dark:text-slate-400 text-xs">
                        <span className="text-slate-400 dark:text-zinc-500 mr-1">•</span>{b}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function CoverLetterPanel({ text }: { text: string }) {
  const t = useT()
  const [copied, setCopied] = useState(false)
  function copy() { navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }) }
  return (
    <div className="glass-card overflow-hidden text-sm">
      <div className="flex items-center justify-between px-4 py-2.5 glass-section rounded-t-xl border-b border-slate-200/60 dark:border-white/[0.07]">
        <span className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
          <Mail size={13} className="text-amber-500" />{t('cover_letter_title')}
        </span>
        <button onClick={copy} className="inline-flex items-center gap-1.5 px-3 py-1 text-xs bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors">
          {copied ? <Check size={11} /> : <Copy size={11} />}{copied ? t('copied_done') : t('copy_btn')}
        </button>
      </div>
      <pre className="p-4 whitespace-pre-wrap text-slate-700 dark:text-slate-300 font-sans leading-relaxed text-xs max-h-64 overflow-y-auto">{text}</pre>
    </div>
  )
}

function ActionButton({ label, icon: Icon, onClick, loading, variant = 'default' }: {
  label: string; icon?: React.ElementType; onClick: () => void; loading?: boolean
  variant?: 'default' | 'success' | 'danger'
}) {
  const colors = {
    default: 'bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-zinc-700',
    success: 'bg-emerald-600 text-white hover:bg-emerald-700',
    danger:  'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-900/60',
  }
  return (
    <button onClick={onClick} disabled={loading} className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors ${colors[variant]}`}>
      {loading ? <Loader2 size={13} className="animate-spin" /> : Icon && <Icon size={13} />}
      {label}
    </button>
  )
}

export default function Jobs() {
  const t = useT()
  const [jobs, setJobs] = useState<Job[]>([])
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState('')
  const [actionSuccess, setActionSuccess] = useState(false)
  const [resume, setResume] = useState<ResumeVersion | null>(null)
  const [coverLetter, setCoverLetter] = useState<string | null>(null)
  const [showJD, setShowJD] = useState(false)
  const [showEval, setShowEval] = useState(false)
  const [docxUrl, setDocxUrl] = useState<string | null>(null)

  useEffect(() => { fetchJobs() }, [])

  async function fetchJobs() {
    setLoading(true)
    try { const r = await api.get('/api/jobs'); setJobs(r.data) } catch {}
    finally { setLoading(false) }
  }

  async function selectJob(job: Job) {
    setSelected(job); setActionMsg(''); setResume(null); setCoverLetter(null)
    setDocxUrl(null); setShowJD(false); setShowEval(false)
    try {
      const r = await api.get(`/api/jobs/${job.id}`)
      setSelected(r.data)
      const versions: ResumeVersion[] = r.data.resume_versions ?? []
      if (versions.length > 0) { setResume(versions[0]); if (r.data.has_docx) setDocxUrl(`/api/files/${job.id}/resume.docx`) }
    } catch {}
    try { const cl = await api.get(`/api/jobs/${job.id}/cover-letter`); setCoverLetter(`Subject: ${cl.data.subject_line}\n\n${cl.data.body}`) } catch {}
  }

  async function updateStatus(jobId: string, status: string) {
    setActionLoading('status')
    try {
      await api.put(`/api/jobs/${jobId}/status`, { status })
      if (status === 'dismissed') { setJobs(p => p.filter(j => j.id !== jobId)); setSelected(null); setResume(null); setCoverLetter(null) }
      else { await fetchJobs(); setSelected(j => j ? { ...j, status } : j); setActionMsg(`Status → "${status}"`); setActionSuccess(true) }
    } catch (e: unknown) { setActionMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed'); setActionSuccess(false) }
    finally { setActionLoading(null) }
  }

  async function tailor(jobId: string) {
    setActionLoading('tailor'); setActionMsg('')
    try {
      const r = await api.post(`/api/jobs/${jobId}/tailor`)
      setResume(r.data); if (r.data.docx_download_url) setDocxUrl(r.data.docx_download_url)
      setActionMsg(t('jobs_resume_tailored')); setActionSuccess(true)
    } catch (e: unknown) { setActionMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Tailor failed'); setActionSuccess(false) }
    finally { setActionLoading(null) }
  }

  async function apply(jobId: string) {
    setActionLoading('apply'); setActionMsg('')
    try {
      const r = await api.post(`/api/jobs/${jobId}/cover-letter`)
      setCoverLetter(`Subject: ${r.data.subject_line}\n\n${r.data.body}`)
      setActionMsg(t('jobs_cover_letter_ready')); setActionSuccess(true); await fetchJobs()
    } catch (e: unknown) { setActionMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Generate cover letter failed'); setActionSuccess(false) }
    finally { setActionLoading(null) }
  }

  const filtered = jobs.filter(j => {
    if (filter === 'all' && j.status === 'dismissed') return false
    if (filter !== 'all' && j.status !== filter) return false
    if (search && !`${j.title} ${j.company}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="flex gap-4" style={{ height: 'calc(100vh - 3rem)' }}>
      {/* Left: job list */}
      <div className="w-72 flex flex-col shrink-0">
        <div className="mb-3 space-y-2">
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t('jobs_search_placeholder')} className="input-field w-full" />
          <select value={filter} onChange={e => setFilter(e.target.value)} className="input-field w-full">
            {STATUSES.map(s => <option key={s} value={s}>{s === 'all' ? t('jobs_all_statuses') : s}</option>)}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          {loading && <p className="text-sm text-slate-400 dark:text-zinc-500 text-center mt-4">{t('jobs_loading')}</p>}
          {!loading && filtered.length === 0 && <p className="text-sm text-slate-400 dark:text-zinc-500 text-center mt-4">{t('jobs_none_found')}</p>}
          {filtered.map(job => <JobCard key={job.id} job={job} selected={selected?.id === job.id} onClick={() => selectJob(job)} />)}
        </div>
      </div>

      {/* Right: detail */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {!selected ? (
          <div className="flex items-center justify-center h-64 text-slate-400 dark:text-zinc-500 text-sm">{t('jobs_select_prompt')}</div>
        ) : (
          <>
            <div className="glass-card p-5 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{selected.title || t('jobs_untitled')}</h2>
                  <p className="text-slate-500 dark:text-slate-400">{selected.company}{selected.location ? ` · ${selected.location}` : ''}</p>
                  {selected.salary_range && <p className="text-sm text-slate-400 dark:text-zinc-500 mt-0.5">{selected.salary_range}</p>}
                  {selected.source_url && (
                    <a href={selected.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-1 text-xs text-amber-600 dark:text-amber-400 hover:underline">
                      <ExternalLink size={11} />{t('jobs_view_original')}
                    </a>
                  )}
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium shrink-0 ${STATUS_COLORS[selected.status] ?? 'bg-slate-100 dark:bg-zinc-800'}`}>
                  {selected.status}
                </span>
              </div>

              {/* Match score */}
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('jobs_match_label')}</span>
                  <span className={`text-sm font-bold ${selected.match_score >= 0.7 ? 'text-emerald-700 dark:text-emerald-400' : selected.match_score >= 0.4 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'}`}>
                    {Math.round(selected.match_score * 100)}%
                  </span>
                </div>
                <div className="h-2 bg-slate-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${selected.match_score >= 0.7 ? 'bg-emerald-500' : selected.match_score >= 0.4 ? 'bg-amber-400' : 'bg-rose-400'}`}
                    style={{ width: `${Math.round(selected.match_score * 100)}%` }} />
                </div>
              </div>

              {/* Gap analysis */}
              {(selected.gap_analysis.strong_matches.length > 0 || selected.gap_analysis.missing_skills.length > 0) && (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="font-medium text-emerald-700 dark:text-emerald-400 mb-1 text-xs flex items-center gap-1"><CheckCircle size={11} />{t('jobs_matches')}</p>
                      <ul className="space-y-0.5 text-slate-600 dark:text-slate-400 text-xs">
                        {selected.gap_analysis.strong_matches.map((m, i) => <li key={i}>• {m}</li>)}
                      </ul>
                    </div>
                    <div>
                      <p className="font-medium text-rose-600 dark:text-rose-400 mb-1 text-xs flex items-center gap-1"><XCircle size={11} />{t('jobs_gaps')}</p>
                      <ul className="space-y-0.5 text-slate-600 dark:text-slate-400 text-xs">
                        {selected.gap_analysis.missing_skills.map((s, i) => <li key={i}>• {s}</li>)}
                      </ul>
                    </div>
                  </div>
                  <button onClick={() => setShowEval(v => !v)} className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:underline">
                    {showEval ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {showEval ? t('jobs_hide_eval') : t('jobs_view_eval')} {t('jobs_full_evaluation')}
                  </button>
                  {showEval && <div className="pt-1"><EvaluationReport gap={selected.gap_analysis} /></div>}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-200/60 dark:border-white/[0.07]">
                <ActionButton label={t('jobs_approve')} icon={CheckCircle} onClick={() => updateStatus(selected.id, 'reviewed')} loading={actionLoading === 'status'} variant="success" />
                <ActionButton label={t('jobs_dismiss')} icon={XCircle} onClick={() => updateStatus(selected.id, 'dismissed')} loading={actionLoading === 'status'} variant="danger" />
                <ActionButton label={actionLoading === 'tailor' ? t('jobs_tailoring') : t('jobs_tailor_btn')} icon={Scissors} onClick={() => tailor(selected.id)} loading={actionLoading === 'tailor'} />
                {docxUrl && (
                  <a href={docxUrl} download className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-amber-500 text-white hover:bg-amber-600 transition-colors">
                    <Download size={13} />{t('jobs_download_word')}
                  </a>
                )}
                <ActionButton label={actionLoading === 'apply' ? t('jobs_cover_generating') : t('jobs_cover_letter_btn')} icon={Mail} onClick={() => apply(selected.id)} loading={actionLoading === 'apply'} />
              </div>

              {actionMsg && (
                <div className={`text-sm px-3 py-2 rounded-lg flex items-center gap-1.5 ${
                  actionSuccess ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300' : 'bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'
                }`}>
                  {actionSuccess ? <Check size={13} /> : <XCircle size={13} />}{actionMsg}
                </div>
              )}

              {/* JD toggle */}
              <div>
                <button onClick={() => setShowJD(v => !v)} className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:underline">
                  {showJD ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  {showJD ? t('jobs_hide_jd') : t('jobs_show_jd')} {t('jobs_full_jd')}
                </button>
                {showJD && <pre className="mt-2 text-xs text-slate-600 dark:text-slate-400 whitespace-pre-wrap glass-section rounded-lg p-3 max-h-52 overflow-y-auto">{selected.raw_jd}</pre>}
              </div>

              {selected.skills_required.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">{t('jobs_required_skills')}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selected.skills_required.map(s => <span key={s} className="tag-neutral">{s}</span>)}
                  </div>
                </div>
              )}
            </div>

            {resume && <ResumePanel resume={resume} />}
            {coverLetter && <CoverLetterPanel text={coverLetter} />}
          </>
        )}
      </div>
    </div>
  )
}
