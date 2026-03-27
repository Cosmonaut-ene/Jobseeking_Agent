import { useRef, useState } from 'react'
import { api } from '../api/client'
import type { Education, Experience, Project, Skill, UserProfile } from '../api/client'
import { useT } from '../contexts/LanguageContext'

// ── Incremental merge helpers ─────────────────────────────────────────────────

function mergeSkills(existing: Skill[], parsed: Skill[]): Skill[] {
  const map = new Map(existing.map((s) => [s.name.toLowerCase(), s]))
  parsed.forEach((s) => {
    const key = s.name.toLowerCase()
    const prev = map.get(key)
    // years only ever goes up — AI inference is unstable; manual edit required to reduce
    map.set(key, prev ? { ...s, years: Math.max(prev.years, s.years) } : s)
  })
  return Array.from(map.values())
}

function mergeExperience(existing: Experience[], parsed: Experience[]): Experience[] {
  const key = (e: Experience) => `${e.company.toLowerCase()}|${e.role.toLowerCase()}`
  const map = new Map(existing.map((e) => [key(e), e]))
  parsed.forEach((e) => map.set(key(e), e))
  return Array.from(map.values())
}

function mergeProjects(existing: Project[], parsed: Project[]): Project[] {
  const map = new Map(existing.map((p) => [p.name.toLowerCase(), p]))
  parsed.forEach((p) => map.set(p.name.toLowerCase(), p))
  return Array.from(map.values())
}

function mergeEducation(existing: Education[], parsed: Education[]): Education[] {
  const key = (e: Education) => `${e.institution.toLowerCase()}|${e.degree.toLowerCase()}`
  const map = new Map(existing.map((e) => [key(e), e]))
  parsed.forEach((e) => map.set(key(e), e))
  return Array.from(map.values())
}

