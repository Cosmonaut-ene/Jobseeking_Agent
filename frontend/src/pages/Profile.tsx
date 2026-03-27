import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Education, Experience, Preferences, Project, Skill, UserProfile } from '../api/client'
import { useT } from '../contexts/LanguageContext'

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
  const t = useT()
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
          <span key={item} className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-md text-xs">
            {item}
            <button onClick={() => onChange(items.filter((x) => x !== item))} className="hover:text-red-600 dark:hover:text-red-400">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder={placeholder}
          className="flex-1 border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
        />
        <button onClick={add} className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600 transition-colors">{t('skill_add_btn')}</button>
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
  const t = useT()
  const { sy, sm, ey, em, isPresent } = parseDuration(value)

  function emit(next: { sy: string; sm: string; ey: string; em: string; isPresent: boolean }) {
    const start = next.sm ? `${next.sy}-${next.sm}` : next.sy
    const end = next.isPresent ? 'Present' : (next.em ? `${next.ey}-${next.em}` : next.ey)
    onChange(`${start} ~ ${end}`)
  }

  const sel = 'border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400'

  return (
    <div className="flex flex-wrap items-center gap-1">
      <select value={sy} onChange={(e) => emit({ sy: e.target.value, sm, ey, em, isPresent })} className={sel}>
        <option value="">{t('duration_year')}</option>
        {YEAR_OPTS.map((y) => <option key={y}>{y}</option>)}
      </select>
      <select value={sm} onChange={(e) => emit({ sy, sm: e.target.value, ey, em, isPresent })} className={sel}>
        <option value="">{t('duration_month')}</option>
        {MONTH_OPTS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
      </select>
      <span className="text-slate-400 dark:text-zinc-500 text-sm">~</span>
      {isPresent ? (
        <>
          <span className="text-slate-500 dark:text-slate-400 text-sm px-1">{t('duration_present')}</span>
          <button
            onClick={() => emit({ sy, sm, ey: String(CUR_YEAR), em: '', isPresent: false })}
            className="text-xs text-amber-500 hover:underline"
          >{t('duration_set_end')}</button>
        </>
      ) : (
        <>
          <select value={ey} onChange={(e) => emit({ sy, sm, ey: e.target.value, em, isPresent })} className={sel}>
            <option value="">{t('duration_year')}</option>
            {YEAR_OPTS.map((y) => <option key={y}>{y}</option>)}
          </select>
          <select value={em} onChange={(e) => emit({ sy, sm, ey, em: e.target.value, isPresent })} className={sel}>
            <option value="">{t('duration_month')}</option>
            {MONTH_OPTS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <button
            onClick={() => emit({ sy, sm, ey: '', em: '', isPresent: true })}
            className="text-xs text-amber-500 hover:underline"
          >{t('duration_present')}</button>
        </>
      )}
    </div>
  )
}

// ── Basic tab ────────────────────────────────────────────────────────────────
function BasicTab({ profile, onChange }: { profile: UserProfile; onChange: (p: UserProfile) => void }) {
  const t = useT()
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('profile_full_name')}</label>
        <input
          value={profile.name}
          onChange={(e) => onChange({ ...profile, name: e.target.value })}
          className="w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('profile_target_roles')}</label>
        <TagListEditor
          items={profile.target_roles}
          onChange={(v) => onChange({ ...profile, target_roles: v })}
          placeholder={t('profile_target_roles_placeholder')}
        />
      </div>
    </div>
  )
}

