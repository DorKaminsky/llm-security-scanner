import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getCurrentUser } from 'aws-amplify/auth'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import ScanPage from '@/pages/ScanPage'
import ReportPage from '@/pages/ReportPage'

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    getCurrentUser()
      .then(() => setAuthenticated(true))
      .catch(() => setAuthenticated(false))
  }, [])

  if (authenticated === null) {
    return <div className="loading-screen">Loading...</div>
  }

  return (
    <Routes>
      <Route path="/login" element={authenticated ? <Navigate to="/" replace /> : <LoginPage onAuth={() => setAuthenticated(true)} />} />
      <Route path="/" element={authenticated ? <DashboardPage /> : <Navigate to="/login" replace />} />
      <Route path="/scan" element={authenticated ? <ScanPage /> : <Navigate to="/login" replace />} />
      <Route path="/report/:scanId" element={authenticated ? <ReportPage /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
