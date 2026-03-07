import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Job, ResumeVersion } from '../api/client'
import JobCard from '../components/JobCard'

const STATUSES = ['all', 'new', 'reviewed', 'dismissed', 'applied', 'interview', 'rejected', 'offer']

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800',
  reviewed: 'bg-purple-100 text-purple-800',
  dismissed: 'bg-gray-100 text-gray-600',
  applied: 'bg-yellow-100 text-yellow-800',
  interview: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  offer: 'bg-emerald-100 text-emerald-800',
}

// ── Tailored resume content types ────────────────────────────────────────────
interface TailoredBullet { rewritten: string; source_raw: string }
interface TailoredProject { name: string; bullets: TailoredBullet[] }
interface TailoredExperience { company: string; role: string; duration: string; bullets: string[] }
interface TailoredContent {
  name?: string
  summary?: string
  skills?: string[]
  projects?: TailoredProject[]
  experience?: TailoredExperience[]
}

// ── Copy button ───────────────────────────────────────────────────────────────
function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }
  return (
    <button
      onClick={copy}
      className="ml-2 px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-500 hover:bg-blue-100 hover:text-blue-700 transition-colors"
    >
      {copied ? '✓' : 'Copy'}
    </button>
  )
}

// ── Full resume viewer ────────────────────────────────────────────────────────
function ResumePanel({ resume }: { resume: ResumeVersion }) {
  const content = resume.content_json as TailoredContent
  const atsPct = Math.round(resume.ats_score * 100)

  return (
    <div className="border rounded-lg bg-white text-sm divide-y">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 rounded-t-lg">
        <span className="font-semibold text-gray-700">✂️ Tailored Resume</span>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>ATS coverage: <strong className={atsPct >= 70 ? 'text-green-700' : atsPct >= 40 ? 'text-yellow-700' : 'text-red-600'}>{atsPct}%</strong></span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Changes summary */}
        {resume.changes_summary && (
          <p className="text-xs text-gray-500 italic border-l-2 border-blue-300 pl-2">{resume.changes_summary}</p>
        )}

        {/* Summary */}
        {content.summary && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1 flex items-center">
              Summary<CopyBtn text={content.summary} />
            </h4>
            <p className="text-gray-800 leading-relaxed">{content.summary}</p>
          </section>
        )}

        {/* Skills */}
        {content.skills && content.skills.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1.5 flex items-center">
              Selected Skills<CopyBtn text={content.skills.join(', ')} />
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {content.skills.map((s, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">{s}</span>
              ))}
            </div>
          </section>
        )}

        {/* Projects */}
        {content.projects && content.projects.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">Tailored Projects</h4>
            <div className="space-y-3">
              {content.projects.map((proj, i) => (
                <div key={i}>
                  <p className="font-medium text-gray-800 mb-1 flex items-center">
                    {proj.name}
                    <CopyBtn text={proj.bullets.map(b => `• ${b.rewritten}`).join('\n')} />
                  </p>
                  <ul className="space-y-1.5 pl-2">
                    {proj.bullets.map((b, j) => (
                      <li key={j} className="text-gray-700 leading-snug">
                        <span className="text-gray-400 mr-1">•</span>
                        {b.rewritten}
                        {b.source_raw && b.source_raw !== b.rewritten && (
                          <details className="mt-0.5">
                            <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 list-none">
                              ↩ original
                            </summary>
                            <p className="text-xs text-gray-400 italic mt-0.5 pl-2">{b.source_raw}</p>
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

        {/* Experience (passed through unchanged) */}
        {content.experience && content.experience.length > 0 && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">Experience</h4>
            <div className="space-y-2">
              {content.experience.map((exp, i) => (
                <div key={i}>
                  <p className="font-medium text-gray-800 flex items-center">
                    {exp.role} <span className="text-gray-500 font-normal ml-1">@ {exp.company}</span>
                    <CopyBtn text={(exp.bullets ?? []).map(b => `• ${b}`).join('\n')} />
                  </p>
                  <p className="text-xs text-gray-400 mb-1">{exp.duration}</p>
                  <ul className="space-y-0.5 pl-2">
                    {(exp.bullets ?? []).map((b, j) => (
                      <li key={j} className="text-gray-600 text-xs">
                        <span className="text-gray-400 mr-1">•</span>{b}
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

// ── Cover letter panel ────────────────────────────────────────────────────────
function CoverLetterPanel({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="border rounded-lg bg-white text-sm">
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 rounded-t-lg border-b">
        <span className="font-semibold text-gray-700">📧 Cover Letter</span>
        <button
          onClick={copy}
          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          {copied ? '✓ Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 whitespace-pre-wrap text-gray-700 font-sans leading-relaxed text-xs max-h-64 overflow-y-auto">
        {text}
      </pre>
    </div>
  )
}

// ── Action button ─────────────────────────────────────────────────────────────
function ActionButton({ label, onClick, loading, variant = 'default' }: {
  label: string
  onClick: () => void
  loading?: boolean
  variant?: 'default' | 'success' | 'danger'
}) {
  const colors = {
    default: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
    success: 'bg-green-600 text-white hover:bg-green-700',
    danger: 'bg-red-100 text-red-700 hover:bg-red-200',
  }
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`px-3 py-1.5 rounded text-sm font-medium disabled:opacity-50 transition-colors ${colors[variant]}`}
    >
      {loading ? '…' : label}
    </button>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState('')
  const [resume, setResume] = useState<ResumeVersion | null>(null)
  const [coverLetter, setCoverLetter] = useState<string | null>(null)
  const [showJD, setShowJD] = useState(false)
  const [docxUrl, setDocxUrl] = useState<string | null>(null)

  useEffect(() => { fetchJobs() }, [])

  async function fetchJobs() {
    setLoading(true)
    try {
      const r = await api.get('/api/jobs')
      setJobs(r.data)
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  async function selectJob(job: Job) {
    setSelected(job)
    setActionMsg('')
    setResume(null)
    setCoverLetter(null)
    setDocxUrl(null)
    setShowJD(false)
    try {
      const r = await api.get(`/api/jobs/${job.id}`)
      setSelected(r.data)
      const versions: ResumeVersion[] = r.data.resume_versions ?? []
      if (versions.length > 0) {
        setResume(versions[0])
        if (r.data.has_docx) setDocxUrl(`/api/files/${job.id}/resume.docx`)
      }
    } catch { /* silent */ }
    try {
      const cl = await api.get(`/api/jobs/${job.id}/cover-letter`)
      setCoverLetter(`Subject: ${cl.data.subject_line}\n\n${cl.data.body}`)
    } catch { /* no cover letter yet */ }
  }

  async function updateStatus(jobId: string, status: string) {
    setActionLoading('status')
    try {
      await api.put(`/api/jobs/${jobId}/status`, { status })
      if (status === 'dismissed') {
        setJobs((prev) => prev.filter((j) => j.id !== jobId))
        setSelected(null)
        setResume(null)
        setCoverLetter(null)
      } else {
        await fetchJobs()
        setSelected((j) => j ? { ...j, status } : j)
        setActionMsg(`Status → "${status}"`)
      }
    } catch (e: unknown) {
      setActionMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed')
    } finally { setActionLoading(null) }
  }

  async function tailor(jobId: string) {
    setActionLoading('tailor')
    setActionMsg('')
    try {
      const r = await api.post(`/api/jobs/${jobId}/tailor`)
      setResume(r.data)
      if (r.data.docx_download_url) setDocxUrl(r.data.docx_download_url)
      setActionMsg('✅ Resume tailored!')
    } catch (e: unknown) {
      setActionMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Tailor failed')
    } finally { setActionLoading(null) }
  }

  async function apply(jobId: string) {
    setActionLoading('apply')
    setActionMsg('')
    try {
      const r = await api.post(`/api/jobs/${jobId}/cover-letter`)
      const text = `Subject: ${r.data.subject_line}\n\n${r.data.body}`
      setCoverLetter(text)
      setActionMsg('✅ Cover letter ready below.')
      await fetchJobs()
    } catch (e: unknown) {
      setActionMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Generate cover letter failed')
    } finally { setActionLoading(null) }
  }

  const filtered = jobs.filter((j) => {
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
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title / company…"
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s === 'all' ? 'All statuses' : s}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          {loading && <p className="text-sm text-gray-400 text-center mt-4">Loading…</p>}
          {!loading && filtered.length === 0 && (
            <p className="text-sm text-gray-400 text-center mt-4">No jobs found.</p>
          )}
          {filtered.map((job) => (
            <JobCard key={job.id} job={job} selected={selected?.id === job.id} onClick={() => selectJob(job)} />
          ))}
        </div>
      </div>

      {/* Right: detail */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {!selected ? (
          <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
            Select a job from the list
          </div>
        ) : (
          <>
            {/* Job header card */}
            <div className="bg-white rounded-lg shadow p-5 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{selected.title || 'Untitled'}</h2>
                  <p className="text-gray-500">{selected.company}{selected.location ? ` · ${selected.location}` : ''}</p>
                  {selected.salary_range && <p className="text-sm text-gray-400 mt-0.5">{selected.salary_range}</p>}
                  {selected.source_url && (
                    <a
                      href={selected.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 mt-1 text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                    >
                      🔗 View original posting
                    </a>
                  )}
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium shrink-0 ${STATUS_COLORS[selected.status] ?? 'bg-gray-100'}`}>
                  {selected.status}
                </span>
              </div>

              {/* Match score */}
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-700">Match</span>
                  <span className={`text-sm font-bold ${selected.match_score >= 0.7 ? 'text-green-700' : selected.match_score >= 0.4 ? 'text-yellow-700' : 'text-red-600'}`}>
                    {Math.round(selected.match_score * 100)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${selected.match_score >= 0.7 ? 'bg-green-500' : selected.match_score >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'}`}
                    style={{ width: `${Math.round(selected.match_score * 100)}%` }}
                  />
                </div>
              </div>

              {/* Gap analysis */}
              {(selected.gap_analysis.strong_matches.length > 0 || selected.gap_analysis.missing_skills.length > 0) && (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="font-medium text-green-700 mb-1 text-xs">✅ Matches</p>
                    <ul className="space-y-0.5 text-gray-600 text-xs">
                      {selected.gap_analysis.strong_matches.map((m, i) => <li key={i}>• {m}</li>)}
                    </ul>
                  </div>
                  <div>
                    <p className="font-medium text-red-600 mb-1 text-xs">⚠️ Gaps</p>
                    <ul className="space-y-0.5 text-gray-600 text-xs">
                      {selected.gap_analysis.missing_skills.map((s, i) => <li key={i}>• {s}</li>)}
                    </ul>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-1 border-t">
                <ActionButton label="✅ Approve" onClick={() => updateStatus(selected.id, 'reviewed')} loading={actionLoading === 'status'} variant="success" />
                <ActionButton label="❌ Dismiss" onClick={() => updateStatus(selected.id, 'dismissed')} loading={actionLoading === 'status'} variant="danger" />
                <ActionButton label={actionLoading === 'tailor' ? 'Tailoring…' : '✂️ Tailor Resume'} onClick={() => tailor(selected.id)} loading={actionLoading === 'tailor'} />
                {docxUrl && (
                  <a
                    href={docxUrl}
                    download
                    className="px-3 py-1.5 rounded text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
                  >
                    ⬇ Download Word
                  </a>
                )}
                <ActionButton label={actionLoading === 'apply' ? 'Generating…' : '📧 Cover Letter'} onClick={() => apply(selected.id)} loading={actionLoading === 'apply'} />
              </div>

              {actionMsg && (
                <div className={`text-sm px-3 py-2 rounded ${actionMsg.startsWith('✅') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-700'}`}>
                  {actionMsg}
                </div>
              )}

              {/* JD toggle */}
              <div>
                <button onClick={() => setShowJD((v) => !v)} className="text-xs text-blue-600 hover:underline">
                  {showJD ? '▲ Hide' : '▼ Show'} Full Job Description
                </button>
                {showJD && (
                  <pre className="mt-2 text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 rounded p-3 max-h-52 overflow-y-auto">
                    {selected.raw_jd}
                  </pre>
                )}
              </div>

              {/* Required skills */}
              {selected.skills_required.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-600 mb-1.5">Required Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selected.skills_required.map((s) => (
                      <span key={s} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Full tailored resume */}
            {resume && <ResumePanel resume={resume} />}

            {/* Cover letter */}
            {coverLetter && <CoverLetterPanel text={coverLetter} />}
          </>
        )}
      </div>
    </div>
  )
}