// ── Skills tab ───────────────────────────────────────────────────────────────
function SkillsTab({ skills, onChange }: { skills: Skill[]; onChange: (s: Skill[]) => void }) {
  const t = useT()
  const [newSkill, setNewSkill] = useState<Skill>({ name: '', level: 'intermediate', years: 1 })

  function add() {
    if (!newSkill.name.trim()) return
    onChange([...skills, { ...newSkill }])
    setNewSkill({ name: '', level: 'intermediate', years: 1 })
  }

  const cellInput = 'w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-md px-2 py-1 text-xs focus:ring-1 focus:ring-amber-400 focus:outline-none'

  return (
    <div className="space-y-3">
      <table className="w-full text-sm">
        <thead className="bg-slate-50/60 dark:bg-zinc-800/60">
          <tr>
            <th className="text-left px-3 py-2 text-slate-600 dark:text-slate-400 font-medium">{t('skill_col_skill')}</th>
            <th className="text-left px-3 py-2 text-slate-600 dark:text-slate-400 font-medium">{t('skill_col_level')}</th>
            <th className="text-left px-3 py-2 text-slate-600 dark:text-slate-400 font-medium">{t('skill_col_years')}</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-zinc-700/60">
          {skills.map((s, i) => (
            <tr key={i}>
              <td className="px-3 py-1.5">
                <input
                  value={s.name}
                  onChange={(e) => onChange(skills.map((x, j) => j === i ? { ...x, name: e.target.value } : x))}
                  className={cellInput}
                />
              </td>
              <td className="px-3 py-1.5">
                <select
                  value={s.level}
                  onChange={(e) => onChange(skills.map((x, j) => j === i ? { ...x, level: e.target.value } : x))}
                  className="border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-md px-2 py-1 text-xs focus:ring-1 focus:ring-amber-400 focus:outline-none"
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
                  className={cellInput}
                />
              </td>
              <td className="px-3 py-1.5">
                <button onClick={() => onChange(skills.filter((_, j) => j !== i))} className="text-rose-400 hover:text-rose-600 dark:hover:text-rose-300 text-xs">{t('skill_remove')}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex gap-2 items-end border-t border-slate-200/60 dark:border-zinc-700/60 pt-3">
        <div className="flex-1">
          <input
            value={newSkill.name}
            onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder={t('skill_name_placeholder')}
            className="w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </div>
        <select
          value={newSkill.level}
          onChange={(e) => setNewSkill({ ...newSkill, level: e.target.value })}
          className="border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
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
          className="w-20 border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <button onClick={add} className="px-4 py-1.5 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600 transition-colors">{t('skill_add_btn')}</button>
      </div>
    </div>
  )
}

// ── Experience tab ───────────────────────────────────────────────────────────
function ExperienceTab({ experience, onChange }: { experience: Experience[]; onChange: (e: Experience[]) => void }) {
  const t = useT()
  function update(i: number, patch: Partial<Experience>) {
    onChange(experience.map((x, j) => j === i ? { ...x, ...patch } : x))
  }

  function addExp() {
    onChange([...experience, { company: '', role: '', duration: '', bullets: [] }])
  }

  const inp = 'border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400'
  const inpSm = 'flex-1 border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400'

  return (
    <div className="space-y-4">
      {experience.map((exp, i) => (
        <div key={i} className="border border-slate-200/60 dark:border-zinc-700/60 rounded-xl p-4 bg-slate-50/60 dark:bg-zinc-800/40 space-y-3">
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-2 flex-1 mr-3">
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={exp.role}
                  onChange={(e) => update(i, { role: e.target.value })}
                  placeholder={t('exp_role_placeholder')}
                  className={inp}
                />
                <input
                  value={exp.company}
                  onChange={(e) => update(i, { company: e.target.value })}
                  placeholder={t('exp_company_placeholder')}
                  className={inp}
                />
              </div>
              <DurationPicker value={exp.duration} onChange={(v) => update(i, { duration: v })} />
            </div>
            <button onClick={() => onChange(experience.filter((_, j) => j !== i))} className="text-rose-400 hover:text-rose-600 dark:hover:text-rose-300 text-sm">{t('exp_remove')}</button>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t('exp_bullets_label')} ({exp.bullets.length})</p>
            <div className="space-y-1">
              {exp.bullets.map((b, k) => (
                <div key={k} className="flex gap-1">
                  <input
                    value={b.raw}
                    onChange={(e) => {
                      const newBullets = exp.bullets.map((bb, l) => l === k ? { ...bb, raw: e.target.value } : bb)
                      update(i, { bullets: newBullets })
                    }}
                    className={inpSm}
                  />
                  <button
                    onClick={() => update(i, { bullets: exp.bullets.filter((_, l) => l !== k) })}
                    className="text-rose-300 hover:text-rose-500 dark:text-rose-500/60 dark:hover:text-rose-400 text-xs px-1"
                  >×</button>
                </div>
              ))}
            </div>
            <button
              onClick={() => update(i, { bullets: [...exp.bullets, { raw: '', tech: [], metric: '' }] })}
              className="mt-1 text-xs text-amber-600 dark:text-amber-400 hover:underline"
            >
              {t('exp_add_bullet')}
            </button>
          </div>
        </div>
      ))}
      <button onClick={addExp} className="w-full py-2 border-2 border-dashed border-slate-300 dark:border-zinc-600 rounded-lg text-sm text-slate-500 dark:text-slate-400 hover:border-amber-400 hover:text-amber-600 dark:hover:border-amber-500 dark:hover:text-amber-400 transition-colors">
        {t('exp_add_exp_btn')}
      </button>
    </div>
  )
}

// ── Projects tab ─────────────────────────────────────────────────────────────
function ProjectsTab({ projects, onChange }: { projects: Project[]; onChange: (p: Project[]) => void }) {
  const t = useT()
  function update(i: number, patch: Partial<Project>) {
    onChange(projects.map((x, j) => j === i ? { ...x, ...patch } : x))
  }

  const inp = 'w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400'
  const inpSm = 'flex-1 border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400'

  return (
    <div className="space-y-4">
      {projects.map((p, i) => (
        <div key={i} className="border border-slate-200/60 dark:border-zinc-700/60 rounded-xl p-4 bg-slate-50/60 dark:bg-zinc-800/40 space-y-3">
          <div className="flex justify-between items-start">
            <div className="flex-1 mr-3 space-y-2">
              <input
                value={p.name}
                onChange={(e) => update(i, { name: e.target.value })}
                placeholder={t('proj_name_placeholder')}
                className={inp}
              />
              <input
                value={p.description}
                onChange={(e) => update(i, { description: e.target.value })}
                placeholder={t('proj_desc_placeholder')}
                className={inp}
              />
            </div>
            <button onClick={() => onChange(projects.filter((_, j) => j !== i))} className="text-rose-400 hover:text-rose-600 dark:hover:text-rose-300 text-sm">{t('proj_remove')}</button>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t('proj_tech_label')}</p>
            <div className="flex flex-wrap gap-1 mb-1">
              {p.tech_stack.map((tech) => (
                <span key={tech} className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded text-xs">
                  {tech}
                  <button onClick={() => update(i, { tech_stack: p.tech_stack.filter((x) => x !== tech) })} className="hover:text-red-600 dark:hover:text-red-400">×</button>
                </span>
              ))}
            </div>
            <input
              placeholder={t('proj_tech_placeholder')}
              className="border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400"
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
            <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t('proj_bullets_label')} ({p.bullets.length})</p>
            <div className="space-y-1">
              {p.bullets.map((b, k) => (
                <div key={k} className="flex gap-1">
                  <input
                    value={b.raw}
                    onChange={(e) => {
                      const newBullets = p.bullets.map((bb, l) => l === k ? { ...bb, raw: e.target.value } : bb)
                      update(i, { bullets: newBullets })
                    }}
                    className={inpSm}
                  />
                  <button
                    onClick={() => update(i, { bullets: p.bullets.filter((_, l) => l !== k) })}
                    className="text-rose-300 hover:text-rose-500 dark:text-rose-500/60 dark:hover:text-rose-400 text-xs px-1"
                  >×</button>
                </div>
              ))}
            </div>
            <button
              onClick={() => update(i, { bullets: [...p.bullets, { raw: '', tech: [], metric: '' }] })}
              className="mt-1 text-xs text-amber-600 dark:text-amber-400 hover:underline"
            >
              {t('proj_add_bullet')}
            </button>
          </div>
        </div>
      ))}
      <button
        onClick={() => onChange([...projects, { name: '', description: '', tech_stack: [], bullets: [] }])}
        className="w-full py-2 border-2 border-dashed border-slate-300 dark:border-zinc-600 rounded-lg text-sm text-slate-500 dark:text-slate-400 hover:border-amber-400 hover:text-amber-600 dark:hover:border-amber-500 dark:hover:text-amber-400 transition-colors"
      >
        {t('proj_add_btn')}
      </button>
    </div>
  )
}

