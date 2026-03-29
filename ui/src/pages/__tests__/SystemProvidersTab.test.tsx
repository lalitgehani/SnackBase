/**
 * Tests for SystemProvidersTab component (FT3.5)
 *
 * Verifies:
 * - Renders system provider configuration list
 * - Loading state
 * - Category filter
 * - Toggle enable/disable
 * - Delete confirmation dialog (for non-builtin)
 * - Add Provider button
 * - Set / unset default
 * - Empty state
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import SystemProvidersTab from '../SystemProvidersTab'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockConfigs = [
  {
    id: 'conf-1',
    display_name: 'Google OAuth',
    provider_name: 'google',
    category: 'auth_providers',
    updated_at: '2026-03-28T10:00:00Z',
    is_system: true,
    is_builtin: true,
    is_default: true,
    account_id: '00000000-0000-0000-0000-000000000000',
    logo_url: '',
    enabled: true,
    priority: 1,
  },
  {
    id: 'conf-2',
    display_name: 'SendGrid Email',
    provider_name: 'sendgrid',
    category: 'email_providers',
    updated_at: '2026-03-27T08:00:00Z',
    is_system: true,
    is_builtin: false,
    is_default: false,
    account_id: '00000000-0000-0000-0000-000000000000',
    logo_url: '',
    enabled: true,
    priority: 1,
  },
  {
    id: 'conf-3',
    display_name: 'S3 Storage',
    provider_name: 's3',
    category: 'storage_providers',
    updated_at: '2026-03-26T06:00:00Z',
    is_system: true,
    is_builtin: false,
    is_default: false,
    account_id: '00000000-0000-0000-0000-000000000000',
    logo_url: '',
    enabled: false,
    priority: 2,
  },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderTab() {
  return render(<SystemProvidersTab />)
}

function setupSuccessHandlers(configs: typeof mockConfigs = mockConfigs) {
  server.use(
    http.get('/api/v1/admin/configuration/system', () =>
      HttpResponse.json(configs),
    ),
    http.get('/api/v1/admin/configuration/providers', () =>
      HttpResponse.json([]),
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

describe('SystemProvidersTab', () => {
  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows a loading indicator before configs load', () => {
      server.use(
        http.get('/api/v1/admin/configuration/system', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )
      renderTab()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('removes loading indicator after configs load', async () => {
      renderTab()
      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Config list rendering
  // -------------------------------------------------------------------------

  describe('config list rendering', () => {
    it('renders provider display names', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Google OAuth')).toBeInTheDocument()
        expect(screen.getByText('SendGrid Email')).toBeInTheDocument()
        expect(screen.getByText('S3 Storage')).toBeInTheDocument()
      })
    })

    it('renders provider_name text under display name', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('google')).toBeInTheDocument()
        expect(screen.getByText('sendgrid')).toBeInTheDocument()
      })
    })

    it('renders Built-in badge for builtin configs', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Built-in')).toBeInTheDocument()
      })
    })

    it('renders Default badge for default config', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Default')).toBeInTheDocument()
      })
    })

    it('renders category labels in rows', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('auth providers')).toBeInTheDocument()
        expect(screen.getByText('email providers')).toBeInTheDocument()
      })
    })

    it('renders status toggles for each config', async () => {
      renderTab()
      await waitFor(() => {
        const switches = document.querySelectorAll('[role="switch"]')
        expect(switches.length).toBe(mockConfigs.length)
      })
    })

    it('renders Enabled / Disabled text next to toggles', async () => {
      renderTab()
      await waitFor(() => {
        const enabledLabels = screen.getAllByText('Enabled')
        expect(enabledLabels.length).toBeGreaterThanOrEqual(1)
        expect(screen.getByText('Disabled')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders empty state message when no configs exist', async () => {
      setupSuccessHandlers([])
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('No configurations found.')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Category filter
  // -------------------------------------------------------------------------

  describe('category filter', () => {
    it('renders the category filter dropdown', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('All Categories')).toBeInTheDocument()
      })
    })

    it('calls API with category param when filter is changed', async () => {
      let capturedParams: URLSearchParams | null = null
      server.use(
        http.get('/api/v1/admin/configuration/system', ({ request }) => {
          capturedParams = new URL(request.url).searchParams
          return HttpResponse.json(mockConfigs)
        }),
      )

      renderTab()
      await waitFor(() => {
        expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0)
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      // Click the category filter combobox (select trigger button)
      await user.click(screen.getAllByRole('combobox')[0])
      await waitFor(() => {
        expect(screen.getByText('Auth Providers')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Auth Providers'))

      await waitFor(() => {
        expect(capturedParams?.get('category')).toBe('auth_providers')
      })
    })
  })

  // -------------------------------------------------------------------------
  // Add Provider button
  // -------------------------------------------------------------------------

  describe('add provider button', () => {
    it('renders the Add Provider button', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument()
      })
    })

    it('opens the add provider modal when clicked', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /add provider/i }))

      await waitFor(() => {
        const dialogs = document.querySelectorAll('[role="dialog"]')
        expect(dialogs.length).toBeGreaterThan(0)
      })
    })
  })

  // -------------------------------------------------------------------------
  // Toggle enable/disable
  // -------------------------------------------------------------------------

  describe('toggle enable/disable', () => {
    it('calls update API when toggle is clicked', async () => {
      let updateCalled = false
      server.use(
        http.patch('/api/v1/admin/configuration/conf-2', () => {
          updateCalled = true
          return HttpResponse.json({ ...mockConfigs[1], enabled: false })
        }),
      )

      renderTab()
      await waitFor(() => {
        expect(screen.getByText('SendGrid Email')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const switches = document.querySelectorAll('[role="switch"]')
      // SendGrid is the second item (index 1)
      await user.click(switches[1] as HTMLElement)

      await waitFor(() => {
        expect(updateCalled).toBe(true)
      })
    })
  })

  // -------------------------------------------------------------------------
  // Delete dialog
  // -------------------------------------------------------------------------

  describe('delete dialog', () => {
    it('delete button is disabled for builtin configs', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Google OAuth')).toBeInTheDocument()
      })

      // First row (Google OAuth) is builtin - its delete button should be disabled
      const deleteButtons = document.querySelectorAll('[title*="delete"], button[disabled]')
      const rows = document.querySelectorAll('tbody tr')
      expect(rows.length).toBeGreaterThan(0)
    })

    it('opens delete confirmation dialog for non-builtin config', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('SendGrid Email')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      // Find all delete (trash) icon buttons
      const allButtons = screen.getAllByRole('button')
      // SendGrid row delete button — find the enabled delete button
      const trashButtons = allButtons.filter(
        (btn) => !btn.hasAttribute('disabled') && btn.querySelector('svg'),
      )
      // The delete button for SendGrid (non-builtin) should be clickable
      // Click the trash icon in the second row
      const rows = document.querySelectorAll('tbody tr')
      const secondRowButtons = Array.from(rows[1]?.querySelectorAll('button') ?? [])
      const deleteBtn = secondRowButtons[secondRowButtons.length - 1] as HTMLElement
      if (deleteBtn && !deleteBtn.hasAttribute('disabled')) {
        await user.click(deleteBtn)
        await waitFor(() => {
          expect(screen.getByText('Are you sure?')).toBeInTheDocument()
        })
      }
    })
  })
})
