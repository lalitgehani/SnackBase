/**
 * Tests for AcceptInvitationPage component (FT3.6)
 *
 * Verifies:
 * - Renders password setup form when a valid invitation token is in the URL
 * - Shows a loading spinner while fetching the invitation
 * - Shows an error when the token is missing from the URL
 * - Shows an error when the token is invalid/expired (API 404/400)
 * - Validates password strength (min 8 characters)
 * - Validates that passwords match
 * - Successful acceptance redirects to /admin/dashboard for admin/superadmin users
 * - Successful acceptance shows a success card for non-admin users
 * - Failed acceptance displays an error message
 * - Submit button is disabled during submission
 *
 * Note on 401 handling: The axios response interceptor intercepts all 401
 * responses to attempt token refresh. Since the accept endpoint can legitimately
 * return non-401 errors (404, 400, 500), those test cases use those status codes.
 * For already-accepted tokens the backend returns 400.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route } from 'react-router'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { useAuthStore } from '@/stores/auth.store'
import AcceptInvitationPage from '../AcceptInvitationPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const VALID_TOKEN = 'valid-invite-token-abc123'

const mockInvitation = {
  email: 'newuser@example.com',
  account_name: 'Acme Corp',
  invited_by_name: 'Jane Admin',
  expires_at: '2026-12-31T00:00:00Z',
  is_valid: true,
}

const mockAuthResponseAdmin = {
  token: 'access-token-abc',
  refresh_token: 'refresh-token-xyz',
  expires_in: 3600,
  account: {
    id: 'AC1234',
    slug: 'acme',
    name: 'Acme Corp',
    created_at: '2024-01-01T00:00:00Z',
  },
  user: {
    id: 'user-1',
    email: 'newuser@example.com',
    role: 'admin',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
}

const mockAuthResponseRegularUser = {
  ...mockAuthResponseAdmin,
  user: {
    ...mockAuthResponseAdmin.user,
    role: 'user',
  },
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
 * Render the AcceptInvitationPage inside a minimal router that also
 * registers /admin/dashboard so navigation assertions work.
 */
function renderPage(token?: string) {
  const path = token
    ? `/accept-invitation?token=${token}`
    : '/accept-invitation'

  return render(
    <Routes>
      <Route path="/accept-invitation" element={<AcceptInvitationPage />} />
      <Route path="/admin/dashboard" element={<div>Dashboard Page</div>} />
    </Routes>,
    { initialEntries: [path] },
  )
}

