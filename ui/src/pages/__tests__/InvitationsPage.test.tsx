/**
 * Tests for InvitationsPage component (FT3.4)
 *
 * Verifies:
 * - Renders invitations with status badges
 * - Create invitation dialog works
 * - Cancel invitation works
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import InvitationsPage from '../InvitationsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockInvitationList = {
  invitations: [
    {
      id: 'inv-1',
      email: 'pending@example.com',
      status: 'pending',
      token: 'tok-pending-1',
      account_id: 'AB1234',
      account_code: 'AB1234',
      email_sent: true,
      expires_at: '2026-04-30T00:00:00Z',
      created_at: '2026-03-29T00:00:00Z',
      updated_at: '2026-03-29T00:00:00Z',
    },
    {
      id: 'inv-2',
      email: 'accepted@example.com',
      status: 'accepted',
      token: 'tok-accepted-2',
      account_id: 'AB1234',
      account_code: 'AB1234',
      email_sent: true,
      expires_at: '2026-04-15T00:00:00Z',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-10T00:00:00Z',
    },
    {
      id: 'inv-3',
      email: 'expired@example.com',
      status: 'expired',
      token: 'tok-expired-3',
      account_id: 'AB1234',
      account_code: 'AB1234',
      email_sent: false,
      expires_at: '2026-01-01T00:00:00Z',
      created_at: '2025-12-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
  total: 3,
}

// The InvitationsPage also loads accounts for the filter dropdown
const mockAccountList = {
  items: [
    {
      id: 'AB1234',
      name: 'Acme Corp',
      slug: 'acme-corp',
      account_code: 'AB1234',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
  total_pages: 1,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSuccessHandler(overrides: Partial<typeof mockInvitationList> = {}) {
  server.use(
    http.get('/api/v1/invitations', () =>
      HttpResponse.json({ ...mockInvitationList, ...overrides }),
    ),
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
  )
}

function setupEmptyHandler() {
  server.use(
    http.get('/api/v1/invitations', () =>
      HttpResponse.json({ invitations: [], total: 0 }),
    ),
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/invitations', () =>
      HttpResponse.json({ detail }, { status }),
    ),
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
  )
}

function setupCancelHandler() {
  server.use(
    http.delete('/api/v1/invitations/:id', () =>
      new HttpResponse(null, { status: 204 }),
    ),
  )
}

function renderPage() {
  return render(<InvitationsPage />)
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ shouldAdvanceTime: true })
  setupSuccessHandler()
})

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('InvitationsPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before invitations are fetched', () => {
      server.use(
        http.get('/api/v1/invitations', async () => {
          await new Promise(() => {}) // never resolves
        }),
        http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after invitations load', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Renders invitations with status badges
  // -------------------------------------------------------------------------

  describe('renders invitations with status badges', () => {
    it('renders invitation emails from the API', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
        expect(screen.getByText('accepted@example.com')).toBeInTheDocument()
        expect(screen.getByText('expired@example.com')).toBeInTheDocument()
      })
    })

    it('renders the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByRole('heading', { name: /invitations/i }),
        ).toBeInTheDocument()
      })
    })

    it('renders the Invitation Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Invitation Management')).toBeInTheDocument()
      })
    })

    it('renders Pending status badge', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Pending')).toBeInTheDocument()
      })
    })

    it('renders Accepted status badge', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Accepted')).toBeInTheDocument()
      })
    })

    it('renders Expired status badge', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Expired')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders "No invitations found" when the API returns an empty list', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no invitations found/i)).toBeInTheDocument()
      })
    })

    it('shows an "Invite your first user" button in the empty state', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no invitations found/i)).toBeInTheDocument()
      })

      expect(
        screen.getByRole('button', { name: /invite your first user/i }),
      ).toBeInTheDocument()
    })

    it('does not render invitation rows when the list is empty', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no invitations found/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('pending@example.com')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays "Failed to load invitations" when the API fails', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load invitations/i)).toBeInTheDocument()
      })
    })

    it('renders a Try Again button on error', async () => {
      setupErrorHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })
    })

    it('retries the fetch when Try Again is clicked', async () => {
      setupErrorHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })

      setupSuccessHandler()

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /try again/i }))

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Create invitation dialog works
  // -------------------------------------------------------------------------

  describe('create invitation dialog works', () => {
    it('renders the Invite User button in the header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      expect(
        screen.getByRole('button', { name: /invite user/i }),
      ).toBeInTheDocument()
    })

    it('opens the Create Invitation dialog when the Invite User button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /invite user/i }))

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Cancel invitation works
  // -------------------------------------------------------------------------

  describe('cancel invitation works', () => {
    it('renders a Cancel Invitation button for pending invitations', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      // Only pending invitations show the cancel button
      const cancelButtons = screen.getAllByTitle(/cancel invitation/i)
      expect(cancelButtons.length).toBeGreaterThanOrEqual(1)
    })

    it('does not render cancel button for non-pending invitations', async () => {
      // Render with only accepted and expired invitations (no pending)
      server.use(
        http.get('/api/v1/invitations', () =>
          HttpResponse.json({
            invitations: [
              mockInvitationList.invitations[1], // accepted
              mockInvitationList.invitations[2], // expired
            ],
            total: 2,
          }),
        ),
      )

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('accepted@example.com')).toBeInTheDocument()
      })

      expect(screen.queryByTitle(/cancel invitation/i)).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Resend email action
  // -------------------------------------------------------------------------

  describe('resend email action', () => {
    it('renders a Resend Email button for pending invitations', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      const resendButtons = screen.getAllByTitle(/resend email/i)
      expect(resendButtons.length).toBeGreaterThanOrEqual(1)
    })
  })

  // -------------------------------------------------------------------------
  // Copy link action
  // -------------------------------------------------------------------------

  describe('copy link action', () => {
    it('renders a Copy Link button for pending invitations', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      const copyButtons = screen.getAllByTitle(/copy link/i)
      expect(copyButtons.length).toBeGreaterThanOrEqual(1)
    })
  })

  // -------------------------------------------------------------------------
  // Status filter dropdown
  // -------------------------------------------------------------------------

  describe('status filter', () => {
    it('renders the Status filter dropdown', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('pending@example.com')).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/status/i)).toBeInTheDocument()
    })
  })
})
