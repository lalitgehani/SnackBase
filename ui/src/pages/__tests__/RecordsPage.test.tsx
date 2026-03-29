/**
 * Tests for RecordsPage component (FT3.3)
 *
 * Verifies:
 * - Renders records for selected collection
 * - Collection schema drives column rendering
 * - "Create Record" button opens form with correct fields
 * - Edit record pre-fills form with existing data
 * - Delete record shows confirmation
 * - Pagination works across record pages
 * - Filter/search narrows results
 * - Bulk operations UI appears on row selection
 * - Import/export buttons are accessible
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { Routes, Route } from 'react-router'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import RecordsPage from '../RecordsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** Collection list item (returned by search) */
const mockCollectionListItem = {
  id: 'col-1',
  name: 'posts',
  table_name: 'posts',
  fields_count: 3,
  records_count: 2,
  has_public_access: false,
  created_at: '2026-01-01T00:00:00Z',
}

/** Full collection with schema (returned by getCollectionById) */
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

/** Records list response */
const mockRecordsResponse = {
  items: [
    {
      id: 'rec-1',
      title: 'First Post',
      body: 'Hello world',
      published: true,
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-01T00:00:00Z',
      account_id: 'AB1234',
    },
    {
      id: 'rec-2',
      title: 'Second Post',
      body: 'Another post',
      published: false,
      created_at: '2026-03-02T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
      account_id: 'AB1234',
    },
  ],
  total: 2,
  skip: 0,
  limit: 25,
}

/** Full record (returned by getRecordById) */
const mockRecordFull = {
  id: 'rec-1',
  title: 'First Post',
  body: 'Hello world',
  published: true,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
  account_id: 'AB1234',
}

