import { useState, useEffect } from 'react'
import { api } from '../api/client'

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
      setTestResult('✅ 通知发送成功！')
    } catch (e: any) {
      setTestResult(`❌ 失败: ${e.response?.data?.detail || e.message}`)
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
      <h1 className="text-2xl font-bold text-gray-900">通知 & 自动爬取</h1>

      {/* Manual Trigger */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">手动触发每日爬取</h2>
        <p className="text-sm text-gray-600 mb-4">
          手动执行全量爬取 (Seek + Indeed + LinkedIn)，并发送通知推送。
          系统每天 9:00 AM 自动执行。
        </p>
        <button
          onClick={triggerScout}
          disabled={triggering || task?.status === 'running'}
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {task?.status === 'running' ? '⏳ 爬取中...' : '🚀 立即执行爬取'}
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
                  <div className="text-xs text-gray-500">爬取统计</div>
                  <div className="text-sm mt-1">
                    <div>Seek: {task.result.scraped.seek}</div>
                    <div>Indeed: {task.result.scraped.indeed}</div>
                    <div>LinkedIn: {task.result.scraped.linkedin}</div>
                  </div>
                </div>
                <div className="bg-white p-3 rounded border">
                  <div className="text-xs text-gray-500">匹配结果</div>
                  <div className="text-sm mt-1">
                    <div>高分 (≥80%): {task.result.high_score}</div>
                    <div>中分 (70-80%): {task.result.mid_score}</div>
                    <div>已保存: {task.result.saved}</div>
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
        <h2 className="text-lg font-semibold mb-3">测试推送通知</h2>
        <p className="text-sm text-gray-600 mb-4">
          发送测试消息验证 Webhook 配置是否正确。请先在设置页面配置 Webhook URL。
        </p>
        <button
          onClick={testNotification}
          disabled={testing}
          className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
        >
          {testing ? '发送中...' : '📱 发送测试通知'}
        </button>
        {testResult && <p className="mt-3 text-sm">{testResult}</p>}
      </div>
    </div>
  )
}
