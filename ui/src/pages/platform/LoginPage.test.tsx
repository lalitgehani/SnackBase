import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import LoginPage from './LoginPage'

const loginMock = vi.fn()

vi.mock('@snackbase/react', () => ({
  useAuth: () => ({
    login: loginMock,
    isAuthenticated: false,
    isLoading: false,
  }),
}))

vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'system',
    setTheme: vi.fn(),
    resolvedTheme: 'light',
  }),
}))

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByText(/account slug or id is required/i)).toBeInTheDocument()
    })
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('submits credentials including account', async () => {
    const user = userEvent.setup()
    loginMock.mockResolvedValue({})
    renderLogin()

    await user.type(screen.getByLabelText(/^account$/i), 'acme')
    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'secret123',
        account: 'acme',
      })
    })
  })

  it('surfaces invalid credentials error', async () => {
    const user = userEvent.setup()
    loginMock.mockRejectedValue(new Error('Invalid credentials'))
    renderLogin()

    await user.type(screen.getByLabelText(/^account$/i), 'acme')
    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent('Invalid credentials')
    })
  })
})
