import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'

vi.mock('aws-amplify/auth', () => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
  confirmSignUp: vi.fn(),
}))

describe('LoginPage', () => {
  it('renders sign in form', () => {
    render(
      <MemoryRouter>
        <LoginPage onAuth={() => {}} />
      </MemoryRouter>
    )
    expect(screen.getByText('LLM Security')).toBeTruthy()
    expect(screen.getByText('Sign In')).toBeTruthy()
  })
})
