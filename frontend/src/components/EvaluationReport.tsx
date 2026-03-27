import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { GapAnalysis } from '../api/client'
import { useT } from '../contexts/LanguageContext'

function Section({ title, defaultOpen = false, children }: {
  title: string; defaultOpen?: boolean; children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-slate-200/60 dark:border-zinc-700/60 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 glass-section hover:opacity-90 text-sm font-semibold text-slate-700 dark:text-slate-200 transition-colors"
      >
        <span>{title}</span>
        {open ? <ChevronUp size={13} className="text-slate-400 dark:text-zinc-500 shrink-0" /> : <ChevronDown size={13} className="text-slate-400 dark:text-zinc-500 shrink-0" />}
      </button>
      {open && <div className="px-4 py-3 space-y-3 bg-white/80 dark:bg-zinc-900/60">{children}</div>}
    </div>
  )
}

function SubList({ label, items, color = 'gray' }: { label: string; items?: string[]; color?: string }) {
  if (!items || items.length === 0) return null
  const dot: Record<string, string> = {
    green:  'text-emerald-500',
    red:    'text-rose-400',
    yellow: 'text-amber-500',
    blue:   'text-sky-500',
    gray:   'text-slate-400 dark:text-zinc-500',
  }
  return (
    <div>
      <p className="text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wide mb-1">{label}</p>
      <ul className="space-y-0.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-slate-700 dark:text-slate-300 flex items-start gap-1.5">
            <span className={`mt-0.5 shrink-0 ${dot[color] ?? dot.gray}`}>•</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

function AtsBar({ pct }: { pct: number }) {
  const t = useT()
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-400' : 'bg-rose-400'
  const textColor = pct >= 70 ? 'text-emerald-700 dark:text-emerald-400' : pct >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2.5 bg-slate-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold ${textColor}`}>{pct}{t('eval_ats_match')}</span>
    </div>
  )
}

export default function EvaluationReport({ gap }: { gap: GapAnalysis }) {
  const t = useT()
  const rec = gap.recommendations
  const si = gap.skills_improvements
  const ri = gap.resume_improvements
  const fi = gap.formatting_improvements

  return (
    <div className="space-y-2">
      <Section title={t('eval_section1')} defaultOpen>
        {gap.ats_pct !== undefined && <AtsBar pct={gap.ats_pct} />}
        <SubList label={t('eval_strong_matches')} items={gap.strong_matches} color="green" />
        <SubList label={t('eval_missing_skills')} items={gap.missing_skills} color="red" />
        <SubList label={t('eval_unmet_reqs')} items={gap.unmet_requirements} color="yellow" />
        {gap.notes && (
          <p className="text-sm text-amber-900 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 rounded px-3 py-2">
            <span className="font-medium">{t('eval_note')}</span>{gap.notes}
          </p>
        )}
      </Section>

      <Section title={t('eval_section2')}>
        {si ? (
          <>
            <SubList label={t('eval_technical')} items={si.technical} color="blue" />
            <SubList label={t('eval_certifications')} items={si.certifications} color="blue" />
            <SubList label={t('eval_soft_skills')} items={si.soft_skills} />
            <SubList label={t('eval_tools')} items={si.tools} />
          </>
        ) : <p className="text-xs text-slate-400 dark:text-zinc-500 italic">{t('eval_skills_resout')}</p>}
      </Section>

      <Section title={t('eval_section3')}>
        {ri ? (
          <>
            <SubList label={t('eval_bullet_strength')} items={ri.bullet_strength} />
            {ri.achievements_feedback && (
              <div>
                <p className="text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wide mb-1">{t('eval_achievements')}</p>
                <p className="text-sm text-slate-700 dark:text-slate-300">{ri.achievements_feedback}</p>
              </div>
            )}
            <SubList label={t('eval_metrics')} items={ri.metrics_suggestions} color="yellow" />
            {ri.ats_keywords && ri.ats_keywords.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 dark:text-zinc-500 uppercase tracking-wide mb-1">{t('eval_ats_keywords')}</p>
                <div className="flex flex-wrap gap-1.5">
                  {ri.ats_keywords.map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-md text-xs font-mono">{kw}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : <p className="text-xs text-slate-400 dark:text-zinc-500 italic">{t('eval_resume_resout')}</p>}
      </Section>

      <Section title={t('eval_section4')}>
        {fi ? (
          <>
            <SubList label={t('eval_tone')} items={fi.tone_clarity} />
            <SubList label={t('eval_action_verbs')} items={fi.action_verbs} color="yellow" />
            <SubList label={t('eval_layout')} items={fi.layout} />
          </>
        ) : <p className="text-xs text-slate-400 dark:text-zinc-500 italic">{t('eval_format_resout')}</p>}
      </Section>

      <Section title={t('eval_section5')}>
        {rec ? (
          <>
            {rec.estimated_improvement_pct !== undefined && (
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 rounded px-3 py-2">
                {t('eval_ats_uplift_pre')}{rec.estimated_improvement_pct}{t('eval_ats_uplift_post')}
              </p>
            )}
            <SubList label={t('eval_top5')} items={rec.top_5} color="blue" />
            <SubList label={t('eval_quick_wins')} items={rec.quick_wins} color="green" />
            <SubList label={t('eval_deeper')} items={rec.deeper_improvements} color="yellow" />
          </>
        ) : <p className="text-xs text-slate-400 dark:text-zinc-500 italic">{t('eval_rec_resout')}</p>}
      </Section>
    </div>
  )
}
