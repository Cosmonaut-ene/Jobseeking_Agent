import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Education, Experience, Preferences, Project, Skill, UserProfile } from '../api/client'

const EMPTY_PROFILE: UserProfile = {
  name: '',
  target_roles: [],
  skills: [],
  experience: [],
  projects: [],
  preferences: { locations: [], salary_range: null, job_types: [] },
  education: [],
}

type Tab = 'basic' | 'skills' | 'education' | 'experience' | 'projects' | 'preferences'

// ── Tag list editor ──────────────────────────────────────────────────────────
function TagListEditor({
  items,
  onChange,
  placeholder,
}: {
  items: string[]
  onChange: (v: string[]) => void
  placeholder?: string
}) {
  const [input, setInput] = useState('')

  function add() {
    const v = input.trim()
    if (v && !items.includes(v)) onChange([...items, v])
    setInput('')
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {items.map((item) => (
          <span key={item} className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
            {item}
            <button onClick={() => onChange(items.filter((x) => x !== item))} className="hover:text-red-600">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder={placeholder}
          className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button onClick={add} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">Add</button>
      </div>
    </div>
  )
}

// ── Duration picker ───────────────────────────────────────────────────────────
const CUR_YEAR = new Date().getFullYear()
const YEAR_OPTS = Array.from({ length: CUR_YEAR - 1989 }, (_, i) => String(CUR_YEAR - i))
const MONTH_OPTS: [string, string][] = [
  ['01','Jan'],['02','Feb'],['03','Mar'],['04','Apr'],
  ['05','May'],['06','Jun'],['07','Jul'],['08','Aug'],
  ['09','Sep'],['10','Oct'],['11','Nov'],['12','Dec'],
]

function parseDuration(s: string) {
  const [startStr = '', endStr = ''] = s.split(' ~ ')
  const [sy = '', sm = ''] = startStr.split('-')
  const isPresent = !endStr || endStr.toLowerCase() === 'present'
  const [ey = '', em = ''] = isPresent ? [] : endStr.split('-')
  return { sy, sm, ey, em, isPresent }
}

function DurationPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { sy, sm, ey, em, isPresent } = parseDuration(value)

  function emit(next: { sy: string; sm: string; ey: string; em: string; isPresent: boolean }) {
    const start = next.sm ? `${next.sy}-${next.sm}` : next.sy
    const end = next.isPresent ? 'Present' : (next.em ? `${next.ey}-${next.em}` : next.ey)
    onChange(`${start} ~ ${end}`)
  }

  const sel = 'border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400'

  return (
    <div className="flex flex-wrap items-center gap-1">
      <select value={sy} onChange={(e) => emit({ sy: e.target.value, sm, ey, em, isPresent })} className={sel}>
        <option value="">Year</option>
        {YEAR_OPTS.map((y) => <option key={y}>{y}</option>)}
      </select>
      <select value={sm} onChange={(e) => emit({ sy, sm: e.target.value, ey, em, isPresent })} className={sel}>
        <option value="">Month</option>
        {MONTH_OPTS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
      </select>
      <span className="text-gray-400 text-sm">~</span>
      {isPresent ? (
        <>
          <span className="text-gray-500 text-sm px-1">Present</span>
          <button
            onClick={() => emit({ sy, sm, ey: String(CUR_YEAR), em: '', isPresent: false })}
            className="text-xs text-blue-500 hover:underline"
          >set end</button>
        </>
      ) : (
        <>
          <select value={ey} onChange={(e) => emit({ sy, sm, ey: e.target.value, em, isPresent })} className={sel}>
            <option value="">Year</option>
            {YEAR_OPTS.map((y) => <option key={y}>{y}</option>)}
          </select>
          <select value={em} onChange={(e) => emit({ sy, sm, ey, em: e.target.value, isPresent })} className={sel}>
            <option value="">Month</option>
            {MONTH_OPTS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <button
            onClick={() => emit({ sy, sm, ey: '', em: '', isPresent: true })}
            className="text-xs text-blue-500 hover:underline"
          >Present</button>
        </>
      )}
    </div>
  )
}

// ── Basic tab ────────────────────────────────────────────────────────────────
function BasicTab({ profile, onChange }: { profile: UserProfile; onChange: (p: UserProfile) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
        <input
          value={profile.name}
          onChange={(e) => onChange({ ...profile, name: e.target.value })}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Target Roles</label>
        <TagListEditor
          items={profile.target_roles}
          onChange={(v) => onChange({ ...profile, target_roles: v })}
          placeholder="e.g. Backend Engineer"
        />
      </div>
    </div>
  )
}

// ── Skills tab ───────────────────────────────────────────────────────────────
function SkillsTab({ skills, onChange }: { skills: Skill[]; onChange: (s: Skill[]) => void }) {
  const [newSkill, setNewSkill] = useState<Skill>({ name: '', level: 'intermediate', years: 1 })

  function add() {
    if (!newSkill.name.trim()) return
    onChange([...skills, { ...newSkill }])
    setNewSkill({ name: '', level: 'intermediate', years: 1 })
  }

  return (
    <div className="space-y-3">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-3 py-2 text-gray-600 font-medium">Skill</th>
            <th className="text-left px-3 py-2 text-gray-600 font-medium">Level</th>
            <th className="text-left px-3 py-2 text-gray-600 font-medium">Years</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {skills.map((s, i) => (
            <tr key={i}>
              <td className="px-3 py-1.5">
                <input
                  value={s.name}
                  onChange={(e) => onChange(skills.map((x, j) => j === i ? { ...x, name: e.target.value } : x))}
                  className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-blue-400 focus:outline-none"
                />
              </td>
              <td className="px-3 py-1.5">
                <select
                  value={s.level}
                  onChange={(e) => onChange(skills.map((x, j) => j === i ? { ...x, level: e.target.value } : x))}
                  className="border border-gray-200 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-blue-400 focus:outline-none"
                >
                  <option>beginner</option>
                  <option>intermediate</option>
                  <option>expert</option>
                </select>
              </td>
              <td className="px-3 py-1.5 w-20">
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={s.years}
                  onChange={(e) => onChange(skills.map((x, j) => j === i ? { ...x, years: Number(e.target.value) } : x))}
                  className="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-blue-400 focus:outline-none"
                />
              </td>
              <td className="px-3 py-1.5">
                <button onClick={() => onChange(skills.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex gap-2 items-end border-t pt-3">
        <div className="flex-1">
          <input
            value={newSkill.name}
            onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="Skill name"
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={newSkill.level}
          onChange={(e) => setNewSkill({ ...newSkill, level: e.target.value })}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option>beginner</option>
          <option>intermediate</option>
          <option>expert</option>
        </select>
        <input
          type="number"
          min={0}
          step={0.5}
          value={newSkill.years}
          onChange={(e) => setNewSkill({ ...newSkill, years: Number(e.target.value) })}
          className="w-20 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button onClick={add} className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">Add</button>
      </div>
    </div>
  )
}

// ── Experience tab ───────────────────────────────────────────────────────────
function ExperienceTab({ experience, onChange }: { experience: Experience[]; onChange: (e: Experience[]) => void }) {
  function update(i: number, patch: Partial<Experience>) {
    onChange(experience.map((x, j) => j === i ? { ...x, ...patch } : x))
  }

  function addExp() {
    onChange([...experience, { company: '', role: '', duration: '', bullets: [] }])
  }

  return (
    <div className="space-y-4">
      {experience.map((exp, i) => (
        <div key={i} className="border rounded-lg p-4 bg-gray-50 space-y-3">
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-2 flex-1 mr-3">
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={exp.role}
                  onChange={(e) => update(i, { role: e.target.value })}
                  placeholder="Role"
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <input
                  value={exp.company}
                  onChange={(e) => update(i, { company: e.target.value })}
                  placeholder="Company"
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>
              <DurationPicker value={exp.duration} onChange={(v) => update(i, { duration: v })} />
            </div>
            <button onClick={() => onChange(experience.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600 text-sm">Remove</button>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">Bullets ({exp.bullets.length})</p>
            <div className="space-y-1">
              {exp.bullets.map((b, k) => (
                <div key={k} className="flex gap-1">
                  <input
                    value={b.raw}
                    onChange={(e) => {
                      const newBullets = exp.bullets.map((bb, l) => l === k ? { ...bb, raw: e.target.value } : bb)
                      update(i, { bullets: newBullets })
                    }}
                    className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                  <button
                    onClick={() => update(i, { bullets: exp.bullets.filter((_, l) => l !== k) })}
                    className="text-red-300 hover:text-red-500 text-xs px-1"
                  >×</button>
                </div>
              ))}
            </div>
            <button
              onClick={() => update(i, { bullets: [...exp.bullets, { raw: '', tech: [], metric: '' }] })}
              className="mt-1 text-xs text-blue-600 hover:underline"
            >
              + Add bullet
            </button>
          </div>
        </div>
      ))}
      <button onClick={addExp} className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors">
        + Add Experience
      </button>
    </div>
  )
}

// ── Projects tab ─────────────────────────────────────────────────────────────
function ProjectsTab({ projects, onChange }: { projects: Project[]; onChange: (p: Project[]) => void }) {
  function update(i: number, patch: Partial<Project>) {
    onChange(projects.map((x, j) => j === i ? { ...x, ...patch } : x))
  }

  return (
    <div className="space-y-4">
      {projects.map((p, i) => (
        <div key={i} className="border rounded-lg p-4 bg-gray-50 space-y-3">
          <div className="flex justify-between items-start">
            <div className="flex-1 mr-3 space-y-2">
              <input
                value={p.name}
                onChange={(e) => update(i, { name: e.target.value })}
                placeholder="Project name"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
              <input
                value={p.description}
                onChange={(e) => update(i, { description: e.target.value })}
                placeholder="Description"
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>
            <button onClick={() => onChange(projects.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600 text-sm">Remove</button>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">Tech Stack</p>
            <div className="flex flex-wrap gap-1 mb-1">
              {p.tech_stack.map((t) => (
                <span key={t} className="flex items-center gap-1 px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-xs">
                  {t}
                  <button onClick={() => update(i, { tech_stack: p.tech_stack.filter((x) => x !== t) })} className="hover:text-red-600">×</button>
                </span>
              ))}
            </div>
            <input
              placeholder="Add tech (press Enter)"
              className="border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const v = (e.target as HTMLInputElement).value.trim()
                  if (v) update(i, { tech_stack: [...p.tech_stack, v] });
                  (e.target as HTMLInputElement).value = ''
                }
              }}
            />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">Bullets ({p.bullets.length})</p>
            <div className="space-y-1">
              {p.bullets.map((b, k) => (
                <div key={k} className="flex gap-1">
                  <input
                    value={b.raw}
                    onChange={(e) => {
                      const newBullets = p.bullets.map((bb, l) => l === k ? { ...bb, raw: e.target.value } : bb)
                      update(i, { bullets: newBullets })
                    }}
                    className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                  <button
                    onClick={() => update(i, { bullets: p.bullets.filter((_, l) => l !== k) })}
                    className="text-red-300 hover:text-red-500 text-xs px-1"
                  >×</button>
                </div>
              ))}
            </div>
            <button
              onClick={() => update(i, { bullets: [...p.bullets, { raw: '', tech: [], metric: '' }] })}
              className="mt-1 text-xs text-blue-600 hover:underline"
            >
              + Add bullet
            </button>
          </div>
        </div>
      ))}
      <button
        onClick={() => onChange([...projects, { name: '', description: '', tech_stack: [], bullets: [] }])}
        className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-purple-400 hover:text-purple-600 transition-colors"
      >
        + Add Project
      </button>
    </div>
  )
}

// ── Education tab ─────────────────────────────────────────────────────────────
function EducationTab({ education, onChange }: { education: Education[]; onChange: (e: Education[]) => void }) {
  function update(i: number, patch: Partial<Education>) {
    onChange(education.map((x, j) => j === i ? { ...x, ...patch } : x))
  }

  return (
    <div className="space-y-4">
      {education.map((edu, i) => (
        <div key={i} className="border rounded-lg p-4 bg-gray-50 space-y-2">
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-2 flex-1 mr-3">
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={edu.institution}
                  onChange={(e) => update(i, { institution: e.target.value })}
                  placeholder="Institution"
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <input
                  value={edu.degree}
                  onChange={(e) => update(i, { degree: e.target.value })}
                  placeholder="Degree (e.g. Bachelor)"
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <input
                  value={edu.field}
                  onChange={(e) => update(i, { field: e.target.value })}
                  placeholder="Field of study"
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <input
                  value={edu.gpa}
                  onChange={(e) => update(i, { gpa: e.target.value })}
                  placeholder="GPA (optional)"
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>
              <DurationPicker value={edu.duration} onChange={(v) => update(i, { duration: v })} />
            </div>
            <button onClick={() => onChange(education.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600 text-sm">Remove</button>
          </div>
        </div>
      ))}
      <button
        onClick={() => onChange([...education, { institution: '', degree: '', field: '', duration: '', gpa: '' }])}
        className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors"
      >
        + Add Education
      </button>
    </div>
  )
}

// ── Preferences tab ──────────────────────────────────────────────────────────
function PreferencesTab({ prefs, onChange }: { prefs: Preferences; onChange: (p: Preferences) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Locations</label>
        <TagListEditor
          items={prefs.locations}
          onChange={(v) => onChange({ ...prefs, locations: v })}
          placeholder="e.g. Sydney"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Job Types</label>
        <TagListEditor
          items={prefs.job_types}
          onChange={(v) => onChange({ ...prefs, job_types: v })}
          placeholder="e.g. full-time"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Salary Range</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="Min"
            value={prefs.salary_range?.min ?? ''}
            onChange={(e) => onChange({ ...prefs, salary_range: { ...prefs.salary_range ?? { min: 0, max: 0, currency: 'AUD' }, min: Number(e.target.value) } })}
            className="w-28 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-gray-500">–</span>
          <input
            type="number"
            placeholder="Max"
            value={prefs.salary_range?.max ?? ''}
            onChange={(e) => onChange({ ...prefs, salary_range: { ...prefs.salary_range ?? { min: 0, max: 0, currency: 'AUD' }, max: Number(e.target.value) } })}
            className="w-28 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            value={prefs.salary_range?.currency ?? 'AUD'}
            onChange={(e) => onChange({ ...prefs, salary_range: { ...prefs.salary_range ?? { min: 0, max: 0, currency: 'AUD' }, currency: e.target.value } })}
            placeholder="Currency"
            className="w-20 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Profile() {
  const [profile, setProfile] = useState<UserProfile>(EMPTY_PROFILE)
  const [tab, setTab] = useState<Tab>('basic')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.get('/api/profile')
      .then((r) => setProfile({
        name: '',
        target_roles: [],
        skills: [],
        experience: [],
        projects: [],
        preferences: { locations: [], salary_range: null, job_types: [] },
        education: [],
        ...r.data
      }))
      .catch(() => { /* profile not yet created */ })
      .finally(() => setLoading(false))
  }, [])

  async function save() {
    setSaving(true)
    setMsg('')
    try {
      await api.put('/api/profile', profile)
      setMsg('✅ Profile saved!')
    } catch (e: unknown) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Save failed'
      setMsg(d)
    } finally {
      setSaving(false)
    }
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: 'basic', label: 'Basic' },
    { key: 'skills', label: `Skills (${(profile.skills ?? []).length})` },
    { key: 'education', label: `Education (${(profile.education ?? []).length})` },
    { key: 'experience', label: `Experience (${(profile.experience ?? []).length})` },
    { key: 'projects', label: `Projects (${(profile.projects ?? []).length})` },
    { key: 'preferences', label: 'Preferences' },
  ]

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <button
          onClick={save}
          disabled={saving || loading}
          className="px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : '💾 Save Profile'}
        </button>
      </div>

      {msg && (
        <div className={`mb-4 text-sm px-3 py-2 rounded ${msg.startsWith('✅') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-700'}`}>
          {msg}
        </div>
      )}

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="bg-white rounded-lg shadow">
          {/* Tabs */}
          <div className="flex border-b overflow-x-auto">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  tab === key
                    ? 'border-b-2 border-blue-600 text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {tab === 'basic' && <BasicTab profile={profile} onChange={setProfile} />}
            {tab === 'skills' && <SkillsTab skills={profile.skills} onChange={(s) => setProfile({ ...profile, skills: s })} />}
            {tab === 'education' && <EducationTab education={profile.education ?? []} onChange={(e) => setProfile({ ...profile, education: e })} />}
            {tab === 'experience' && <ExperienceTab experience={profile.experience} onChange={(e) => setProfile({ ...profile, experience: e })} />}
            {tab === 'projects' && <ProjectsTab projects={profile.projects} onChange={(p) => setProfile({ ...profile, projects: p })} />}
            {tab === 'preferences' && <PreferencesTab prefs={profile.preferences} onChange={(p) => setProfile({ ...profile, preferences: p })} />}
          </div>
        </div>
      )}
    </div>
  )
}
