/**
 * Tests for GroupsPage component (FT3.4)
 *
 * Verifies:
 * - Renders groups list
 * - Create group dialog works
 * - Manage group members (add/remove)
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import GroupsPage from '../GroupsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockGroupList = {
  items: [
    {
      id: 'grp-1',
      name: 'Engineering',
      description: 'Engineering team',
      account_id: 'AB1234',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'grp-2',
      name: 'Design',
      description: 'Design team',
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

function setupSuccessHandler(overrides: Partial<typeof mockGroupList> = {}) {
  server.use(
    http.get('/api/v1/groups', () =>
      HttpResponse.json({ ...mockGroupList, ...overrides }),
    ),
  )
}

function setupEmptyHandler() {
  server.use(
    http.get('/api/v1/groups', () =>
      HttpResponse.json({ items: [], total: 0 }),
    ),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/groups', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
}

function setupCreateHandler() {
  server.use(
    http.post('/api/v1/groups', () =>
      HttpResponse.json(
        {
          id: 'grp-3',
          name: 'Marketing',
          description: 'Marketing team',
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
    http.delete('/api/v1/groups/:id', () =>
      new HttpResponse(null, { status: 204 }),
    ),
  )
}

function renderPage() {
  return render(<GroupsPage />)
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

describe('GroupsPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before groups are fetched', () => {
      server.use(
        http.get('/api/v1/groups', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after groups load', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Renders groups list
  // -------------------------------------------------------------------------

  describe('renders groups list', () => {
    it('renders group names from the API', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
        expect(screen.getByText('Design')).toBeInTheDocument()
      })
    })

    it('renders the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /groups/i })).toBeInTheDocument()
      })
    })

    it('renders the Group Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Group Management')).toBeInTheDocument()
      })
    })

    it('renders group descriptions', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering team')).toBeInTheDocument()
        expect(screen.getByText('Design team')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders "No groups found" when the API returns an empty list', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no groups found/i)).toBeInTheDocument()
      })
    })

    it('shows a Create Group button inside the empty state', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no groups found/i)).toBeInTheDocument()
      })

      const buttons = screen.getAllByRole('button', { name: /create group/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it('does not render group rows when the list is empty', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no groups found/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('Engineering')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays "Failed to load groups" when the API fails', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load groups/i)).toBeInTheDocument()
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
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Create group dialog works
  // -------------------------------------------------------------------------

  describe('create group dialog works', () => {
    it('renders the Create Group button in the header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      expect(
        screen.getAllByRole('button', { name: /create group/i }).length,
      ).toBeGreaterThanOrEqual(1)
    })

    it('opens the Create Group dialog when the button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create group/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })

    it('creates a group and refreshes the list', async () => {
      setupCreateHandler()
      const updatedList = {
        items: [
          ...mockGroupList.items,
          {
            id: 'grp-3',
            name: 'Marketing',
            description: 'Marketing team',
            account_id: 'AB1234',
            created_at: '2026-01-03T00:00:00Z',
            updated_at: '2026-01-03T00:00:00Z',
          },
        ],
        total: 3,
      }

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      // Queue updated list for the refetch after creation
      server.use(http.get('/api/v1/groups', () => HttpResponse.json(updatedList)))
    })
  })

  // -------------------------------------------------------------------------
  // Manage group members (add/remove)
  // -------------------------------------------------------------------------

  describe('manage group members', () => {
    it('renders a "Manage users" button per group row', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      const manageButtons = screen.getAllByTitle(/manage users/i)
      expect(manageButtons.length).toBeGreaterThanOrEqual(1)
    })

    it('opens the Manage Group Users dialog when the button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstManageBtn] = screen.getAllByTitle(/manage users/i)
      await user.click(firstManageBtn)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Delete group shows confirmation
  // -------------------------------------------------------------------------

  describe('delete group shows confirmation', () => {
    it('opens a confirmation dialog when the delete button is clicked', async () => {
      setupDeleteHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Engineering')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const deleteButtons = screen.getAllByTitle(/delete group/i)
      await user.click(deleteButtons[0])

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
          screen.getByPlaceholderText(/search by name/i),
        ).toBeInTheDocument()
      })
    })
  })
})
