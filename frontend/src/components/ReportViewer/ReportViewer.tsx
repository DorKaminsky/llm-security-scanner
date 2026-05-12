import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { getScan } from '@/api/client'
import type { CheckResult, ScanRecord } from '@/types'

const CHECK_LABELS: Record<string, string> = {
  'prompt-injection': 'Prompt Injection',
  'sensitive-disclosure': 'Sensitive Disclosure',
  'dos-resilience': 'DoS Resilience',
  'excessive-agency': 'Excessive Agency',
}

function scoreColor(pct: number) {
  if (pct >= 80) return 'var(--color-success)'
  if (pct >= 60) return 'var(--color-low)'
  if (pct >= 40) return 'var(--color-medium)'
  if (pct >= 20) return 'var(--color-high)'
  return 'var(--color-danger)'
}

interface Props { scanId: string }

export default function ReportViewer({ scanId }: Props) {
  const navigate = useNavigate()
  const [scan, setScan] = useState<ScanRecord | null>(null)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchScan = useCallback(async () => {
    try {
      const data = await getScan(scanId)
      setScan(data)
      if (data.status === 'COMPLETE' || data.status === 'FAILED') {
        if (pollRef.current) clearInterval(pollRef.current)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load scan')
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [scanId])

  useEffect(() => {
    fetchScan()
    pollRef.current = setInterval(fetchScan, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [fetchScan])

  if (error) return <div className="page container"><p className="error-text">{error}</p></div>
  if (!scan) return <div className="page container" style={{ textAlign: 'center' }}><span className="spinner" /></div>

  const inProgress = scan.status === 'PENDING' || scan.status === 'RUNNING'
  const radarData = (scan.check_results ?? []).map(r => ({
    subject: CHECK_LABELS[r.check_type] ?? r.check_type,
    score: r.max_score > 0 ? Math.round((r.score / r.max_score) * 100) : 0,
  }))

  return (
    <>
      <nav className="navbar">
        <a href="/" className="brand">LLM Security Scanner</a>
        <div className="nav-actions">
          <button className="btn btn-outline" onClick={() => navigate('/')}>← Dashboard</button>
        </div>
      </nav>

      <div className="page container">
        <div className="page-header">
          <div>
            <h1 className="page-title">{scan.target_url}</h1>
            <span style={{ fontSize: 13, color: 'var(--color-muted)' }}>
              {new Date(scan.created_at).toLocaleString()} · {scan.provider}
            </span>
          </div>
          <span className={`badge badge-${scan.status}`}>{scan.status}</span>
        </div>

        {inProgress && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span className="spinner" />
              <span style={{ color: 'var(--color-muted)' }}>
                Running checks… {scan.checks_complete}/{scan.checks_total}
              </span>
            </div>
            <div className="progress-bar-wrap" style={{ width: '100%', height: 10 }}>
              <div className="progress-bar-fill" style={{ width: `${scan.progress_pct ?? 0}%` }} />
            </div>
          </div>
        )}

        {scan.status === 'COMPLETE' && scan.total_score !== undefined && (
          <div className="score-summary">
            <div>
              <div className={`grade grade-${scan.grade}`}>{scan.grade}</div>
              <div className="score-label">Grade</div>
            </div>
            <div>
              <div className="score-number">
                {scan.total_score}/{scan.max_possible_score}
              </div>
              <div className="score-label">Total Score</div>
            </div>
          </div>
        )}

        {scan.status === 'COMPLETE' && radarData.length > 0 && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h2 className="section-title">Security Coverage</h2>
            <div className="radar-container">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--color-border)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--color-muted)', fontSize: 12 }} />
                  <Radar name="Score" dataKey="score" fill="var(--color-primary)" fillOpacity={0.3} stroke="var(--color-primary)" />
                  <Tooltip
                    contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                    formatter={(v: number) => [`${v}%`, 'Score']}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {scan.report_pdf_url || scan.report_json_url ? (
          <div className="report-actions">
            {scan.report_pdf_url && (
              <a className="btn btn-primary" href={scan.report_pdf_url} target="_blank" rel="noreferrer">
                Download PDF Report
              </a>
            )}
            {scan.report_json_url && (
              <a className="btn btn-outline" href={scan.report_json_url} target="_blank" rel="noreferrer">
                Download JSON Report
              </a>
            )}
          </div>
        ) : null}

        {(scan.check_results ?? []).length > 0 && (
          <>
            <h2 className="section-title">Check Results</h2>
            <div className="checks-grid">
              {scan.check_results!.map(check => <CheckCard key={check.check_type} check={check} />)}
            </div>
          </>
        )}
      </div>
    </>
  )
}

function CheckCard({ check }: { check: CheckResult }) {
  const pct = check.max_score > 0 ? Math.round((check.score / check.max_score) * 100) : 0
  return (
    <div className="card check-card">
      <div className="check-card-header">
        <span className="check-name">{CHECK_LABELS[check.check_type] ?? check.check_type}</span>
        <span className={`badge badge-${check.status}`}>{check.status}</span>
      </div>
      <div className="score-bar-wrap">
        <div className="score-bar-bg">
          <div className="score-bar-fill" style={{ width: `${pct}%`, background: scoreColor(pct) }} />
        </div>
        <span>{check.score}/{check.max_score}</span>
      </div>
      {check.findings.length > 0 && (
        <div className="findings-list">
          {check.findings.map((f, i) => (
            <div key={i} className={`finding-card ${f.severity}`}>
              <div className="finding-title">
                <span className={`badge badge-${f.severity}`}>{f.severity}</span>
                {f.title}
              </div>
              <p className="finding-desc">{f.description}</p>
              <p className="finding-rec">{f.recommendation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
