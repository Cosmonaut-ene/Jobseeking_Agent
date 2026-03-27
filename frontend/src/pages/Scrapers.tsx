import { useState, useEffect } from 'react'
import { Search, Play, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import type { Job } from '../api/client'
import EvaluationReport from '../components/EvaluationReport'
import { useT } from '../contexts/LanguageContext'

interface TaskState {
  status: string
  progress: string
  results?: any[]
  error?: string
}

// Module-level scraper inputs — persists across page navigation
const _inputs = {
  seekRoles: null as string | null,   // null = not yet loaded from profile
  seekLoc:   null as string | null,
  seekMax:   10,
  liKeywords: null as string | null,
  liLoc:      null as string | null,
  liMax:      25,
}

// Module-level store: polling lives outside React, survives component unmount/remount
const store = new Map<string, {
  intervalId: ReturnType<typeof setInterval>
  state: TaskState
  listeners: Set<(s: TaskState) => void>
}>()

function ensurePolling(storageKey: string, taskId: string) {
  if (store.has(storageKey)) return
  const entry = {
    intervalId: null as any,
    state: { status: 'running', progress: '...' } as TaskState,
    listeners: new Set<(s: TaskState) => void>(),
  }
  store.set(storageKey, entry)
  entry.intervalId = setInterval(async () => {
    try {
      const r = await api.get(`/api/tasks/${taskId}`)
      entry.state = r.data
      entry.listeners.forEach(fn => fn(r.data))
      if (r.data.status === 'done' || r.data.status === 'error' || r.data.status === 'cancelled') {
        clearInterval(entry.intervalId)
        store.delete(storageKey)
        sessionStorage.removeItem(storageKey)
      }
    } catch (err: any) {
      if (err?.response?.status === 404) {
        clearInterval(entry.intervalId)
        store.delete(storageKey)
        sessionStorage.removeItem(storageKey)
        const gone: TaskState = { status: 'error', progress: '__task_lost__' }
        entry.listeners.forEach(fn => fn(gone))
      }
    }
  }, 2000)
}

function stopPolling(storageKey: string) {
  const entry = store.get(storageKey)
  if (entry) {
    clearInterval(entry.intervalId)
    store.delete(storageKey)
  }
  sessionStorage.removeItem(storageKey)
}

function usePersistentTask(storageKey: string) {
  const [task, setTask] = useState<TaskState | null>(
    () => store.get(storageKey)?.state ?? null
  )

  useEffect(() => {
    const savedId = sessionStorage.getItem(storageKey)
    if (savedId && !store.has(storageKey)) {
      ensurePolling(storageKey, savedId)
    }
    const entry = store.get(storageKey)
    if (!entry) return
    setTask(entry.state)
    const listener = (s: TaskState) => setTask(s)
    entry.listeners.add(listener)
    return () => { entry.listeners.delete(listener) }
  }, [storageKey])

  const startTask = (taskId: string) => {
    sessionStorage.setItem(storageKey, taskId)
    ensurePolling(storageKey, taskId)
    setTask({ status: 'running', progress: '...' })
  }

  const cancelTask = async () => {
    const taskId = sessionStorage.getItem(storageKey)
    if (taskId) {
      try { await api.delete(`/api/tasks/${taskId}`) } catch {}
    }
    stopPolling(storageKey)
    setTask(null)
  }

  return { task, startTask, cancelTask }
}

function TaskStatus({ task, onCancel }: { task: TaskState | null; onCancel: () => void }) {
  const t = useT()
  if (!task) return null
  const isActive = task.status !== 'done' && task.status !== 'error'
  const progressText = task.progress === '__task_lost__' ? t('scrapers_task_lost') : task.progress
  return (
    <div className="mt-4 p-4 bg-slate-50/70 dark:bg-zinc-800/50 rounded-xl border border-slate-200/60 dark:border-zinc-700/60">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-md text-xs font-medium ${
            task.status === 'done'  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' :
            task.status === 'error' ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' :
                                      'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
          }`}>{task.status}</span>
          <span className="text-sm text-slate-600 dark:text-slate-300">{progressText}</span>
        </div>
        {isActive && (
          <button
            onClick={onCancel}
            className="text-xs px-2 py-1 rounded-md border border-rose-300 dark:border-rose-500/50 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
          >
            {t('scrapers_cancel')}
          </button>
        )}
      </div>
      {task.results && (
        <p className="text-sm text-emerald-700 dark:text-emerald-400 font-medium mt-2">{task.results.length} {t('scrapers_jobs_saved')}</p>
      )}
      {task.error && <p className="text-sm text-rose-600 dark:text-rose-400 mt-2">{task.error}</p>}
    </div>
  )
}

export default function Scrapers() {
  const t = useT()

  // Manual paste scout
  const [jd, setJd] = useState('')
  const [jdSource, setJdSource] = useState('manual')
  const [jdLoading, setJdLoading] = useState(false)
  const [jdError, setJdError] = useState('')
  const [jdResult, setJdResult] = useState<Job | null>(null)

  async function analyzeJd() {
    if (!jd.trim()) return
    setJdLoading(true)
    setJdError('')
    setJdResult(null)
    try {
      const r = await api.post('/api/jobs/scout', { raw_jd: jd, source: jdSource, auto_filter: false })
      setJdResult(r.data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t('scrapers_analysis_failed')
      setJdError(msg)
    } finally {
      setJdLoading(false)
    }
  }

  // Seek — initialise from module-level cache (persists across navigation)
  const [seekRoles, _setSeekRoles] = useState(_inputs.seekRoles ?? '')
  const [seekLoc,   _setSeekLoc]   = useState(_inputs.seekLoc   ?? '')
  const [seekMax,   _setSeekMax]   = useState(_inputs.seekMax)
  const setSeekRoles = (v: string)  => { _inputs.seekRoles = v; _setSeekRoles(v) }
  const setSeekLoc   = (v: string)  => { _inputs.seekLoc   = v; _setSeekLoc(v) }
  const setSeekMax   = (v: number)  => { _inputs.seekMax   = v; _setSeekMax(v) }
  const { task: seekTask, startTask: startSeekTask, cancelTask: cancelSeek } = usePersistentTask('scraper_seek_task')

  // LinkedIn — same pattern
  const [rssKeywords, _setRssKeywords] = useState(_inputs.liKeywords ?? '')
  const [rssLoc,      _setRssLoc]      = useState(_inputs.liLoc      ?? '')
  const [rssMax,      _setRssMax]      = useState(_inputs.liMax)
  const setRssKeywords = (v: string) => { _inputs.liKeywords = v; _setRssKeywords(v) }
  const setRssLoc      = (v: string) => { _inputs.liLoc      = v; _setRssLoc(v) }
  const setRssMax      = (v: number) => { _inputs.liMax      = v; _setRssMax(v) }
  const { task: rssTask, startTask: startRssTask, cancelTask: cancelRss } = usePersistentTask('scraper_rss_task')

  // Load profile defaults once (only when _inputs hasn't been populated yet)
  useEffect(() => {
    if (_inputs.seekRoles !== null) return
    api.get('/api/profile').then(r => {
      const roles = (r.data.target_roles as string[] | undefined)?.join(', ') ?? ''
      const loc   = (r.data.preferences?.locations as string[] | undefined)?.[0] ?? ''
      setSeekRoles(roles)
      setSeekLoc(loc)
      setRssKeywords(roles)
      setRssLoc(loc)
    }).catch(() => {
      _inputs.seekRoles = ''
    })
  }, [])

  const startSeek = async () => {
    const r = await api.post('/api/scrapers/seek', {
      roles: seekRoles.split(',').map(s => s.trim()).filter(Boolean),
      locations: [seekLoc],
      max_per_query: seekMax
    })
    startSeekTask(r.data.task_id)
  }

  const startLinkedIn = async () => {
    const r = await api.post('/api/scrapers/linkedin', {
      keywords: rssKeywords.split(',').map(s => s.trim()).filter(Boolean),
      location: rssLoc,
      max_results: rssMax
    })
    startRssTask(r.data.task_id)
  }

  const inputCls = 'w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 backdrop-blur-sm rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400'
  const btnCls = 'bg-amber-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors shadow-sm'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('scrapers_title')}</h1>

      {/* Manual paste */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-1">{t('scrapers_manual_title')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{t('scrapers_manual_desc')}</p>
        <textarea
          value={jd}
          onChange={e => setJd(e.target.value)}
          rows={8}
          placeholder={t('scrapers_manual_placeholder')}
          className="w-full border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 backdrop-blur-sm rounded-lg px-3 py-2 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 mb-3"
        />
        <div className="flex items-center gap-3">
          <select
            value={jdSource}
            onChange={e => setJdSource(e.target.value)}
            className="border border-slate-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-800/80 text-slate-900 dark:text-slate-100 backdrop-blur-sm rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
          >
            <option value="manual">Manual</option>
            <option value="seek">Seek</option>
            <option value="linkedin">LinkedIn</option>
            <option value="indeed">Indeed</option>
          </select>
          <button
            onClick={analyzeJd}
            disabled={jdLoading || !jd.trim()}
            className={`inline-flex items-center gap-1.5 ${btnCls}`}
          >
            {jdLoading ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
            {jdLoading ? t('scrapers_analysing') : t('scrapers_analyse_btn')}
          </button>
        </div>
        {jdError && <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{jdError}</p>}
        {jdResult && (
          <div className="mt-5 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-slate-900 dark:text-slate-100">{jdResult.title}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">{jdResult.company}{jdResult.location ? ` · ${jdResult.location}` : ''}</p>
              </div>
              <span className={`text-sm font-bold ${jdResult.match_score >= 0.7 ? 'text-emerald-700 dark:text-emerald-400' : jdResult.match_score >= 0.4 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'}`}>
                {Math.round(jdResult.match_score * 100)}%
              </span>
            </div>
            <EvaluationReport gap={jdResult.gap_analysis} />
            <p className="text-xs text-slate-400 dark:text-zinc-500">{t('scrapers_saved_to_jobs')}<span className="font-mono">{jdResult.id.slice(0, 8)}</span></p>
          </div>
        )}
      </div>

      {/* Seek */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4">Seek.com.au</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('scrapers_job_keywords')}</label>
            <input className={inputCls} value={seekRoles} onChange={e => setSeekRoles(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('scrapers_location')}</label>
            <input className={inputCls} value={seekLoc} onChange={e => setSeekLoc(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('scrapers_max_results')}</label>
            <input className={inputCls} type="number" value={seekMax} onChange={e => setSeekMax(Number(e.target.value))} />
          </div>
        </div>
        <button className={`inline-flex items-center gap-1.5 ${btnCls}`} onClick={startSeek} disabled={seekTask?.status === 'running'}>
          {seekTask?.status === 'running' ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          {seekTask?.status === 'running' ? t('scrapers_seek_scraping') : t('scrapers_seek_start')}
        </button>
        <TaskStatus task={seekTask} onCancel={cancelSeek} />
      </div>

      {/* LinkedIn */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-2">{t('scrapers_linkedin_title')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{t('scrapers_linkedin_desc')}</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('scrapers_keywords')}</label>
            <input className={inputCls} value={rssKeywords} onChange={e => setRssKeywords(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('scrapers_location')}</label>
            <input className={inputCls} value={rssLoc} onChange={e => setRssLoc(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('scrapers_max_results')}</label>
            <input className={inputCls} type="number" value={rssMax} onChange={e => setRssMax(Number(e.target.value))} />
          </div>
        </div>
        <button className={`inline-flex items-center gap-1.5 ${btnCls}`} onClick={startLinkedIn} disabled={rssTask?.status === 'running'}>
          {rssTask?.status === 'running' ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          {rssTask?.status === 'running' ? t('scrapers_seek_scraping') : t('scrapers_linkedin_search')}
        </button>
        <TaskStatus task={rssTask} onCancel={cancelRss} />
      </div>
    </div>
  )
}
