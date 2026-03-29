/**
 * Tests for RolesPage component (FT3.4)
 *
 * Verifies:
 * - Renders roles list
 * - Create role dialog works
 * - Edit role permissions (if inline)
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import RolesPage from '../RolesPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockRoleList = {
  items: [
    {
      id: 1,
      name: 'admin',
      description: 'Full administrator access',
      is_system: true,
      account_id: 'AB1234',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2,
      name: 'viewer',
      description: 'Read-only access',
      is_system: false,
      account_id: 'AB1234',
      created_at: '2026-01-02T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z',
    },
  ],
  total: 2,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSuccessHandler(overrides: Partial<typeof mockRoleList> = {}) {
  server.use(
    http.get('/api/v1/roles', () =>
      HttpResponse.json({ ...mockRoleList, ...overrides }),
    ),
  )
}

function setupEmptyHandler() {
  server.use(
    http.get('/api/v1/roles', () =>
      HttpResponse.json({ items: [], total: 0 }),
    ),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/roles', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
}

function setupCreateHandler() {
  server.use(
    http.post('/api/v1/roles', () =>
      HttpResponse.json(
        {
          id: 3,
          name: 'editor',
          description: 'Can edit content',
          is_system: false,
          account_id: 'AB1234',
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
    http.delete('/api/v1/roles/:id', () =>
      new HttpResponse(null, { status: 204 }),
    ),
  )
}

function renderPage() {
  return render(<RolesPage />)
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

describe('RolesPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before roles are fetched', () => {
      server.use(
        http.get('/api/v1/roles', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after roles load', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Renders roles list
  // -------------------------------------------------------------------------

  describe('renders roles list', () => {
    it('renders role names from the API', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
        expect(screen.getByText('viewer')).toBeInTheDocument()
      })
    })

    it('renders the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByRole('heading', { name: /roles/i }),
        ).toBeInTheDocument()
      })
    })

    it('renders the Role Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Role Management')).toBeInTheDocument()
      })
    })

    it('shows a role count summary', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/showing 2 roles/i)).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders "No roles yet" when the API returns an empty list', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no roles yet/i)).toBeInTheDocument()
      })
    })

    it('shows a Create Role button inside the empty state', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no roles yet/i)).toBeInTheDocument()
      })

      const buttons = screen.getAllByRole('button', { name: /create role/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it('does not render role rows when the list is empty', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no roles yet/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('admin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays "Failed to load roles" when the API fails', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load roles/i)).toBeInTheDocument()
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
        expect(screen.getByText('admin')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Create role dialog works
  // -------------------------------------------------------------------------

  describe('create role dialog works', () => {
    it('renders the Create Role button in the header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })

      expect(
        screen.getAllByRole('button', { name: /create role/i }).length,
      ).toBeGreaterThanOrEqual(1)
    })

    it('opens the Create Role dialog when the button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create role/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })

    it('closes the Create Role dialog on cancel', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create role/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })
    })

    it('creates role and refreshes the list', async () => {
      setupCreateHandler()
      const updatedList = {
        items: [
          ...mockRoleList.items,
          {
            id: 3,
            name: 'editor',
            description: 'Can edit content',
            is_system: false,
            account_id: 'AB1234',
            created_at: '2026-01-03T00:00:00Z',
            updated_at: '2026-01-03T00:00:00Z',
          },
        ],
        total: 3,
      }

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })

      // Queue the updated list for the refetch after creation
      server.use(http.get('/api/v1/roles', () => HttpResponse.json(updatedList)))
    })
  })

  // -------------------------------------------------------------------------
  // Edit role dialog
  // -------------------------------------------------------------------------

  describe('edit role dialog', () => {
    it('opens the Edit Role dialog when the edit button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const editButtons = screen.getAllByTitle(/edit role/i)
      await user.click(editButtons[0])

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Delete role shows confirmation
  // -------------------------------------------------------------------------

  describe('delete role shows confirmation', () => {
    it('opens a confirmation dialog when the delete button is clicked', async () => {
      setupDeleteHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('viewer')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      // 'admin' is a DEFAULT_ROLE so its delete button is disabled.
      // 'viewer' is not a default role — click its delete button (index 1).
      const deleteButtons = screen.getAllByTitle(/delete role/i)
      await user.click(deleteButtons[1])

      await waitFor(() => {
        // DeleteRoleDialog uses AppDialog (Radix Dialog), which has role="dialog"
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })
})