/** Register default MSW handlers for a valid invitation fetch. */
function mockValidInvitation(token = VALID_TOKEN) {
  server.use(
    http.get(`/api/v1/invitations/${token}`, () =>
      HttpResponse.json(mockInvitation),
    ),
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

describe('AcceptInvitationPage', () => {
  // -------------------------------------------------------------------------
  // Missing token
  // -------------------------------------------------------------------------

  describe('when token is absent from the URL', () => {
    it('shows an error about the missing token', async () => {
      renderPage() // no token query param

      await waitFor(() => {
        expect(screen.getByText(/invitation token is missing/i)).toBeInTheDocument()
      })
    })

    it('does not show the password form', async () => {
      renderPage()

      // Give any async effects time to settle
      await waitFor(() => {
        expect(screen.queryByLabelText(/create password/i)).not.toBeInTheDocument()
      })
    })

    it('shows a link to return to login', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /return to login/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows a loading spinner while fetching the invitation', async () => {
      let resolveRequest!: () => void
      const pending = new Promise<void>((resolve) => { resolveRequest = resolve })

      server.use(
        http.get(`/api/v1/invitations/${VALID_TOKEN}`, async () => {
          await pending
          return HttpResponse.json(mockInvitation)
        }),
      )

      renderPage(VALID_TOKEN)

      // Spinner should be visible immediately
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()

      resolveRequest()

      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Invalid / expired token
  // -------------------------------------------------------------------------

  describe('when the invitation token is invalid or expired', () => {
    it('shows an error when the API returns 404', async () => {
      server.use(
        http.get(`/api/v1/invitations/${VALID_TOKEN}`, () =>
          HttpResponse.json(
            { message: 'Invitation not found.' },
            { status: 404 },
          ),
        ),
      )

      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByText(/invitation not found\./i)).toBeInTheDocument()
      })
    })

    it('falls back to a generic error message when backend provides no message', async () => {
      server.use(
        http.get(`/api/v1/invitations/${VALID_TOKEN}`, () =>
          HttpResponse.json({}, { status: 404 }),
        ),
      )

      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByText(/invalid or expired invitation/i)).toBeInTheDocument()
      })
    })

    it('does not render the password form after a fetch error', async () => {
      server.use(
        http.get(`/api/v1/invitations/${VALID_TOKEN}`, () =>
          HttpResponse.json({ message: 'Expired.' }, { status: 400 }),
        ),
      )

      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.queryByLabelText(/create password/i)).not.toBeInTheDocument()
      })
    })

    it('shows the "Invitation Error" heading on fetch failure', async () => {
      server.use(
        http.get(`/api/v1/invitations/${VALID_TOKEN}`, () =>
          HttpResponse.json({ message: 'Already used.' }, { status: 400 }),
        ),
      )

      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByText(/invitation error/i)).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Already-accepted token
  // -------------------------------------------------------------------------

  describe('already-accepted token', () => {
    it('shows the backend error message for an already-accepted token', async () => {
      server.use(
        http.get(`/api/v1/invitations/${VALID_TOKEN}`, () =>
          HttpResponse.json(
            { message: 'This invitation has already been accepted.' },
            { status: 400 },
          ),
        ),
      )

      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(
          screen.getByText(/this invitation has already been accepted\./i),
        ).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Valid invitation — form rendering
  // -------------------------------------------------------------------------

  describe('with a valid invitation token', () => {
    beforeEach(() => {
      mockValidInvitation()
    })

    it('renders the password form after fetching invitation details', async () => {
      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByLabelText(/create password/i)).toBeInTheDocument()
      })
    })

    it('renders the confirm password field', async () => {
      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
      })
    })

    it('renders the "Join Team" submit button', async () => {
      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /join team/i })).toBeInTheDocument()
      })
    })

    it('displays the invited email address', async () => {
      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByText(/newuser@example\.com/)).toBeInTheDocument()
      })
    })

    it('displays the account name', async () => {
      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByText(/acme corp/i)).toBeInTheDocument()
      })
    })

    it('displays the inviter name', async () => {
      renderPage(VALID_TOKEN)

      await waitFor(() => {
        expect(screen.getByText(/jane admin/i)).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Password validation
  // -------------------------------------------------------------------------

  describe('password validation', () => {
    beforeEach(() => {
      mockValidInvitation()
    })

    it('shows an error when password is shorter than 8 characters', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'short')
      await user.type(screen.getByLabelText(/confirm password/i), 'short')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/password must be at least 8 characters/i),
        ).toBeInTheDocument()
      })
    })

    it('shows an error when passwords do not match', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1')
      await user.type(screen.getByLabelText(/confirm password/i), 'DifferentPass1')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      })
    })

    it('does not call the API when validation fails', async () => {
      let apiCalled = false
      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, () => {
          apiCalled = true
          return HttpResponse.json(mockAuthResponseAdmin)
        }),
      )

      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'bad')
      await user.type(screen.getByLabelText(/confirm password/i), 'bad')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument()
      })

      expect(apiCalled).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // Successful acceptance — admin/superadmin
  // -------------------------------------------------------------------------

  describe('successful acceptance for admin/superadmin user', () => {
    beforeEach(() => {
      mockValidInvitation()
      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, () =>
          HttpResponse.json(mockAuthResponseAdmin),
        ),
      )
    })

    it('navigates to /admin/dashboard after successful acceptance', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })

    it('does not show an error after a successful acceptance', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })

      expect(screen.queryByText(/failed to accept invitation/i)).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Successful acceptance — regular user
  // -------------------------------------------------------------------------

  describe('successful acceptance for a non-admin user', () => {
    beforeEach(() => {
      mockValidInvitation()
      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, () =>
          HttpResponse.json(mockAuthResponseRegularUser),
        ),
      )
    })

    it('shows a success card rather than redirecting to the dashboard', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText(/welcome to snackbase/i)).toBeInTheDocument()
      })
    })

    it('does not navigate to the admin dashboard for a regular user', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument()
      })
    })

    it('shows the account name in the success card', async () => {
      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText(/acme corp/i)).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Failed acceptance
  // -------------------------------------------------------------------------

  describe('failed acceptance', () => {
    beforeEach(() => {
      mockValidInvitation()
    })

    it('displays the generic fallback message when the API returns 500 with no message', async () => {
      server.use(
        // Return a 500 with no message/error fields so the component falls
        // back to the hardcoded "Failed to accept invitation. Please try again."
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, () =>
          HttpResponse.json({}, { status: 500 }),
        ),
      )

      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText(/failed to accept invitation\. please try again\./i)).toBeInTheDocument()
      })
    })

    it('shows the backend error message for a 400 response', async () => {
      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, () =>
          HttpResponse.json(
            { error: 'Password does not meet requirements.' },
            { status: 400 },
          ),
        ),
      )

      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/password does not meet requirements\./i),
        ).toBeInTheDocument()
      })
    })

    it('does not navigate to dashboard after a failed acceptance', async () => {
      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, () =>
          HttpResponse.json({ message: 'Error' }, { status: 500 }),
        ),
      )

      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Loading state during submission
  // -------------------------------------------------------------------------

  describe('loading state during submission', () => {
    beforeEach(() => {
      mockValidInvitation()
    })

    it('disables the submit button while the acceptance request is in flight', async () => {
      let resolveAccept!: () => void
      const pending = new Promise<void>((resolve) => { resolveAccept = resolve })

      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, async () => {
          await pending
          return HttpResponse.json(mockAuthResponseAdmin)
        }),
      )

      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /joining/i })).toBeDisabled()
      })

      resolveAccept()

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })

    it('shows "Joining..." text on the button while submitting', async () => {
      let resolveAccept!: () => void
      const pending = new Promise<void>((resolve) => { resolveAccept = resolve })

      server.use(
        http.post(`/api/v1/invitations/${VALID_TOKEN}/accept`, async () => {
          await pending
          return HttpResponse.json(mockAuthResponseAdmin)
        }),
      )

      const user = userEvent.setup()
      renderPage(VALID_TOKEN)

      await waitFor(() => screen.getByLabelText(/create password/i))

      await user.type(screen.getByLabelText(/create password/i), 'SecurePass1!')
      await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
      await user.click(screen.getByRole('button', { name: /join team/i }))

      await waitFor(() => {
        expect(screen.getByText(/joining\.\.\./i)).toBeInTheDocument()
      })

      resolveAccept()

      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
      })
    })
  })
})
