import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { AdvisorReport, DashboardStats } from '../api/client'

const STAT_CARDS = [
  { key: 'new', label: 'New', color: 'bg-blue-500' },
  { key: 'reviewed', label: 'Reviewed', color: 'bg-purple-500' },
  { key: 'applied', label: 'Applied', color: 'bg-yellow-500' },
  { key: 'interview', label: 'Interview', color: 'bg-green-500' },
  { key: 'offer', label: 'Offer', color: 'bg-emerald-500' },
]

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [followups, setFollowups] = useState<{ application: Record<string, unknown>; job_title: string; company: string }[]>([])
  const [report, setReport] = useState<AdvisorReport | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [reportError, setReportError] = useState('')

  useEffect(() => {
    api.get('/api/dashboard/stats').then((r) => setStats(r.data)).catch(() => {})
    api.get('/api/dashboard/followups').then((r) => setFollowups(r.data)).catch(() => {})
  }, [])

  async function runAdvisor() {
    setLoadingReport(true)
    setReportError('')
    try {
      const r = await api.post('/api/dashboard/advisor')
      setReport(r.data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to generate report'
      setReportError(msg)
    } finally {
      setLoadingReport(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        {STAT_CARDS.map(({ key, label, color }) => (
          <div key={key} className="bg-white rounded-lg shadow p-4 text-center">
            <div className={`text-2xl font-bold text-white ${color} rounded-lg py-2 mb-2`}>
              {stats?.job_counts?.[key] ?? 0}
            </div>
            <p className="text-sm text-gray-600">{label}</p>
          </div>
        ))}
      </div>

      {/* Summary row */}
      {stats && (
        <div className="flex gap-6 mb-8 text-sm text-gray-600">
          <span>Total jobs: <strong className="text-gray-900">{stats.total_jobs}</strong></span>
          <span>Applications: <strong className="text-gray-900">{stats.total_applications}</strong></span>
          <span>Dismissed: <strong className="text-gray-900">{stats.job_counts?.dismissed ?? 0}</strong></span>
          <span>Rejected: <strong className="text-gray-900">{stats.job_counts?.rejected ?? 0}</strong></span>
        </div>
      )}

      {/* Follow-up table */}
      {followups.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-5 py-3 border-b">
            <h2 className="font-semibold text-gray-700">Follow-ups Due</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-5 py-2 text-gray-600 font-medium">Role</th>
                <th className="text-left px-5 py-2 text-gray-600 font-medium">Company</th>
                <th className="text-left px-5 py-2 text-gray-600 font-medium">Follow-up Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {followups.map((f, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-5 py-2">{f.job_title || '—'}</td>
                  <td className="px-5 py-2">{f.company || '—'}</td>
                  <td className="px-5 py-2 text-orange-600">
                    {String(f.application.follow_up_date ?? '—')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Advisor */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-700">AI Advisor Report</h2>
          <button
            onClick={runAdvisor}
            disabled={loadingReport}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {loadingReport ? 'Generating…' : '✨ Generate Report'}
          </button>
        </div>

        {reportError && <p className="text-red-600 text-sm mb-3">{reportError}</p>}

        {report && (
          <div className="space-y-4 text-sm">
            <section>
              <h3 className="font-medium text-gray-800 mb-1">Market Summary</h3>
              <p className="text-gray-600">{report.market_summary}</p>
            </section>
            <section>
              <h3 className="font-medium text-gray-800 mb-1">Skill Gap Analysis</h3>
              <p className="text-gray-600">{report.skill_gap_analysis}</p>
            </section>
            <section>
              <h3 className="font-medium text-gray-800 mb-2">Recommended Actions</h3>
              <ol className="list-decimal list-inside space-y-1 text-gray-600">
                {report.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}
              </ol>
            </section>
            <section className="grid grid-cols-2 gap-4 pt-2 border-t">
              <div>
                <h3 className="font-medium text-gray-800 mb-1">Top Missing Skills</h3>
                <div className="flex flex-wrap gap-1">
                  {report.top_missing_skills.slice(0, 8).map((s) => (
                    <span key={s.skill} className="px-2 py-0.5 bg-red-100 text-red-800 rounded text-xs">
                      {s.skill} ({s.count})
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-medium text-gray-800 mb-1">Your Skills in Demand</h3>
                <div className="flex flex-wrap gap-1">
                  {report.top_present_skills.slice(0, 8).map((s) => (
                    <span key={s.skill} className="px-2 py-0.5 bg-green-100 text-green-800 rounded text-xs">
                      {s.skill} ({s.count})
                    </span>
                  ))}
                </div>
              </div>
            </section>
          </div>
        )}

        {!report && !loadingReport && (
          <p className="text-gray-400 text-sm">Click "Generate Report" to analyse your job market data.</p>
        )}
      </div>
    </div>
  )
}
