import { useState } from 'react'
import { signIn, signUp, confirmSignUp } from 'aws-amplify/auth'

interface Props {
  onAuth: () => void
}

type Mode = 'login' | 'register' | 'confirm'

export default function Auth({ onAuth }: Props) {
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signIn({ username: email, password })
      onAuth()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signUp({ username: email, password, options: { userAttributes: { email } } })
      setMode('confirm')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await confirmSignUp({ username: email, confirmationCode: code })
      await signIn({ username: email, password })
      onAuth()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Confirmation failed')
    } finally {
      setLoading(false)
    }
  }

  if (mode === 'confirm') {
    return (
      <form onSubmit={handleConfirm}>
        <div className="auth-subtitle">Enter the verification code sent to {email}</div>
        <div className="form-group">
          <label className="form-label">Verification Code</label>
          <input className="form-input" value={code} onChange={e => setCode(e.target.value)} required autoFocus />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
          {loading ? <span className="spinner" /> : 'Verify'}
        </button>
      </form>
    )
  }

  if (mode === 'register') {
    return (
      <form onSubmit={handleRegister}>
        <div className="form-group">
          <label className="form-label">Email</label>
          <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
        </div>
        <div className="form-group">
          <label className="form-label">Password</label>
          <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" style={{ width: '100%', marginBottom: 12 }} disabled={loading}>
          {loading ? <span className="spinner" /> : 'Create Account'}
        </button>
        <div className="auth-toggle">
          Already have an account?{' '}
          <button type="button" onClick={() => { setMode('login'); setError('') }}>Sign in</button>
        </div>
      </form>
    )
  }

  return (
    <form onSubmit={handleLogin}>
      <div className="form-group">
        <label className="form-label">Email</label>
        <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
      </div>
      <div className="form-group">
        <label className="form-label">Password</label>
        <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
      </div>
      {error && <p className="error-text">{error}</p>}
      <button className="btn btn-primary" style={{ width: '100%', marginBottom: 12 }} disabled={loading}>
        {loading ? <span className="spinner" /> : 'Sign In'}
      </button>
      <div className="auth-toggle">
        No account?{' '}
        <button type="button" onClick={() => { setMode('register'); setError('') }}>Create one</button>
      </div>
    </form>
  )
}