export default function Resume() {
  const t = useT()
  const [tab, setTab] = useState<'paste' | 'upload'>('paste')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [parsing, setParsing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [parsed, setParsed] = useState<UserProfile | null>(null)
  const [savedMsg, setSavedMsg] = useState('')
  const [savedSuccess, setSavedSuccess] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function parse() {
    setParsing(true)
    setError('')
    setParsed(null)
    setSavedMsg('')
    try {
      let data: UserProfile
      if (tab === 'upload' && file) {
        const form = new FormData()
        form.append('file', file)
        const r = await api.post('/api/profile/upload-resume', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        data = r.data.profile
      } else {
        if (!text.trim()) { setError(t('resume_paste_first')); setParsing(false); return }
        const r = await api.post('/api/profile/parse-resume', { text })
        data = r.data.profile
      }
      setParsed(data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Parsing failed'
      setError(msg)
    } finally {
      setParsing(false)
    }
  }

  async function saveProfile() {
    if (!parsed) return
    setSaving(true)
    setSavedMsg('')
    try {
      // Fetch existing profile and merge incrementally (new items added, duplicates replaced by parsed)
      let existing: UserProfile | null = null
      try { existing = (await api.get('/api/profile')).data } catch { /* no existing profile */ }

      const PLACEHOLDER_PATTERNS = /^(n\/a|unknown|not provided|not specified|none|null|undefined|-)$/i
      const isReal = (v: string | null | undefined) =>
        !!v && v.trim() !== '' && !PLACEHOLDER_PATTERNS.test(v.trim())

      const merged: UserProfile = {
        // existing profile as base — prevents N/A from overwriting real data
        ...existing,
        // scalar fields: only overwrite when parsed value is meaningful
        name: isReal(parsed.name) ? parsed.name : (existing?.name ?? ''),
        target_roles: parsed.target_roles?.length
          ? parsed.target_roles
          : (existing?.target_roles ?? []),
        // preferences: field-level merge so partial pastes don't wipe existing prefs
        preferences: {
          locations: existing?.preferences?.locations ?? [],
          job_types: existing?.preferences?.job_types ?? [],
          salary_range: existing?.preferences?.salary_range ?? null,
          ...(parsed.preferences?.locations?.length
            ? { locations: parsed.preferences.locations } : {}),
          ...(parsed.preferences?.job_types?.length
            ? { job_types: parsed.preferences.job_types } : {}),
          ...(parsed.preferences?.salary_range
            ? { salary_range: parsed.preferences.salary_range } : {}),
        },
        // array fields: incremental merge (existing items kept; parsed items upserted by key)
        skills:     mergeSkills(existing?.skills ?? [], parsed.skills ?? []),
        experience: mergeExperience(existing?.experience ?? [], parsed.experience ?? []),
        projects:   mergeProjects(existing?.projects ?? [], parsed.projects ?? []),
        education:  mergeEducation(existing?.education ?? [], parsed.education ?? []),
      }

      await api.put('/api/profile', merged)
      setSavedMsg(t('resume_saved_msg'))
      setSavedSuccess(true)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Save failed'
      setSavedMsg(msg)
      setSavedSuccess(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-6">{t('resume_title')}</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">{t('resume_description')}</p>

      <div className="glass-card overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-slate-200/60 dark:border-zinc-700/60">
          {(['paste', 'upload'] as const).map((tabKey) => (
            <button
              key={tabKey}
              onClick={() => setTab(tabKey)}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                tab === tabKey
                  ? 'border-b-2 border-amber-500 text-amber-600 dark:text-amber-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
            >
              {tabKey === 'paste' ? t('resume_tab_paste') : t('resume_tab_upload')}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 'paste' ? (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={12}
              placeholder={t('resume_paste_placeholder')}
              className="w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 font-mono resize-y"
            />
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-slate-200 dark:border-zinc-700 rounded-lg p-10 text-center cursor-pointer hover:border-amber-400 dark:hover:border-amber-500 transition-colors"
            >
              <p className="text-slate-500 dark:text-slate-400 text-sm">
                {file ? (
                  <span className="text-amber-600 dark:text-amber-400 font-medium">{file.name}</span>
                ) : (
                  <>{t('resume_upload_hint')} <strong>PDF</strong>, <strong>DOCX</strong>, <strong>TXT</strong> {t('resume_upload_types')}</>
                )}
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          )}

          <div className="flex items-center gap-3 mt-4">
            <button
              onClick={parse}
              disabled={parsing}
              className="px-5 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors"
            >
              {parsing ? t('resume_parsing') : t('resume_parse_btn')}
            </button>
            {parsing && <span className="text-sm text-slate-500 dark:text-slate-400">{t('resume_parsing_wait')}</span>}
          </div>

          {error && <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{error}</p>}
        </div>
      </div>

      {/* Parsed result */}
      {parsed && (
        <div className="mt-6 glass-card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{t('resume_parsed_title')}</h2>
            <button
              onClick={saveProfile}
              disabled={saving}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {saving ? t('resume_save_saving') : t('resume_save_btn')}
            </button>
          </div>

          {savedMsg && (
            <div className={`text-sm px-3 py-2 rounded-lg ${savedSuccess ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300' : 'bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'}`}>
              {savedMsg}
            </div>
          )}

          {/* Basic */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">{t('resume_basic_info')}</h3>
            <p className="text-sm text-slate-800 dark:text-slate-200 font-medium">{parsed.name}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{t('resume_target_roles')} {parsed.target_roles?.join(', ') ?? '—'}</p>
          </section>

          {/* Skills */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{t('resume_skills')} ({parsed.skills?.length ?? 0})</h3>
            <div className="flex flex-wrap gap-1.5">
              {(parsed.skills ?? []).map((s) => (
                <span key={s.name} className="px-2 py-0.5 bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 rounded text-xs">
                  {s.name} · {s.level} · {s.years}y
                </span>
              ))}
            </div>
          </section>

          {/* Experience */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{t('resume_experience')} ({parsed.experience?.length ?? 0})</h3>
            <div className="space-y-2">
              {(parsed.experience ?? []).map((exp, i) => (
                <div key={i} className="border-l-2 border-amber-200 dark:border-amber-700/60 pl-3">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{exp.role} @ {exp.company}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{exp.duration}</p>
                  <ul className="mt-1 space-y-0.5">
                    {(exp.bullets ?? []).slice(0, 2).map((b, j) => (
                      <li key={j} className="text-xs text-slate-600 dark:text-slate-400">• {b.raw}</li>
                    ))}
                    {(exp.bullets?.length ?? 0) > 2 && <li className="text-xs text-slate-400 dark:text-zinc-500">+{(exp.bullets?.length ?? 0) - 2} more</li>}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          {/* Projects */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{t('resume_projects')} ({parsed.projects?.length ?? 0})</h3>
            <div className="space-y-2">
              {(parsed.projects ?? []).map((p, i) => (
                <div key={i} className="border-l-2 border-violet-200 dark:border-violet-700/60 pl-3">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{p.name}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{p.tech_stack?.join(', ')}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Education */}
          {parsed.education && parsed.education.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{t('resume_education')} ({parsed.education.length})</h3>
              <div className="space-y-2">
                {parsed.education.map((edu, i) => (
                  <div key={i} className="border-l-2 border-emerald-200 dark:border-emerald-700/60 pl-3">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{edu.degree}{edu.field ? ` in ${edu.field}` : ''}</p>
                    <p className="text-xs text-slate-600 dark:text-slate-400">{edu.institution}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{edu.duration}{edu.gpa ? ` · GPA: ${edu.gpa}` : ''}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Preferences */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">{t('profile_tab_preferences')}</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('resume_locations')} {parsed.preferences?.locations?.join(', ') || '—'}
            </p>
            {parsed.preferences?.salary_range && (
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t('resume_salary')} {parsed.preferences.salary_range.min}–{parsed.preferences.salary_range.max} {parsed.preferences.salary_range.currency}
              </p>
            )}
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('resume_job_types')} {parsed.preferences?.job_types?.join(', ') || '—'}
            </p>
          </section>
        </div>
      )}
    </div>
  )
}
