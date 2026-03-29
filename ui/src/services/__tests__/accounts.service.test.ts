import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getAccounts,
  getAccountById,
  createAccount,
  updateAccount,
  deleteAccount,
  getAccountUsers,
} from '../accounts.service'
import type {
  AccountListResponse,
  AccountDetail,
  AccountUsersResponse,
} from '../accounts.service'

const mockAccountListResponse: AccountListResponse = {
  items: [
    {
      id: 'AB1234',
      account_code: 'AB1234',
      slug: 'acme',
      name: 'Acme Corp',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      user_count: 5,
      status: 'active',
    },
    {
      id: 'CD5678',
      account_code: 'CD5678',
      slug: 'globex',
      name: 'Globex',
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
      user_count: 2,
      status: 'active',
    },
  ],
  total: 2,
  page: 1,
  page_size: 25,
  total_pages: 1,
}

const mockAccountDetail: AccountDetail = {
  id: 'AB1234',
  account_code: 'AB1234',
  slug: 'acme',
  name: 'Acme Corp',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user_count: 5,
  collections_used: ['posts', 'products'],
}

const mockAccountUsersResponse: AccountUsersResponse = {
  items: [
    {
      id: 'user-1',
      email: 'alice@acme.com',
      role: 'admin',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
  total_pages: 1,
}

describe('Accounts Service', () => {
  describe('getAccounts()', () => {
    it('sends GET to /accounts', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/accounts', () => {
          requestReceived = true
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await getAccounts()
      expect(requestReceived).toBe(true)
    })

    it('returns account list response on success', async () => {
      server.use(
        http.get('/api/v1/accounts', () => HttpResponse.json(mockAccountListResponse))
      )

      const result = await getAccounts()
      expect(result).toEqual(mockAccountListResponse)
    })

    it('passes query params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/accounts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await getAccounts({ page: 2, page_size: 10, search: 'acme' })

      expect(capturedUrl).toContain('page=2')
      expect(capturedUrl).toContain('page_size=10')
      expect(capturedUrl).toContain('search=acme')
    })

    it('passes sort params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/accounts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAccountListResponse)
        })
      )

      await getAccounts({ sort_by: 'name', sort_order: 'asc' })

      expect(capturedUrl).toContain('sort_by=name')
      expect(capturedUrl).toContain('sort_order=asc')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/accounts', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getAccounts()).rejects.toThrow()
    })
  })

  describe('getAccountById()', () => {
    it('sends GET to /accounts/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/accounts/AB1234', () => {
          requestReceived = true
          return HttpResponse.json(mockAccountDetail)
        })
      )

      await getAccountById('AB1234')
      expect(requestReceived).toBe(true)
    })

    it('returns account detail on success', async () => {
      server.use(
        http.get('/api/v1/accounts/AB1234', () => HttpResponse.json(mockAccountDetail))
      )

      const result = await getAccountById('AB1234')
      expect(result).toEqual(mockAccountDetail)
    })

    it('returns collections_used in the response', async () => {
      server.use(
        http.get('/api/v1/accounts/AB1234', () => HttpResponse.json(mockAccountDetail))
      )

      const result = await getAccountById('AB1234')
      expect(result.collections_used).toEqual(['posts', 'products'])
    })

    it('propagates 404 when account not found', async () => {
      server.use(
        http.get('/api/v1/accounts/ZZZZZZ', () =>
          HttpResponse.json({ detail: 'Account not found' }, { status: 404 })
        )
      )

      await expect(getAccountById('ZZZZZZ')).rejects.toThrow()
    })
  })

  describe('createAccount()', () => {
    it('sends POST to /accounts with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/accounts', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockAccountDetail, { status: 201 })
        })
      )

      await createAccount({ name: 'Acme Corp', slug: 'acme' })

      expect(capturedBody).toEqual({ name: 'Acme Corp', slug: 'acme' })
    })

    it('sends POST without slug when not provided', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/accounts', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockAccountDetail, { status: 201 })
        })
      )

      await createAccount({ name: 'Acme Corp' })

      expect(capturedBody).toEqual({ name: 'Acme Corp' })
    })

    it('returns created account detail on success', async () => {
      server.use(
        http.post('/api/v1/accounts', () =>
          HttpResponse.json(mockAccountDetail, { status: 201 })
        )
      )

      const result = await createAccount({ name: 'Acme Corp' })
      expect(result).toEqual(mockAccountDetail)
    })

    it('propagates API errors on duplicate slug', async () => {
      server.use(
        http.post('/api/v1/accounts', () =>
          HttpResponse.json({ detail: 'Slug already exists' }, { status: 409 })
        )
      )

      await expect(createAccount({ name: 'Acme Corp', slug: 'acme' })).rejects.toThrow()
    })
  })

  describe('updateAccount()', () => {
    it('sends PUT to /accounts/{id} with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.put('/api/v1/accounts/AB1234', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockAccountDetail)
        })
      )

      await updateAccount('AB1234', { name: 'Acme Corp Updated' })

      expect(capturedBody).toEqual({ name: 'Acme Corp Updated' })
    })

    it('returns updated account detail on success', async () => {
      const updated = { ...mockAccountDetail, name: 'Acme Corp Updated' }

      server.use(
        http.put('/api/v1/accounts/AB1234', () => HttpResponse.json(updated))
      )

      const result = await updateAccount('AB1234', { name: 'Acme Corp Updated' })
      expect(result.name).toBe('Acme Corp Updated')
    })

    it('propagates 404 when account not found', async () => {
      server.use(
        http.put('/api/v1/accounts/ZZZZZZ', () =>
          HttpResponse.json({ detail: 'Account not found' }, { status: 404 })
        )
      )

      await expect(updateAccount('ZZZZZZ', { name: 'Nope' })).rejects.toThrow()
    })
  })

  describe('deleteAccount()', () => {
    it('sends DELETE to /accounts/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/accounts/AB1234', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deleteAccount('AB1234')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/accounts/AB1234', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await deleteAccount('AB1234')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when account not found', async () => {
      server.use(
        http.delete('/api/v1/accounts/ZZZZZZ', () =>
          HttpResponse.json({ detail: 'Account not found' }, { status: 404 })
        )
      )

      await expect(deleteAccount('ZZZZZZ')).rejects.toThrow()
    })
  })

  describe('getAccountUsers()', () => {
    it('sends GET to /accounts/{id}/users', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/accounts/AB1234/users', () => {
          requestReceived = true
          return HttpResponse.json(mockAccountUsersResponse)
        })
      )

      await getAccountUsers('AB1234')
      expect(requestReceived).toBe(true)
    })

    it('returns account users response on success', async () => {
      server.use(
        http.get('/api/v1/accounts/AB1234/users', () =>
          HttpResponse.json(mockAccountUsersResponse)
        )
      )

      const result = await getAccountUsers('AB1234')
      expect(result).toEqual(mockAccountUsersResponse)
    })

    it('passes page and page_size params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/accounts/AB1234/users', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAccountUsersResponse)
        })
      )

      await getAccountUsers('AB1234', 2, 10)

      expect(capturedUrl).toContain('page=2')
      expect(capturedUrl).toContain('page_size=10')
    })
  })
})
