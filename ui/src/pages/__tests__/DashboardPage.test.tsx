/**
 * Tests for DashboardPage component (Phase 1 dashboard redesign)
 *
 * Verifies:
 * - Renders KPI strip (accounts, users, collections, records, sessions, storage)
 * - Public collections badge remains discoverable
 * - Displays loading skeletons while fetching stats
 * - Handles API error gracefully with error message
 * - Stat values match mocked API response
 * - Range selector and period deltas
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import DashboardPage from '../DashboardPage'

const mockNavigate = vi.fn()

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockTimeSeries = {
  accounts_created: [
    { date: '2026-07-13', count: 0 },
    { date: '2026-07-14', count: 1 },
    { date: '2026-07-15', count: 0 },
    { date: '2026-07-16', count: 0 },
    { date: '2026-07-17', count: 1 },
    { date: '2026-07-18', count: 1 },
    { date: '2026-07-19', count: 0 },
  ],
  users_created: [
    { date: '2026-07-13', count: 1 },
    { date: '2026-07-14', count: 2 },
    { date: '2026-07-15', count: 1 },
    { date: '2026-07-16', count: 0 },
    { date: '2026-07-17', count: 3 },
    { date: '2026-07-18', count: 2 },
    { date: '2026-07-19', count: 2 },
  ],
}

const mockDashboardStats = {
  total_accounts: 12,
  total_users: 47,
  total_collections: 8,
  total_records: 1523,
  new_accounts_7d: 3,
  new_users_7d: 11,
  range: '7d' as const,
  previous_period: { new_accounts: 1, new_users: 5 },
  time_series: mockTimeSeries,
  public_collections_count: 2,
  active_sessions: 5,
  system_health: {
    database_status: 'connected',
    storage_usage_mb: 42.75,
  },
  recent_registrations: [
    {
      id: 'reg-1',
      email: 'alice@example.com',
      account_id: 'AB1234',
      account_code: 'AB1234',
      account_name: 'Acme Corp',
      created_at: '2026-03-20T10:00:00Z',
    },
    {
      id: 'reg-2',
      email: 'bob@example.com',
      account_id: 'CD5678',
      account_code: 'CD5678',
      account_name: 'Beta LLC',
      created_at: '2026-03-21T12:30:00Z',
    },
  ],
  recent_audit_logs: [
    {
      id: 'log-1',
      action: 'user.login',
      actor_email: 'admin@example.com',
      account_id: 'SY0000',
      resource_type: 'user',
      resource_id: 'user-1',
      occurred_at: '2026-03-29T08:00:00Z',
      ip_address: '127.0.0.1',
      user_agent: 'Mozilla/5.0',
      metadata: {},
    },
  ],
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderDashboard() {
  return render(<DashboardPage />)
}

function setupSuccessHandler(overrides: Partial<typeof mockDashboardStats> = {}) {
  server.use(
    http.get('/api/v1/dashboard/stats', ({ request }) => {
      const url = new URL(request.url)
      const range = url.searchParams.get('range') || '7d'
      return HttpResponse.json({
        ...mockDashboardStats,
        ...overrides,
        range: overrides.range ?? range,
      })
    }),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('/api/v1/dashboard/stats', () =>
      HttpResponse.json({ detail }, { status }),
    ),
  )
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
  mockNavigate.mockClear()
  vi.useFakeTimers({ shouldAdvanceTime: true })
  setupSuccessHandler()
})

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('DashboardPage', () => {
  describe('loading state', () => {
    it('displays loading skeletons before stats are fetched', () => {
      server.use(
        http.get('/api/v1/dashboard/stats', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderDashboard()

      expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      // Skeletons render for KPI values
      expect(document.querySelectorAll('[data-slot="skeleton"], .animate-pulse').length).toBeGreaterThan(0)
    })

    it('shows KPI values after stats load', async () => {
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByText('12')).toBeInTheDocument()
      })
    })
  })

  describe('stat cards', () => {
    it('renders the Total Accounts card with the correct value', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
      expect(screen.getByText('12')).toBeInTheDocument()
    })

    it('renders the Total Users card with the correct value', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Users')).toBeInTheDocument()
      })
      expect(screen.getByText('47')).toBeInTheDocument()
    })

    it('renders the Total Collections card with the correct value', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Collections')).toBeInTheDocument()
      })
      expect(screen.getByText('8')).toBeInTheDocument()
    })

    it('renders the Total Records card with the correct value', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Records')).toBeInTheDocument()
      })
      expect(screen.getByText('1523')).toBeInTheDocument()
    })

    it('renders public collections as a discoverable badge', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText(/2 public/i)).toBeInTheDocument()
      })
    })

    it('renders Active Sessions count', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Active Sessions')).toBeInTheDocument()
      })
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('renders Storage with formatted usage', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Storage')).toBeInTheDocument()
      })
      expect(screen.getByText('42.75 MB')).toBeInTheDocument()
    })

    it('renders period deltas for accounts and users', async () => {
      renderDashboard()
      await waitFor(() => {
        // +2 vs previous 7d (3 current - 1 previous)
        expect(screen.getByText('+2 vs previous 7d')).toBeInTheDocument()
        // +6 vs previous 7d (11 current - 5 previous)
        expect(screen.getByText('+6 vs previous 7d')).toBeInTheDocument()
      })
    })
  })

  describe('navigation', () => {
    it('navigates to accounts when Total Accounts is clicked', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByText('Total Accounts'))
      expect(mockNavigate).toHaveBeenCalledWith('/admin/accounts')
    })

    it('navigates to users when Total Users is clicked', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Users')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByText('Total Users'))
      expect(mockNavigate).toHaveBeenCalledWith('/admin/users')
    })

    it('navigates to collections when Total Collections is clicked', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Collections')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByText('Total Collections'))
      expect(mockNavigate).toHaveBeenCalledWith('/admin/collections')
    })
  })

  describe('range selector', () => {
    it('renders the time range selector with default 7d', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Last 7 days')).toBeInTheDocument()
      })
    })

    it('persists selected range in localStorage', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Last 7 days')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByLabelText('Time range'))
      await user.click(screen.getByRole('option', { name: 'Last 30 days' }))

      await waitFor(() => {
        expect(localStorage.getItem('dashboard-range')).toBe('30d')
      })
    })

    it('restores range from localStorage', async () => {
      localStorage.setItem('dashboard-range', '90d')
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Last 90 days')).toBeInTheDocument()
      })
    })
  })

  describe('system health', () => {
    it('renders System Health section', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('System Health')).toBeInTheDocument()
      })
    })

    it('shows database status as connected', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('connected')).toBeInTheDocument()
      })
    })

    it('shows disconnected badge when database is down', async () => {
      setupSuccessHandler({
        system_health: { database_status: 'disconnected', storage_usage_mb: 0 },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('disconnected')).toBeInTheDocument()
      })
    })
  })

  describe('recent registrations table', () => {
    it('renders the Recent Registrations section heading', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Recent Registrations')).toBeInTheDocument()
      })
    })

    it('renders registration rows with email addresses', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('alice@example.com')).toBeInTheDocument()
        expect(screen.getByText('bob@example.com')).toBeInTheDocument()
      })
    })

    it('renders account names in the registrations table', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument()
        expect(screen.getByText('Beta LLC')).toBeInTheDocument()
      })
    })

    it('shows "No recent registrations" when list is empty', async () => {
      setupSuccessHandler({ recent_registrations: [] })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('No recent registrations')).toBeInTheDocument()
      })
    })
  })

  describe('recent audit logs section', () => {
    it('renders the Recent Audit Logs heading', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Recent Audit Logs')).toBeInTheDocument()
      })
    })

    it('renders a "View All" link to the audit logs page', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /view all/i })).toBeInTheDocument()
      })
    })
  })

  describe('quick actions', () => {
    it('renders the Quick Actions section', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Quick Actions')).toBeInTheDocument()
      })
    })

    it('renders a Create Account button', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
      })
    })

    it('renders a Create Collection button', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create collection/i })).toBeInTheDocument()
      })
    })
  })

  describe('error state', () => {
    it('displays an error message when the API fails', async () => {
      setupErrorHandler(500, 'Internal server error')
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByText('Failed to load dashboard')).toBeInTheDocument()
      })
    })

    it('shows the API error detail in the error message', async () => {
      setupErrorHandler(500, 'Internal server error')
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByText(/internal server error/i)).toBeInTheDocument()
      })
    })

    it('renders a Try Again button when there is an error', async () => {
      setupErrorHandler(500, 'Service unavailable')
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })
    })

    it('does not render stats cards when API fails with no prior data', async () => {
      setupErrorHandler(500, 'Fetch failed')
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByText('Failed to load dashboard')).toBeInTheDocument()
      })

      expect(screen.queryByText('Total Accounts')).not.toBeInTheDocument()
    })

    it('retries fetch when Try Again button is clicked', async () => {
      setupErrorHandler(500, 'Temporary failure')
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })

      setupSuccessHandler()

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /try again/i }))

      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
    })
  })

  describe('refresh controls', () => {
    it('renders the manual refresh button', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
      expect(screen.getByLabelText('Refresh dashboard')).toBeInTheDocument()
    })

    it('renders the refresh frequency selector', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('No refresh')).toBeInTheDocument()
      })
    })
  })

  describe('stat values match API response', () => {
    it('displays zeros when all counts are 0', async () => {
      setupSuccessHandler({
        total_accounts: 0,
        total_users: 0,
        total_collections: 0,
        total_records: 0,
        public_collections_count: 0,
        new_accounts_7d: 0,
        new_users_7d: 0,
        previous_period: { new_accounts: 0, new_users: 0 },
        active_sessions: 0,
        system_health: { database_status: 'connected', storage_usage_mb: 0 },
      })
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })

      const zeros = screen.getAllByText('0')
      expect(zeros.length).toBeGreaterThan(0)
    })

    it('displays large numbers correctly', async () => {
      setupSuccessHandler({
        total_records: 999999,
        total_users: 10000,
      })
      renderDashboard()

      await waitFor(() => {
        expect(screen.getByText('999999')).toBeInTheDocument()
        expect(screen.getByText('10000')).toBeInTheDocument()
      })
    })
  })
})
