import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { apiKeysService } from '../api-keys.service'
import type {
  APIKeyListResponse,
  APIKeyCreateResponse,
  APIKeyDetailResponse,
} from '../api-keys.service'

const mockApiKeyListItem = {
  id: 'key-1',
  name: 'My API Key',
  key: 'sb_sk_AB1234_****',
  last_used_at: null,
  expires_at: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

const mockApiKeyListResponse: APIKeyListResponse = {
  items: [mockApiKeyListItem],
  total: 1,
}

const mockApiKeyCreateResponse: APIKeyCreateResponse = {
  id: 'key-2',
  name: 'New Key',
  key: 'sb_sk_AB1234_abcdefghijklmnopqrstuvwxyz123456',
  expires_at: null,
  created_at: '2024-01-01T00:00:00Z',
}

const mockApiKeyDetail: APIKeyDetailResponse = {
  ...mockApiKeyListItem,
  updated_at: '2024-01-02T00:00:00Z',
}

// ─────────────────────────────────────────────────────────────────────────────
// getApiKeys()
// ─────────────────────────────────────────────────────────────────────────────

describe('API Keys Service', () => {
  describe('getApiKeys()', () => {
    it('sends GET to /admin/api-keys', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/api-keys', () => {
          requestReceived = true
          return HttpResponse.json(mockApiKeyListResponse)
        })
      )

      await apiKeysService.getApiKeys()
      expect(requestReceived).toBe(true)
    })

    it('returns api key list on success', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys', () => HttpResponse.json(mockApiKeyListResponse))
      )

      const result = await apiKeysService.getApiKeys()
      expect(result).toEqual(mockApiKeyListResponse)
    })

    it('returns total count', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys', () => HttpResponse.json(mockApiKeyListResponse))
      )

      const result = await apiKeysService.getApiKeys()
      expect(result.total).toBe(1)
      expect(result.items).toHaveLength(1)
    })

    it('returns masked key in list items', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys', () => HttpResponse.json(mockApiKeyListResponse))
      )

      const result = await apiKeysService.getApiKeys()
      expect(result.items[0].key).toContain('****')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys', () =>
          HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
        )
      )

      await expect(apiKeysService.getApiKeys()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // createApiKey()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('createApiKey()', () => {
    it('sends POST to /admin/api-keys with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/admin/api-keys', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockApiKeyCreateResponse, { status: 201 })
        })
      )

      await apiKeysService.createApiKey({ name: 'New Key', expires_at: null })

      expect(capturedBody).toEqual({ name: 'New Key', expires_at: null })
    })

    it('returns the created key with plaintext key value', async () => {
      server.use(
        http.post('/api/v1/admin/api-keys', () =>
          HttpResponse.json(mockApiKeyCreateResponse, { status: 201 })
        )
      )

      const result = await apiKeysService.createApiKey({ name: 'New Key', expires_at: null })
      expect(result).toEqual(mockApiKeyCreateResponse)
      expect(result.key).toContain('sb_sk_')
    })

    it('sends expires_at when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/admin/api-keys', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockApiKeyCreateResponse, { status: 201 })
        })
      )

      await apiKeysService.createApiKey({ name: 'Expiring Key', expires_at: '2025-12-31T00:00:00Z' })

      expect(capturedBody?.expires_at).toBe('2025-12-31T00:00:00Z')
    })

    it('propagates API errors', async () => {
      server.use(
        http.post('/api/v1/admin/api-keys', () =>
          HttpResponse.json({ detail: 'Validation error' }, { status: 422 })
        )
      )

      await expect(apiKeysService.createApiKey({ name: '', expires_at: null })).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getApiKeyById()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getApiKeyById()', () => {
    it('sends GET to /admin/api-keys/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/api-keys/key-1', () => {
          requestReceived = true
          return HttpResponse.json(mockApiKeyDetail)
        })
      )

      await apiKeysService.getApiKeyById('key-1')
      expect(requestReceived).toBe(true)
    })

    it('returns api key detail on success', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys/key-1', () => HttpResponse.json(mockApiKeyDetail))
      )

      const result = await apiKeysService.getApiKeyById('key-1')
      expect(result).toEqual(mockApiKeyDetail)
    })

    it('includes updated_at in the detail response', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys/key-1', () => HttpResponse.json(mockApiKeyDetail))
      )

      const result = await apiKeysService.getApiKeyById('key-1')
      expect(result.updated_at).toBe('2024-01-02T00:00:00Z')
    })

    it('propagates 404 when key not found', async () => {
      server.use(
        http.get('/api/v1/admin/api-keys/missing', () =>
          HttpResponse.json({ detail: 'API key not found' }, { status: 404 })
        )
      )

      await expect(apiKeysService.getApiKeyById('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // revokeApiKey()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('revokeApiKey()', () => {
    it('sends DELETE to /admin/api-keys/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/admin/api-keys/key-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await apiKeysService.revokeApiKey('key-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/admin/api-keys/key-1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await apiKeysService.revokeApiKey('key-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when key not found', async () => {
      server.use(
        http.delete('/api/v1/admin/api-keys/missing', () =>
          HttpResponse.json({ detail: 'API key not found' }, { status: 404 })
        )
      )

      await expect(apiKeysService.revokeApiKey('missing')).rejects.toThrow()
    })
  })
})
