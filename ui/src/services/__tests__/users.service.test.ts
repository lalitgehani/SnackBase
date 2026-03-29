import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getUsers,
  getUser,
  createUser,
  updateUser,
  deactivateUser,
  resetUserPassword,
  verifyUser,
  resendUserVerification,
} from '../users.service'
import type { User, UserListResponse } from '../users.service'

const mockUser: User = {
  id: 'user-1',
  email: 'alice@acme.com',
  account_id: 'AB1234',
  account_code: 'AB1234',
  account_name: 'Acme Corp',
  role_id: 2,
  role_name: 'admin',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2024-06-01T12:00:00Z',
  email_verified: true,
  email_verified_at: '2024-01-02T00:00:00Z',
}

const mockUserListResponse: UserListResponse = {
  total: 2,
  items: [
    mockUser,
    {
      id: 'user-2',
      email: 'bob@acme.com',
      account_id: 'AB1234',
      account_code: 'AB1234',
      account_name: 'Acme Corp',
      role_id: 3,
      role_name: 'member',
      is_active: true,
      created_at: '2024-02-01T00:00:00Z',
      last_login: null,
      email_verified: false,
      email_verified_at: null,
    },
  ],
}

describe('Users Service', () => {
  describe('getUsers()', () => {
    it('sends GET to /users', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/users', () => {
          requestReceived = true
          return HttpResponse.json(mockUserListResponse)
        })
      )

      await getUsers()
      expect(requestReceived).toBe(true)
    })

    it('returns user list response on success', async () => {
      server.use(
        http.get('/api/v1/users', () => HttpResponse.json(mockUserListResponse))
      )

      const result = await getUsers()
      expect(result).toEqual(mockUserListResponse)
    })

    it('passes account_id filter param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/users', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockUserListResponse)
        })
      )

      await getUsers({ account_id: 'AB1234' })

      expect(capturedUrl).toContain('account_id=AB1234')
    })

    it('passes is_active filter param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/users', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockUserListResponse)
        })
      )

      await getUsers({ is_active: true })

      expect(capturedUrl).toContain('is_active=true')
    })

    it('passes search param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/users', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockUserListResponse)
        })
      )

      await getUsers({ search: 'alice' })

      expect(capturedUrl).toContain('search=alice')
    })

    it('passes pagination params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/users', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockUserListResponse)
        })
      )

      await getUsers({ skip: 25, limit: 25 })

      expect(capturedUrl).toContain('skip=25')
      expect(capturedUrl).toContain('limit=25')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/users', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getUsers()).rejects.toThrow()
    })
  })

  describe('getUser()', () => {
    it('sends GET to /users/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/users/user-1', () => {
          requestReceived = true
          return HttpResponse.json(mockUser)
        })
      )

      await getUser('user-1')
      expect(requestReceived).toBe(true)
    })

    it('returns user on success', async () => {
      server.use(
        http.get('/api/v1/users/user-1', () => HttpResponse.json(mockUser))
      )

      const result = await getUser('user-1')
      expect(result).toEqual(mockUser)
    })

    it('propagates 404 when user not found', async () => {
      server.use(
        http.get('/api/v1/users/nonexistent', () =>
          HttpResponse.json({ detail: 'User not found' }, { status: 404 })
        )
      )

      await expect(getUser('nonexistent')).rejects.toThrow()
    })
  })

  describe('createUser()', () => {
    it('sends POST to /users with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/users', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockUser, { status: 201 })
        })
      )

      await createUser({
        email: 'alice@acme.com',
        password: 'secret123',
        account_id: 'AB1234',
        role_id: 2,
      })

      expect(capturedBody).toEqual({
        email: 'alice@acme.com',
        password: 'secret123',
        account_id: 'AB1234',
        role_id: 2,
      })
    })

    it('sends is_active when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/users', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockUser, { status: 201 })
        })
      )

      await createUser({
        email: 'alice@acme.com',
        password: 'secret123',
        account_id: 'AB1234',
        role_id: 2,
        is_active: false,
      })

      expect(capturedBody).toMatchObject({ is_active: false })
    })

    it('returns created user on success', async () => {
      server.use(
        http.post('/api/v1/users', () => HttpResponse.json(mockUser, { status: 201 }))
      )

      const result = await createUser({
        email: 'alice@acme.com',
        password: 'secret123',
        account_id: 'AB1234',
        role_id: 2,
      })

      expect(result).toEqual(mockUser)
    })

    it('propagates API errors on duplicate email', async () => {
      server.use(
        http.post('/api/v1/users', () =>
          HttpResponse.json({ detail: 'Email already exists' }, { status: 409 })
        )
      )

      await expect(
        createUser({ email: 'alice@acme.com', password: 'pass', account_id: 'AB1234', role_id: 2 })
      ).rejects.toThrow()
    })
  })

  describe('updateUser()', () => {
    it('sends PATCH to /users/{id} with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.patch('/api/v1/users/user-1', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockUser)
        })
      )

      await updateUser('user-1', { role_id: 3, is_active: false })

      expect(capturedBody).toEqual({ role_id: 3, is_active: false })
    })

    it('returns updated user on success', async () => {
      const updated = { ...mockUser, role_id: 3, role_name: 'member' }

      server.use(
        http.patch('/api/v1/users/user-1', () => HttpResponse.json(updated))
      )

      const result = await updateUser('user-1', { role_id: 3 })
      expect(result.role_id).toBe(3)
    })

    it('propagates 404 when user not found', async () => {
      server.use(
        http.patch('/api/v1/users/nonexistent', () =>
          HttpResponse.json({ detail: 'User not found' }, { status: 404 })
        )
      )

      await expect(updateUser('nonexistent', { is_active: false })).rejects.toThrow()
    })
  })

  describe('deactivateUser()', () => {
    it('sends DELETE to /users/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/users/user-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deactivateUser('user-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/users/user-1', () => new HttpResponse(null, { status: 204 }))
      )

      const result = await deactivateUser('user-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when user not found', async () => {
      server.use(
        http.delete('/api/v1/users/nonexistent', () =>
          HttpResponse.json({ detail: 'User not found' }, { status: 404 })
        )
      )

      await expect(deactivateUser('nonexistent')).rejects.toThrow()
    })
  })

  describe('resetUserPassword()', () => {
    it('sends PUT to /users/{id}/password with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.put('/api/v1/users/user-1/password', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ message: 'Password updated' })
        })
      )

      await resetUserPassword('user-1', { new_password: 'newpass123' })

      expect(capturedBody).toEqual({ new_password: 'newpass123' })
    })

    it('returns message on success', async () => {
      server.use(
        http.put('/api/v1/users/user-1/password', () =>
          HttpResponse.json({ message: 'Password updated' })
        )
      )

      const result = await resetUserPassword('user-1', { new_password: 'newpass123' })
      expect(result.message).toBe('Password updated')
    })
  })

  describe('verifyUser()', () => {
    it('sends POST to /users/{id}/verify', async () => {
      let requestReceived = false

      server.use(
        http.post('/api/v1/users/user-1/verify', () => {
          requestReceived = true
          return HttpResponse.json({ message: 'Email verified' })
        })
      )

      await verifyUser('user-1')
      expect(requestReceived).toBe(true)
    })

    it('returns message on success', async () => {
      server.use(
        http.post('/api/v1/users/user-1/verify', () =>
          HttpResponse.json({ message: 'Email verified' })
        )
      )

      const result = await verifyUser('user-1')
      expect(result.message).toBe('Email verified')
    })
  })

  describe('resendUserVerification()', () => {
    it('sends POST to /users/{id}/resend-verification', async () => {
      let requestReceived = false

      server.use(
        http.post('/api/v1/users/user-1/resend-verification', () => {
          requestReceived = true
          return HttpResponse.json({ message: 'Verification email sent' })
        })
      )

      await resendUserVerification('user-1')
      expect(requestReceived).toBe(true)
    })

    it('returns message on success', async () => {
      server.use(
        http.post('/api/v1/users/user-1/resend-verification', () =>
          HttpResponse.json({ message: 'Verification email sent' })
        )
      )

      const result = await resendUserVerification('user-1')
      expect(result.message).toBe('Verification email sent')
    })
  })
})
