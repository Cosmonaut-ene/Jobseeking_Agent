import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useT } from '../contexts/LanguageContext'

export default function Settings() {
  const t = useT()

  // API Key
  const [keyInput, setKeyInput] = useState('')
  const [hasKey, setHasKey] = useState(false)
  const [keyPreview, setKeyPreview] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  // Notification / Scheduler settings
  const [webhookUrl, setWebhookUrl] = useState('')
  const [chatId, setChatId] = useState('')
  const [highScoreThreshold, setHighScoreThreshold] = useState('0.80')
  const [midScoreThreshold, setMidScoreThreshold] = useState('0.70')
  const [schedulerEnabled, setSchedulerEnabled] = useState(false)
  const [schedulerHour, setSchedulerHour] = useState('9')
  const [savingSettings, setSavingSettings] = useState(false)
  const [settingsMsg, setSettingsMsg] = useState('')

  useEffect(() => {
    api.get('/api/settings/status').then((r) => {
      setHasKey(r.data.has_key)
      setKeyPreview(r.data.key_preview)
    })
    api.get('/api/settings').then((r) => {
      const d = r.data
      if (d.notification_webhook_url) setWebhookUrl(d.notification_webhook_url)
      if (d.notification_chat_id) setChatId(d.notification_chat_id)
      if (d.high_score_threshold !== undefined) setHighScoreThreshold(String(d.high_score_threshold))
      if (d.mid_score_threshold !== undefined) setMidScoreThreshold(String(d.mid_score_threshold))
      if (d.scheduler_enabled !== undefined) setSchedulerEnabled(d.scheduler_enabled)
      if (d.scheduler_hour !== undefined) setSchedulerHour(String(d.scheduler_hour))
    }).catch(() => {})
  }, [])

  async function save() {
    if (!keyInput.trim()) return
    setSaving(true)
    setMsg('')
    try {
      await api.post('/api/settings/key', { key: keyInput.trim() })
      setMsg(t('settings_key_saved'))
      setHasKey(true)
      setKeyPreview(`...${keyInput.trim().slice(-4)}`)
      setKeyInput('')
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (!status) {
        setMsg('Cannot reach server. Make sure uvicorn is running: uv run uvicorn web.backend.main:app --reload')
      } else {
        setMsg(`Error ${status}: ${detail ?? 'Failed to save key.'}`)
      }
    } finally {
      setSaving(false)
    }
  }

  async function saveSettings() {
    setSavingSettings(true)
    setSettingsMsg('')
    try {
      await api.post('/api/settings', {
        notification_webhook_url: webhookUrl || undefined,
        notification_chat_id: chatId || undefined,
        high_score_threshold: parseFloat(highScoreThreshold),
        mid_score_threshold: parseFloat(midScoreThreshold),
        scheduler_enabled: schedulerEnabled,
        scheduler_hour: parseInt(schedulerHour, 10),
      })
      setSettingsMsg(t('settings_saved'))
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSettingsMsg(`Error: ${detail ?? 'Failed to save settings.'}`)
    } finally {
      setSavingSettings(false)
    }
  }

  const inputCls = 'flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t('settings_title')}</h1>

      {/* Gemini API Key */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-700 mb-1">{t('settings_gemini_title')}</h2>
          <p className="text-sm text-gray-500 mb-3">
            {t('settings_gemini_desc_pre')}{' '}
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline"
            >
              Google AI Studio
            </a>
            {t('settings_gemini_desc_post')}
          </p>

          {/* Status */}
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm mb-4 ${
            hasKey ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${hasKey ? 'bg-green-500' : 'bg-red-500'}`} />
            {hasKey ? `${t('settings_connected')} ${keyPreview}` : t('settings_not_configured')}
          </div>

          <div className="flex gap-2">
            <input
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && save()}
              placeholder="AIza..."
              className={inputCls}
            />
            <button
              onClick={save}
              disabled={saving || !keyInput.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? t('settings_saving') : t('settings_save')}
            </button>
          </div>
          {msg && <p className="mt-2 text-sm text-green-600">{msg}</p>}
        </div>

        <div className="border-t pt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">{t('settings_production_title')}</h3>
          <p className="text-sm text-gray-500">
            {t('settings_production_desc_pre')} <code className="bg-gray-100 px-1 rounded">GEMINI_API_KEY</code> {t('settings_production_desc_post')}
          </p>
        </div>
      </div>

      {/* Notifications & Scheduler */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-700">{t('settings_notif_title')}</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings_webhook_label')}</label>
          <input
            type="text"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.slack.com/... or Telegram bot URL"
            className={inputCls + ' w-full'}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings_chat_id_label')}</label>
          <input
            type="text"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            placeholder="Telegram chat ID or channel"
            className={inputCls + ' w-full'}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings_high_threshold')}</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={highScoreThreshold}
              onChange={(e) => setHighScoreThreshold(e.target.value)}
              className={inputCls + ' w-full'}
            />
            <p className="text-xs text-gray-400 mt-1">{t('settings_threshold_hint_80')}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('settings_mid_threshold')}</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={midScoreThreshold}
              onChange={(e) => setMidScoreThreshold(e.target.value)}
              className={inputCls + ' w-full'}
            />
            <p className="text-xs text-gray-400 mt-1">{t('settings_threshold_hint_70')}</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="scheduler-enabled"
              checked={schedulerEnabled}
              onChange={(e) => setSchedulerEnabled(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label htmlFor="scheduler-enabled" className="text-sm font-medium text-gray-700">
              {t('settings_scheduler_enable')}
            </label>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">{t('settings_scheduler_hour')}</label>
            <input
              type="number"
              min="0"
              max="23"
              value={schedulerHour}
              onChange={(e) => setSchedulerHour(e.target.value)}
              className="w-16 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-500">:00</span>
          </div>
        </div>

        <div className="border-t pt-4">
          <button
            onClick={saveSettings}
            disabled={savingSettings}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {savingSettings ? t('settings_saving') : t('settings_save_settings')}
          </button>
          {settingsMsg && <p className="mt-2 text-sm text-green-600">{settingsMsg}</p>}
        </div>
      </div>
    </div>
  )
}
