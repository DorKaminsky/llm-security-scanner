import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getCurrentUser } from 'aws-amplify/auth'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import ScanPage from '@/pages/ScanPage'
import ReportPage from '@/pages/ReportPage'

const IS_LOCAL = import.meta.env.VITE_COGNITO_USER_POOL_ID === 'local_pool'

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    if (IS_LOCAL) {
      const localAuth = sessionStorage.getItem('local_auth')
      setAuthenticated(localAuth === 'true')
      return
    }
    getCurrentUser()
      .then(() => setAuthenticated(true))
      .catch(() => setAuthenticated(false))
  }, [])

  if (authenticated === null) {
    return <div className="loading-screen">Loading...</div>
  }

  return (
    <Routes>
      <Route path="/login" element={authenticated ? <Navigate to="/" replace /> : <LoginPage onAuth={() => { if (IS_LOCAL) sessionStorage.setItem('local_auth', 'true'); setAuthenticated(true) }} />} />
      <Route path="/" element={authenticated ? <DashboardPage /> : <Navigate to="/login" replace />} />
      <Route path="/scan" element={authenticated ? <ScanPage /> : <Navigate to="/login" replace />} />
      <Route path="/report/:scanId" element={authenticated ? <ReportPage /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