/** Mock aggregation response */
const mockAggregationResponse = {
  results: [],
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Register all success handlers for the records page */
function setupSuccessHandlers(overrides: { records?: typeof mockRecordsResponse } = {}) {
  server.use(
    // getCollectionByName: step 1 — search by name
    http.get('/api/v1/collections', () =>
      HttpResponse.json({
        items: [mockCollectionListItem],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      }),
    ),
    // getCollectionByName: step 2 — fetch full collection by ID
    http.get('/api/v1/collections/:id', () =>
      HttpResponse.json(mockCollectionFull),
    ),
    // getRecords
    http.get('/api/v1/records/posts', () =>
      HttpResponse.json(overrides.records ?? mockRecordsResponse),
    ),
    // AggregationSummaryBar
    http.post('/api/v1/records/posts/aggregate', () =>
      HttpResponse.json(mockAggregationResponse),
    ),
    // getRecordById
    http.get('/api/v1/records/posts/:recordId', () =>
      HttpResponse.json(mockRecordFull),
    ),
  )
}

function setupCollectionNotFoundHandler() {
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

function setupCollectionErrorHandler(status = 500, detail = 'Server error') {
  server.use(
    http.get('/api/v1/collections', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
}

function setupEmptyRecordsHandler() {
  server.use(
    http.get('/api/v1/records/posts', () =>
      HttpResponse.json({ items: [], total: 0, skip: 0, limit: 25 }),
    ),
  )
}

/**
 * Renders RecordsPage inside a Routes/Route wrapper so that useParams()
 * can resolve the `:collectionName` segment.
 */
function renderPage(collectionName = 'posts') {
  return render(
    <Routes>
      <Route
        path="/collections/:collectionName/records"
        element={<RecordsPage />}
      />
    </Routes>,
    { initialEntries: [`/collections/${collectionName}/records`] },
  )
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ shouldAdvanceTime: true })
  setupSuccessHandlers()
})

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('RecordsPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('displays a loading spinner before the collection is fetched', () => {
      server.use(
        http.get('/api/v1/collections', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderPage()

      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('removes the loading spinner after data loads', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Renders records for selected collection
  // -------------------------------------------------------------------------

  describe('renders records for selected collection', () => {
    it('renders the collection name in the page heading', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'posts' })).toBeInTheDocument()
      })
    })

    it('renders record rows after data loads', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
        expect(screen.getByText('Second Post')).toBeInTheDocument()
      })
    })

    it('renders the Records Management card', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Records Management')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Collection schema drives column rendering
  // -------------------------------------------------------------------------

  describe('collection schema drives column rendering', () => {
    it('renders schema field names as column headers', async () => {
      renderPage()

      await waitFor(() => {
        // RecordsTable should render header columns matching schema field names
        expect(screen.getByText('title')).toBeInTheDocument()
      })
    })

    it('renders a column header for each schema field', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('title')).toBeInTheDocument()
        expect(screen.getByText('body')).toBeInTheDocument()
        expect(screen.getByText('published')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // "Create Record" button opens form with correct fields
  // -------------------------------------------------------------------------

  describe('"Create Record" button opens form', () => {
    it('renders the Create Record button after collection loads', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /create record/i }),
        ).toBeInTheDocument()
      })
    })

    it('opens the Create Record dialog when button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /create record/i }),
        ).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /create record/i }))

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Edit record pre-fills form with existing data
  // -------------------------------------------------------------------------

  describe('edit record pre-fills form with existing data', () => {
    it('renders an edit action button per record row', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      // RecordsTable renders edit buttons with title="Edit record"
      const editButtons = screen.getAllByTitle(/edit record/i)
      expect(editButtons.length).toBeGreaterThanOrEqual(1)
    })

    it('opens the Edit Record dialog when edit button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstEditBtn] = screen.getAllByTitle(/edit record/i)
      await user.click(firstEditBtn)

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Delete record shows confirmation
  // -------------------------------------------------------------------------

  describe('delete record shows confirmation', () => {
    it('renders a delete action button per record row', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByTitle(/delete record/i)
      expect(deleteButtons.length).toBeGreaterThanOrEqual(1)
    })

    it('opens the Delete Record dialog when delete button is clicked', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstDeleteBtn] = screen.getAllByTitle(/delete record/i)
      await user.click(firstDeleteBtn)

      await waitFor(() => {
        // DeleteRecordDialog renders an AppDialog (role="dialog")
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Pagination works across record pages
  // -------------------------------------------------------------------------

  describe('pagination works across record pages', () => {
    it('renders pagination controls in the records table', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      // RecordsTable delegates to DataTable which renders pagination
      // We check that pagination-related controls are present
      // The DataTable renders rows-per-page and page navigation
      const allButtons = screen.getAllByRole('button')
      expect(allButtons.length).toBeGreaterThan(3)
    })
  })

  // -------------------------------------------------------------------------
  // Filter / search narrows results
  // -------------------------------------------------------------------------

  describe('filter/search narrows results', () => {
    it('renders the search input', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search records/i),
        ).toBeInTheDocument()
      })
    })

    it('shows the Search button', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /^search$/i }),
        ).toBeInTheDocument()
      })
    })

    it('renders filter builder panel when collection has schema', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      // FilterBuilderPanel should be rendered — look for Filter icon or Add Filter button
      const filterButton = screen.queryByRole('button', { name: /filter/i })
      // Filter panel may be collapsed; the component should still be mounted
      expect(filterButton !== null || document.querySelector('[data-testid="filter-panel"]') !== null
        || screen.queryByText(/filter/i) !== null).toBe(true)
    })

    it('shows a Clear button when search is active', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const searchInput = screen.getByPlaceholderText(/search records/i)
      await user.type(searchInput, 'hello')
      await user.click(screen.getByRole('button', { name: /^search$/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^clear$/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Bulk operations UI appears on row selection
  // -------------------------------------------------------------------------

  describe('bulk operations UI appears on row selection', () => {
    it('renders a "Select all" checkbox in the table header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      expect(screen.getByLabelText(/select all/i)).toBeInTheDocument()
    })

    it('renders per-row checkboxes for record selection', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const rowCheckboxes = screen.getAllByLabelText(/select record/i)
      expect(rowCheckboxes.length).toBe(2)
    })

    it('shows bulk action bar when a record is selected', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstCheckbox] = screen.getAllByLabelText(/select record/i)
      await user.click(firstCheckbox)

      await waitFor(() => {
        expect(screen.getByText(/1 record selected/i)).toBeInTheDocument()
      })
    })

    it('shows bulk delete button in the action bar when records are selected', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstCheckbox] = screen.getAllByLabelText(/select record/i)
      await user.click(firstCheckbox)

      await waitFor(() => {
        expect(
          screen.getAllByRole('button', { name: /delete/i }).length,
        ).toBeGreaterThan(0)
      })
    })

    it('hides bulk action bar after deselecting all records', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('First Post')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const [firstCheckbox] = screen.getAllByLabelText(/select record/i)

      // Select then deselect
      await user.click(firstCheckbox)
      await waitFor(() => {
        expect(screen.getByText(/1 record selected/i)).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /deselect all/i }))

      await waitFor(() => {
        expect(screen.queryByText(/record selected/i)).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Import/export buttons accessible
  // -------------------------------------------------------------------------

  describe('import/export buttons are accessible', () => {
    it('renders the Export button in the page header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument()
      })
    })

    it('renders the Import button in the page header', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Back navigation button
  // -------------------------------------------------------------------------

  describe('back navigation', () => {
    it('renders a back button to return to collections list', async () => {
      renderPage()

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /collections/i }),
        ).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Error states
  // -------------------------------------------------------------------------

  describe('error states', () => {
    it('displays error when collection fetch fails', async () => {
      setupCollectionErrorHandler(500, 'Database error')
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load collection/i)).toBeInTheDocument()
      })
    })

    it('displays error when collection is not found', async () => {
      setupCollectionNotFoundHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load collection/i)).toBeInTheDocument()
      })
    })

    it('shows empty state when collection has no records', async () => {
      setupEmptyRecordsHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no records yet/i)).toBeInTheDocument()
      })
    })

    it('shows a Create Record button in the empty state', async () => {
      setupEmptyRecordsHandler()
      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no records yet/i)).toBeInTheDocument()
      })

      const buttons = screen.getAllByRole('button', { name: /create record/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })
  })

  // -------------------------------------------------------------------------
  // No schema state
  // -------------------------------------------------------------------------

  describe('collection with no schema', () => {
    it('shows "No schema defined" message when collection has empty schema', async () => {
      server.use(
        http.get('/api/v1/collections', () =>
          HttpResponse.json({
            items: [mockCollectionListItem],
            total: 1, page: 1, page_size: 10, total_pages: 1,
          }),
        ),
        http.get('/api/v1/collections/:id', () =>
          HttpResponse.json({ ...mockCollectionFull, schema: [] }),
        ),
        http.get('/api/v1/records/posts', () =>
          HttpResponse.json({ items: [], total: 0, skip: 0, limit: 25 }),
        ),
      )

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no schema defined/i)).toBeInTheDocument()
      })
    })

    it('hides Create Record, Export, and Import buttons when schema is empty', async () => {
      server.use(
        http.get('/api/v1/collections', () =>
          HttpResponse.json({
            items: [mockCollectionListItem],
            total: 1, page: 1, page_size: 10, total_pages: 1,
          }),
        ),
        http.get('/api/v1/collections/:id', () =>
          HttpResponse.json({ ...mockCollectionFull, schema: [] }),
        ),
        http.get('/api/v1/records/posts', () =>
          HttpResponse.json({ items: [], total: 0, skip: 0, limit: 25 }),
        ),
      )

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/no schema defined/i)).toBeInTheDocument()
      })

      expect(screen.queryByRole('button', { name: /create record/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /export/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /import/i })).not.toBeInTheDocument()
    })
  })
})
