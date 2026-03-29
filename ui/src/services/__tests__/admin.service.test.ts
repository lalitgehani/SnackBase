import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { adminService } from '../admin.service'
import type {
  Configuration,
  ConfigurationStats,
  AvailableProvider,
  ProviderSchema,
} from '../admin.service'
import type { AccountListResponse } from '../accounts.service'

const mockConfiguration: Configuration = {
  id: 'cfg-1',
  display_name: 'Google OAuth',
  provider_name: 'google',
  category: 'oauth',
  updated_at: '2024-01-01T00:00:00Z',
  is_system: false,
  is_builtin: false,
  is_default: false,
  account_id: 'AB1234',
  logo_url: 'https://example.com/google.png',
  enabled: true,
  priority: 1,
}

const mockConfigStats: ConfigurationStats = {
  system_configs: { total: 3, by_category: { oauth: 2, email: 1 } },
  account_configs: { total: 1, by_category: { oauth: 1 } },
}

const mockAvailableProvider: AvailableProvider = {
  category: 'oauth',
  provider_name: 'google',
  display_name: 'Google',
  logo_url: 'https://example.com/google.png',
  description: 'Sign in with Google',
}

const mockProviderSchema: ProviderSchema = {
  category: 'oauth',
  provider_name: 'google',
  display_name: 'Google',
  properties: {
    client_id: { type: 'string', title: 'Client ID' },
    client_secret: { type: 'string', title: 'Client Secret', writeOnly: true },
  },
  required: ['client_id', 'client_secret'],
}

