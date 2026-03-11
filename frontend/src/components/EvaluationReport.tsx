import { useState } from 'react'
import type { GapAnalysis } from '../api/client'
import { useT } from '../contexts/LanguageContext'

// ── Helpers ───────────────────────────────────────────────────────────────────

function Section({
  title,
  defaultOpen = false,
  children,
}: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-sm font-semibold text-gray-700 transition-colors"
      >
        <span>{title}</span>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-4 py-3 space-y-3 bg-white">{children}</div>}
    </div>
  )
}

function SubList({ label, items, color = 'gray' }: { label: string; items?: string[]; color?: string }) {
  if (!items || items.length === 0) return null
  const dot: Record<string, string> = {
    green: 'text-green-500',
    red: 'text-red-400',
    yellow: 'text-yellow-500',
    blue: 'text-blue-500',
    gray: 'text-gray-400',
  }
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <ul className="space-y-0.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-700 flex items-start gap-1.5">
            <span className={`mt-0.5 shrink-0 ${dot[color] ?? dot.gray}`}>•</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ── ATS score bar ─────────────────────────────────────────────────────────────

function AtsBar({ pct }: { pct: number }) {
  const t = useT()
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  const textColor = pct >= 70 ? 'text-green-700' : pct >= 40 ? 'text-yellow-700' : 'text-red-600'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold ${textColor}`}>{pct}{t('eval_ats_match')}</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function EvaluationReport({ gap }: { gap: GapAnalysis }) {
  const t = useT()
  const rec = gap.recommendations
  const si = gap.skills_improvements
  const ri = gap.resume_improvements
  const fi = gap.formatting_improvements

  return (
    <div className="space-y-2">
      {/* 1. Match Analysis */}
      <Section title={t('eval_section1')} defaultOpen>
        {gap.ats_pct !== undefined && <AtsBar pct={gap.ats_pct} />}
        <SubList label={t('eval_strong_matches')} items={gap.strong_matches} color="green" />
        <SubList label={t('eval_missing_skills')} items={gap.missing_skills} color="red" />
        <SubList label={t('eval_unmet_reqs')} items={gap.unmet_requirements} color="yellow" />
        {gap.notes && (
          <p className="text-sm text-blue-900 bg-blue-50 rounded px-3 py-2">
            <span className="font-medium">{t('eval_note')}</span>{gap.notes}
          </p>
        )}
      </Section>

      {/* 2. Skills & Qualifications */}
      <Section title={t('eval_section2')}>
        {si ? (
          <>
            <SubList label={t('eval_technical')} items={si.technical} color="blue" />
            <SubList label={t('eval_certifications')} items={si.certifications} color="blue" />
            <SubList label={t('eval_soft_skills')} items={si.soft_skills} />
            <SubList label={t('eval_tools')} items={si.tools} />
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">{t('eval_skills_resout')}</p>
        )}
      </Section>

      {/* 3. Resume Content */}
      <Section title={t('eval_section3')}>
        {ri ? (
          <>
            <SubList label={t('eval_bullet_strength')} items={ri.bullet_strength} />
            {ri.achievements_feedback && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{t('eval_achievements')}</p>
                <p className="text-sm text-gray-700">{ri.achievements_feedback}</p>
              </div>
            )}
            <SubList label={t('eval_metrics')} items={ri.metrics_suggestions} color="yellow" />
            {ri.ats_keywords && ri.ats_keywords.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{t('eval_ats_keywords')}</p>
                <div className="flex flex-wrap gap-1.5">
                  {ri.ats_keywords.map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded text-xs font-mono">{kw}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">{t('eval_resume_resout')}</p>
        )}
      </Section>

      {/* 4. Formatting */}
      <Section title={t('eval_section4')}>
        {fi ? (
          <>
            <SubList label={t('eval_tone')} items={fi.tone_clarity} />
            <SubList label={t('eval_action_verbs')} items={fi.action_verbs} color="yellow" />
            <SubList label={t('eval_layout')} items={fi.layout} />
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">{t('eval_format_resout')}</p>
        )}
      </Section>

      {/* 5. Recommendations */}
      <Section title={t('eval_section5')}>
        {rec ? (
          <>
            {rec.estimated_improvement_pct !== undefined && (
              <p className="text-sm font-medium text-green-700 bg-green-50 rounded px-3 py-2">
                {t('eval_ats_uplift_pre')}{rec.estimated_improvement_pct}{t('eval_ats_uplift_post')}
              </p>
            )}
            <SubList label={t('eval_top5')} items={rec.top_5} color="blue" />
            <SubList label={t('eval_quick_wins')} items={rec.quick_wins} color="green" />
            <SubList label={t('eval_deeper')} items={rec.deeper_improvements} color="yellow" />
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">{t('eval_rec_resout')}</p>
        )}
      </Section>
    </div>
  )
}
