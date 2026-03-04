import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface TaskState {
  status: string
  progress: string
  results?: any[]
  error?: string
}

function useTask(taskId: string | null) {
  const [task, setTask] = useState<TaskState | null>(null)

  useEffect(() => {
    if (!taskId) return
    setTask({ status: 'pending', progress: 'Queued' })
    const interval = setInterval(async () => {
      try {
        const r = await api.get(`/api/tasks/${taskId}`)
        setTask(r.data)
        if (r.data.status === 'done' || r.data.status === 'error') {
          clearInterval(interval)
        }
      } catch {}
    }, 2000)
    return () => clearInterval(interval)
  }, [taskId])

  return task
}

function TaskStatus({ task }: { task: TaskState | null }) {
  if (!task) return null
  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
      <div className="flex items-center gap-2 mb-2">
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          task.status === 'done' ? 'bg-green-100 text-green-700' :
          task.status === 'error' ? 'bg-red-100 text-red-700' :
          'bg-blue-100 text-blue-700'
        }`}>{task.status}</span>
        <span className="text-sm text-gray-600">{task.progress}</span>
      </div>
      {task.results && (
        <p className="text-sm text-green-700 font-medium">{task.results.length} jobs saved</p>
      )}
      {task.error && <p className="text-sm text-red-600">{task.error}</p>}
    </div>
  )
}

export default function Scrapers() {
  // Seek
  const [seekRoles, setSeekRoles] = useState('Data Scientist, ML Engineer')
  const [seekLoc, setSeekLoc] = useState('Sydney NSW')
  const [seekMax, setSeekMax] = useState(10)
  const [seekTaskId, setSeekTaskId] = useState<string | null>(null)
  const seekTask = useTask(seekTaskId)

  // Indeed
  const [indeedRoles, setIndeedRoles] = useState('Data Scientist, ML Engineer')
  const [indeedLoc, setIndeedLoc] = useState('Sydney NSW')
  const [indeedMax, setIndeedMax] = useState(10)
  const [indeedTaskId, setIndeedTaskId] = useState<string | null>(null)
  const indeedTask = useTask(indeedTaskId)

  // LinkedIn URLs
  const [liUrls, setLiUrls] = useState('')
  const [liUrlTaskId, setLiUrlTaskId] = useState<string | null>(null)
  const liUrlTask = useTask(liUrlTaskId)

  // LinkedIn RSS (no login)
  const [rssKeywords, setRssKeywords] = useState('Data Scientist, Machine Learning Engineer')
  const [rssLoc, setRssLoc] = useState('Sydney, New South Wales, Australia')
  const [rssMax, setRssMax] = useState(25)
  const [rssTaskId, setRssTaskId] = useState<string | null>(null)
  const rssTask = useTask(rssTaskId)

  const startSeek = async () => {
    const r = await api.post('/api/scrapers/seek', {
      roles: seekRoles.split(',').map(s => s.trim()).filter(Boolean),
      locations: [seekLoc],
      max_per_query: seekMax
    })
    setSeekTaskId(r.data.task_id)
  }

  const startIndeed = async () => {
    const r = await api.post('/api/scrapers/indeed', {
      roles: indeedRoles.split(',').map(s => s.trim()).filter(Boolean),
      locations: [indeedLoc],
      max_per_query: indeedMax
    })
    setIndeedTaskId(r.data.task_id)
  }

  const startLinkedInUrls = async () => {
    const urls = liUrls.split('\n').map(u => u.trim()).filter(Boolean)
    const r = await api.post('/api/scrapers/linkedin-urls', { urls })
    setLiUrlTaskId(r.data.task_id)
  }

  const startLinkedInRss = async () => {
    const r = await api.post('/api/scrapers/linkedin-rss', {
      keywords: rssKeywords.split(',').map(s => s.trim()).filter(Boolean),
      location: rssLoc,
      max_results: rssMax
    })
    setRssTaskId(r.data.task_id)
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
        <TaskStatus task={seekTask} />
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
        <TaskStatus task={indeedTask} />
      </div>

      {/* LinkedIn URL */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-2">LinkedIn URL 模式</h2>
        <p className="text-sm text-gray-500 mb-4">
          在 LinkedIn 找到感兴趣的职位后，粘贴 URL 由系统自动抓取详情并评分。
        </p>
        <textarea
          className={inputCls + ' h-24 font-mono'}
          placeholder="每行粘贴一个 LinkedIn 职位 URL"
          value={liUrls}
          onChange={e => setLiUrls(e.target.value)}
        />
        <button className={btnCls + ' mt-2'} onClick={startLinkedInUrls} disabled={liUrlTask?.status === 'running'}>
          {liUrlTask?.status === 'running' ? '⏳ 处理中...' : '📥 处理 URLs'}
        </button>
        <TaskStatus task={liUrlTask} />
      </div>

      {/* LinkedIn RSS */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-2">LinkedIn RSS (无需登录)</h2>
        <p className="text-sm text-gray-500 mb-4">
          通过 LinkedIn 公开 RSS 搜索职位，无需 Cookies，零封号风险。
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
        <TaskStatus task={rssTask} />
      </div>
    </div>
  )
}
