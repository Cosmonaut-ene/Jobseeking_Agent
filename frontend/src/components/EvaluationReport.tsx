import { useState } from 'react'
import type { GapAnalysis } from '../api/client'

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
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  const textColor = pct >= 70 ? 'text-green-700' : pct >= 40 ? 'text-yellow-700' : 'text-red-600'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold ${textColor}`}>{pct}% ATS match</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function EvaluationReport({ gap }: { gap: GapAnalysis }) {
  const rec = gap.recommendations
  const si = gap.skills_improvements
  const ri = gap.resume_improvements
  const fi = gap.formatting_improvements

  return (
    <div className="space-y-2">
      {/* 1. Match Analysis */}
      <Section title="1. Match Analysis" defaultOpen>
        {gap.ats_pct !== undefined && <AtsBar pct={gap.ats_pct} />}
        <SubList label="Strong Matches" items={gap.strong_matches} color="green" />
        <SubList label="Missing Skills" items={gap.missing_skills} color="red" />
        <SubList label="Unmet Requirements" items={gap.unmet_requirements} color="yellow" />
        {gap.notes && (
          <p className="text-sm text-blue-900 bg-blue-50 rounded px-3 py-2">
            <span className="font-medium">Note: </span>{gap.notes}
          </p>
        )}
      </Section>

      {/* 2. Skills & Qualifications */}
      <Section title="2. Skills & Qualification Improvements">
        {si ? (
          <>
            <SubList label="Technical Skills to Learn" items={si.technical} color="blue" />
            <SubList label="Certifications" items={si.certifications} color="blue" />
            <SubList label="Soft Skills" items={si.soft_skills} />
            <SubList label="Tools & Platforms" items={si.tools} />
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">Re-scout this job to see skill improvement suggestions.</p>
        )}
      </Section>

      {/* 3. Resume Content */}
      <Section title="3. Resume Content Improvements">
        {ri ? (
          <>
            <SubList label="Bullet Strength Tips" items={ri.bullet_strength} />
            {ri.achievements_feedback && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Achievements Feedback</p>
                <p className="text-sm text-gray-700">{ri.achievements_feedback}</p>
              </div>
            )}
            <SubList label="Add Metrics / Numbers" items={ri.metrics_suggestions} color="yellow" />
            {ri.ats_keywords && ri.ats_keywords.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Missing ATS Keywords</p>
                <div className="flex flex-wrap gap-1.5">
                  {ri.ats_keywords.map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded text-xs font-mono">{kw}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">Re-scout this job to see resume content suggestions.</p>
        )}
      </Section>

      {/* 4. Formatting */}
      <Section title="4. Flow, Grammar & Formatting">
        {fi ? (
          <>
            <SubList label="Tone & Clarity" items={fi.tone_clarity} />
            <SubList label="Action Verb Upgrades" items={fi.action_verbs} color="yellow" />
            <SubList label="Layout Suggestions" items={fi.layout} />
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">Re-scout this job to see formatting suggestions.</p>
        )}
      </Section>

      {/* 5. Recommendations */}
      <Section title="5. Overall Recommendations">
        {rec ? (
          <>
            {rec.estimated_improvement_pct !== undefined && (
              <p className="text-sm font-medium text-green-700 bg-green-50 rounded px-3 py-2">
                Estimated ATS score uplift if top recommendations implemented: +{rec.estimated_improvement_pct}%
              </p>
            )}
            <SubList label="Top 5 Priority Actions" items={rec.top_5} color="blue" />
            <SubList label="Quick Wins (under 1 hour)" items={rec.quick_wins} color="green" />
            <SubList label="Deeper Improvements (1–4 weeks)" items={rec.deeper_improvements} color="yellow" />
          </>
        ) : (
          <p className="text-xs text-gray-400 italic">Re-scout this job to see prioritised recommendations.</p>
        )}
      </Section>
    </div>
  )
}
