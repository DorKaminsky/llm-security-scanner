import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startScan } from '@/api/client'
import type { LLMProvider, StartScanRequest } from '@/types'

const PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'custom', label: 'Custom Endpoint' },
]

export default function ScanForm() {
  const navigate = useNavigate()
  const [form, setForm] = useState<StartScanRequest>({
    target_url: '',
    provider: 'openai',
    api_key: '',
    model_id: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set<K extends keyof StartScanRequest>(key: K, value: StartScanRequest[K]) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { scan_id } = await startScan(form)
      navigate(`/report/${scan_id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start scan')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 600 }}>
      <h2 style={{ marginBottom: 24 }}>New Security Scan</h2>

      <div className="form-group">
        <label className="form-label">Target URL</label>
        <input
          className="form-input"
          type="url"
          placeholder="https://api.example.com/v1/chat"
          value={form.target_url}
          onChange={e => set('target_url', e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label">Provider</label>
        <select
          className="form-select"
          value={form.provider}
          onChange={e => set('provider', e.target.value as LLMProvider)}
        >
          {PROVIDERS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label className="form-label">API Key</label>
        <input
          className="form-input"
          type="password"
          placeholder="sk-..."
          value={form.api_key}
          onChange={e => set('api_key', e.target.value)}
          required
        />
        <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
          Stored encrypted in AWS Secrets Manager — never logged
        </span>
      </div>

      <div className="form-group">
        <label className="form-label">Model ID <span style={{ fontWeight: 400 }}>(optional)</span></label>
        <input
          className="form-input"
          placeholder="gpt-4o, claude-3-5-sonnet-20241022, …"
          value={form.model_id ?? ''}
          onChange={e => set('model_id', e.target.value)}
        />
      </div>

      {error && <p className="error-text" style={{ marginBottom: 16 }}>{error}</p>}

      <div style={{ display: 'flex', gap: 12 }}>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <><span className="spinner" /> Starting…</> : 'Start Scan'}
        </button>
        <button type="button" className="btn btn-outline" onClick={() => navigate('/')}>
          Cancel
        </button>
      </div>
    </form>
  )
}
