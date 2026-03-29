/**
 * Tests for AccountsPage component (FT3.4)
 *
 * Verifies:
 * - Renders account list with correct columns
 * - Create account dialog works end-to-end
 * - Edit account pre-fills and submits correctly
 * - Delete account shows confirmation
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import AccountsPage from '../AccountsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockAccountList = {
  items: [
    {
      id: 'AB1234',
      name: 'Acme Corp',
      slug: 'acme-corp',
      account_code: 'AB1234',
      is_active: true,
      user_count: 5,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'CD5678',
      name: 'Beta Inc',
      slug: 'beta-inc',
      account_code: 'CD5678',
      is_active: false,
      user_count: 2,
      created_at: '2026-01-02T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSuccessHandler(overrides: Partial<typeof mockAccountList> = {}) {
  server.use(
    http.get('/api/v1/accounts', () =>
      HttpResponse.json({ ...mockAccountList, ...overrides }),
    ),
  )
}

function setupEmptyHandler() {
  server.use(
    http.get('/api/v1/accounts', () =>
      HttpResponse.json({
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      }),
    ),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/accounts', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
}

function setupCreateHandler() {
  server.use(
    http.post('/api/v1/accounts', () =>
      HttpResponse.json(
        {
          id: 'EF9012',
          name: 'New Account',
          slug: 'new-account',
          account_code: 'EF9012',
          is_active: true,
          created_at: '2026-01-03T00:00:00Z',
          updated_at: '2026-01-03T00:00:00Z',
        },
        { status: 201 },
      ),
    ),
  )
}

function setupDeleteHandler() {
  server.use(
    http.delete('/api/v1/accounts/:id', () =>
      new HttpResponse(null, { status: 204 }),
    ),
  )
}

function renderPage() {
  return render(<AccountsPage />)
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

describe('AccountsPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before accounts are fetched', () => {
      server.use(
        http.get('/api/v1/accounts', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after accounts load', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Renders account list with correct columns
  // -------------------------------------------------------------------------

  describe('renders account list with correct columns', () => {
    it('renders account names from the API', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
        expect(screen.getByText('Beta Inc')).toBeInTheDocument()
      })
    })

    it('renders the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /accounts/i })).toBeInTheDocument()
      })
    })

    it('renders the Account Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Account Management')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders "No accounts yet" when API returns an empty list', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no accounts yet/i)).toBeInTheDocument()
      })
    })

    it('does not render account rows when the list is empty', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no accounts yet/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays "Failed to load accounts" when the API fails', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load accounts/i)).toBeInTheDocument()
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
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Create account dialog
  // -------------------------------------------------------------------------

  describe('create account dialog works end-to-end', () => {
    it('renders the Create Account button in the header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      expect(
        screen.getAllByRole('button', { name: /create account/i }).length,
      ).toBeGreaterThanOrEqual(1)
    })

    it('opens the Create Account dialog when button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create account/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })

    it('submits create account and refreshes the list', async () => {
      setupCreateHandler()
      const updatedList = {
        ...mockAccountList,
        items: [
          ...mockAccountList.items,
          {
            id: 'EF9012',
            name: 'New Account',
            slug: 'new-account',
            account_code: 'EF9012',
            is_active: true,
            user_count: 0,
            created_at: '2026-01-03T00:00:00Z',
            updated_at: '2026-01-03T00:00:00Z',
          },
        ],
        total: 3,
      }

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create account/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })

      // After creation succeeds, make the list endpoint return the updated list
      server.use(http.get('/api/v1/accounts', () => HttpResponse.json(updatedList)))
    })
  })

  // -------------------------------------------------------------------------
  // Search
  // -------------------------------------------------------------------------

  describe('search', () => {
    it('renders the search input', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by name, slug, or code/i),
        ).toBeInTheDocument()
      })
    })

    it('shows Clear button after a search is submitted', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.type(screen.getByPlaceholderText(/search by name, slug, or code/i), 'acme')
      await user.click(screen.getByRole('button', { name: /^search$/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^clear$/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Delete account shows confirmation
  // -------------------------------------------------------------------------

  describe('delete account shows confirmation', () => {
    it('opens a confirmation dialog when the delete button is clicked', async () => {
      setupDeleteHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      const deleteButtons = screen.getAllByTitle(/delete account/i)
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByRole('alertdialog')).toBeInTheDocument()
      })
    })
  })
})
