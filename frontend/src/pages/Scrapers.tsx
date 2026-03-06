import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface TaskState {
  status: string
  progress: string
  results?: any[]
  error?: string
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
    state: { status: 'running', progress: '运行中...' } as TaskState,
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
      // 404 = task gone (server restarted); stop polling and clear stale state
      if (err?.response?.status === 404) {
        clearInterval(entry.intervalId)
        store.delete(storageKey)
        sessionStorage.removeItem(storageKey)
        const gone: TaskState = { status: 'error', progress: '任务已丢失（服务器已重启），请重新发起。' }
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
    // Resume polling from sessionStorage if page was refreshed
    const savedId = sessionStorage.getItem(storageKey)
    if (savedId && !store.has(storageKey)) {
      ensurePolling(storageKey, savedId)
    }
    // Subscribe to ongoing polling updates
    const entry = store.get(storageKey)
    if (!entry) return
    setTask(entry.state)
    const listener = (s: TaskState) => setTask(s)
    entry.listeners.add(listener)
    return () => { entry.listeners.delete(listener) }  // unsubscribe only, polling keeps running
  }, [storageKey])

  const startTask = (taskId: string) => {
    sessionStorage.setItem(storageKey, taskId)
    ensurePolling(storageKey, taskId)
    setTask({ status: 'running', progress: '运行中...' })
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
  if (!task) return null
  const isActive = task.status !== 'done' && task.status !== 'error'
  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            task.status === 'done'  ? 'bg-green-100 text-green-700' :
            task.status === 'error' ? 'bg-red-100 text-red-700' :
                                      'bg-blue-100 text-blue-700'
          }`}>{task.status}</span>
          <span className="text-sm text-gray-600">{task.progress}</span>
        </div>
        {isActive && (
          <button
            onClick={onCancel}
            className="text-xs px-2 py-1 rounded border border-red-300 text-red-600 hover:bg-red-50"
          >
            取消
          </button>
        )}
      </div>
      {task.results && (
        <p className="text-sm text-green-700 font-medium mt-2">{task.results.length} jobs saved</p>
      )}
      {task.error && <p className="text-sm text-red-600 mt-2">{task.error}</p>}
    </div>
  )
}

export default function Scrapers() {
  // Seek
  const [seekRoles, setSeekRoles] = useState('Data Scientist, ML Engineer')
  const [seekLoc, setSeekLoc] = useState('Sydney NSW')
  const [seekMax, setSeekMax] = useState(10)
  const { task: seekTask, startTask: startSeekTask, cancelTask: cancelSeek } = usePersistentTask('scraper_seek_task')

  // Indeed
  const [indeedRoles, setIndeedRoles] = useState('Data Scientist, ML Engineer')
  const [indeedLoc, setIndeedLoc] = useState('Sydney NSW')
  const [indeedMax, setIndeedMax] = useState(10)
  const { task: indeedTask, startTask: startIndeedTask, cancelTask: cancelIndeed } = usePersistentTask('scraper_indeed_task')

  // LinkedIn
  const [rssKeywords, setRssKeywords] = useState('Data Scientist, Machine Learning Engineer')
  const [rssLoc, setRssLoc] = useState('Sydney, New South Wales, Australia')
  const [rssMax, setRssMax] = useState(25)
  const { task: rssTask, startTask: startRssTask, cancelTask: cancelRss } = usePersistentTask('scraper_rss_task')

  const startSeek = async () => {
    const r = await api.post('/api/scrapers/seek', {
      roles: seekRoles.split(',').map(s => s.trim()).filter(Boolean),
      locations: [seekLoc],
      max_per_query: seekMax
    })
    startSeekTask(r.data.task_id)
  }

  const startIndeed = async () => {
    const r = await api.post('/api/scrapers/indeed', {
      roles: indeedRoles.split(',').map(s => s.trim()).filter(Boolean),
      locations: [indeedLoc],
      max_per_query: indeedMax
    })
    startIndeedTask(r.data.task_id)
  }

  const startLinkedInRss = async () => {
    const r = await api.post('/api/scrapers/linkedin-rss', {
      keywords: rssKeywords.split(',').map(s => s.trim()).filter(Boolean),
      location: rssLoc,
      max_results: rssMax
    })
    startRssTask(r.data.task_id)
  }

  const inputCls = 'w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400'
  const btnCls = 'bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">爬虫控制台</h1>

      {/* Seek */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Seek.com.au</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">职位关键词 (逗号分隔)</label>
            <input className={inputCls} value={seekRoles} onChange={e => setSeekRoles(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">地点</label>
            <input className={inputCls} value={seekLoc} onChange={e => setSeekLoc(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">最大数量</label>
            <input className={inputCls} type="number" value={seekMax} onChange={e => setSeekMax(Number(e.target.value))} />
          </div>
        </div>
        <button className={btnCls} onClick={startSeek} disabled={seekTask?.status === 'running'}>
          {seekTask?.status === 'running' ? '⏳ 爬取中...' : '🚀 开始爬取'}
        </button>
        <TaskStatus task={seekTask} onCancel={cancelSeek} />
      </div>

      {/* Indeed */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Indeed.com</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">职位关键词 (逗号分隔)</label>
            <input className={inputCls} value={indeedRoles} onChange={e => setIndeedRoles(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">地点</label>
            <input className={inputCls} value={indeedLoc} onChange={e => setIndeedLoc(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">最大数量</label>
            <input className={inputCls} type="number" value={indeedMax} onChange={e => setIndeedMax(Number(e.target.value))} />
          </div>
        </div>
        <button className={btnCls} onClick={startIndeed} disabled={indeedTask?.status === 'running'}>
          {indeedTask?.status === 'running' ? '⏳ 爬取中...' : '🚀 开始爬取'}
        </button>
        <TaskStatus task={indeedTask} onCancel={cancelIndeed} />
      </div>

      {/* LinkedIn */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-2">LinkedIn (无需登录)</h2>
        <p className="text-sm text-gray-500 mb-4">
          通过 LinkedIn 公开接口搜索职位，无需账号，零封号风险。
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">关键词 (逗号分隔)</label>
            <input className={inputCls} value={rssKeywords} onChange={e => setRssKeywords(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">地点</label>
            <input className={inputCls} value={rssLoc} onChange={e => setRssLoc(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">最大数量</label>
            <input className={inputCls} type="number" value={rssMax} onChange={e => setRssMax(Number(e.target.value))} />
          </div>
        </div>
        <button className={btnCls} onClick={startLinkedInRss} disabled={rssTask?.status === 'running'}>
          {rssTask?.status === 'running' ? '⏳ 爬取中...' : '🚀 RSS 搜索'}
        </button>
        <TaskStatus task={rssTask} onCancel={cancelRss} />
      </div>
    </div>
  )
}
