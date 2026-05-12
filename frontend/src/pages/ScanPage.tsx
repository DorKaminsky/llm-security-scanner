import { useNavigate } from 'react-router-dom'
import { signOut } from 'aws-amplify/auth'
import ScanForm from '@/components/ScanForm/ScanForm'

export default function ScanPage() {
  const navigate = useNavigate()

  return (
    <>
      <nav className="navbar">
        <a href="/" className="brand">LLM Security Scanner</a>
        <div className="nav-actions">
          <button className="btn btn-outline" onClick={() => navigate('/')}>← Dashboard</button>
          <button className="btn btn-outline" onClick={async () => { await signOut(); window.location.reload() }}>Sign Out</button>
        </div>
      </nav>
      <div className="page container">
        <div className="page-header">
          <h1 className="page-title">Configure Scan</h1>
        </div>
        <ScanForm />
      </div>
    </>
  )
}
