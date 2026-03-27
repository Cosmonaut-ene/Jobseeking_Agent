import { useState, useEffect } from 'react'
import { Play, Bell, Loader2 } from 'lucide-react'
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

export default function Notifications() {
  const t = useT()
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<TaskResult | null>(null)

  useEffect(() => {
    if (!taskId || task?.status === 'done' || task?.status === 'error') return
    const interval = setInterval(() => {
      api.get(`/api/notifications/tasks/${taskId}`).then(r => setTask(r.data)).catch(() => {})
    }, 2000)
    return () => clearInterval(interval)
  }, [taskId, task?.status])

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
    setTask(null)
    try {
      const r = await api.post('/api/notifications/trigger-scout')
      setTaskId(r.data.task_id)
      setTask({ status: 'running', progress: 'Starting...' })
    } catch (e: any) {
      setTask({ status: 'error', progress: e.response?.data?.detail || e.message })
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('notif_title')}</h1>

      {/* Manual Trigger */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">{t('notif_trigger_title')}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">{t('notif_trigger_desc')}</p>
        <button
          onClick={triggerScout}
          disabled={triggering || task?.status === 'running'}
          className="inline-flex items-center gap-1.5 bg-amber-500 text-white px-6 py-2 rounded-lg font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors shadow-sm"
        >
          {task?.status === 'running' ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {task?.status === 'running' ? t('notif_scraping') : t('notif_run_now')}
        </button>

        {task && (
          <div className="mt-4 p-4 bg-slate-50/70 dark:bg-zinc-800/50 rounded-xl border border-slate-200/60 dark:border-zinc-700/60">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-1 rounded-md text-xs font-medium ${
                task.status === 'done'  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' :
                task.status === 'error' ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' :
                                          'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
              }`}>
                {task.status}
              </span>
              <span className="text-sm text-slate-600 dark:text-slate-300">{task.progress}</span>
            </div>
            {task.result && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="bg-white/80 dark:bg-zinc-900/60 p-3 rounded-lg border border-slate-200/60 dark:border-zinc-700/60">
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('notif_stats_label')}</div>
                  <div className="text-sm space-y-0.5 text-slate-700 dark:text-slate-300">
                    <div>Seek: {task.result.scraped.seek}</div>
                    <div>Indeed: {task.result.scraped.indeed}</div>
                    <div>LinkedIn: {task.result.scraped.linkedin}</div>
                  </div>
                </div>
                <div className="bg-white/80 dark:bg-zinc-900/60 p-3 rounded-lg border border-slate-200/60 dark:border-zinc-700/60">
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">{t('notif_match_label')}</div>
                  <div className="text-sm space-y-0.5 text-slate-700 dark:text-slate-300">
                    <div>{t('notif_high_score')} {task.result.high_score}</div>
                    <div>{t('notif_mid_score')} {task.result.mid_score}</div>
                    <div>{t('notif_saved')} {task.result.saved}</div>
                  </div>
                </div>
              </div>
            )}
            {task.error && <p className="text-rose-600 dark:text-rose-400 text-sm mt-2">{task.error}</p>}
          </div>
        )}
      </div>

      {/* Test Notification */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">{t('notif_test_title')}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">{t('notif_test_desc')}</p>
        <button
          onClick={testNotification}
          disabled={testing}
          className="inline-flex items-center gap-1.5 bg-emerald-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-sm"
        >
          {testing ? <Loader2 size={14} className="animate-spin" /> : <Bell size={14} />}
          {testing ? t('notif_sending') : t('notif_send_test')}
        </button>
        {testResult && <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">{testResult}</p>}
      </div>
    </div>
  )
}
