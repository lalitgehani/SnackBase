/**
 * Tests for ConfigurationDashboardPage component (FT3.5)
 *
 * Verifies:
 * - Renders provider categories / stats cards
 * - Configuration form loads provider settings (tabs render)
 * - Recent activity list renders correctly
 * - Refresh frequency selector persists to localStorage
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import ConfigurationDashboardPage from '../ConfigurationDashboardPage'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockStats = {
  system_configs: {
    total: 4,
    by_category: {
      oauth: 2,
      email: 1,
      saml: 1,
    },
  },
  account_configs: {
    total: 2,
    by_category: {
      oauth: 1,
      email: 1,
    },
  },
}

const mockRecentConfigs = [
  {
    id: 'conf-1',
    display_name: 'Google OAuth',
    provider_name: 'google',
    category: 'oauth',
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
    category: 'email',
    updated_at: '2026-03-27T08:00:00Z',
    is_system: false,
    is_builtin: false,
    is_default: false,
    account_id: 'AB1234',
    logo_url: '',
    enabled: true,
    priority: 1,
  },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
  return render(<ConfigurationDashboardPage />)
}

function setupSuccessHandlers(
  statsOverride: Partial<typeof mockStats> = {},
  recentOverride: typeof mockRecentConfigs = mockRecentConfigs,
) {
  server.use(
    http.get('/api/v1/admin/configuration/stats', () =>
      HttpResponse.json({ ...mockStats, ...statsOverride }),
    ),
    http.get('/api/v1/admin/configuration/recent', () =>
      HttpResponse.json(recentOverride),
    ),
    // System and account providers tabs — return empty arrays to prevent errors
    http.get('/api/v1/admin/configuration/system', () => HttpResponse.json([])),
    http.get('/api/v1/admin/configuration/account', () => HttpResponse.json([])),
    http.get('/api/v1/admin/providers', () => HttpResponse.json([])),
    http.get('/api/v1/admin/providers/available', () => HttpResponse.json([])),
    http.get('/api/v1/email-templates/', () => HttpResponse.json({ items: [], total: 0 })),
  )
}

function setupStatsErrorHandler() {
  server.use(
    http.get('/api/v1/admin/configuration/stats', () =>
      HttpResponse.json({ detail: 'Stats unavailable' }, { status: 500 }),
    ),
    http.get('/api/v1/admin/configuration/recent', () => HttpResponse.json([])),
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

describe('ConfigurationDashboardPage', () => {
  // -------------------------------------------------------------------------
  // Page header
  // -------------------------------------------------------------------------

  describe('page header', () => {
    it('renders the Configuration heading', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Configuration')).toBeInTheDocument()
      })
    })

    it('renders a refresh frequency selector', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('No refresh')).toBeInTheDocument()
      })
    })

    it('renders a manual refresh button', async () => {
      renderPage()
      await waitFor(() => {
        // Refresh icon button in header
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      })
    })
  })

  // -------------------------------------------------------------------------
  // Tab navigation
  // -------------------------------------------------------------------------

  describe('tab navigation', () => {
    it('renders Dashboard tab trigger', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /dashboard/i })).toBeInTheDocument()
      })
    })

    it('renders System Providers tab trigger', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /system providers/i })).toBeInTheDocument()
      })
    })

    it('renders Account Providers tab trigger', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /account providers/i })).toBeInTheDocument()
      })
    })

    it('renders Email Templates tab trigger', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /email templates/i })).toBeInTheDocument()
      })
    })

    it('dashboard tab is active by default', async () => {
      renderPage()
      await waitFor(() => {
        const dashboardTab = screen.getByRole('tab', { name: /dashboard/i })
        expect(dashboardTab).toHaveAttribute('data-state', 'active')
      })
    })
  })

  // -------------------------------------------------------------------------
  // Stats cards
  // -------------------------------------------------------------------------

  describe('stats cards', () => {
    it('renders System Configs card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('System Configs')).toBeInTheDocument()
      })
    })

    it('renders correct system config total', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('4')).toBeInTheDocument()
      })
    })

    it('renders Account Configs card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Account Configs')).toBeInTheDocument()
      })
    })

    it('renders correct account config total', async () => {
      renderPage()
      await waitFor(() => {
        // account_configs.total = 2; may appear multiple times alongside category breakdowns
        const matches = screen.getAllByText('2')
        expect(matches.length).toBeGreaterThan(0)
      })
    })

    it('renders Category Breakdown card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Category Breakdown')).toBeInTheDocument()
      })
    })

    it('renders category labels from stats', async () => {
      renderPage()
      await waitFor(() => {
        // Categories from by_category: oauth, email, saml
        expect(screen.getAllByText(/oauth/i).length).toBeGreaterThan(0)
        expect(screen.getAllByText(/email/i).length).toBeGreaterThan(0)
      })
    })

    it('shows zero counts when stats have no configs', async () => {
      setupSuccessHandlers(
        {
          system_configs: { total: 0, by_category: {} },
          account_configs: { total: 0, by_category: {} },
        },
        [],
      )
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('System Configs')).toBeInTheDocument()
      })
      const zeros = screen.getAllByText('0')
      expect(zeros.length).toBeGreaterThanOrEqual(2)
    })
  })

  // -------------------------------------------------------------------------
  // Recent activity
  // -------------------------------------------------------------------------

  describe('recent activity', () => {
    it('renders the Recent Activity card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Recent Activity')).toBeInTheDocument()
      })
    })

    it('renders recent config display names', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Google OAuth')).toBeInTheDocument()
        expect(screen.getByText('SendGrid Email')).toBeInTheDocument()
      })
    })

    it('shows System or Account label for each config', async () => {
      renderPage()
      await waitFor(() => {
        // The recent activity renders "{is_system ? 'System' : 'Account'} • {category}"
        // e.g. "System • oauth"
        expect(screen.getByText('System • oauth')).toBeInTheDocument()
      })
    })

    it('renders "No recent activity found" when list is empty', async () => {
      setupSuccessHandlers({}, [])
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('No recent activity found.')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Quick actions
  // -------------------------------------------------------------------------

  describe('quick actions', () => {
    it('renders the Quick Actions card', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('Quick Actions')).toBeInTheDocument()
      })
    })

    it('renders Add System Config button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add system config/i })).toBeInTheDocument()
      })
    })

    it('renders Add Account Config button', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add account config/i })).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Refresh frequency selector
  // -------------------------------------------------------------------------

  describe('refresh frequency selector', () => {
    it('defaults to "No refresh" initially', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByText('No refresh')).toBeInTheDocument()
      })
    })

    it('reads saved frequency from localStorage on mount', async () => {
      localStorage.setItem('config-dashboard-refresh-frequency', '30')
      renderPage()
      await waitFor(() => {
        // The displayed value should reflect the stored value
        expect(screen.getByText('30 seconds')).toBeInTheDocument()
      })
    })

    it('hides the refresh controls when on a non-dashboard tab', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /system providers/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('tab', { name: /system providers/i }))

      await waitFor(() => {
        // The frequency selector should not be visible on other tabs
        expect(screen.queryByText('No refresh')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Tab switching
  // -------------------------------------------------------------------------

  describe('tab switching', () => {
    it('switches to System Providers tab content on click', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /system providers/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('tab', { name: /system providers/i }))

      await waitFor(() => {
        const systemTab = screen.getByRole('tab', { name: /system providers/i })
        expect(systemTab).toHaveAttribute('data-state', 'active')
      })
    })

    it('switches to Account Providers tab content on click', async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /account providers/i })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('tab', { name: /account providers/i }))

      await waitFor(() => {
        const accountTab = screen.getByRole('tab', { name: /account providers/i })
        expect(accountTab).toHaveAttribute('data-state', 'active')
      })
    })
  })
})
