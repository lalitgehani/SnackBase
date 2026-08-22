import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getDashboardStats,
  formatStorageUsage,
  formatPeriodDelta,
  isDashboardRange,
} from '../dashboard.service'
import type { DashboardStats } from '../dashboard.service'

const mockDashboardStats: DashboardStats = {
  total_accounts: 5,
  total_users: 42,
  total_collections: 10,
  total_records: 1500,
  new_accounts_7d: 2,
  new_users_7d: 8,
  range: '7d',
  previous_period: { new_accounts: 1, new_users: 3 },
  time_series: {
    accounts_created: [
      { date: '2026-07-13', count: 0 },
      { date: '2026-07-14', count: 1 },
      { date: '2026-07-15', count: 0 },
      { date: '2026-07-16', count: 0 },
      { date: '2026-07-17', count: 1 },
      { date: '2026-07-18', count: 0 },
      { date: '2026-07-19', count: 0 },
    ],
    users_created: [
      { date: '2026-07-13', count: 1 },
      { date: '2026-07-14', count: 2 },
      { date: '2026-07-15', count: 1 },
      { date: '2026-07-16', count: 0 },
      { date: '2026-07-17', count: 2 },
      { date: '2026-07-18', count: 1 },
      { date: '2026-07-19', count: 1 },
    ],
    audit_by_operation: [
      { date: '2026-07-13', create: 1, update: 0, delete: 0 },
      { date: '2026-07-14', create: 0, update: 2, delete: 0 },
      { date: '2026-07-15', create: 0, update: 0, delete: 1 },
      { date: '2026-07-16', create: 0, update: 0, delete: 0 },
      { date: '2026-07-17', create: 3, update: 1, delete: 0 },
      { date: '2026-07-18', create: 0, update: 0, delete: 0 },
      { date: '2026-07-19', create: 1, update: 1, delete: 0 },
    ],
  },
  recent_registrations: [
    {
      id: 'user-1',
      email: 'user@example.com',
      account_id: 'AB1234',
      account_code: 'AB1234',
      account_name: 'Acme Corp',
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  system_health: {
    database_status: 'healthy',
    storage_usage_mb: 128,
  },
  active_sessions: 7,
  public_collections_count: 3,
  records_by_collection: [
    { name: 'posts', count: 900 },
    { name: 'comments', count: 600 },
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
  recent_audit_logs: [],
}

// ─────────────────────────────────────────────────────────────────────────────
// getDashboardStats()
// ─────────────────────────────────────────────────────────────────────────────

describe('Dashboard Service', () => {
  describe('getDashboardStats()', () => {
    it('sends GET to /dashboard/stats with default range', async () => {
      let requestUrl = ''

      server.use(
        http.get('*/api/v1/dashboard/stats', ({ request }) => {
          requestUrl = request.url
          return HttpResponse.json(mockDashboardStats)
        }),
      )

      await getDashboardStats()
      expect(requestUrl).toContain('/api/v1/dashboard/stats')
      expect(requestUrl).toContain('range=7d')
    })

    it('serializes the range query parameter', async () => {
      let requestUrl = ''

      server.use(
        http.get('*/api/v1/dashboard/stats', ({ request }) => {
          requestUrl = request.url
          return HttpResponse.json({ ...mockDashboardStats, range: '30d' })
        }),
      )

      await getDashboardStats('30d')
      expect(requestUrl).toContain('range=30d')
    })

    it('returns dashboard stats on success', async () => {
      server.use(
        http.get('*/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats)),
      )

      const result = await getDashboardStats()
      expect(result).toEqual(mockDashboardStats)
    })

    it('returns correct account and user counts', async () => {
      server.use(
        http.get('*/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats)),
      )

      const result = await getDashboardStats()
      expect(result.total_accounts).toBe(5)
      expect(result.total_users).toBe(42)
      expect(result.previous_period.new_accounts).toBe(1)
      expect(result.time_series.accounts_created).toHaveLength(7)
    })

    it('returns system health status', async () => {
      server.use(
        http.get('*/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats)),
      )

      const result = await getDashboardStats()
      expect(result.system_health.database_status).toBe('healthy')
    })

    it('returns recent registrations array', async () => {
      server.use(
        http.get('*/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats)),
      )

      const result = await getDashboardStats()
      expect(result.recent_registrations).toHaveLength(1)
      expect(result.recent_registrations[0].email).toBe('user@example.com')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('*/api/v1/dashboard/stats', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 }),
        ),
      )

      await expect(getDashboardStats()).rejects.toThrow()
    })
  })

  describe('formatStorageUsage()', () => {
    it('formats MB values', () => {
      expect(formatStorageUsage(42.75)).toBe('42.75 MB')
    })

    it('formats GB for large values', () => {
      expect(formatStorageUsage(2048)).toBe('2.00 GB')
    })

    it('formats small values as KB', () => {
      expect(formatStorageUsage(0.005)).toBe('5.1 KB')
    })
  })

  describe('formatPeriodDelta()', () => {
    it('formats positive deltas', () => {
      expect(formatPeriodDelta(11, 5, '7d')).toBe('+6 vs previous 7d')
    })

    it('formats negative deltas', () => {
      expect(formatPeriodDelta(2, 5, '30d')).toBe('-3 vs previous 30d')
    })
  })

  describe('isDashboardRange()', () => {
    it('accepts valid ranges', () => {
      expect(isDashboardRange('7d')).toBe(true)
      expect(isDashboardRange('30d')).toBe(true)
      expect(isDashboardRange('90d')).toBe(true)
    })

    it('rejects invalid ranges', () => {
      expect(isDashboardRange('1y')).toBe(false)
      expect(isDashboardRange('')).toBe(false)
    })
  })
})
