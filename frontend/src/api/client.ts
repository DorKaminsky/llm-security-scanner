import axios from 'axios'
import { fetchAuthSession } from 'aws-amplify/auth'
import type { ScanRecord, StartScanRequest, StartScanResponse } from '@/types'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'
const IS_LOCAL = import.meta.env.VITE_COGNITO_USER_POOL_ID === 'local_pool'

const http = axios.create({ baseURL: BASE_URL })

http.interceptors.request.use(async (config) => {
  if (IS_LOCAL) return config
  const session = await fetchAuthSession()
  const token = session.tokens?.idToken?.toString()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function startScan(req: StartScanRequest): Promise<StartScanResponse> {
  const { data } = await http.post<StartScanResponse>('/scans', req)
  return data
}

export async function getScan(scanId: string): Promise<ScanRecord> {
  const { data } = await http.get<ScanRecord>(`/scans/${scanId}`)
  return data
}