// ── Education tab ─────────────────────────────────────────────────────────────
function EducationTab({ education, onChange }: { education: Education[]; onChange: (e: Education[]) => void }) {
  const t = useT()
  function update(i: number, patch: Partial<Education>) {
    onChange(education.map((x, j) => j === i ? { ...x, ...patch } : x))
  }

  const inp = 'border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400'

  return (
    <div className="space-y-4">
      {education.map((edu, i) => (
        <div key={i} className="border border-slate-200/60 dark:border-zinc-700/60 rounded-xl p-4 bg-slate-50/60 dark:bg-zinc-800/40 space-y-2">
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-2 flex-1 mr-3">
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={edu.institution}
                  onChange={(e) => update(i, { institution: e.target.value })}
                  placeholder={t('edu_institution_placeholder')}
                  className={inp}
                />
                <input
                  value={edu.degree}
                  onChange={(e) => update(i, { degree: e.target.value })}
                  placeholder={t('edu_degree_placeholder')}
                  className={inp}
                />
                <input
                  value={edu.field}
                  onChange={(e) => update(i, { field: e.target.value })}
                  placeholder={t('edu_field_placeholder')}
                  className={inp}
                />
                <input
                  value={edu.gpa}
                  onChange={(e) => update(i, { gpa: e.target.value })}
                  placeholder={t('edu_gpa_placeholder')}
                  className={inp}
                />
              </div>
              <DurationPicker value={edu.duration} onChange={(v) => update(i, { duration: v })} />
            </div>
            <button onClick={() => onChange(education.filter((_, j) => j !== i))} className="text-rose-400 hover:text-rose-600 dark:hover:text-rose-300 text-sm">{t('edu_remove')}</button>
          </div>
        </div>
      ))}
      <button
        onClick={() => onChange([...education, { institution: '', degree: '', field: '', duration: '', gpa: '' }])}
        className="w-full py-2 border-2 border-dashed border-slate-300 dark:border-zinc-600 rounded-lg text-sm text-slate-500 dark:text-slate-400 hover:border-amber-400 hover:text-amber-600 dark:hover:border-amber-500 dark:hover:text-amber-400 transition-colors"
      >
        {t('edu_add_btn')}
      </button>
    </div>
  )
}

