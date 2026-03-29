import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  listMigrations,
  getCurrentMigration,
  getMigrationHistory,
} from '../migrations.service'
import type {
  MigrationListResponse,
  CurrentRevisionResponse,
  MigrationHistoryResponse,
} from '@/types/migrations'

const mockRevision = {
  revision: 'abc123',
  description: 'Add users table',
  down_revision: null,
  branch_labels: null,
  is_applied: true,
  is_head: true,
  is_dynamic: false,
  created_at: '2024-01-01T00:00:00Z',
}

const mockPendingRevision = {
  revision: 'def456',
  description: 'Add posts table',
  down_revision: 'abc123',
  branch_labels: null,
  is_applied: false,
  is_head: false,
  is_dynamic: true,
  created_at: null,
}

const mockMigrationListResponse: MigrationListResponse = {
  revisions: [mockRevision, mockPendingRevision],
  total: 2,
  current_revision: 'abc123',
}

const mockCurrentRevision: CurrentRevisionResponse = {
  revision: 'abc123',
  description: 'Add users table',
  created_at: '2024-01-01T00:00:00Z',
}

const mockHistoryResponse: MigrationHistoryResponse = {
  history: [
    {
      revision: 'abc123',
      description: 'Add users table',
      is_dynamic: false,
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  total: 1,
}

// ─────────────────────────────────────────────────────────────────────────────
// listMigrations()
// ─────────────────────────────────────────────────────────────────────────────

describe('Migrations Service', () => {
  describe('listMigrations()', () => {
    it('sends GET to /migrations', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/migrations', () => {
          requestReceived = true
          return HttpResponse.json(mockMigrationListResponse)
        })
      )

      await listMigrations()
      expect(requestReceived).toBe(true)
    })

    it('returns migration list response on success', async () => {
      server.use(
        http.get('/api/v1/migrations', () => HttpResponse.json(mockMigrationListResponse))
      )

      const result = await listMigrations()
      expect(result).toEqual(mockMigrationListResponse)
    })

    it('includes both applied and pending revisions', async () => {
      server.use(
        http.get('/api/v1/migrations', () => HttpResponse.json(mockMigrationListResponse))
      )

      const result = await listMigrations()
      const applied = result.revisions.filter(r => r.is_applied)
      const pending = result.revisions.filter(r => !r.is_applied)

      expect(applied).toHaveLength(1)
      expect(pending).toHaveLength(1)
    })

    it('includes current_revision in the response', async () => {
      server.use(
        http.get('/api/v1/migrations', () => HttpResponse.json(mockMigrationListResponse))
      )

      const result = await listMigrations()
      expect(result.current_revision).toBe('abc123')
    })

    it('returns null current_revision when no migrations are applied', async () => {
      const noMigrationsResponse: MigrationListResponse = {
        revisions: [{ ...mockPendingRevision }],
        total: 1,
        current_revision: null,
      }

      server.use(
        http.get('/api/v1/migrations', () => HttpResponse.json(noMigrationsResponse))
      )

      const result = await listMigrations()
      expect(result.current_revision).toBeNull()
    })

    it('marks head revision correctly', async () => {
      server.use(
        http.get('/api/v1/migrations', () => HttpResponse.json(mockMigrationListResponse))
      )

      const result = await listMigrations()
      const headRevision = result.revisions.find(r => r.is_head)

      expect(headRevision).toBeDefined()
      expect(headRevision?.revision).toBe('abc123')
    })

    it('marks dynamic (user-created) revisions correctly', async () => {
      server.use(
        http.get('/api/v1/migrations', () => HttpResponse.json(mockMigrationListResponse))
      )

      const result = await listMigrations()
      const dynamicRevisions = result.revisions.filter(r => r.is_dynamic)

      expect(dynamicRevisions).toHaveLength(1)
      expect(dynamicRevisions[0].revision).toBe('def456')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/migrations', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(listMigrations()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getCurrentMigration()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getCurrentMigration()', () => {
    it('sends GET to /migrations/current', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/migrations/current', () => {
          requestReceived = true
          return HttpResponse.json(mockCurrentRevision)
        })
      )

      await getCurrentMigration()
      expect(requestReceived).toBe(true)
    })

    it('returns current revision on success', async () => {
      server.use(
        http.get('/api/v1/migrations/current', () => HttpResponse.json(mockCurrentRevision))
      )

      const result = await getCurrentMigration()
      expect(result).toEqual(mockCurrentRevision)
    })

    it('returns null when no current revision exists (404)', async () => {
      server.use(
        http.get('/api/v1/migrations/current', () =>
          HttpResponse.json({ detail: 'No current revision' }, { status: 404 })
        )
      )

      const result = await getCurrentMigration()
      expect(result).toBeNull()
    })

    it('includes revision description in response', async () => {
      server.use(
        http.get('/api/v1/migrations/current', () => HttpResponse.json(mockCurrentRevision))
      )

      const result = await getCurrentMigration()
      expect(result?.description).toBe('Add users table')
    })

    it('propagates non-404 errors', async () => {
      server.use(
        http.get('/api/v1/migrations/current', () =>
          HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 })
        )
      )

      await expect(getCurrentMigration()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getMigrationHistory()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getMigrationHistory()', () => {
    it('sends GET to /migrations/history', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/migrations/history', () => {
          requestReceived = true
          return HttpResponse.json(mockHistoryResponse)
        })
      )

      await getMigrationHistory()
      expect(requestReceived).toBe(true)
    })

    it('returns migration history on success', async () => {
      server.use(
        http.get('/api/v1/migrations/history', () => HttpResponse.json(mockHistoryResponse))
      )

      const result = await getMigrationHistory()
      expect(result).toEqual(mockHistoryResponse)
    })

    it('returns history items in order', async () => {
      const multiHistory: MigrationHistoryResponse = {
        history: [
          { revision: 'rev-3', description: 'Third', is_dynamic: false, created_at: '2024-03-01T00:00:00Z' },
          { revision: 'rev-2', description: 'Second', is_dynamic: true, created_at: '2024-02-01T00:00:00Z' },
          { revision: 'rev-1', description: 'First', is_dynamic: false, created_at: '2024-01-01T00:00:00Z' },
        ],
        total: 3,
      }

      server.use(
        http.get('/api/v1/migrations/history', () => HttpResponse.json(multiHistory))
      )

      const result = await getMigrationHistory()
      expect(result.history).toHaveLength(3)
      expect(result.history[0].revision).toBe('rev-3')
    })

    it('marks dynamic history items correctly', async () => {
      const historyWithDynamic: MigrationHistoryResponse = {
        history: [
          { revision: 'rev-2', description: 'User collection', is_dynamic: true, created_at: null },
          { revision: 'rev-1', description: 'Core schema', is_dynamic: false, created_at: '2024-01-01T00:00:00Z' },
        ],
        total: 2,
      }

      server.use(
        http.get('/api/v1/migrations/history', () => HttpResponse.json(historyWithDynamic))
      )

      const result = await getMigrationHistory()
      const dynamicItems = result.history.filter(h => h.is_dynamic)

      expect(dynamicItems).toHaveLength(1)
      expect(dynamicItems[0].revision).toBe('rev-2')
    })

    it('returns empty history when no migrations have been applied', async () => {
      const emptyHistory: MigrationHistoryResponse = { history: [], total: 0 }

      server.use(
        http.get('/api/v1/migrations/history', () => HttpResponse.json(emptyHistory))
      )

      const result = await getMigrationHistory()
      expect(result.history).toEqual([])
      expect(result.total).toBe(0)
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/migrations/history', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getMigrationHistory()).rejects.toThrow()
    })
  })
})
