import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Job, TaskStatus } from '../api/client'
import JobCard from '../components/JobCard'

function ProgressBar({ status, progress }: { status: string; progress: string }) {
  const running = status === 'running' || status === 'pending'
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-1">
        {running && (
          <svg className="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
        )}
        <span className="text-sm text-gray-600">{progress}</span>
      </div>
      {running && (
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 rounded-full animate-pulse w-full" />
        </div>
      )}
      {status === 'done' && (
        <div className="h-1.5 bg-green-500 rounded-full" />
      )}
      {status === 'error' && (
        <div className="h-1.5 bg-red-400 rounded-full" />
      )}
    </div>
  )
}

function useTaskPoller(taskId: string | null) {
  const [task, setTask] = useState<TaskStatus | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!taskId) return
    setTask({ status: 'pending', progress: 'Queued' })

    intervalRef.current = setInterval(async () => {
      try {
        const r = await api.get(`/api/tasks/${taskId}`)
        setTask(r.data)
        if (r.data.status === 'done' || r.data.status === 'error') {
          clearInterval(intervalRef.current!)
        }
      } catch {
        clearInterval(intervalRef.current!)
      }
    }, 2000)

    return () => clearInterval(intervalRef.current!)
  }, [taskId])

  return task
}

// ── Seek tab ──────────────────────────────────────────────────────────────────

function SeekTab() {
  const [roles, setRoles] = useState('')
  const [locations, setLocations] = useState('')
  const [maxPerQuery, setMaxPerQuery] = useState(10)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const task = useTaskPoller(taskId)

  async function run() {
    setError('')
    setTaskId(null)
    const roleList = roles.split(',').map((r) => r.trim()).filter(Boolean)
    const locList = locations.split(',').map((l) => l.trim()).filter(Boolean)
    if (!roleList.length) { setError('Enter at least one role.'); return }
    try {
      const r = await api.post('/api/scrapers/seek', {
        roles: roleList,
        locations: locList,
        max_per_query: maxPerQuery,
      })
      setTaskId(r.data.task_id)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to start'
      setError(msg)
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Target Roles <span className="text-gray-400 font-normal">(comma-separated)</span>
          </label>
          <input
            value={roles}
            onChange={(e) => setRoles(e.target.value)}
            placeholder="Python Developer, Backend Engineer"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Locations <span className="text-gray-400 font-normal">(comma-separated)</span>
          </label>
          <input
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
            placeholder="Sydney, Melbourne"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Max per query:</label>
        <input
          type="range"
          min={1}
          max={25}
          value={maxPerQuery}
          onChange={(e) => setMaxPerQuery(Number(e.target.value))}
          className="w-32"
        />
        <span className="text-sm font-medium text-gray-800 w-6">{maxPerQuery}</span>
        <button
          onClick={run}
          disabled={task?.status === 'running' || task?.status === 'pending'}
          className="ml-auto px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {task?.status === 'running' || task?.status === 'pending' ? 'Running…' : '▶ Run Seek Scraper'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {task && <ProgressBar status={task.status} progress={task.progress} />}

      {task?.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">
          {task.error}
        </div>
      )}

      {task?.status === 'done' && task.results && (
        <div>
          <h3 className="font-medium text-gray-700 mb-3">Results ({task.results.length} jobs)</h3>
          <div className="space-y-2">
            {task.results.map((job) => <JobCard key={job.id} job={job as Job} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ── LinkedIn tab ──────────────────────────────────────────────────────────────

function LinkedInTab() {
  const [urlsText, setUrlsText] = useState('')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const task = useTaskPoller(taskId)

  async function run() {
    setError('')
    setTaskId(null)
    const urls = urlsText.split('\n').map((u) => u.trim()).filter(Boolean)
    if (!urls.length) { setError('Enter at least one URL.'); return }
    try {
      const r = await api.post('/api/scrapers/linkedin', { urls })
      setTaskId(r.data.task_id)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to start'
      setError(msg)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          LinkedIn Job URLs <span className="text-gray-400 font-normal">(one per line)</span>
        </label>
        <textarea
          value={urlsText}
          onChange={(e) => setUrlsText(e.target.value)}
          rows={6}
          placeholder="https://www.linkedin.com/jobs/view/123456&#10;https://www.linkedin.com/jobs/view/789012"
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
      </div>

      <div className="flex justify-end">
        <button
          onClick={run}
          disabled={task?.status === 'running' || task?.status === 'pending'}
          className="px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {task?.status === 'running' || task?.status === 'pending' ? 'Running…' : '▶ Run LinkedIn Scraper'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {task && <ProgressBar status={task.status} progress={task.progress} />}

      {task?.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">
          {task.error}
        </div>
      )}

      {task?.status === 'done' && task.results && (
        <div>
          <h3 className="font-medium text-gray-700 mb-3">Results ({task.results.length} jobs)</h3>
          <div className="space-y-2">
            {task.results.map((job) => <JobCard key={job.id} job={job as Job} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Scrapers() {
  const [tab, setTab] = useState<'seek' | 'linkedin'>('seek')

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Scrapers</h1>

      <div className="bg-white rounded-lg shadow">
        {/* Tabs */}
        <div className="flex border-b">
          {(['seek', 'linkedin'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                tab === t
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'seek' ? '🇦🇺 Seek.com.au' : '💼 LinkedIn'}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 'seek' ? <SeekTab /> : <LinkedInTab />}
        </div>
      </div>
    </div>
  )
}