const mockAccountListResponse: AccountListResponse = {
  items: [
    {
      id: 'AB1234',
      name: 'Acme Corp',
      slug: 'acme',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      is_active: true,
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
  total_pages: 1,
}

// ─────────────────────────────────────────────────────────────────────────────
// getStats()
// ─────────────────────────────────────────────────────────────────────────────

describe('Admin Service', () => {
  describe('getStats()', () => {
    it('sends GET to /admin/configuration/stats', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/configuration/stats', () => {
          requestReceived = true
          return HttpResponse.json(mockConfigStats)
        })
      )

      await adminService.getStats()
      expect(requestReceived).toBe(true)
    })

    it('returns configuration stats on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/stats', () => HttpResponse.json(mockConfigStats))
      )

      const result = await adminService.getStats()
      expect(result).toEqual(mockConfigStats)
    })

    it('returns system and account config counts', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/stats', () => HttpResponse.json(mockConfigStats))
      )

      const result = await adminService.getStats()
      expect(result.system_configs.total).toBe(3)
      expect(result.account_configs.total).toBe(1)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getRecentConfigs()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getRecentConfigs()', () => {
    it('sends GET to /admin/configuration/recent', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/configuration/recent', () => {
          requestReceived = true
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getRecentConfigs()
      expect(requestReceived).toBe(true)
    })

    it('returns recent configurations on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/recent', () =>
          HttpResponse.json([mockConfiguration])
        )
      )

      const result = await adminService.getRecentConfigs()
      expect(result).toEqual([mockConfiguration])
    })

    it('passes default limit of 5', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/recent', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getRecentConfigs()
      expect(capturedUrl).toContain('limit=5')
    })

    it('passes custom limit param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/recent', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getRecentConfigs(10)
      expect(capturedUrl).toContain('limit=10')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getSystemConfigs()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getSystemConfigs()', () => {
    it('sends GET to /admin/configuration/system', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/configuration/system', () => {
          requestReceived = true
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getSystemConfigs()
      expect(requestReceived).toBe(true)
    })

    it('returns system configurations on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/system', () =>
          HttpResponse.json([mockConfiguration])
        )
      )

      const result = await adminService.getSystemConfigs()
      expect(result).toEqual([mockConfiguration])
    })

    it('passes category param when provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/system', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getSystemConfigs('oauth')
      expect(capturedUrl).toContain('category=oauth')
    })

    it('omits category param when "all" is passed', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/system', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getSystemConfigs('all')
      expect(capturedUrl).not.toContain('category=all')
    })

    it('omits category param when not provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/system', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getSystemConfigs()
      expect(capturedUrl).not.toContain('category')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getAccountConfigs()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getAccountConfigs()', () => {
    it('sends GET to /admin/configuration/account with account_id', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/account', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getAccountConfigs('AB1234')
      expect(capturedUrl).toContain('account_id=AB1234')
    })

    it('returns account configurations on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/account', () =>
          HttpResponse.json([mockConfiguration])
        )
      )

      const result = await adminService.getAccountConfigs('AB1234')
      expect(result).toEqual([mockConfiguration])
    })

    it('passes category param when provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/account', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getAccountConfigs('AB1234', 'email')
      expect(capturedUrl).toContain('category=email')
      expect(capturedUrl).toContain('account_id=AB1234')
    })

    it('omits category param when "all" is passed', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/account', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockConfiguration])
        })
      )

      await adminService.getAccountConfigs('AB1234', 'all')
      expect(capturedUrl).not.toContain('category=all')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getAccounts()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getAccounts()', () => {
    it('sends GET to /accounts', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/accounts', () => {
          requestReceived = true
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await adminService.getAccounts()
      expect(requestReceived).toBe(true)
    })

    it('returns account list on success', async () => {
      server.use(
        http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountListResponse))
      )

      const result = await adminService.getAccounts()
      expect(result).toEqual(mockAccountListResponse)
    })

    it('passes default page and page_size params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/accounts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await adminService.getAccounts()
      expect(capturedUrl).toContain('page=1')
      expect(capturedUrl).toContain('page_size=100')
    })

    it('passes search param when provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/accounts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await adminService.getAccounts('acme')
      expect(capturedUrl).toContain('search=acme')
    })

    it('passes custom page and page_size', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/accounts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await adminService.getAccounts(undefined, 2, 25)
      expect(capturedUrl).toContain('page=2')
      expect(capturedUrl).toContain('page_size=25')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateConfig()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateConfig()', () => {
    it('sends PATCH to /admin/configuration/{configId} with enabled flag', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.patch('/api/v1/admin/configuration/cfg-1', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ ...mockConfiguration, enabled: false })
        })
      )

      await adminService.updateConfig('cfg-1', false)
      expect(capturedBody).toEqual({ enabled: false })
    })

    it('returns updated configuration on success', async () => {
      const updatedConfig = { ...mockConfiguration, enabled: false }

      server.use(
        http.patch('/api/v1/admin/configuration/cfg-1', () =>
          HttpResponse.json(updatedConfig)
        )
      )

      const result = await adminService.updateConfig('cfg-1', false)
      expect(result.enabled).toBe(false)
    })

    it('propagates 404 when config not found', async () => {
      server.use(
        http.patch('/api/v1/admin/configuration/missing', () =>
          HttpResponse.json({ detail: 'Configuration not found' }, { status: 404 })
        )
      )

      await expect(adminService.updateConfig('missing', true)).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // deleteConfig()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('deleteConfig()', () => {
    it('sends DELETE to /admin/configuration/{configId}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/admin/configuration/cfg-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await adminService.deleteConfig('cfg-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/admin/configuration/cfg-1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await adminService.deleteConfig('cfg-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when config not found', async () => {
      server.use(
        http.delete('/api/v1/admin/configuration/missing', () =>
          HttpResponse.json({ detail: 'Configuration not found' }, { status: 404 })
        )
      )

      await expect(adminService.deleteConfig('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getAvailableProviders()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getAvailableProviders()', () => {
    it('sends GET to /admin/configuration/providers', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/configuration/providers', () => {
          requestReceived = true
          return HttpResponse.json([mockAvailableProvider])
        })
      )

      await adminService.getAvailableProviders()
      expect(requestReceived).toBe(true)
    })

    it('returns list of available providers on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/providers', () =>
          HttpResponse.json([mockAvailableProvider])
        )
      )

      const result = await adminService.getAvailableProviders()
      expect(result).toEqual([mockAvailableProvider])
    })

    it('passes category filter when provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/providers', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockAvailableProvider])
        })
      )

      await adminService.getAvailableProviders('oauth')
      expect(capturedUrl).toContain('category=oauth')
    })

    it('omits category param when "all" is passed', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/configuration/providers', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockAvailableProvider])
        })
      )

      await adminService.getAvailableProviders('all')
      expect(capturedUrl).not.toContain('category=all')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getProviderSchema()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getProviderSchema()', () => {
    it('sends GET to /admin/configuration/schema/{category}/{providerName}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/configuration/schema/oauth/google', () => {
          requestReceived = true
          return HttpResponse.json(mockProviderSchema)
        })
      )

      await adminService.getProviderSchema('oauth', 'google')
      expect(requestReceived).toBe(true)
    })

    it('returns provider schema on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/schema/oauth/google', () =>
          HttpResponse.json(mockProviderSchema)
        )
      )

      const result = await adminService.getProviderSchema('oauth', 'google')
      expect(result).toEqual(mockProviderSchema)
    })

    it('returns required fields list', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/schema/oauth/google', () =>
          HttpResponse.json(mockProviderSchema)
        )
      )

      const result = await adminService.getProviderSchema('oauth', 'google')
      expect(result.required).toContain('client_id')
      expect(result.required).toContain('client_secret')
    })

    it('propagates 404 when schema not found', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/schema/oauth/unknown', () =>
          HttpResponse.json({ detail: 'Provider not found' }, { status: 404 })
        )
      )

      await expect(adminService.getProviderSchema('oauth', 'unknown')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getConfigValues()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getConfigValues()', () => {
    it('sends GET to /admin/configuration/{configId}/values', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/configuration/cfg-1/values', () => {
          requestReceived = true
          return HttpResponse.json({ client_id: 'abc123' })
        })
      )

      await adminService.getConfigValues('cfg-1')
      expect(requestReceived).toBe(true)
    })

    it('returns config values on success', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/cfg-1/values', () =>
          HttpResponse.json({ client_id: 'abc123', client_secret: '***' })
        )
      )

      const result = await adminService.getConfigValues('cfg-1')
      expect(result).toEqual({ client_id: 'abc123', client_secret: '***' })
    })

    it('propagates 404 when config not found', async () => {
      server.use(
        http.get('/api/v1/admin/configuration/missing/values', () =>
          HttpResponse.json({ detail: 'Configuration not found' }, { status: 404 })
        )
      )

      await expect(adminService.getConfigValues('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateConfigValues()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateConfigValues()', () => {
    it('sends PATCH to /admin/configuration/{configId}/values with values', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.patch('/api/v1/admin/configuration/cfg-1/values', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockConfiguration)
        })
      )

      await adminService.updateConfigValues('cfg-1', { client_id: 'new-id' })

      expect(capturedBody).toEqual({ client_id: 'new-id' })
    })

    it('returns updated configuration on success', async () => {
      server.use(
        http.patch('/api/v1/admin/configuration/cfg-1/values', () =>
          HttpResponse.json(mockConfiguration)
        )
      )

      const result = await adminService.updateConfigValues('cfg-1', { client_id: 'new-id' })
      expect(result).toEqual(mockConfiguration)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // createConfig()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('createConfig()', () => {
    it('sends POST to /admin/configuration with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/admin/configuration', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockConfiguration, { status: 201 })
        })
      )

      await adminService.createConfig({
        category: 'oauth',
        provider_name: 'google',
        display_name: 'Google OAuth',
        config: { client_id: 'abc', client_secret: 'xyz' },
      })

      expect(capturedBody).toMatchObject({
        category: 'oauth',
        provider_name: 'google',
        display_name: 'Google OAuth',
      })
    })

    it('returns created configuration on success', async () => {
      server.use(
        http.post('/api/v1/admin/configuration', () =>
          HttpResponse.json(mockConfiguration, { status: 201 })
        )
      )

      const result = await adminService.createConfig({
        category: 'oauth',
        provider_name: 'google',
        display_name: 'Google OAuth',
        config: {},
      })
      expect(result).toEqual(mockConfiguration)
    })

    it('propagates API errors', async () => {
      server.use(
        http.post('/api/v1/admin/configuration', () =>
          HttpResponse.json({ detail: 'Provider already configured' }, { status: 409 })
        )
      )

      await expect(
        adminService.createConfig({
          category: 'oauth',
          provider_name: 'google',
          display_name: 'Google',
          config: {},
        })
      ).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // testConnection()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('testConnection()', () => {
    it('sends POST to /admin/configuration/test-connection with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/admin/configuration/test-connection', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ success: true, message: 'Connection successful' })
        })
      )

      await adminService.testConnection({
        category: 'oauth',
        provider_name: 'google',
        config: { client_id: 'abc', client_secret: 'xyz' },
      })

      expect(capturedBody).toMatchObject({ category: 'oauth', provider_name: 'google' })
    })

    it('returns success and message on successful connection', async () => {
      server.use(
        http.post('/api/v1/admin/configuration/test-connection', () =>
          HttpResponse.json({ success: true, message: 'Connection successful' })
        )
      )

      const result = await adminService.testConnection({
        category: 'oauth',
        provider_name: 'google',
        config: {},
      })
      expect(result.success).toBe(true)
      expect(result.message).toBe('Connection successful')
    })

    it('returns failure details on unsuccessful connection', async () => {
      server.use(
        http.post('/api/v1/admin/configuration/test-connection', () =>
          HttpResponse.json({ success: false, message: 'Invalid credentials' })
        )
      )

      const result = await adminService.testConnection({
        category: 'oauth',
        provider_name: 'google',
        config: {},
      })
      expect(result.success).toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // setDefaultConfig()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('setDefaultConfig()', () => {
    it('sends POST to /admin/configuration/{configId}/set-default', async () => {
      let requestReceived = false

      server.use(
        http.post('/api/v1/admin/configuration/cfg-1/set-default', () => {
          requestReceived = true
          return HttpResponse.json({
            status: 'ok',
            is_default: true,
            provider_name: 'google',
            display_name: 'Google OAuth',
          })
        })
      )

      await adminService.setDefaultConfig('cfg-1')
      expect(requestReceived).toBe(true)
    })

    it('returns is_default: true on success', async () => {
      server.use(
        http.post('/api/v1/admin/configuration/cfg-1/set-default', () =>
          HttpResponse.json({
            status: 'ok',
            is_default: true,
            provider_name: 'google',
            display_name: 'Google OAuth',
          })
        )
      )

      const result = await adminService.setDefaultConfig('cfg-1')
      expect(result.is_default).toBe(true)
    })

    it('propagates 404 when config not found', async () => {
      server.use(
        http.post('/api/v1/admin/configuration/missing/set-default', () =>
          HttpResponse.json({ detail: 'Configuration not found' }, { status: 404 })
        )
      )

      await expect(adminService.setDefaultConfig('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // unsetDefaultConfig()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('unsetDefaultConfig()', () => {
    it('sends DELETE to /admin/configuration/{configId}/set-default', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/admin/configuration/cfg-1/set-default', () => {
          requestReceived = true
          return HttpResponse.json({ status: 'ok', is_default: false })
        })
      )

      await adminService.unsetDefaultConfig('cfg-1')
      expect(requestReceived).toBe(true)
    })

    it('returns is_default: false on success', async () => {
      server.use(
        http.delete('/api/v1/admin/configuration/cfg-1/set-default', () =>
          HttpResponse.json({ status: 'ok', is_default: false })
        )
      )

      const result = await adminService.unsetDefaultConfig('cfg-1')
      expect(result.is_default).toBe(false)
    })

    it('propagates 404 when config not found', async () => {
      server.use(
        http.delete('/api/v1/admin/configuration/missing/set-default', () =>
          HttpResponse.json({ detail: 'Configuration not found' }, { status: 404 })
        )
      )

      await expect(adminService.unsetDefaultConfig('missing')).rejects.toThrow()
    })
  })
})
