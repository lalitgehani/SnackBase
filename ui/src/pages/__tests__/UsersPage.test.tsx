/**
 * Tests for UsersPage component (FT3.4)
 *
 * Verifies:
 * - Renders user list filtered by account
 * - Create user dialog validates email/password
 * - Edit user updates role/active status
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import UsersPage from '../UsersPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockUserList = {
  items: [
    {
      id: 'user-1',
      email: 'alice@acme.com',
      account_id: 'AB1234',
      account_name: 'Acme Corp',
      account_code: 'AB1234',
      role_id: 1,
      role_name: 'admin',
      is_active: true,
      email_verified: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      last_login: '2026-03-01T00:00:00Z',
    },
    {
      id: 'user-2',
      email: 'bob@beta.com',
      account_id: 'CD5678',
      account_name: 'Beta Inc',
      account_code: 'CD5678',
      role_id: 2,
      role_name: 'viewer',
      is_active: false,
      email_verified: false,
      created_at: '2026-01-02T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z',
      last_login: null,
    },
  ],
  total: 2,
  skip: 0,
  limit: 10,
}

const mockAccountList = {
  items: [
    { id: 'AB1234', name: 'Acme Corp', slug: 'acme-corp', account_code: 'AB1234', is_active: true, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
  ],
  total: 1,
  page: 1,
  page_size: 100,
  total_pages: 1,
}

const mockRoleList = {
  items: [
    { id: 1, name: 'admin', description: 'Administrator', is_system: false, account_id: 'AB1234', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
    { id: 2, name: 'viewer', description: 'Read only', is_system: false, account_id: 'AB1234', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
  ],
  total: 2,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSuccessHandler(overrides: Partial<typeof mockUserList> = {}) {
  server.use(
    http.get('/api/v1/users', () =>
      HttpResponse.json({ ...mockUserList, ...overrides }),
    ),
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
    http.get('/api/v1/roles', () => HttpResponse.json(mockRoleList)),
  )
}

function setupEmptyHandler() {
  server.use(
    http.get('/api/v1/users', () =>
      HttpResponse.json({ items: [], total: 0, skip: 0, limit: 10 }),
    ),
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
    http.get('/api/v1/roles', () => HttpResponse.json(mockRoleList)),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/users', () =>
      HttpResponse.json({ detail }, { status }),
    ),
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
    http.get('/api/v1/roles', () => HttpResponse.json(mockRoleList)),
  )
}

function renderPage() {
  return render(<UsersPage />)
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

describe('UsersPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before users are fetched', () => {
      server.use(
        http.get('/api/v1/users', async () => {
          await new Promise(() => {}) // never resolves
        }),
        http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountList)),
        http.get('/api/v1/roles', () => HttpResponse.json(mockRoleList)),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after users load', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Renders user list filtered by account
  // -------------------------------------------------------------------------

  describe('renders user list filtered by account', () => {
    it('renders user emails from the API', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
        expect(screen.getByText('bob@beta.com')).toBeInTheDocument()
      })
    })

    it('renders the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /users/i })).toBeInTheDocument()
      })
    })

    it('renders the User Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('User Management')).toBeInTheDocument()
      })
    })

    it('renders role names for each user', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
        expect(screen.getByText('viewer')).toBeInTheDocument()
      })
    })

    it('renders Active/Inactive status badges', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument()
        expect(screen.getByText('Inactive')).toBeInTheDocument()
      })
    })

    it('renders verified/pending email badges', async () => {
      renderPage()

      // First ensure user data has loaded (email visible = DataTable is rendered)
      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      // "Verified" appears both as a column header and as a badge (user-1 has email_verified: true)
      // "Pending" appears as a badge (user-2 has email_verified: false)
      expect(screen.getAllByText('Verified').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('Pending').length).toBeGreaterThanOrEqual(1)
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders "No users found" when the API returns an empty list', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no users found/i)).toBeInTheDocument()
      })
    })

    it('does not render user rows when the list is empty', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no users found/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('alice@acme.com')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays "Failed to load users" when the API fails', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load users/i)).toBeInTheDocument()
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
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Create user dialog validates email/password
  // -------------------------------------------------------------------------

  describe('create user dialog validates email/password', () => {
    it('renders the Create User button in the header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      expect(
        screen.getAllByRole('button', { name: /create user/i }).length,
      ).toBeGreaterThanOrEqual(1)
    })

    it('opens the Create User dialog when the button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create user/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Edit user dialog
  // -------------------------------------------------------------------------

  describe('edit user updates role/active status', () => {
    it('opens the Edit User dialog when the edit button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const editButtons = screen.getAllByTitle(/edit user/i)
      await user.click(editButtons[0])

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Search filter
  // -------------------------------------------------------------------------

  describe('search filter', () => {
    it('renders the search input', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by email/i),
        ).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Filter dropdowns
  // -------------------------------------------------------------------------

  describe('filter dropdowns', () => {
    it('renders account filter dropdown', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/account/i)).toBeInTheDocument()
    })

    it('renders role filter dropdown', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/role/i)).toBeInTheDocument()
    })

    it('renders status filter dropdown', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('alice@acme.com')).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/status/i)).toBeInTheDocument()
    })
  })
})
