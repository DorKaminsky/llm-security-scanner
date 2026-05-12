export type ScanStatus = 'PENDING' | 'RUNNING' | 'COMPLETE' | 'FAILED'

export type CheckType =
  | 'prompt-injection'
  | 'sensitive-disclosure'
  | 'dos-resilience'
  | 'excessive-agency'

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'

export type LLMProvider = 'openai' | 'anthropic' | 'custom'

export interface CheckFinding {
  severity: Severity
  title: string
  description: string
  evidence?: string
  recommendation: string
}

export interface CheckResult {
  scan_id: string
  check_type: CheckType
  status: 'PENDING' | 'RUNNING' | 'PASS' | 'FAIL' | 'ERROR'
  score: number
  max_score: number
  findings: CheckFinding[]
  completed_at?: string
}

export interface ScanRecord {
  scan_id: string
  user_id: string
  target_url: string
  provider: LLMProvider
  status: ScanStatus
  checks_total: number
  checks_complete: number
  total_score?: number
  max_possible_score?: number
  grade?: string
  created_at: string
  completed_at?: string
  report_pdf_url?: string
  report_json_url?: string
  check_results?: CheckResult[]
  progress_pct?: number
}

export interface StartScanRequest {
  target_url: string
  provider: LLMProvider
  api_key: string
  model_id?: string
}

export interface StartScanResponse {
  scan_id: string
  status: ScanStatus
}
