import Auth from '@/components/Auth/Auth'

interface Props { onAuth: () => void }

export default function LoginPage({ onAuth }: Props) {
  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div className="auth-title">LLM Security</div>
        <div className="auth-subtitle">Test your AI endpoints against OWASP Top 10 for LLMs</div>
        <Auth onAuth={onAuth} />
      </div>
    </div>
  )
}
