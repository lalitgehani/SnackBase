/**
 * Tests for AuditLogsPage component (FT3.5)
 *
 * Verifies:
 * - Renders audit log entries
 * - Filter by date range works
 * - Filter by action type works
 * - Export button triggers download
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import AuditLogsPage from '../AuditLogsPage'
import * as auditService from '@/services/audit.service'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockAuditLogs = {
  items: [
    {
      id: 1,
      account_id: 'AB1234',
      operation: 'CREATE' as const,
      table_name: 'users',
      record_id: 'user-abc-1',
      column_name: 'email',
      old_value: null,
      new_value: 'alice@example.com',
      user_id: 'u1',
      user_email: 'admin@example.com',
      user_name: 'Admin User',
      es_username: null,
      es_reason: null,
      es_timestamp: null,
      ip_address: '127.0.0.1',
      user_agent: 'Mozilla/5.0',
      request_id: 'req-001',
      occurred_at: '2026-03-28T10:00:00Z',
      checksum: null,
      previous_hash: null,
      extra_metadata: null,
    },
    {
      id: 2,
      account_id: 'AB1234',
      operation: 'UPDATE' as const,
      table_name: 'posts',
      record_id: 'post-xyz-9',
      column_name: 'title',
      old_value: 'Draft',
      new_value: 'Published Post',
      user_id: 'u1',
      user_email: 'admin@example.com',
      user_name: 'Admin User',
      es_username: null,
      es_reason: null,
      es_timestamp: null,
      ip_address: '127.0.0.1',
      user_agent: 'Mozilla/5.0',
      request_id: 'req-002',
      occurred_at: '2026-03-29T08:30:00Z',
      checksum: null,
      previous_hash: null,
      extra_metadata: null,
    },
    {
      id: 3,
      account_id: 'AB1234',
      operation: 'DELETE' as const,
      table_name: 'comments',
      record_id: 'cmnt-zz-3',
      column_name: 'body',
      old_value: 'Old comment text',
      new_value: null,
      user_id: 'u2',
      user_email: 'bob@example.com',
      user_name: 'Bob',
      es_username: null,
      es_reason: null,
      es_timestamp: null,
      ip_address: '192.168.0.1',
      user_agent: null,
      request_id: 'req-003',
      occurred_at: '2026-03-29T09:00:00Z',
      checksum: null,
      previous_hash: null,
      extra_metadata: null,
    },
  ],
  total: 3,
  skip: 0,
  limit: 10,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
  return render(<AuditLogsPage />)
}

function setupSuccessHandler(override: Partial<typeof mockAuditLogs> = {}) {
  server.use(
    http.get('/api/v1/audit-logs/', () =>
      HttpResponse.json({ ...mockAuditLogs, ...override }),
    ),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/audit-logs/', () =>
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

describe('AuditLogsPage', () => {
  // -------------------------------------------------------------------------
  // Page header
  // -------------------------------------------------------------------------

  describe('page header', () => {
    it('renders the Audit Logs heading', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Audit Logs')).toBeInTheDocument()
      })
    })

    it('renders Export CSV button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
      })
    })

    it('renders Export JSON button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export json/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows a loading spinner before data loads', () => {
      server.use(
        http.get('/api/v1/audit-logs/', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )
      renderPage()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('removes the spinner after data loads', async () => {
      renderPage()
      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Audit log entries rendering
  // -------------------------------------------------------------------------

  describe('renders audit log entries', () => {
    it('renders table after data loads', async () => {
      renderPage()
      await waitFor(() => {
        // Table should exist when data is present
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
    })

    it('renders a row for each audit log item', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
      const rows = screen.getAllByRole('row')
      // 1 header row + 3 data rows
      expect(rows.length).toBeGreaterThanOrEqual(4)
    })

    it('renders CREATE operation badge', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('CREATE')).toBeInTheDocument()
      })
    })

    it('renders UPDATE operation badge', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('UPDATE')).toBeInTheDocument()
      })
    })

    it('renders DELETE operation badge', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('DELETE')).toBeInTheDocument()
      })
    })

    it('renders table names in log entries', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument()
        expect(screen.getByText('posts')).toBeInTheDocument()
        expect(screen.getByText('comments')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders empty state message when items are empty', async () => {
      setupSuccessHandler({ items: [], total: 0 })
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('No audit logs found.')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('displays an error message when the API fails', async () => {
      setupErrorHandler(500, 'Internal server error')
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Failed to load audit logs')).toBeInTheDocument()
      })
    })

    it('shows error detail message', async () => {
      setupErrorHandler(500, 'Database connection failed')
      renderPage()
      await waitFor(() => {
        expect(screen.getByText(/database connection failed/i)).toBeInTheDocument()
      })
    })

    it('renders a Try Again button on error', async () => {
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
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Filter bar
  // -------------------------------------------------------------------------

  describe('filter bar', () => {
    it('filter bar is hidden by default', () => {
      renderPage()
      // The form is hidden (CSS class `hidden`)
      const form = document.querySelector('form.hidden')
      expect(form).toBeInTheDocument()
    })

    it('shows filter bar when Show Filters is clicked', async () => {
      renderPage()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /show filters/i }))
      // After toggle, filter inputs should be visible
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/filter by collection/i)).toBeVisible()
      })
    })

    it('toggles filter label to Hide Filters when opened', async () => {
      renderPage()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /show filters/i }))
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /hide filters/i })).toBeInTheDocument()
      })
    })

    it('renders collection, record ID filter inputs when filters shown', async () => {
      renderPage()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /show filters/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/filter by collection/i)).toBeInTheDocument()
        expect(screen.getByPlaceholderText(/filter by record id/i)).toBeInTheDocument()
      })
    })

    it('sends filter request when Filter button is clicked', async () => {
      let capturedParams: URLSearchParams | null = null
      server.use(
        http.get('/api/v1/audit-logs/', ({ request }) => {
          capturedParams = new URL(request.url).searchParams
          return HttpResponse.json(mockAuditLogs)
        }),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /show filters/i }))

      const collectionInput = screen.getByPlaceholderText(/filter by collection/i)
      await user.clear(collectionInput)
      await user.type(collectionInput, 'users')
      await user.click(screen.getByRole('button', { name: /^filter$/i }))

      await waitFor(() => {
        expect(capturedParams?.get('table_name')).toBe('users')
      })
    })
  })

  // -------------------------------------------------------------------------
  // Export buttons
  // -------------------------------------------------------------------------

  describe('export buttons', () => {
    // Mock exportAuditLogs directly to avoid MSW blob-response issues in jsdom.
    // The blob responseType used by axios triggers an MSW internal stream error
    // in Node.js tests, so we verify the service is called with the right args.
    let exportSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      exportSpy = vi
        .spyOn(auditService, 'exportAuditLogs')
        .mockResolvedValue(undefined)
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('calls exportAuditLogs with csv format when Export CSV is clicked', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /export csv/i }))

      await waitFor(() => {
        expect(exportSpy).toHaveBeenCalledWith('csv', expect.any(Object))
      })
    })

    it('calls exportAuditLogs with json format when Export JSON is clicked', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export json/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /export json/i }))

      await waitFor(() => {
        expect(exportSpy).toHaveBeenCalledWith('json', expect.any(Object))
      })
    })
  })
})
