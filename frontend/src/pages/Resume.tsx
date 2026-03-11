import { useRef, useState } from 'react'
import { api } from '../api/client'
import type { Education, Experience, Project, Skill, UserProfile } from '../api/client'
import { useT } from '../contexts/LanguageContext'

// ── Incremental merge helpers ─────────────────────────────────────────────────

function mergeSkills(existing: Skill[], parsed: Skill[]): Skill[] {
  const map = new Map(existing.map((s) => [s.name.toLowerCase(), s]))
  parsed.forEach((s) => map.set(s.name.toLowerCase(), s))
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
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Save failed'
      setSavedMsg(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t('resume_title')}</h1>
      <p className="text-sm text-gray-500 mb-6">{t('resume_description')}</p>

      <div className="bg-white rounded-lg shadow">
        {/* Tabs */}
        <div className="flex border-b">
          {(['paste', 'upload'] as const).map((tabKey) => (
            <button
              key={tabKey}
              onClick={() => setTab(tabKey)}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                tab === tabKey
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
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
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-y"
            />
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-10 text-center cursor-pointer hover:border-blue-400 transition-colors"
            >
              <p className="text-gray-500 text-sm">
                {file ? (
                  <span className="text-blue-600 font-medium">{file.name}</span>
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
              className="px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {parsing ? t('resume_parsing') : t('resume_parse_btn')}
            </button>
            {parsing && <span className="text-sm text-gray-500">{t('resume_parsing_wait')}</span>}
          </div>

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>
      </div>

      {/* Parsed result */}
      {parsed && (
        <div className="mt-6 bg-white rounded-lg shadow p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">{t('resume_parsed_title')}</h2>
            <button
              onClick={saveProfile}
              disabled={saving}
              className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {saving ? t('resume_save_saving') : t('resume_save_btn')}
            </button>
          </div>

          {savedMsg && (
            <div className={`text-sm px-3 py-2 rounded ${savedMsg.startsWith('✅') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-700'}`}>
              {savedMsg}
            </div>
          )}

          {/* Basic */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">{t('resume_basic_info')}</h3>
            <p className="text-sm text-gray-800 font-medium">{parsed.name}</p>
            <p className="text-sm text-gray-500">{t('resume_target_roles')} {parsed.target_roles?.join(', ') ?? '—'}</p>
          </section>

          {/* Skills */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t('resume_skills')} ({parsed.skills?.length ?? 0})</h3>
            <div className="flex flex-wrap gap-1.5">
              {(parsed.skills ?? []).map((s) => (
                <span key={s.name} className="px-2 py-0.5 bg-blue-50 text-blue-800 rounded text-xs">
                  {s.name} · {s.level} · {s.years}y
                </span>
              ))}
            </div>
          </section>

          {/* Experience */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t('resume_experience')} ({parsed.experience?.length ?? 0})</h3>
            <div className="space-y-2">
              {(parsed.experience ?? []).map((exp, i) => (
                <div key={i} className="border-l-2 border-blue-200 pl-3">
                  <p className="text-sm font-medium text-gray-800">{exp.role} @ {exp.company}</p>
                  <p className="text-xs text-gray-500">{exp.duration}</p>
                  <ul className="mt-1 space-y-0.5">
                    {(exp.bullets ?? []).slice(0, 2).map((b, j) => (
                      <li key={j} className="text-xs text-gray-600">• {b.raw}</li>
                    ))}
                    {(exp.bullets?.length ?? 0) > 2 && <li className="text-xs text-gray-400">+{(exp.bullets?.length ?? 0) - 2} more</li>}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          {/* Projects */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t('resume_projects')} ({parsed.projects?.length ?? 0})</h3>
            <div className="space-y-2">
              {(parsed.projects ?? []).map((p, i) => (
                <div key={i} className="border-l-2 border-purple-200 pl-3">
                  <p className="text-sm font-medium text-gray-800">{p.name}</p>
                  <p className="text-xs text-gray-500">{p.tech_stack?.join(', ')}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Education */}
          {parsed.education && parsed.education.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">{t('resume_education')} ({parsed.education.length})</h3>
              <div className="space-y-2">
                {parsed.education.map((edu, i) => (
                  <div key={i} className="border-l-2 border-green-200 pl-3">
                    <p className="text-sm font-medium text-gray-800">{edu.degree}{edu.field ? ` in ${edu.field}` : ''}</p>
                    <p className="text-xs text-gray-600">{edu.institution}</p>
                    <p className="text-xs text-gray-500">{edu.duration}{edu.gpa ? ` · GPA: ${edu.gpa}` : ''}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Preferences */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">{t('profile_tab_preferences')}</h3>
            <p className="text-sm text-gray-600">
              {t('resume_locations')} {parsed.preferences?.locations?.join(', ') || '—'}
            </p>
            {parsed.preferences?.salary_range && (
              <p className="text-sm text-gray-600">
                {t('resume_salary')} {parsed.preferences.salary_range.min}–{parsed.preferences.salary_range.max} {parsed.preferences.salary_range.currency}
              </p>
            )}
            <p className="text-sm text-gray-600">
              {t('resume_job_types')} {parsed.preferences?.job_types?.join(', ') || '—'}
            </p>
          </section>
        </div>
      )}
    </div>
  )
}
