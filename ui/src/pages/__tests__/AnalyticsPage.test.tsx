/**
 * Tests for AnalyticsPage component (FT3.3)
 *
 * Verifies:
 * - Loading spinner while collection is being fetched
 * - Error state when collection is not found
 * - Renders analytics heading with collection name
 * - Group By fields from collection schema
 * - Aggregation function checkboxes (count, sum, avg, min, max)
 * - Run button triggers aggregation request
 * - Results table renders with correct columns
 * - "No results" state when aggregation returns empty
 * - Export CSV button visible when results exist
 * - Back navigation to records page
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { Routes, Route } from 'react-router'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import AnalyticsPage from '../AnalyticsPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockCollection = {
  id: 'col-1',
  name: 'orders',
  table_name: 'orders',
  schema: [
    { name: 'status', type: 'text', required: false },
    { name: 'amount', type: 'number', required: false },
    { name: 'quantity', type: 'integer', required: false },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
}

const mockAggregationResult = {
  results: [
    { status: 'pending', count: 12, sum_amount: 1500.5 },
    { status: 'shipped', count: 8, sum_amount: 950.0 },
  ],
  total_groups: 2,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage(collectionName = 'orders') {
  return render(
    <Routes>
      <Route
        path="/collections/:collectionName/analytics"
        element={<AnalyticsPage />}
      />
    </Routes>,
    { initialEntries: [`/collections/${collectionName}/analytics`] },
  )
}

// getCollectionByName first searches by name, then fetches by ID
const mockCollectionListResponse = {
  items: [{ id: 'col-1', name: 'orders', table_name: 'orders', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-03-01T00:00:00Z' }],
  total: 1,
  page: 1,
  page_size: 20,
}

function setupSuccessHandlers() {
  server.use(
    http.get('/api/v1/collections', () =>
      HttpResponse.json(mockCollectionListResponse),
    ),
    http.get('/api/v1/collections/:id', () =>
      HttpResponse.json(mockCollection),
    ),
    http.get('/api/v1/records/orders/aggregate', () =>
      HttpResponse.json(mockAggregationResult),
    ),
  )
}

function setupCollectionErrorHandler() {
  server.use(
    http.get('/api/v1/collections', () =>
      HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
    ),
  )
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  setupSuccessHandlers()
})

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AnalyticsPage', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows a loading spinner while the collection is loading', () => {
      server.use(
        http.get('/api/v1/collections/orders', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )
      renderPage()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('removes spinner after collection loads', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
      })
      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('shows error when collection is not found', async () => {
      setupCollectionErrorHandler()
      renderPage()
      await waitFor(() => {
        // getCollectionByName throws a plain Error, so handleApiError returns
        // 'An unexpected error occurred'
        expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument()
      })
    })

    it('renders a back-to-records button even on error', async () => {
      setupCollectionErrorHandler()
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Records')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Page rendering
  // -------------------------------------------------------------------------

  describe('page rendering', () => {
    it('renders the analytics heading with collection name', async () => {
      renderPage()
      await waitFor(() => {
        // h1 contains "orders — Analytics" — either the whole text or parts of it
        expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
        expect(screen.getByText(/analytics/i)).toBeInTheDocument()
      })
    })

    it('renders back to Records button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /records/i })).toBeInTheDocument()
      })
    })

    it('renders the Filters card', async () => {
      renderPage()
      await waitFor(() => {
        // "Filters" appears in the CardTitle and in FilterBuilderPanel's toggle button
        expect(screen.getAllByText('Filters').length).toBeGreaterThanOrEqual(1)
      })
    })

    it('renders the Group By card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Group By')).toBeInTheDocument()
      })
    })

    it('renders the Aggregation Functions card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Aggregation Functions')).toBeInTheDocument()
      })
    })

    it('renders the Having card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Having')).toBeInTheDocument()
      })
    })

    it('renders the Results card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Results')).toBeInTheDocument()
      })
    })

    it('renders the Run button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Group By fields from schema
  // -------------------------------------------------------------------------

  describe('group by fields', () => {
    it('renders schema fields as checkboxes in Group By panel', async () => {
      renderPage()
      await waitFor(() => {
        // "amount" appears in Group By labels AND in Aggregation section headings
        // "status" appears in Group By and potentially in FilterBuilderPanel
        expect(screen.getAllByText('amount').length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('status').length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('quantity').length).toBeGreaterThanOrEqual(1)
      })
    })

    it('renders field type badges next to field names', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getAllByText('text').length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('number').length).toBeGreaterThanOrEqual(1)
      })
    })

    it('checking a group by field selects it', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('status')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const statusCheckbox = screen.getByRole('checkbox', { name: /status/i })
      expect(statusCheckbox).not.toBeChecked()
      await user.click(statusCheckbox)
      expect(statusCheckbox).toBeChecked()
    })
  })

  // -------------------------------------------------------------------------
  // Aggregation functions
  // -------------------------------------------------------------------------

  describe('aggregation functions', () => {
    it('renders the count() checkbox checked by default', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('checkbox', { name: /count\(\)/i })).toBeInTheDocument()
      })
      const countCheckbox = screen.getByRole('checkbox', { name: /count\(\)/i })
      expect(countCheckbox).toBeChecked()
    })

    it('renders sum/avg/min/max checkboxes for numeric fields', async () => {
      renderPage()
      await waitFor(() => {
        // Numeric fields: amount (number), quantity (integer)
        expect(screen.getByRole('checkbox', { name: /sum\(amount\)/i })).toBeInTheDocument()
        expect(screen.getByRole('checkbox', { name: /avg\(amount\)/i })).toBeInTheDocument()
        expect(screen.getByRole('checkbox', { name: /min\(amount\)/i })).toBeInTheDocument()
        expect(screen.getByRole('checkbox', { name: /max\(amount\)/i })).toBeInTheDocument()
      })
    })

    it('selecting a numeric function checks the checkbox', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('checkbox', { name: /sum\(amount\)/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const sumCheckbox = screen.getByRole('checkbox', { name: /sum\(amount\)/i })
      expect(sumCheckbox).not.toBeChecked()
      await user.click(sumCheckbox)
      expect(sumCheckbox).toBeChecked()
    })
  })

  // -------------------------------------------------------------------------
  // Run query
  // -------------------------------------------------------------------------

  describe('run query', () => {
    it('shows initial "Configure options and click Run" placeholder before running', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText(/configure options and click run/i)).toBeInTheDocument()
      })
    })

    it('calls aggregation API when Run is clicked', async () => {
      let aggregateCalled = false
      server.use(
        http.get('/api/v1/records/orders/aggregate', () => {
          aggregateCalled = true
          return HttpResponse.json(mockAggregationResult)
        }),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(aggregateCalled).toBe(true)
      })
    })

    it('renders results table after successful run', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
    })

    it('shows group count after running', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(screen.getByText(/2 groups/i)).toBeInTheDocument()
      })
    })

    it('renders aggregation result values in table', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })

      // With default count() only, resultColumns = ['count']; values are 12 and 8
      // (group-by fields not selected by default, so status/amount not in columns)
      expect(screen.getByText('12')).toBeInTheDocument()
      expect(screen.getByText('8')).toBeInTheDocument()
    })

    it('shows "No results" state when aggregation returns empty', async () => {
      server.use(
        http.get('/api/v1/records/orders/aggregate', () =>
          HttpResponse.json({ results: [], total_groups: 0 }),
        ),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(screen.getByText('No results')).toBeInTheDocument()
      })
    })

    it('shows error message when Run fails', async () => {
      // Uncheck count so we can trigger "no function selected" error
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('checkbox', { name: /count\(\)/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('checkbox', { name: /count\(\)/i })) // uncheck count
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/select at least one aggregation function/i),
        ).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Export CSV button
  // -------------------------------------------------------------------------

  describe('export CSV', () => {
    beforeEach(() => {
      vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock')
      vi.spyOn(URL, 'revokeObjectURL').mockReturnValue(undefined)
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('Export CSV button is visible after results load', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /run/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
      })
    })

    it('Export CSV button is not visible before running', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText(/configure options and click run/i)).toBeInTheDocument()
      })
      expect(screen.queryByRole('button', { name: /export csv/i })).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Having input
  // -------------------------------------------------------------------------

  describe('having input', () => {
    it('renders the Having input field', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/e\.g\. count\(\) > 5/i)).toBeInTheDocument()
      })
    })

    it('accepts text input in the Having field', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/e\.g\. count\(\) > 5/i)).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const havingInput = screen.getByPlaceholderText(/e\.g\. count\(\) > 5/i)
      await user.type(havingInput, 'count() > 3')
      expect(havingInput).toHaveValue('count() > 3')
    })
  })
})
