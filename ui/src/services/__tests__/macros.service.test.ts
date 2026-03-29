import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  listMacros,
  getMacro,
  createMacro,
  updateMacro,
  deleteMacro,
  testMacro,
} from '../macros.service'
import type { Macro, MacroCreate, MacroUpdate } from '@/types/macro'

const mockMacro: Macro = {
  id: 1,
  name: 'get_active_users',
  description: 'Returns all active users for an account',
  sql_query: 'SELECT * FROM users WHERE account_id = $1 AND is_active = true',
  parameters: '["account_id"]',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  created_by: 'superadmin',
}

const mockMacroList: Macro[] = [
  mockMacro,
  {
    id: 2,
    name: 'count_records',
    description: null,
    sql_query: 'SELECT COUNT(*) FROM $1 WHERE account_id = $2',
    parameters: '["table", "account_id"]',
    created_at: '2024-02-01T00:00:00Z',
    updated_at: '2024-02-01T00:00:00Z',
    created_by: null,
  },
]

// ─────────────────────────────────────────────────────────────────────────────
// listMacros()
// ─────────────────────────────────────────────────────────────────────────────

describe('Macros Service', () => {
  describe('listMacros()', () => {
    it('sends GET to /macros', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/macros', () => {
          requestReceived = true
          return HttpResponse.json(mockMacroList)
        })
      )

      await listMacros()
      expect(requestReceived).toBe(true)
    })

    it('returns array of macros on success', async () => {
      server.use(
        http.get('/api/v1/macros', () => HttpResponse.json(mockMacroList))
      )

      const result = await listMacros()
      expect(result).toEqual(mockMacroList)
    })

    it('passes skip and limit params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/macros', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockMacroList)
        })
      )

      await listMacros(10, 50)

      expect(capturedUrl).toContain('skip=10')
      expect(capturedUrl).toContain('limit=50')
    })

    it('uses default skip=0 and limit=100 when not provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/macros', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockMacroList)
        })
      )

      await listMacros()

      expect(capturedUrl).toContain('skip=0')
      expect(capturedUrl).toContain('limit=100')
    })

    it('returns empty array when no macros exist', async () => {
      server.use(
        http.get('/api/v1/macros', () => HttpResponse.json([]))
      )

      const result = await listMacros()
      expect(result).toEqual([])
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/macros', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(listMacros()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getMacro()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getMacro()', () => {
    it('sends GET to /macros/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/macros/1', () => {
          requestReceived = true
          return HttpResponse.json(mockMacro)
        })
      )

      await getMacro(1)
      expect(requestReceived).toBe(true)
    })

    it('returns macro detail on success', async () => {
      server.use(
        http.get('/api/v1/macros/1', () => HttpResponse.json(mockMacro))
      )

      const result = await getMacro(1)
      expect(result).toEqual(mockMacro)
    })

    it('propagates 404 when macro not found', async () => {
      server.use(
        http.get('/api/v1/macros/999', () =>
          HttpResponse.json({ detail: 'Macro not found' }, { status: 404 })
        )
      )

      await expect(getMacro(999)).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // createMacro()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('createMacro()', () => {
    const newMacroPayload: MacroCreate = {
      name: 'get_active_users',
      description: 'Returns active users',
      sql_query: 'SELECT * FROM users WHERE is_active = true',
      parameters: ['account_id'],
    }

    it('sends POST to /macros with payload', async () => {
      let capturedBody: MacroCreate | null = null

      server.use(
        http.post('/api/v1/macros', async ({ request }) => {
          capturedBody = (await request.json()) as MacroCreate
          return HttpResponse.json(mockMacro, { status: 201 })
        })
      )

      await createMacro(newMacroPayload)

      expect(capturedBody).toEqual(newMacroPayload)
    })

    it('returns created macro on success', async () => {
      server.use(
        http.post('/api/v1/macros', () =>
          HttpResponse.json(mockMacro, { status: 201 })
        )
      )

      const result = await createMacro(newMacroPayload)
      expect(result).toEqual(mockMacro)
    })

    it('propagates API errors on duplicate name', async () => {
      server.use(
        http.post('/api/v1/macros', () =>
          HttpResponse.json({ detail: 'Macro name already exists' }, { status: 409 })
        )
      )

      await expect(createMacro(newMacroPayload)).rejects.toThrow()
    })

    it('propagates validation errors for invalid SQL', async () => {
      server.use(
        http.post('/api/v1/macros', () =>
          HttpResponse.json({ detail: 'Invalid SQL query' }, { status: 422 })
        )
      )

      await expect(
        createMacro({ ...newMacroPayload, sql_query: 'NOT VALID SQL;;;' })
      ).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateMacro()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateMacro()', () => {
    const updatePayload: MacroUpdate = {
      name: 'get_active_users',
      description: 'Updated description',
      sql_query: 'SELECT id, email FROM users WHERE is_active = true',
      parameters: ['account_id'],
    }

    it('sends PUT to /macros/{id} with payload', async () => {
      let capturedBody: MacroUpdate | null = null

      server.use(
        http.put('/api/v1/macros/1', async ({ request }) => {
          capturedBody = (await request.json()) as MacroUpdate
          return HttpResponse.json({ ...mockMacro, ...updatePayload })
        })
      )

      await updateMacro(1, updatePayload)

      expect(capturedBody).toEqual(updatePayload)
    })

    it('returns updated macro on success', async () => {
      const updatedMacro = { ...mockMacro, description: 'Updated description' }

      server.use(
        http.put('/api/v1/macros/1', () => HttpResponse.json(updatedMacro))
      )

      const result = await updateMacro(1, updatePayload)
      expect(result.description).toBe('Updated description')
    })

    it('propagates 404 when macro not found', async () => {
      server.use(
        http.put('/api/v1/macros/999', () =>
          HttpResponse.json({ detail: 'Macro not found' }, { status: 404 })
        )
      )

      await expect(updateMacro(999, updatePayload)).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // deleteMacro()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('deleteMacro()', () => {
    it('sends DELETE to /macros/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/macros/1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deleteMacro(1)
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/macros/1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await deleteMacro(1)
      expect(result).toBeUndefined()
    })

    it('propagates 404 when macro not found', async () => {
      server.use(
        http.delete('/api/v1/macros/999', () =>
          HttpResponse.json({ detail: 'Macro not found' }, { status: 404 })
        )
      )

      await expect(deleteMacro(999)).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // testMacro()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('testMacro()', () => {
    const mockTestResponse = {
      result: '[{"id": "user-1", "email": "alice@example.com"}]',
      execution_time: 12.5,
      rows_affected: 1,
    }

    it('sends POST to /macros/{id}/test with parameters', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/macros/1/test', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockTestResponse)
        })
      )

      await testMacro(1, { parameters: ['AB1234'] })

      expect(capturedBody).toEqual({ parameters: ['AB1234'] })
    })

    it('returns test result on success', async () => {
      server.use(
        http.post('/api/v1/macros/1/test', () => HttpResponse.json(mockTestResponse))
      )

      const result = await testMacro(1, { parameters: ['AB1234'] })
      expect(result).toEqual(mockTestResponse)
    })

    it('returns null result when macro returns no rows', async () => {
      const emptyResult = { result: null, execution_time: 5.0, rows_affected: 0 }

      server.use(
        http.post('/api/v1/macros/1/test', () => HttpResponse.json(emptyResult))
      )

      const result = await testMacro(1, { parameters: [] })
      expect(result.result).toBeNull()
      expect(result.rows_affected).toBe(0)
    })

    it('propagates errors when macro execution fails', async () => {
      server.use(
        http.post('/api/v1/macros/1/test', () =>
          HttpResponse.json({ detail: 'SQL execution error' }, { status: 500 })
        )
      )

      await expect(testMacro(1, { parameters: [] })).rejects.toThrow()
    })

    it('propagates 404 when macro not found', async () => {
      server.use(
        http.post('/api/v1/macros/999/test', () =>
          HttpResponse.json({ detail: 'Macro not found' }, { status: 404 })
        )
      )

      await expect(testMacro(999, { parameters: [] })).rejects.toThrow()
    })
  })
})
