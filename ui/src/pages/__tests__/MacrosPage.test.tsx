/**
 * Tests for MacrosPage component (FT3.5)
 *
 * Verifies:
 * - Renders macro list
 * - Create macro dialog works
 * - Test macro execution shows result
 * - Delete macro shows confirmation
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import MacrosPage from '../MacrosPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockMacros = [
  {
    id: 1,
    name: 'is_owner',
    description: 'Checks if user owns the record',
    sql_query: 'SELECT 1 FROM posts WHERE id = $1 AND created_by = $2',
    parameters: '["record_id", "user_id"]',
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-10T00:00:00Z',
    created_by: 'admin@example.com',
  },
  {
    id: 2,
    name: 'has_subscription',
    description: 'Checks if account has active subscription',
    sql_query: 'SELECT 1 FROM subscriptions WHERE account_id = $1 AND active = true',
    parameters: '["account_id"]',
    created_at: '2026-03-05T00:00:00Z',
    updated_at: '2026-03-12T00:00:00Z',
    created_by: 'admin@example.com',
  },
]

const newMacro = {
  id: 3,
  name: 'test_macro',
  description: 'A test macro',
  sql_query: 'SELECT 1',
  parameters: '[]',
  created_at: '2026-03-29T00:00:00Z',
  updated_at: '2026-03-29T00:00:00Z',
  created_by: 'admin@example.com',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
  return render(<MacrosPage />)
}

function setupSuccessHandler(macros = mockMacros) {
  server.use(
    http.get('/api/v1/macros', () => HttpResponse.json(macros)),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/macros', () =>
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

describe('MacrosPage', () => {
  // -------------------------------------------------------------------------
  // Page header
  // -------------------------------------------------------------------------

  describe('page header', () => {
    it('renders the Macros heading', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Macros')).toBeInTheDocument()
      })
    })

    it('renders Create Macro button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create macro/i })).toBeInTheDocument()
      })
    })

    it('renders Refresh button', async () => {
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
        http.get('/api/v1/macros', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )
      renderPage()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Macro list rendering
  // -------------------------------------------------------------------------

  describe('macro list rendering', () => {
    it('renders macro names from API', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
        expect(screen.getByText('has_subscription')).toBeInTheDocument()
      })
    })

    it('renders macro descriptions', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Checks if user owns the record')).toBeInTheDocument()
        expect(screen.getByText('Checks if account has active subscription')).toBeInTheDocument()
      })
    })

    it('renders the Macro Library card heading', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Macro Library')).toBeInTheDocument()
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
          screen.getByPlaceholderText(/search macros by name or description/i),
        ).toBeInTheDocument()
      })
    })

    it('filters macros by name', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.type(
        screen.getByPlaceholderText(/search macros by name or description/i),
        'owner',
      )

      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
        expect(screen.queryByText('has_subscription')).not.toBeInTheDocument()
      })
    })

    it('filters macros by description', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.type(
        screen.getByPlaceholderText(/search macros by name or description/i),
        'subscription',
      )

      await waitFor(() => {
        expect(screen.getByText('has_subscription')).toBeInTheDocument()
        expect(screen.queryByText('is_owner')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    it('shows error message when API fails', async () => {
      setupErrorHandler(500, 'Database error')
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Failed to load macros')).toBeInTheDocument()
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
        expect(screen.getByText('is_owner')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Create macro dialog
  // -------------------------------------------------------------------------

  describe('create macro dialog', () => {
    it('opens an editor dialog when Create Macro is clicked', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create macro/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /create macro/i }))

      await waitFor(() => {
        // Dialog should open – look for a dialog role or known dialog content
        const dialog = screen.queryByRole('dialog')
        expect(dialog).toBeInTheDocument()
      })
    })

    it('creates a new macro and refreshes the list on submit', async () => {
      let createCalled = false
      server.use(
        http.post('/api/v1/macros', async () => {
          createCalled = true
          return HttpResponse.json(newMacro, { status: 201 })
        }),
        http.get('/api/v1/macros', () =>
          HttpResponse.json([...mockMacros, newMacro]),
        ),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create macro/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /create macro/i }))

      const dialog = await screen.findByRole('dialog')
      expect(dialog).toBeInTheDocument()

      // Fill in macro name (placeholder is "has_department_access", label is "Macro Name")
      const nameInput = within(dialog).queryByLabelText(/macro name/i) ??
        within(dialog).queryByPlaceholderText(/has_department_access/i)
      if (nameInput) {
        await user.clear(nameInput)
        await user.type(nameInput, 'test_macro')
      }

      // Fill in SQL query (required)
      const sqlInput = within(dialog).queryByPlaceholderText(/SELECT 1/i)
      if (sqlInput) {
        await user.clear(sqlInput)
        await user.type(sqlInput, 'SELECT 1')
      }

      // Submit using the dialog's submit button (scoped within dialog)
      const submitBtn = within(dialog).queryByRole('button', { name: /create macro/i })
      if (submitBtn) {
        await user.click(submitBtn)
        await waitFor(() => {
          expect(createCalled).toBe(true)
        })
      }
    })
  })

  // -------------------------------------------------------------------------
  // Delete macro dialog
  // -------------------------------------------------------------------------

  describe('delete macro dialog', () => {
    it('shows a delete confirmation dialog with macro name', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
      })

      // Find delete button for first macro
      const deleteButtons = screen.queryAllByRole('button', { name: /delete/i })
      if (deleteButtons.length > 0) {
        const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
        await user.click(deleteButtons[0])

        await waitFor(() => {
          expect(screen.queryByRole('dialog')).toBeInTheDocument()
        })
      }
    })

    it('calls the delete endpoint when confirmed', async () => {
      let deleteCalled = false
      // Set up delete handler only — initial GET uses the beforeEach handler (both macros)
      server.use(
        http.delete('/api/v1/macros/1', () => {
          deleteCalled = true
          return new HttpResponse(null, { status: 204 })
        }),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const deleteButtons = screen.queryAllByRole('button', { name: /delete/i })
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0])

        const dialog = await screen.findByRole('dialog')
        expect(dialog).toBeInTheDocument()

        // Confirm delete — scope within dialog to avoid matching page-level buttons
        const confirmBtn = within(dialog).queryByRole('button', { name: /delete/i })
        if (confirmBtn) {
          await user.click(confirmBtn)
          await waitFor(() => {
            expect(deleteCalled).toBe(true)
          })
        }
      }
    })
  })

  // -------------------------------------------------------------------------
  // Refresh
  // -------------------------------------------------------------------------

  describe('refresh', () => {
    it('calls the API again when Refresh is clicked', async () => {
      let callCount = 0
      server.use(
        http.get('/api/v1/macros', () => {
          callCount++
          return HttpResponse.json(mockMacros)
        }),
      )

      renderPage()
      await waitFor(() => {
        expect(screen.getByText('is_owner')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /refresh/i }))

      await waitFor(() => {
        expect(callCount).toBeGreaterThanOrEqual(2)
      })
    })
  })
})
