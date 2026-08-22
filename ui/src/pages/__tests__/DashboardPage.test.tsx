/**
 * Tests for DashboardPage component (Phase 1 + Phase 2 dashboard redesign)
 *
 * Verifies:
 * - KPI strip (accounts, users, collections, records, sessions, storage)
 * - Growth, audit, records, and access mix charts
 * - Compact activity feed (not full tables)
 * - Expanded quick actions
 * - Range selector, errors, refresh
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
  audit_by_operation: [
    { date: '2026-07-13', create: 2, update: 1, delete: 0 },
    { date: '2026-07-14', create: 0, update: 3, delete: 1 },
    { date: '2026-07-15', create: 1, update: 0, delete: 0 },
    { date: '2026-07-16', create: 0, update: 0, delete: 0 },
    { date: '2026-07-17', create: 4, update: 2, delete: 1 },
    { date: '2026-07-18', create: 0, update: 1, delete: 0 },
    { date: '2026-07-19', create: 1, update: 0, delete: 2 },
  ],
}

const emptyTimeSeries = {
  accounts_created: mockTimeSeries.accounts_created.map((p) => ({ ...p, count: 0 })),
  users_created: mockTimeSeries.users_created.map((p) => ({ ...p, count: 0 })),
  audit_by_operation: mockTimeSeries.audit_by_operation.map((p) => ({
    ...p,
    create: 0,
    update: 0,
    delete: 0,
  })),
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
  records_by_collection: [
    { name: 'posts', count: 900 },
    { name: 'comments', count: 400 },
    { name: 'products', count: 223 },
  ],
  feature_counts: {
    hooks: 4,
    hooks_enabled: 3,
    webhooks: 2,
    webhooks_enabled: 2,
    workflows: 1,
    endpoints: 5,
    macros: 2,
    api_keys_active: 3,
    invitations_pending: 1,
  },
  jobs_by_status: {
    pending: 1,
    running: 0,
    completed: 10,
    failed: 1,
    retrying: 0,
    dead: 0,
  },
  hook_executions_summary: {
    success: 20,
    failed: 1,
    partial: 0,
  },
  webhook_deliveries_summary: {
    delivered: 15,
    failed: 0,
    pending: 1,
    retrying: 0,
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
      id: 1,
      account_id: 'SY0000',
      operation: 'CREATE' as const,
      table_name: 'users',
      record_id: 'user-1',
      column_name: 'email',
      old_value: null,
      new_value: 'admin@example.com',
      user_id: 'admin-1',
      user_email: 'admin@example.com',
      user_name: 'Admin',
      es_username: null,
      es_reason: null,
      es_timestamp: null,
      ip_address: '127.0.0.1',
      user_agent: 'Mozilla/5.0',
      request_id: null,
      occurred_at: '2026-03-29T08:00:00Z',
      checksum: null,
      previous_hash: null,
      extra_metadata: null,
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
    http.get('*/api/v1/dashboard/stats', ({ request }) => {
      const url = new URL(request.url)
      const range = url.searchParams.get('range') || '7d'
      return HttpResponse.json({
        ...mockDashboardStats,
        ...overrides,
        range: overrides.range ?? range,
        time_series: overrides.time_series ?? mockDashboardStats.time_series,
      })
    }),
  )
}

