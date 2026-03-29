/**
 * Tests for LoginPage component (FT3.1)
 *
 * Verifies:
 * - Renders email and password fields
 * - Submit button is disabled while submitting
 * - Successful login redirects to /admin/dashboard
 * - Failed login displays an error message
 * - Validation errors show for invalid/missing email and password
 * - Loading spinner shows during login request
 *
 * Note on 401 error display: The axios response interceptor intercepts all
 * 401 responses to attempt token refresh. When no refresh token exists, it
 * throws a generic error, so the displayed message is "An unexpected error
 * occurred" rather than the API's detail string. Non-401 errors (e.g. 500)
 * propagate normally and show the API's detail.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route } from 'react-router'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { useAuthStore } from '@/stores/auth.store'
import LoginPage from '../LoginPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockAuthResponse = {
  token: 'access-token-abc',
  refresh_token: 'refresh-token-xyz',
  expires_in: 3600,
  account: {
    id: 'SY0000',
    slug: 'system',
    name: 'System',
    created_at: '2024-01-01T00:00:00Z',
  },
  user: {
    id: 'user-1',
    email: 'admin@example.com',
    role: 'superadmin',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Reset the auth store to a clean unauthenticated state. */
function resetAuthStore() {
  useAuthStore.setState({
    user: null,
    account: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  })
}

/**
 * Render the login page inside a minimal router that also registers the
 * /admin/dashboard route so navigation can be verified.
 */
function renderLoginPage(initialEntries: string[] = ['/admin/login']) {
  return render(
    <Routes>
      <Route path="/admin/login" element={<LoginPage />} />
      <Route path="/admin/dashboard" element={<div>Dashboard Page</div>} />
    </Routes>,
    { initialEntries },
  )
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
  resetAuthStore()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LoginPage', () => {
  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------

  describe('initial render', () => {
    it('renders the email input', () => {
      renderLoginPage()
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument()
    })

    it('renders the password input', () => {
      renderLoginPage()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    })

    it('renders the login submit button', () => {
      renderLoginPage()
      expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument()
    })

    it('renders the card title', () => {
      renderLoginPage()
      // Use exact text to avoid matching the description ("Enter your email below to login to your account")
      expect(screen.getByText('Login to your account')).toBeInTheDocument()
    })

    it('does not show an error message on initial render', () => {
      renderLoginPage()
      expect(screen.queryByText(/an unexpected error occurred/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/invalid email/i)).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Validation
  // -------------------------------------------------------------------------

  describe('form validation', () => {
    it('shows a validation error when email is missing on submit', async () => {
      // Note: typing an invalid-format email (e.g. "not-an-email") triggers jsdom's
      // native HTML5 constraint validation which blocks the submit event before
      // React Hook Form / Zod runs. Testing with an empty email field avoids this —
      // HTML5 allows empty optional fields, so Zod's .email() validation runs and
      // returns "Invalid email address".
      const user = userEvent.setup()
      renderLoginPage()

      // Fill password only — leave email blank
      await user.type(screen.getByLabelText(/^password$/i), 'secret')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument()
      })
    })

    it('shows a validation error when password is empty', async () => {
      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText('Password is required')).toBeInTheDocument()
      })
    })

    it('does not call the API when required fields are empty', async () => {
      let apiCalled = false
      server.use(
        http.post('/api/v1/auth/login', () => {
          apiCalled = true
          return HttpResponse.json(mockAuthResponse)
        }),
      )

      const user = userEvent.setup()
      renderLoginPage()

      // Click submit without filling any fields
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument()
      })

      expect(apiCalled).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // Successful login
  // -------------------------------------------------------------------------

  describe('successful login', () => {
    beforeEach(() => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
      )
    })

    it('navigates to /admin/dashboard on success', async () => {
      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })

    it('does not show an error message after successful login', async () => {
      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })

      expect(screen.queryByText(/an unexpected error occurred/i)).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Failed login
  // -------------------------------------------------------------------------

  describe('failed login', () => {
    it('displays an error message when the API returns 401', async () => {
      // The axios response interceptor intercepts 401 responses for token refresh.
      // Since no refresh token exists, the error reaching the component is generic.
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 }),
        ),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'wrongpassword')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText(/an unexpected error occurred/i)).toBeInTheDocument()
      })
    })

    it('displays the API error detail when the server returns a 500', async () => {
      // Non-401 errors bypass the token-refresh interceptor and propagate normally
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Internal server error' }, { status: 500 }),
        ),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText(/internal server error/i)).toBeInTheDocument()
      })
    })

    it('does not navigate to dashboard after a failed login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 }),
        ),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'wrong')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument()
      })
    })

    it('clears a previous error when a new successful submission occurs', async () => {
      // First attempt: fail with 500 (direct error propagation)
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Service temporarily unavailable' }, { status: 503 }),
        ),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText(/service temporarily unavailable/i)).toBeInTheDocument()
      })

      // Second attempt: succeed
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
      )

      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state during submission', () => {
    it('shows a loading spinner while the login request is in flight', async () => {
      let resolveLogin!: () => void
      const loginPending = new Promise<void>((resolve) => {
        resolveLogin = resolve
      })

      server.use(
        http.post('/api/v1/auth/login', async () => {
          await loginPending
          return HttpResponse.json(mockAuthResponse)
        }),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      // Spinner text should appear while request is pending
      await waitFor(() => {
        expect(screen.getByText(/logging in/i)).toBeInTheDocument()
      })

      // Unblock the request
      resolveLogin()

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })

    it('disables the submit button while submission is in progress', async () => {
      let resolveLogin!: () => void
      const loginPending = new Promise<void>((resolve) => {
        resolveLogin = resolve
      })

      server.use(
        http.post('/api/v1/auth/login', async () => {
          await loginPending
          return HttpResponse.json(mockAuthResponse)
        }),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /logging in/i })).toBeDisabled()
      })

      resolveLogin()

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })

    it('disables the email input while submitting', async () => {
      let resolveLogin!: () => void
      const loginPending = new Promise<void>((resolve) => {
        resolveLogin = resolve
      })

      server.use(
        http.post('/api/v1/auth/login', async () => {
          await loginPending
          return HttpResponse.json(mockAuthResponse)
        }),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByLabelText(/^email$/i)).toBeDisabled()
      })

      resolveLogin()

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })

    it('disables the password input while submitting', async () => {
      let resolveLogin!: () => void
      const loginPending = new Promise<void>((resolve) => {
        resolveLogin = resolve
      })

      server.use(
        http.post('/api/v1/auth/login', async () => {
          await loginPending
          return HttpResponse.json(mockAuthResponse)
        }),
      )

      const user = userEvent.setup()
      renderLoginPage()

      await user.type(screen.getByLabelText(/^email$/i), 'admin@example.com')
      await user.type(screen.getByLabelText(/^password$/i), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(screen.getByLabelText(/^password$/i)).toBeDisabled()
      })

      resolveLogin()

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })
  })
})
