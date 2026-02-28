import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Settings() {
  const [keyInput, setKeyInput] = useState('')
  const [hasKey, setHasKey] = useState(false)
  const [keyPreview, setKeyPreview] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.get('/api/settings/status').then((r) => {
      setHasKey(r.data.has_key)
      setKeyPreview(r.data.key_preview)
    })
  }, [])

  async function save() {
    if (!keyInput.trim()) return
    setSaving(true)
    setMsg('')
    try {
      await api.post('/api/settings/key', { key: keyInput.trim() })
      setMsg('API key saved for this session.')
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

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-700 mb-1">Gemini API Key</h2>
          <p className="text-sm text-gray-500 mb-3">
            Required for all AI features. Get yours at{' '}
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline"
            >
              Google AI Studio
            </a>
            . The key is stored in the server process memory only.
          </p>

          {/* Status */}
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm mb-4 ${
            hasKey ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${hasKey ? 'bg-green-500' : 'bg-red-500'}`} />
            {hasKey ? `Connected · Key ${keyPreview}` : 'Not configured'}
          </div>

          <div className="flex gap-2">
            <input
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && save()}
              placeholder="AIza..."
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={save}
              disabled={saving || !keyInput.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
          {msg && <p className="mt-2 text-sm text-green-600">{msg}</p>}
        </div>

        <div className="border-t pt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Production deployment</h3>
          <p className="text-sm text-gray-500">
            On Render.com, set <code className="bg-gray-100 px-1 rounded">GEMINI_API_KEY</code> as an
            environment variable. The Settings page is for demo / testing without redeploying.
          </p>
        </div>
      </div>
    </div>
  )
}