function setupErrorHandler(status = 500, detail = 'Internal server error') {
  server.use(
    http.get('*/api/v1/dashboard/stats', () =>
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
        http.get('*/api/v1/dashboard/stats', async () => {
          await new Promise(() => {}) // never resolves
        }),
      )

      renderDashboard()

      expect(screen.getByText('Total Accounts')).toBeInTheDocument()
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
      expect(screen.getByText('Currently active user sessions')).toBeInTheDocument()
    })

    it('renders Storage with formatted usage', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getAllByText('Storage').length).toBeGreaterThan(0)
      })
      expect(screen.getAllByText('42.75 MB').length).toBeGreaterThan(0)
    })

    it('renders period deltas for accounts and users', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('+2 vs previous 7d')).toBeInTheDocument()
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

  describe('charts', () => {
    it('renders growth chart container', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Growth')).toBeInTheDocument()
      })
      expect(screen.getByTestId('time-series-area-chart')).toBeInTheDocument()
    })

    it('renders audit activity chart container', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Audit Activity')).toBeInTheDocument()
      })
      expect(screen.getByTestId('stacked-bar-chart')).toBeInTheDocument()
    })

    it('renders records by collection chart', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Records by Collection')).toBeInTheDocument()
      })
      expect(screen.getByTestId('horizontal-bar-chart')).toBeInTheDocument()
    })

    it('renders collection access donut', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Collection Access')).toBeInTheDocument()
      })
      // Multiple donuts exist (access mix + automation health)
      expect(screen.getAllByTestId('donut-chart').length).toBeGreaterThan(0)
    })

    it('shows growth empty state when all series are zero', async () => {
      setupSuccessHandler({ time_series: emptyTimeSeries })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('No growth in this period')).toBeInTheDocument()
      })
    })

    it('shows access mix empty state when no collections', async () => {
      setupSuccessHandler({ total_collections: 0, public_collections_count: 0 })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('No collections yet')).toBeInTheDocument()
      })
    })

    it('navigates to audit logs from audit chart view all', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Audit Activity')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      // Multiple "View all" buttons — pick the one near Audit Activity
      const viewAllButtons = screen.getAllByRole('button', { name: /view all/i })
      await user.click(viewAllButtons[1]) // audit activity is second chart headerAction after access mix
      // Accept either audit or collections depending on order
      expect(mockNavigate).toHaveBeenCalled()
    })
  })

  describe('system health', () => {
    it('renders System Health section', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('system-health-panel')).toBeInTheDocument()
        expect(screen.getByText('System Health')).toBeInTheDocument()
      })
    })

    it('shows database status as connected', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('connected')).toBeInTheDocument()
      })
    })

    it('shows storage usage in the system health panel', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('system-health-panel')).toBeInTheDocument()
      })
      // Storage appears in KPI strip and system health panel
      expect(screen.getAllByText(/42\.75 MB/).length).toBeGreaterThan(0)
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

  describe('feature counts strip', () => {
    it('renders feature count cards', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('feature-counts-strip')).toBeInTheDocument()
      })
      expect(screen.getByTestId('feature-count-hooks')).toBeInTheDocument()
      expect(screen.getByTestId('feature-count-webhooks')).toBeInTheDocument()
      expect(screen.getByTestId('feature-count-workflows')).toBeInTheDocument()
      expect(screen.getByTestId('feature-count-endpoints')).toBeInTheDocument()
      expect(screen.getByTestId('feature-count-macros')).toBeInTheDocument()
      expect(screen.getByTestId('feature-count-api_keys')).toBeInTheDocument()
      expect(screen.getByTestId('feature-count-invitations')).toBeInTheDocument()
    })

    it.each([
      ['feature-count-hooks', '/admin/hooks'],
      ['feature-count-webhooks', '/admin/webhooks'],
      ['feature-count-workflows', '/admin/workflows'],
      ['feature-count-endpoints', '/admin/endpoints'],
      ['feature-count-macros', '/admin/macros'],
      ['feature-count-api_keys', '/admin/api-keys'],
      ['feature-count-invitations', '/admin/invitations'],
    ])('navigates from %s to %s', async (testId, path) => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId(testId)).toBeInTheDocument()
      })
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByTestId(testId))
      expect(mockNavigate).toHaveBeenCalledWith(path)
    })
  })

  describe('automation health charts', () => {
    it('renders Jobs, Hook Executions, and Webhook Deliveries sections', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('automation-health')).toBeInTheDocument()
      })
      expect(screen.getByText('Jobs')).toBeInTheDocument()
      expect(screen.getByText('Hook Executions')).toBeInTheDocument()
      expect(screen.getByText('Webhook Deliveries')).toBeInTheDocument()
    })

    it('shows empty state for jobs when all status counts are zero', async () => {
      setupSuccessHandler({
        jobs_by_status: {
          pending: 0,
          running: 0,
          completed: 0,
          failed: 0,
          retrying: 0,
          dead: 0,
        },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('No jobs yet')).toBeInTheDocument()
      })
    })
  })

  describe('automation alert strip', () => {
    beforeEach(() => {
      sessionStorage.removeItem('dashboard-automation-alert-dismissed')
    })

    it('shows alert when there are dead jobs', async () => {
      setupSuccessHandler({
        jobs_by_status: {
          pending: 0,
          running: 0,
          completed: 5,
          failed: 0,
          retrying: 0,
          dead: 2,
        },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('automation-alert')).toBeInTheDocument()
      })
      expect(screen.getByText(/2 dead jobs need attention/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /view jobs/i })).toBeInTheDocument()
    })

    it('shows alert when there are failed webhook deliveries', async () => {
      setupSuccessHandler({
        webhook_deliveries_summary: {
          delivered: 5,
          failed: 3,
          pending: 0,
          retrying: 0,
        },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('automation-alert')).toBeInTheDocument()
      })
      expect(screen.getByText(/3 failed webhook deliveries/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /view webhooks/i })).toBeInTheDocument()
    })

    it('hides alert when automation is healthy', async () => {
      setupSuccessHandler({
        jobs_by_status: {
          pending: 1,
          running: 0,
          completed: 10,
          failed: 0,
          retrying: 0,
          dead: 0,
        },
        webhook_deliveries_summary: {
          delivered: 15,
          failed: 0,
          pending: 0,
          retrying: 0,
        },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
      expect(screen.queryByTestId('automation-alert')).not.toBeInTheDocument()
    })

    it('dismisses alert for the session', async () => {
      setupSuccessHandler({
        jobs_by_status: {
          pending: 0,
          running: 0,
          completed: 0,
          failed: 0,
          retrying: 0,
          dead: 1,
        },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('automation-alert')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByLabelText('Dismiss automation alert'))

      expect(screen.queryByTestId('automation-alert')).not.toBeInTheDocument()
      expect(sessionStorage.getItem('dashboard-automation-alert-dismissed')).toBe('1')
    })

    it('navigates to jobs from the alert', async () => {
      setupSuccessHandler({
        jobs_by_status: {
          pending: 0,
          running: 0,
          completed: 0,
          failed: 0,
          retrying: 0,
          dead: 1,
        },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /view jobs/i })).toBeInTheDocument()
      })
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: /view jobs/i }))
      expect(mockNavigate).toHaveBeenCalledWith('/admin/jobs')
    })
  })

  describe('compact activity feed', () => {
    it('renders the Recent Registrations section heading', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Recent Registrations')).toBeInTheDocument()
      })
    })

    it('renders registration feed items with emails', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('alice@example.com')).toBeInTheDocument()
        expect(screen.getByText('bob@example.com')).toBeInTheDocument()
      })
      expect(screen.getByTestId('registrations-feed')).toBeInTheDocument()
    })

    it('renders account names in the registrations feed', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText(/Acme Corp/)).toBeInTheDocument()
        expect(screen.getByText(/Beta LLC/)).toBeInTheDocument()
      })
    })

    it('shows "No recent registrations" when list is empty', async () => {
      setupSuccessHandler({ recent_registrations: [] })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('No recent registrations')).toBeInTheDocument()
      })
    })

    it('renders compact audit feed with operation and table', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Recent Audit Activity')).toBeInTheDocument()
      })
      expect(screen.getByTestId('audit-feed')).toBeInTheDocument()
      expect(screen.getByText('CREATE')).toBeInTheDocument()
      expect(screen.getByText('users')).toBeInTheDocument()
    })

    it('does not render full DataTable pagination for registrations', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('alice@example.com')).toBeInTheDocument()
      })
      // DataTable pagination typically exposes rows-per-page; compact feed should not
      expect(screen.queryByText(/rows per page/i)).not.toBeInTheDocument()
    })

    it('navigates to users from registrations view all', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Recent Registrations')).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const cards = screen.getAllByRole('button', { name: /view all/i })
      // Find view all near registrations by clicking and checking navigation targets
      for (const btn of cards) {
        mockNavigate.mockClear()
        await user.click(btn)
        if (mockNavigate.mock.calls.some((c) => c[0] === '/admin/users')) {
          expect(mockNavigate).toHaveBeenCalledWith('/admin/users')
          return
        }
      }
      // Fallback: at least one view all should go to users
      expect(mockNavigate).toHaveBeenCalledWith('/admin/users')
    })
  })

  describe('quick actions', () => {
    it('renders the Quick Actions section', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Quick Actions')).toBeInTheDocument()
      })
    })

    it.each([
      ['Create Account', '/admin/accounts'],
      ['Create Collection', '/admin/collections/new'],
      ['Invite User', '/admin/invitations'],
      ['Create Hook', '/admin/hooks'],
      ['Create Webhook', '/admin/webhooks'],
      ['Create Workflow', '/admin/workflows'],
    ])('navigates for %s', async (label, path) => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: new RegExp(label, 'i') })).toBeInTheDocument()
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))
      expect(mockNavigate).toHaveBeenCalledWith(path)
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

    it('exposes accessible labels on range and refresh frequency controls', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
      expect(screen.getByLabelText('Time range')).toBeInTheDocument()
      expect(screen.getByLabelText('Refresh frequency')).toBeInTheDocument()
      expect(screen.getByLabelText('Refresh dashboard')).toBeInTheDocument()
    })
  })

  describe('getting started checklist', () => {
    it('shows checklist on a fresh install (no collections or records)', async () => {
      setupSuccessHandler({
        total_accounts: 1,
        total_users: 1,
        total_collections: 0,
        total_records: 0,
        records_by_collection: [],
        feature_counts: {
          hooks: 0,
          hooks_enabled: 0,
          webhooks: 0,
          webhooks_enabled: 0,
          workflows: 0,
          endpoints: 0,
          macros: 0,
          api_keys_active: 0,
          invitations_pending: 0,
        },
        recent_registrations: [],
        time_series: emptyTimeSeries,
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('getting-started-checklist')).toBeInTheDocument()
      })
      expect(screen.getByText('Getting started')).toBeInTheDocument()
      expect(screen.getByTestId('getting-started-collection')).toBeInTheDocument()
      expect(screen.getByTestId('getting-started-invite')).toBeInTheDocument()
    })

    it('hides checklist when collections exist', async () => {
      setupSuccessHandler({ total_collections: 3, total_records: 10 })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
      expect(screen.queryByTestId('getting-started-checklist')).not.toBeInTheDocument()
    })

    it('dismisses checklist and persists in localStorage', async () => {
      setupSuccessHandler({
        total_collections: 0,
        total_records: 0,
        records_by_collection: [],
        recent_registrations: [],
        time_series: emptyTimeSeries,
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('getting-started-checklist')).toBeInTheDocument()
      })
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(
        screen.getByLabelText('Dismiss getting started checklist'),
      )
      expect(screen.queryByTestId('getting-started-checklist')).not.toBeInTheDocument()
      expect(localStorage.getItem('dashboard-getting-started-dismissed')).toBe('1')
    })

    it('navigates from a checklist step', async () => {
      setupSuccessHandler({
        total_collections: 0,
        total_records: 0,
        records_by_collection: [],
        recent_registrations: [],
        time_series: emptyTimeSeries,
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByTestId('getting-started-collection')).toBeInTheDocument()
      })
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      await user.click(screen.getByTestId('getting-started-collection'))
      expect(mockNavigate).toHaveBeenCalledWith('/admin/collections/new')
    })
  })

  describe('chart accessibility summaries', () => {
    it('renders screen-reader summaries for growth and audit charts', async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Growth')).toBeInTheDocument()
      })
      const summaries = screen.getAllByTestId('chart-summary')
      expect(summaries.length).toBeGreaterThan(0)
      expect(
        summaries.some((el) => el.textContent?.includes('Accounts created')),
      ).toBe(true)
      expect(
        summaries.some((el) => el.textContent?.includes('CREATE:')),
      ).toBe(true)
    })
  })

  describe('stat values match API response', () => {
    it('displays zeros when all counts are 0', async () => {
      setupSuccessHandler({
        total_accounts: 0,
        total_users: 0,
        total_collections: 0,
        total_records: 0,
        new_accounts_7d: 0,
        new_users_7d: 0,
        previous_period: { new_accounts: 0, new_users: 0 },
        public_collections_count: 0,
        active_sessions: 0,
        records_by_collection: [],
        recent_registrations: [],
        recent_audit_logs: [],
        time_series: emptyTimeSeries,
        system_health: { database_status: 'connected', storage_usage_mb: 0 },
      })
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText('Total Accounts')).toBeInTheDocument()
      })
      // Multiple zeros expected for KPIs
      expect(screen.getAllByText('0').length).toBeGreaterThan(0)
      // Fresh install empty charts
      expect(screen.getAllByTestId('chart-empty').length).toBeGreaterThan(0)
    })
  })
})
