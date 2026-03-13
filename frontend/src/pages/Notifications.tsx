import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { useT } from '../contexts/LanguageContext'

interface TaskResult {
  status: string
  progress: string
  result?: {
    scraped: { seek: number; indeed: number; linkedin: number }
    saved: number
    high_score: number
    mid_score: number
  }
  error?: string
}

const STORAGE_KEY = 'notifications_scout_task'

// Module-level store: polling survives page navigation
const store: {
  intervalId: ReturnType<typeof setInterval> | null
  state: TaskResult | null
  listeners: Set<(s: TaskResult | null) => void>
} = { intervalId: null, state: null, listeners: new Set() }

function ensurePolling(taskId: string) {
  if (store.intervalId !== null) return
  store.intervalId = setInterval(async () => {
    try {
      const r = await api.get(`/api/notifications/tasks/${taskId}`)
      store.state = r.data
      store.listeners.forEach(fn => fn(r.data))
      if (r.data.status === 'done' || r.data.status === 'error') {
        clearInterval(store.intervalId!)
        store.intervalId = null
        sessionStorage.removeItem(STORAGE_KEY)
      }
    } catch (err: any) {
      if (err?.response?.status === 404) {
        clearInterval(store.intervalId!)
        store.intervalId = null
        sessionStorage.removeItem(STORAGE_KEY)
        const gone: TaskResult = { status: 'error', progress: '任务已丢失（服务器已重启），请重新发起。' }
        store.state = gone
        store.listeners.forEach(fn => fn(gone))
      }
    }
  }, 2000)
}

export default function Notifications() {
  const t = useT()
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [task, setTask] = useState<TaskResult | null>(() => store.state)

  useEffect(() => {
    // Resume polling if page was refreshed and task was in progress
    const savedId = sessionStorage.getItem(STORAGE_KEY)
    if (savedId && store.intervalId === null && (!store.state || store.state.status === 'running')) {
      ensurePolling(savedId)
    }
    // Subscribe to updates
    const listener = (s: TaskResult | null) => setTask(s)
    store.listeners.add(listener)
    if (store.state) setTask(store.state)
    return () => { store.listeners.delete(listener) }
  }, [])

  const testNotification = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      await api.post('/api/notifications/test')
      setTestResult(t('notif_success'))
    } catch (e: any) {
      setTestResult(`${t('notif_failed')} ${e.response?.data?.detail || e.message}`)
    } finally {
      setTesting(false)
    }
  }

  const triggerScout = async () => {
    setTriggering(true)
    store.state = null
    setTask(null)
    try {
      const r = await api.post('/api/notifications/trigger-scout')
      const taskId = r.data.task_id
      sessionStorage.setItem(STORAGE_KEY, taskId)
      const initial: TaskResult = { status: 'running', progress: 'Starting...' }
      store.state = initial
      setTask(initial)
      ensurePolling(taskId)
    } catch (e: any) {
      const errState: TaskResult = { status: 'error', progress: e.response?.data?.detail || e.message }
      store.state = errState
      setTask(errState)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t('notif_title')}</h1>

      {/* Manual Trigger */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">{t('notif_trigger_title')}</h2>
        <p className="text-sm text-gray-600 mb-4">{t('notif_trigger_desc')}</p>
        <button
          onClick={triggerScout}
          disabled={triggering || task?.status === 'running'}
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {task?.status === 'running' ? t('notif_scraping') : t('notif_run_now')}
        </button>

        {task && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                task.status === 'done' ? 'bg-green-100 text-green-700' :
                task.status === 'error' ? 'bg-red-100 text-red-700' :
                'bg-blue-100 text-blue-700'
              }`}>
                {task.status}
              </span>
              <span className="text-sm text-gray-600">{task.progress}</span>
            </div>
            {task.result && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="bg-white p-3 rounded border">
                  <div className="text-xs text-gray-500">{t('notif_stats_label')}</div>
                  <div className="text-sm mt-1">
                    <div>Seek: {task.result.scraped.seek}</div>
                    <div>Indeed: {task.result.scraped.indeed}</div>
                    <div>LinkedIn: {task.result.scraped.linkedin}</div>
                  </div>
                </div>
                <div className="bg-white p-3 rounded border">
                  <div className="text-xs text-gray-500">{t('notif_match_label')}</div>
                  <div className="text-sm mt-1">
                    <div>{t('notif_high_score')} {task.result.high_score}</div>
                    <div>{t('notif_mid_score')} {task.result.mid_score}</div>
                    <div>{t('notif_saved')} {task.result.saved}</div>
                  </div>
                </div>
              </div>
            )}
            {task.error && <p className="text-red-600 text-sm mt-2">{task.error}</p>}
          </div>
        )}
      </div>

      {/* Test Notification */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">{t('notif_test_title')}</h2>
        <p className="text-sm text-gray-600 mb-4">{t('notif_test_desc')}</p>
        <button
          onClick={testNotification}
          disabled={testing}
          className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
        >
          {testing ? t('notif_sending') : t('notif_send_test')}
        </button>
        {testResult && <p className="mt-3 text-sm">{testResult}</p>}
      </div>
    </div>
  )
}
