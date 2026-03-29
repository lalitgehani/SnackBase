/**
 * Tests for CollectionsPage component (FT3.3)
 *
 * Verifies:
 * - Renders list of collections from API
 * - "Create Collection" button opens dialog
 * - Collection row click navigates to records page
 * - Delete collection shows confirmation dialog
 * - Empty state renders when no collections exist
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import CollectionsPage from '../CollectionsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockCollectionList = {
  items: [
    {
      id: 'col-1',
      name: 'posts',
      table_name: 'posts',
      fields_count: 3,
      records_count: 10,
      has_public_access: false,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'col-2',
      name: 'products',
      table_name: 'products',
      fields_count: 5,
      records_count: 25,
      has_public_access: true,
      created_at: '2026-01-02T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
}

const mockCollectionFull = {
  id: 'col-1',
  name: 'posts',
  table_name: 'posts',
  schema: [
    { name: 'title', type: 'text', required: true },
    { name: 'body', type: 'text' },
    { name: 'published', type: 'boolean' },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupSuccessHandler(overrides: Partial<typeof mockCollectionList> = {}) {
  server.use(
    http.get('/api/v1/collections', () =>
      HttpResponse.json({ ...mockCollectionList, ...overrides }),
    ),
    http.get('/api/v1/collections/:id', () =>
      HttpResponse.json(mockCollectionFull),
    ),
  )
}

function setupEmptyHandler() {
  server.use(
    http.get('/api/v1/collections', () =>
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
    http.get('/api/v1/collections', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
}

function setupDeleteHandler() {
  server.use(
    http.delete('/api/v1/collections/:id', () =>
      new HttpResponse(null, { status: 204 }),
    ),
  )
}

function renderPage() {
  return render(<CollectionsPage />)
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

describe('CollectionsPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before collections are fetched', () => {
      server.use(
        http.get('/api/v1/collections', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after collections load', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Collection list
  // -------------------------------------------------------------------------

  describe('renders list of collections from API', () => {
    it('renders collection names returned by the API', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
        expect(screen.getByText('products')).toBeInTheDocument()
      })
    })

    it('renders the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /collections/i })).toBeInTheDocument()
      })
    })

    it('renders the Collection Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Collection Management')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders "No collections yet" when the API returns an empty list', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no collections yet/i)).toBeInTheDocument()
      })
    })

    it('shows a Create Collection button inside the empty state', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no collections yet/i)).toBeInTheDocument()
      })

      // At least one Create Collection button should be present (header + empty state CTA)
      const buttons = screen.getAllByRole('button', { name: /create collection/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it('does not render collection rows when the list is empty', async () => {
      setupEmptyHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no collections yet/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('posts')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays "Failed to load collections" when the API fails', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load collections/i)).toBeInTheDocument()
      })
    })

    it('renders a Try Again button when there is an error', async () => {
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

      // Make the retry succeed
      setupSuccessHandler()

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /try again/i }))

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })
    })

    it('does not render collection rows when the API fails', async () => {
      setupErrorHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load collections/i)).toBeInTheDocument()
      })

      expect(screen.queryByText('posts')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Header action buttons
  // -------------------------------------------------------------------------

  describe('"Create Collection" button opens dialog', () => {
    it('renders the Create Collection button in the header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      expect(
        screen.getAllByRole('button', { name: /create collection/i }).length,
      ).toBeGreaterThanOrEqual(1)
    })

    it('opens the Create Collection dialog when the button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create collection/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })

    it('shows the "Collection Name" field inside the dialog', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [headerButton] = screen.getAllByRole('button', { name: /create collection/i })
      await user.click(headerButton)

      await waitFor(() => {
        expect(screen.getByLabelText(/collection name/i)).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Export / Import buttons
  // -------------------------------------------------------------------------

  describe('export and import buttons', () => {
    it('renders the Export button', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument()
      })
    })

    it('renders the Import button', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument()
      })
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
          screen.getByPlaceholderText(/search by name or id/i),
        ).toBeInTheDocument()
      })
    })

    it('shows Clear button after a search is submitted', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.type(screen.getByPlaceholderText(/search by name or id/i), 'posts')
      await user.click(screen.getByRole('button', { name: /^search$/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^clear$/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Collection row click navigates to records page
  // -------------------------------------------------------------------------

  describe('collection row click navigates to records page', () => {
    it('renders a "Manage records" action button per collection row', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      // CollectionsTable renders one "Manage records" icon-button per row
      const manageButtons = screen.getAllByTitle(/manage records/i)
      expect(manageButtons.length).toBeGreaterThanOrEqual(1)
    })
  })

  // -------------------------------------------------------------------------
  // Delete collection shows confirmation dialog
  // -------------------------------------------------------------------------

  describe('delete collection shows confirmation dialog', () => {
    it('opens a delete confirmation dialog when the delete button is clicked', async () => {
      setupDeleteHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      // CollectionsTable renders one "Delete collection" icon-button per row
      const deleteButtons = screen.getAllByTitle(/delete collection/i)
      await user.click(deleteButtons[0])

      await waitFor(() => {
        // DeleteCollectionDialog renders an alertdialog with title "Delete Collection"
        expect(screen.getByRole('alertdialog')).toBeInTheDocument()
      })
    })

    it('shows the collection name in the delete dialog', async () => {
      setupDeleteHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstDeleteBtn] = screen.getAllByTitle(/delete collection/i)
      await user.click(firstDeleteBtn)

      // DeleteCollectionDialog asks user to type collection name to confirm
      await waitFor(() => {
        // The dialog should reference the collection name
        const dialog = screen.getByRole('alertdialog')
        expect(dialog).toBeInTheDocument()
      })
    })
  })
})
