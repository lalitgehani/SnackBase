/**
 * Tests for MigrationsPage component (FT3.5)
 *
 * Verifies:
 * - Renders migration history
 * - Status indicators display correctly (applied, pending)
 * - Stats cards render correct counts
 * - Search narrows results
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import MigrationsPage from '../MigrationsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockMigrationsData = {
  revisions: [
    {
      revision: 'abc123def456',
      description: 'Create users table',
      down_revision: null,
      branch_labels: null,
      is_applied: true,
      is_head: false,
      is_dynamic: false,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      revision: 'bbb222ccc333',
      description: 'Add email index',
      down_revision: 'abc123def456',
      branch_labels: null,
      is_applied: true,
      is_head: false,
      is_dynamic: false,
      created_at: '2026-01-15T00:00:00Z',
    },
    {
      revision: 'ddd444eee555',
      description: 'Create posts table',
      down_revision: 'bbb222ccc333',
      branch_labels: null,
      is_applied: false,
      is_head: true,
      is_dynamic: true,
      created_at: null,
    },
  ],
  total: 3,
  current_revision: 'bbb222ccc333',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
  return render(<MigrationsPage />)
}

function setupSuccessHandler(override: Partial<typeof mockMigrationsData> = {}) {
  server.use(
    http.get('/api/v1/migrations', () =>
      HttpResponse.json({ ...mockMigrationsData, ...override }),
    ),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/migrations', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
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

describe('MigrationsPage', () => {
  // -------------------------------------------------------------------------
  // Page header
  // -------------------------------------------------------------------------

  describe('page header', () => {
    it('renders the Migrations heading', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Migrations')).toBeInTheDocument()
      })
    })

    it('renders a Refresh button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows a loading spinner before data loads', () => {
      server.use(
        http.get('/api/v1/migrations', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )
      renderPage()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Stats cards
  // -------------------------------------------------------------------------

  describe('stats cards', () => {
    it('renders the Total Migrations card with correct value', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Total Migrations')).toBeInTheDocument()
      })
      expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('renders Applied count correctly', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Applied')).toBeInTheDocument()
      })
      // 2 applied migrations
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('renders Pending count correctly', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Pending')).toBeInTheDocument()
      })
      // 1 pending migration (total 3 - applied 2)
      expect(screen.getByText('1')).toBeInTheDocument()
    })

    it('renders Current Revision card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Current Revision')).toBeInTheDocument()
      })
    })

    it('shows current revision in card', async () => {
      renderPage()
      await waitFor(() => {
        // The revision appears in both the stats card and the table - check at least one exists
        const els = screen.getAllByText('bbb222ccc333')
        expect(els.length).toBeGreaterThan(0)
      })
    })

    it('shows "None" when there is no current revision', async () => {
      setupSuccessHandler({ current_revision: null })
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('None')).toBeInTheDocument()
      })
    })

    it('shows core and dynamic breakdown in Total Migrations card', async () => {
      renderPage()
      await waitFor(() => {
        // 2 core migrations, 1 dynamic
        expect(screen.getByText(/2 core, 1 dynamic/i)).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Migration table
  // -------------------------------------------------------------------------

  describe('migration history table', () => {
    it('renders the Migration History card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Migration History')).toBeInTheDocument()
      })
    })

    it('renders a row for each migration', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
      // 3 data rows + 1 header row
      const rows = screen.getAllByRole('row')
      expect(rows.length).toBeGreaterThanOrEqual(4)
    })

    it('renders migration descriptions', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
        expect(screen.getByText('Add email index')).toBeInTheDocument()
        expect(screen.getByText('Create posts table')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Search filtering
  // -------------------------------------------------------------------------

  describe('search filtering', () => {
    it('renders the search input', async () => {
      renderPage()
      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search by description or revision/i),
        ).toBeInTheDocument()
      })
    })

    it('filters migrations by description search query', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const searchInput = screen.getByPlaceholderText(/search by description or revision/i)
      await user.type(searchInput, 'email')

      await waitFor(() => {
        expect(screen.getByText('Add email index')).toBeInTheDocument()
        expect(screen.queryByText('Create users table')).not.toBeInTheDocument()
        expect(screen.queryByText('Create posts table')).not.toBeInTheDocument()
      })
    })

    it('filters migrations by revision ID', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const searchInput = screen.getByPlaceholderText(/search by description or revision/i)
      await user.type(searchInput, 'abc123')

      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
        expect(screen.queryByText('Add email index')).not.toBeInTheDocument()
      })
    })

    it('shows "no migrations found" message when search yields no results', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const searchInput = screen.getByPlaceholderText(/search by description or revision/i)
      await user.type(searchInput, 'xyznonexistent')

      await waitFor(() => {
        expect(screen.getByText(/no migrations found matching/i)).toBeInTheDocument()
      })
    })

    it('shows Clear button when search query is entered', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.type(
        screen.getByPlaceholderText(/search by description or revision/i),
        'email',
      )

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument()
      })
    })

    it('clears search and restores all migrations when Clear is clicked', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const searchInput = screen.getByPlaceholderText(/search by description or revision/i)
      await user.type(searchInput, 'email')

      await waitFor(() => {
        expect(screen.queryByText('Create users table')).not.toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /clear/i }))

      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
        expect(screen.getByText('Add email index')).toBeInTheDocument()
        expect(screen.getByText('Create posts table')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays error message when API fails', async () => {
      setupErrorHandler(500, 'Internal server error')
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Failed to load migrations')).toBeInTheDocument()
      })
    })

    it('renders Try Again button on error', async () => {
      setupErrorHandler(500)
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })
    })

    it('retries fetch when Try Again is clicked', async () => {
      setupErrorHandler(500)
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })

      setupSuccessHandler()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /try again/i }))

      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Refresh
  // -------------------------------------------------------------------------

  describe('refresh', () => {
    it('calls the API again when Refresh is clicked', async () => {
      let callCount = 0
      server.use(
        http.get('/api/v1/migrations', () => {
          callCount++
          return HttpResponse.json(mockMigrationsData)
        }),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Create users table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /refresh/i }))

      await waitFor(() => {
        expect(callCount).toBeGreaterThanOrEqual(2)
      })
    })
  })
})
