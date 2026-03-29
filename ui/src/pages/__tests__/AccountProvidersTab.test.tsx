/**
 * Tests for AccountProvidersTab component (FT3.5)
 *
 * Verifies:
 * - Initial empty state prompting account selection
 * - Account selector popover renders and lists accounts
 * - After selecting account, loads and renders configs
 * - Category filter appears after account is selected
 * - Toggle enable/disable calls API
 * - Delete confirmation dialog
 * - Add Provider button appears when account is selected
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import AccountProvidersTab from '../AccountProvidersTab'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockAccounts = {
  items: [
    { id: 'AB1234', name: 'Acme Corp', slug: 'acme', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
    { id: 'XY5678', name: 'Beta Inc', slug: 'beta', created_at: '2026-01-15T00:00:00Z', updated_at: '2026-01-15T00:00:00Z' },
  ],
  total: 2,
  page: 1,
  page_size: 100,
}

const mockAccountConfigs = [
  {
    id: 'aconf-1',
    display_name: 'Custom OAuth',
    provider_name: 'custom_oauth',
    category: 'auth_providers',
    updated_at: '2026-03-28T10:00:00Z',
    is_system: false,
    is_builtin: false,
    is_default: false,
    account_id: 'AB1234',
    logo_url: '',
    enabled: true,
    priority: 1,
  },
  {
    id: 'aconf-2',
    display_name: 'Mailgun Email',
    provider_name: 'mailgun',
    category: 'email_providers',
    updated_at: '2026-03-27T06:00:00Z',
    is_system: false,
    is_builtin: false,
    is_default: true,
    account_id: 'AB1234',
    logo_url: '',
    enabled: true,
    priority: 1,
  },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderTab() {
  return render(<AccountProvidersTab />)
}

function setupSuccessHandlers() {
  server.use(
    http.get('/api/v1/accounts', () => HttpResponse.json(mockAccounts)),
    http.get('/api/v1/admin/configuration/account', () =>
      HttpResponse.json(mockAccountConfigs),
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

describe('AccountProvidersTab', () => {
  // -------------------------------------------------------------------------
  // Initial state (no account selected)
  // -------------------------------------------------------------------------

  describe('initial state', () => {
    it('renders "Select an account" prompt initially', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Select an account')).toBeInTheDocument()
      })
    })

    it('renders the description text for account selection', async () => {
      renderTab()
      await waitFor(() => {
        expect(
          screen.getByText(/choose an account from the dropdown/i),
        ).toBeInTheDocument()
      })
    })

    it('renders the account selector button', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })
    })

    it('does not render category filter before account is selected', () => {
      renderTab()
      expect(screen.queryByText('All Categories')).not.toBeInTheDocument()
    })

    it('does not render Add Provider button before account is selected', () => {
      renderTab()
      expect(screen.queryByRole('button', { name: /add provider/i })).not.toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Account selector
  // -------------------------------------------------------------------------

  describe('account selector', () => {
    it('opens the account popover on click', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search accounts/i)).toBeInTheDocument()
      })
    })

    it('lists accounts inside the popover', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
        expect(screen.getByText('Beta Inc')).toBeInTheDocument()
      })
    })

    it('shows account slugs under account names', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('acme')).toBeInTheDocument()
        expect(screen.getByText('beta')).toBeInTheDocument()
      })
    })

    it('loads configs after selecting an account', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Acme Corp'))

      await waitFor(() => {
        expect(screen.getByText('Custom OAuth')).toBeInTheDocument()
        expect(screen.getByText('Mailgun Email')).toBeInTheDocument()
      })
    })

    it('shows category filter after account is selected', async () => {
      renderTab()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
      await user.click(screen.getByRole('combobox'))
      await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
      await user.click(screen.getByText('Acme Corp'))

      await waitFor(() => {
        expect(screen.getByText('All Categories')).toBeInTheDocument()
      })
    })

    it('shows Add Provider button after account is selected', async () => {
      renderTab()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
      await user.click(screen.getByRole('combobox'))
      await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
      await user.click(screen.getByText('Acme Corp'))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Config list (after account selected)
  // -------------------------------------------------------------------------

  describe('config list after account selected', () => {
    async function selectAccount() {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
      await user.click(screen.getByRole('combobox'))
      await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
      await user.click(screen.getByText('Acme Corp'))
      return user
    }

    it('renders provider names in the table', async () => {
      renderTab()
      await selectAccount()
      await waitFor(() => {
        expect(screen.getByText('Custom OAuth')).toBeInTheDocument()
        expect(screen.getByText('Mailgun Email')).toBeInTheDocument()
      })
    })

    it('renders Default badge for default config', async () => {
      renderTab()
      await selectAccount()
      await waitFor(() => {
        expect(screen.getByText('Default')).toBeInTheDocument()
      })
    })

    it('renders status toggles for each config', async () => {
      renderTab()
      await selectAccount()
      await waitFor(() => {
        const switches = document.querySelectorAll('[role="switch"]')
        expect(switches.length).toBe(mockAccountConfigs.length)
      })
    })

    it('renders empty state message when account has no configs', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/account', () =>
          HttpResponse.json([]),
        ),
      )
      renderTab()
      await selectAccount()
      await waitFor(() => {
        expect(
          screen.getByText(/no account-level configurations found/i),
        ).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Toggle enable/disable
  // -------------------------------------------------------------------------

  describe('toggle enable/disable', () => {
    it('calls update API when a switch is toggled', async () => {
      let updateCalled = false
      server.use(
        http.patch('/api/v1/admin/configuration/aconf-1', () => {
          updateCalled = true
          return HttpResponse.json({ ...mockAccountConfigs[0], enabled: false })
        }),
      )

      renderTab()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
      await user.click(screen.getByRole('combobox'))
      await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
      await user.click(screen.getByText('Acme Corp'))

      await waitFor(() => {
        const switches = document.querySelectorAll('[role="switch"]')
        expect(switches.length).toBe(mockAccountConfigs.length)
      })

      const switches = document.querySelectorAll('[role="switch"]')
      await user.click(switches[0] as HTMLElement)

      await waitFor(() => {
        expect(updateCalled).toBe(true)
      })
    })
  })

  // -------------------------------------------------------------------------
  // Delete dialog
  // -------------------------------------------------------------------------

  describe('delete dialog', () => {
    it('opens delete confirmation dialog when delete button is clicked', async () => {
      renderTab()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
      await user.click(screen.getByRole('combobox'))
      await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
      await user.click(screen.getByText('Acme Corp'))

      await waitFor(() => {
        expect(screen.getByText('Custom OAuth')).toBeInTheDocument()
      })

      // Click the trash/delete button in the first row
      const rows = document.querySelectorAll('tbody tr')
      const firstRowButtons = Array.from(rows[0]?.querySelectorAll('button') ?? [])
      const deleteBtn = firstRowButtons[firstRowButtons.length - 1] as HTMLElement
      if (deleteBtn) {
        await user.click(deleteBtn)
        await waitFor(() => {
          expect(screen.getByText('Are you sure?')).toBeInTheDocument()
        })
      }
    })

    it('closes delete dialog when Cancel is clicked', async () => {
      renderTab()
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
      await user.click(screen.getByRole('combobox'))
      await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
      await user.click(screen.getByText('Acme Corp'))

      await waitFor(() => {
        expect(screen.getByText('Custom OAuth')).toBeInTheDocument()
      })

      const rows = document.querySelectorAll('tbody tr')
      const firstRowButtons = Array.from(rows[0]?.querySelectorAll('button') ?? [])
      const deleteBtn = firstRowButtons[firstRowButtons.length - 1] as HTMLElement
      if (deleteBtn) {
        await user.click(deleteBtn)
        await waitFor(() => {
          expect(screen.getByText('Are you sure?')).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /cancel/i }))
        await waitFor(() => {
          expect(screen.queryByText('Are you sure?')).not.toBeInTheDocument()
        })
      }
    })
  })
})
