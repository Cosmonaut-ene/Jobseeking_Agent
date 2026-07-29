import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useT } from '../contexts/LanguageContext'

// ── Types (mirror backend/app/routers/analytics.py response shapes) ────────────

interface FunnelRow {
  source: string
  new: number; reviewed: number; dismissed: number; applied: number
  interview: number; rejected: number; offer: number; total: number
}
interface SkillGap { skill: string; count: number }
interface ScoreDistribution {
  histogram: { bucket_start: number; count: number }[]
  by_source: { source: string; count: number; avg_score: number; min_score: number; max_score: number }[]
}
interface DiscoveryTrendPoint { day: string; jobs_found: number; moving_avg_7d: number }
interface ConversionRow { score_bucket: string; total_jobs: number; applications: number; conversion_pct: number }
interface TopCompany { company: string; industry: string; job_count: number; avg_match_score: number }

// ── Data hook ────────────────────────────────────────────────────────────────

function useAnalytics<T>(endpoint: string) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.get(endpoint)
      .then(r => { if (!cancelled) { setData(r.data); setError(null) } })
      .catch((e: unknown) => {
        if (cancelled) return
        const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setError(detail ?? 'Failed to load')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [endpoint])

  return { data, loading, error }
}

// ── Shared card shell (loading / error / empty / content) ──────────────────────

function AnalyticsCard({ title, loading, error, empty, children }: {
  title: string; loading: boolean; error: string | null; empty: boolean; children: React.ReactNode
}) {
  const t = useT()
  return (
    <div className="glass-card p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-zinc-400 mb-3">{title}</h2>
      {loading && <p className="text-sm text-slate-400 dark:text-zinc-500">{t('analytics_loading')}</p>}
      {!loading && error && (
        <p className="text-sm text-amber-600 dark:text-amber-400">{error}</p>
      )}
      {!loading && !error && empty && (
        <p className="text-sm text-slate-400 dark:text-zinc-500">{t('analytics_no_data')}</p>
      )}
      {!loading && !error && !empty && children}
    </div>
  )
}

