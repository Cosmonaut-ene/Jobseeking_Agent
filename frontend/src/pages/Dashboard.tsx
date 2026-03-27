import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { AdvisorReport, DashboardStats } from '../api/client'
import { useT } from '../contexts/LanguageContext'

export default function Dashboard() {
  const navigate = useNavigate()
  const t = useT()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [followups, setFollowups] = useState<{ application: Record<string, unknown>; job: Record<string, string> | null; overdue_days: number }[]>([])
  const [report, setReport] = useState<AdvisorReport | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [reportError, setReportError] = useState('')

  const STAT_CARDS = [
    { key: 'new',       label: t('stat_new'),       accent: 'bg-sky-500' },
    { key: 'reviewed',  label: t('stat_reviewed'),  accent: 'bg-violet-500' },
    { key: 'applied',   label: t('stat_applied'),   accent: 'bg-amber-500' },
    { key: 'interview', label: t('stat_interview'), accent: 'bg-emerald-500' },
    { key: 'offer',     label: t('stat_offer'),     accent: 'bg-teal-500' },
  ]

  useEffect(() => {
    api.get('/api/dashboard/stats').then(r => setStats(r.data)).catch(() => {})
    api.get('/api/dashboard/followups').then(r => setFollowups(r.data)).catch(() => {})
  }, [])

  async function runAdvisor() {
    setLoadingReport(true)
    setReportError('')
    try {
      const r = await api.get('/api/dashboard/advisor')
      setReport(r.data)
    } catch (e: unknown) {
      setReportError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to generate report')
    } finally {
      setLoadingReport(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('dashboard_title')}</h1>
        <button
          onClick={() => navigate('/notifications')}
          className="inline-flex items-center gap-1.5 bg-amber-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors shadow-sm"
        >
          <Play size={13} />
          {t('dashboard_trigger_btn')}
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-3 mb-8">
        {STAT_CARDS.map(({ key, label, accent }) => (
          <div key={key} className="glass-card p-4 text-center">
            <div className={`text-2xl font-bold text-white ${accent} rounded-lg py-2 mb-2`}>
              {stats?.by_status?.[key] ?? 0}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{label}</p>
          </div>
        ))}
      </div>

      {/* Summary row */}
      {stats && (
        <div className="flex flex-wrap gap-6 mb-8 text-sm text-slate-500 dark:text-slate-400">
          <span>{t('total_jobs')} <strong className="text-slate-800 dark:text-slate-200">{stats.total_jobs}</strong></span>
          <span>{t('dismissed')} <strong className="text-slate-800 dark:text-slate-200">{stats.by_status?.dismissed ?? 0}</strong></span>
          <span>{t('rejected')} <strong className="text-slate-800 dark:text-slate-200">{stats.by_status?.rejected ?? 0}</strong></span>
          {stats.high_score_count !== undefined && (
            <span>{t('high_score_label')} <strong className="text-emerald-700 dark:text-emerald-400">{stats.high_score_count}</strong></span>
          )}
          {stats.mid_score_count !== undefined && (
            <span>{t('mid_score_label')} <strong className="text-amber-700 dark:text-amber-400">{stats.mid_score_count}</strong></span>
          )}
        </div>
      )}

      {/* Follow-up table */}
      {followups.length > 0 && (
        <div className="glass-card mb-8 overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200/60 dark:border-white/[0.07] glass-section">
            <h2 className="font-semibold text-slate-700 dark:text-slate-200">{t('followups_title')}</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="glass-section">
              <tr>
                <th className="text-left px-5 py-2 text-slate-500 dark:text-slate-400 font-medium">{t('col_role')}</th>
                <th className="text-left px-5 py-2 text-slate-500 dark:text-slate-400 font-medium">{t('col_company')}</th>
                <th className="text-left px-5 py-2 text-slate-500 dark:text-slate-400 font-medium">{t('col_followup_date')}</th>
              </tr>
            </thead>
            <tbody className="divide-theme">
              {followups.map((f, i) => (
                <tr key={i} className="hover:bg-amber-50/40 dark:hover:bg-amber-900/10 transition-colors">
                  <td className="px-5 py-2 text-slate-700 dark:text-slate-300">{(f.job as Record<string, string> | null)?.title || '—'}</td>
                  <td className="px-5 py-2 text-slate-600 dark:text-slate-400">{(f.job as Record<string, string> | null)?.company || '—'}</td>
                  <td className="px-5 py-2 text-amber-600 dark:text-amber-400 font-medium">{String(f.application.follow_up_date ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Advisor */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-700 dark:text-slate-200">{t('advisor_title')}</h2>
          <button
            onClick={runAdvisor}
            disabled={loadingReport}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600 disabled:opacity-50 transition-colors shadow-sm"
          >
            <Sparkles size={13} />
            {loadingReport ? t('advisor_generating') : t('advisor_generate_btn')}
          </button>
        </div>

        {reportError && <p className="text-rose-600 dark:text-rose-400 text-sm mb-3">{reportError}</p>}

        {report && (
          <div className="space-y-4 text-sm">
            <section>
              <h3 className="font-medium text-slate-800 dark:text-slate-200 mb-1">{t('advisor_market_summary')}</h3>
              <p className="text-slate-600 dark:text-slate-400">{report.market_summary}</p>
            </section>
            <section>
              <h3 className="font-medium text-slate-800 dark:text-slate-200 mb-1">{t('advisor_skill_gap')}</h3>
              <p className="text-slate-600 dark:text-slate-400">{report.skill_gap_analysis}</p>
            </section>
            <section>
              <h3 className="font-medium text-slate-800 dark:text-slate-200 mb-2">{t('advisor_recommended')}</h3>
              <ol className="list-decimal list-inside space-y-1 text-slate-600 dark:text-slate-400">
                {report.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}
              </ol>
            </section>
            <section className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-200/60 dark:border-white/[0.07]">
              <div>
                <h3 className="font-medium text-slate-800 dark:text-slate-200 mb-1">{t('advisor_missing_skills')}</h3>
                <div className="flex flex-wrap gap-1">
                  {report.top_missing_skills.slice(0, 8).map(s => (
                    <span key={s.skill} className="px-2 py-0.5 bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 rounded-md text-xs">
                      {s.skill} ({s.count})
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-medium text-slate-800 dark:text-slate-200 mb-1">{t('advisor_present_skills')}</h3>
                <div className="flex flex-wrap gap-1">
                  {report.top_present_skills.slice(0, 8).map(s => (
                    <span key={s.skill} className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded-md text-xs">
                      {s.skill} ({s.count})
                    </span>
                  ))}
                </div>
              </div>
            </section>
          </div>
        )}

        {!report && !loadingReport && (
          <p className="text-slate-400 dark:text-zinc-500 text-sm">{t('advisor_placeholder')}</p>
        )}
      </div>
    </div>
  )
}
