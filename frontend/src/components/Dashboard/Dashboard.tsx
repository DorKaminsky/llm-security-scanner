import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signOut } from 'aws-amplify/auth'
import { getScan } from '@/api/client'
import type { ScanRecord } from '@/types'

export default function Dashboard() {
  const navigate = useNavigate()
  const [scans, setScans] = useState<ScanRecord[]>([])
  const [loading, setLoading] = useState(true)

  // LocalStorage-backed scan list (scan IDs stored after each new scan)
  useEffect(() => {
    const ids: string[] = JSON.parse(localStorage.getItem('scan_ids') ?? '[]')
    if (!ids.length) { setLoading(false); return }

    Promise.allSettled(ids.map(id => getScan(id))).then(results => {
      const loaded = results
        .filter((r): r is PromiseFulfilledResult<ScanRecord> => r.status === 'fulfilled')
        .map(r => r.value)
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
      setScans(loaded)
      setLoading(false)
    })
  }, [])

  async function handleSignOut() {
    await signOut()
    window.location.reload()
  }

  return (
    <>
      <nav className="navbar">
        <a href="/" className="brand">LLM Security Scanner</a>
        <div className="nav-actions">
          <button className="btn btn-primary" onClick={() => navigate('/scan')}>+ New Scan</button>
          <button className="btn btn-outline" onClick={handleSignOut}>Sign Out</button>
        </div>
      </nav>

      <div className="page container">
        <div className="page-header">
          <h1 className="page-title">My Scans</h1>
        </div>

        {loading && <div style={{ textAlign: 'center', padding: 32 }}><span className="spinner" /></div>}

        {!loading && scans.length === 0 && (
          <div className="empty-state">
            <h2>No scans yet</h2>
            <p>Run your first LLM security scan to see results here.</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/scan')}>
              Start a Scan
            </button>
          </div>
        )}

        {!loading && scans.length > 0 && (
          <div className="scan-list">
            {scans.map(scan => (
              <div key={scan.scan_id} className="card scan-item" onClick={() => navigate(`/report/${scan.scan_id}`)}>
                <div className="scan-item-meta">
                  <span className="scan-item-url">{scan.target_url}</span>
                  <span className="scan-item-date">{new Date(scan.created_at).toLocaleString()}</span>
                </div>
                <div className="scan-item-right">
                  {scan.grade && (
                    <span className={`grade grade-${scan.grade}`} style={{ fontSize: 24 }}>{scan.grade}</span>
                  )}
                  {['PENDING', 'RUNNING'].includes(scan.status) && (
                    <div>
                      <div className="progress-bar-wrap">
                        <div className="progress-bar-fill" style={{ width: `${scan.progress_pct ?? 0}%` }} />
                      </div>
                      <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>{scan.progress_pct ?? 0}%</span>
                    </div>
                  )}
                  <span className={`badge badge-${scan.status}`}>{scan.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
