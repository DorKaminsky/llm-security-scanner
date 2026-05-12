import { useParams, Navigate } from 'react-router-dom'
import ReportViewer from '@/components/ReportViewer/ReportViewer'

export default function ReportPage() {
  const { scanId } = useParams<{ scanId: string }>()
  if (!scanId) return <Navigate to="/" replace />
  return <ReportViewer scanId={scanId} />
}
