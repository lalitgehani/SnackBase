import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { getDashboardStats } from '../dashboard.service'
import type { DashboardStats } from '../dashboard.service'

const mockDashboardStats: DashboardStats = {
  total_accounts: 5,
  total_users: 42,
  total_collections: 10,
  total_records: 1500,
  new_accounts_7d: 2,
  new_users_7d: 8,
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
  recent_audit_logs: [],
}

// ─────────────────────────────────────────────────────────────────────────────
// getDashboardStats()
// ─────────────────────────────────────────────────────────────────────────────

describe('Dashboard Service', () => {
  describe('getDashboardStats()', () => {
    it('sends GET to /dashboard/stats', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/dashboard/stats', () => {
          requestReceived = true
          return HttpResponse.json(mockDashboardStats)
        })
      )

      await getDashboardStats()
      expect(requestReceived).toBe(true)
    })

    it('returns dashboard stats on success', async () => {
      server.use(
        http.get('/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats))
      )

      const result = await getDashboardStats()
      expect(result).toEqual(mockDashboardStats)
    })

    it('returns correct account and user counts', async () => {
      server.use(
        http.get('/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats))
      )

      const result = await getDashboardStats()
      expect(result.total_accounts).toBe(5)
      expect(result.total_users).toBe(42)
    })

    it('returns system health status', async () => {
      server.use(
        http.get('/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats))
      )

      const result = await getDashboardStats()
      expect(result.system_health.database_status).toBe('healthy')
    })

    it('returns recent registrations array', async () => {
      server.use(
        http.get('/api/v1/dashboard/stats', () => HttpResponse.json(mockDashboardStats))
      )

      const result = await getDashboardStats()
      expect(result.recent_registrations).toHaveLength(1)
      expect(result.recent_registrations[0].email).toBe('user@example.com')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/dashboard/stats', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getDashboardStats()).rejects.toThrow()
    })
  })
})
