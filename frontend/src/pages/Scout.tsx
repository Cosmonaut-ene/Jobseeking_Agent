import { useState } from 'react'
import { api } from '../api/client'
import type { Job } from '../api/client'
import EvaluationReport from '../components/EvaluationReport'

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-lg font-bold ${pct >= 70 ? 'text-green-700' : pct >= 40 ? 'text-yellow-700' : 'text-red-600'}`}>
        {pct}%
      </span>
    </div>
  )
}

export default function Scout() {
  const [jd, setJd] = useState('')
  const [source, setSource] = useState('manual')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Job | null>(null)

  async function analyze() {
    if (!jd.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.post('/api/jobs/scout', { raw_jd: jd, source })
      setResult(r.data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Analysis failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Scout — Analyse a Job</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Paste Job Description
        </label>
        <textarea
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          rows={10}
          placeholder="Paste the full job description here…"
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-y"
        />

        <div className="flex items-center gap-3 mt-3">
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="manual">Manual</option>
            <option value="seek">Seek</option>
            <option value="linkedin">LinkedIn</option>
            <option value="indeed">Indeed</option>
          </select>
          <button
            onClick={analyze}
            disabled={loading || !jd.trim()}
            className="px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Analysing…' : '🔍 Analyse'}
          </button>
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      {result && (
        <div className="bg-white rounded-lg shadow p-6 space-y-5">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900">{result.title}</h2>
              <p className="text-gray-500 text-sm">{result.company}{result.location ? ` · ${result.location}` : ''}</p>
              {result.salary_range && <p className="text-sm text-gray-500 mt-0.5">{result.salary_range}</p>}
            </div>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
              {result.source}
            </span>
          </div>

          {/* Match score */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Match Score</h3>
            <ScoreBar score={result.match_score} />
          </div>

          {/* Full 5-section evaluation */}
          <EvaluationReport gap={result.gap_analysis} />

          {/* Skills */}
          {result.skills_required.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Required Skills</h3>
              <div className="flex flex-wrap gap-1.5">
                {result.skills_required.map((s) => (
                  <span key={s} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">{s}</span>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-gray-400">Saved to Jobs as: <span className="font-mono">{result.id.slice(0, 8)}</span></p>
        </div>
      )}
    </div>
  )
}