// ── Preferences tab ──────────────────────────────────────────────────────────
function PreferencesTab({ prefs, onChange }: { prefs: Preferences; onChange: (p: Preferences) => void }) {
  const t = useT()
  const numInp = 'w-28 border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400'
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('pref_locations')}</label>
        <TagListEditor
          items={prefs.locations}
          onChange={(v) => onChange({ ...prefs, locations: v })}
          placeholder={t('pref_locations_placeholder')}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{t('pref_job_types')}</label>
        <TagListEditor
          items={prefs.job_types}
          onChange={(v) => onChange({ ...prefs, job_types: v })}
          placeholder={t('pref_job_types_placeholder')}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">{t('pref_salary')}</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder={t('pref_salary_min')}
            value={prefs.salary_range?.min ?? ''}
            onChange={(e) => onChange({ ...prefs, salary_range: { ...prefs.salary_range ?? { min: 0, max: 0, currency: 'AUD' }, min: Number(e.target.value) } })}
            className={numInp}
          />
          <span className="text-slate-500 dark:text-slate-400">–</span>
          <input
            type="number"
            placeholder={t('pref_salary_max')}
            value={prefs.salary_range?.max ?? ''}
            onChange={(e) => onChange({ ...prefs, salary_range: { ...prefs.salary_range ?? { min: 0, max: 0, currency: 'AUD' }, max: Number(e.target.value) } })}
            className={numInp}
          />
          <input
            value={prefs.salary_range?.currency ?? 'AUD'}
            onChange={(e) => onChange({ ...prefs, salary_range: { ...prefs.salary_range ?? { min: 0, max: 0, currency: 'AUD' }, currency: e.target.value } })}
            placeholder={t('pref_salary_currency')}
            className="w-20 border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </div>
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Profile() {
  const t = useT()
  const [profile, setProfile] = useState<UserProfile>(EMPTY_PROFILE)
  const [tab, setTab] = useState<Tab>('basic')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [msgSuccess, setMsgSuccess] = useState(false)

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
      setMsg(t('profile_saved'))
      setMsgSuccess(true)
    } catch (e: unknown) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Save failed'
      setMsg(d)
      setMsgSuccess(false)
    } finally {
      setSaving(false)
    }
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: 'basic', label: t('profile_tab_basic') },
    { key: 'skills', label: `${t('profile_tab_skills')} (${(profile.skills ?? []).length})` },
    { key: 'education', label: `${t('profile_tab_education')} (${(profile.education ?? []).length})` },
    { key: 'experience', label: `${t('profile_tab_experience')} (${(profile.experience ?? []).length})` },
    { key: 'projects', label: `${t('profile_tab_projects')} (${(profile.projects ?? []).length})` },
    { key: 'preferences', label: t('profile_tab_preferences') },
  ]

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('profile_title')}</h1>
        <button
          onClick={save}
          disabled={saving || loading}
          className="px-5 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors shadow-sm"
        >
          {saving ? t('profile_saving') : t('profile_save_btn')}
        </button>
      </div>

      {msg && (
        <div className={`mb-4 text-sm px-3 py-2 rounded-lg ${msgSuccess ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300' : 'bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'}`}>
          {msg}
        </div>
      )}

      {loading ? (
        <p className="text-slate-400 dark:text-zinc-500 text-sm">{t('profile_loading')}</p>
      ) : (
        <div className="glass-card overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-slate-200/60 dark:border-zinc-700/60 overflow-x-auto">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  tab === key
                    ? 'border-b-2 border-amber-500 text-amber-600 dark:text-amber-400'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
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