function BarRow({ label, value, max, format }: {
  label: string; value: number; max: number; format?: (v: number) => string
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
        <span className="truncate pr-2">{label}</span>
        <span className="font-medium text-slate-800 dark:text-slate-200 shrink-0">{format ? format(value) : value}</span>
      </div>
      <div className="h-2 bg-slate-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div className="h-full bg-amber-400 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Sparkline({ points }: { points: number[] }) {
  if (points.length === 0) return null
  const height = 48
  const width = 100
  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1
  const stepX = width / Math.max(points.length - 1, 1)
  const coords = points
    .map((p, i) => `${(i * stepX).toFixed(2)},${(height - ((p - min) / range) * height).toFixed(2)}`)
    .join(' ')
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="w-full text-amber-500" style={{ height }}>
      <polyline points={coords} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Analytics() {
  const t = useT()

  const funnel = useAnalytics<FunnelRow[]>('/api/analytics/funnel')
  const skillGaps = useAnalytics<SkillGap[]>('/api/analytics/skill-gaps')
  const scoreDist = useAnalytics<ScoreDistribution>('/api/analytics/score-distribution')
  const trend = useAnalytics<DiscoveryTrendPoint[]>('/api/analytics/discovery-trend')
  const conversion = useAnalytics<ConversionRow[]>('/api/analytics/conversion')
  const topCompanies = useAnalytics<TopCompany[]>('/api/analytics/top-companies')

  const maxSkillCount = Math.max(1, ...(skillGaps.data ?? []).map(s => s.count))
  const maxHistBucket = Math.max(1, ...(scoreDist.data?.histogram ?? []).map(b => b.count))
  const maxConversionPct = Math.max(1, ...(conversion.data ?? []).map(c => c.conversion_pct))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('analytics_title')}</h1>
        <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">{t('analytics_synthetic_notice')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 1. Funnel */}
        <AnalyticsCard
          title={t('analytics_funnel_title')}
          loading={funnel.loading} error={funnel.error} empty={!funnel.data?.length}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-500 dark:text-slate-400">
                  <th className="text-left pb-1.5 pr-2">{t('analytics_col_source')}</th>
                  <th className="text-right pb-1.5 px-1.5">{t('analytics_col_new')}</th>
                  <th className="text-right pb-1.5 px-1.5">{t('analytics_col_reviewed')}</th>
                  <th className="text-right pb-1.5 px-1.5">{t('analytics_col_applied')}</th>
                  <th className="text-right pb-1.5 px-1.5">{t('analytics_col_interview')}</th>
                  <th className="text-right pb-1.5 px-1.5">{t('analytics_col_offer')}</th>
                  <th className="text-right pb-1.5 pl-1.5 font-semibold">{t('analytics_col_total')}</th>
                </tr>
              </thead>
              <tbody className="divide-theme">
                {funnel.data?.map(row => (
                  <tr key={row.source} className="text-slate-700 dark:text-slate-300">
                    <td className="py-1 pr-2 font-medium">{row.source}</td>
                    <td className="text-right px-1.5">{row.new}</td>
                    <td className="text-right px-1.5">{row.reviewed}</td>
                    <td className="text-right px-1.5">{row.applied}</td>
                    <td className="text-right px-1.5">{row.interview}</td>
                    <td className="text-right px-1.5">{row.offer}</td>
                    <td className="text-right pl-1.5 font-semibold">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AnalyticsCard>

        {/* 2. Skill gaps */}
        <AnalyticsCard
          title={t('analytics_skill_gaps_title')}
          loading={skillGaps.loading} error={skillGaps.error} empty={!skillGaps.data?.length}
        >
          <div className="space-y-2">
            {skillGaps.data?.map(s => (
              <BarRow key={s.skill} label={s.skill} value={s.count} max={maxSkillCount} />
            ))}
          </div>
        </AnalyticsCard>

        {/* 3. Score distribution */}
        <AnalyticsCard
          title={t('analytics_score_distribution_title')}
          loading={scoreDist.loading} error={scoreDist.error} empty={!scoreDist.data?.histogram?.length}
        >
          <div className="space-y-2">
            {scoreDist.data?.histogram.map(b => (
              <BarRow
                key={b.bucket_start}
                label={`${b.bucket_start}-${b.bucket_start + 9}%`}
                value={b.count}
                max={maxHistBucket}
              />
            ))}
          </div>
          {!!scoreDist.data?.by_source?.length && (
            <table className="w-full text-xs mt-4 pt-3 border-t border-slate-200/60 dark:border-white/[0.07]">
              <thead>
                <tr className="text-slate-500 dark:text-slate-400">
                  <th className="text-left pb-1">{t('analytics_col_source')}</th>
                  <th className="text-right pb-1">{t('analytics_col_avg_score')}</th>
                  <th className="text-right pb-1">{t('analytics_col_total')}</th>
                </tr>
              </thead>
              <tbody className="divide-theme">
                {scoreDist.data.by_source.map(s => (
                  <tr key={s.source} className="text-slate-700 dark:text-slate-300">
                    <td className="py-0.5">{s.source}</td>
                    <td className="text-right">{Math.round(s.avg_score * 100)}%</td>
                    <td className="text-right">{s.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AnalyticsCard>

        {/* 4. Discovery trend + 7d moving average */}
        <AnalyticsCard
          title={t('analytics_discovery_trend_title')}
          loading={trend.loading} error={trend.error} empty={!trend.data?.length}
        >
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{t('analytics_moving_avg_label')}</p>
          <Sparkline points={(trend.data ?? []).map(p => p.moving_avg_7d)} />
          {!!trend.data?.length && (
            <p className="text-xs text-slate-400 dark:text-zinc-500 mt-2">
              {trend.data[0].day} → {trend.data[trend.data.length - 1].day}
            </p>
          )}
        </AnalyticsCard>

        {/* 5. Conversion by score bucket */}
        <AnalyticsCard
          title={t('analytics_conversion_title')}
          loading={conversion.loading} error={conversion.error} empty={!conversion.data?.length}
        >
          <div className="space-y-2">
            {conversion.data?.map(c => (
              <BarRow
                key={c.score_bucket}
                label={`${c.score_bucket} (${c.applications}/${c.total_jobs})`}
                value={c.conversion_pct}
                max={maxConversionPct}
                format={v => `${v}%`}
              />
            ))}
          </div>
        </AnalyticsCard>

        {/* 6. Top companies */}
        <AnalyticsCard
          title={t('analytics_top_companies_title')}
          loading={topCompanies.loading} error={topCompanies.error} empty={!topCompanies.data?.length}
        >
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 dark:text-slate-400">
                <th className="text-left pb-1.5">{t('analytics_col_company')}</th>
                <th className="text-left pb-1.5">{t('analytics_col_industry')}</th>
                <th className="text-right pb-1.5">{t('analytics_col_job_count')}</th>
                <th className="text-right pb-1.5">{t('analytics_col_avg_score')}</th>
              </tr>
            </thead>
            <tbody className="divide-theme">
              {topCompanies.data?.map(c => (
                <tr key={c.company} className="text-slate-700 dark:text-slate-300">
                  <td className="py-1 truncate max-w-[10rem]">{c.company}</td>
                  <td className="py-1 text-slate-500 dark:text-slate-400">{c.industry}</td>
                  <td className="py-1 text-right">{c.job_count}</td>
                  <td className="py-1 text-right">{Math.round(c.avg_match_score * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </AnalyticsCard>
      </div>
    </div>
  )
}
