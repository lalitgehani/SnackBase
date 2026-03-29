import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { login, refreshToken, getCurrentUser, logout } from '../auth.service'
import type { AuthResponse, TokenRefreshResponse, CurrentUserResponse } from '@/types/auth.types'

const mockAuthResponse: AuthResponse = {
  token: 'access-token-abc',
  refresh_token: 'refresh-token-xyz',
  expires_in: 3600,
  account: {
    id: 'SY0000',
    slug: 'system',
    name: 'System',
    created_at: '2024-01-01T00:00:00Z',
  },
  user: {
    id: 'user-1',
    email: 'admin@example.com',
    role: 'superadmin',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
}

const mockRefreshResponse: TokenRefreshResponse = {
  token: 'new-access-token',
  refresh_token: 'new-refresh-token',
  expires_in: 3600,
}

const mockCurrentUser: CurrentUserResponse = {
  user_id: 'user-1',
  account_id: 'SY0000',
  email: 'admin@example.com',
  role: 'superadmin',
}

describe('Auth Service', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('login()', () => {
    it('sends POST to /auth/login with correct payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/auth/login', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockAuthResponse)
        })
      )

      await login('admin@example.com', 'secret123')

      expect(capturedBody).toEqual({
        account: 'SY0000',
        email: 'admin@example.com',
        password: 'secret123',
      })
    })

    it('returns auth response on success', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      const result = await login('admin@example.com', 'secret123')
      expect(result).toEqual(mockAuthResponse)
    })

    it('returns token and refresh_token in the response', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      const result = await login('admin@example.com', 'secret123')
      expect(result.token).toBe('access-token-abc')
      expect(result.refresh_token).toBe('refresh-token-xyz')
    })

    it('returns account and user info in the response', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      const result = await login('admin@example.com', 'secret123')
      expect(result.account.id).toBe('SY0000')
      expect(result.user.email).toBe('admin@example.com')
    })

    it('propagates API errors on invalid credentials', async () => {
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 })
        )
      )

      await expect(login('admin@example.com', 'wrong')).rejects.toThrow()
    })

    it('propagates API errors on account not found', async () => {
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Account not found' }, { status: 404 })
        )
      )

      await expect(login('admin@example.com', 'secret123')).rejects.toThrow()
    })

    it('propagates network errors', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.error())
      )

      await expect(login('admin@example.com', 'secret123')).rejects.toThrow()
    })
  })

  describe('refreshToken()', () => {
    it('sends POST to /auth/refresh with the refresh token', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/auth/refresh', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockRefreshResponse)
        })
      )

      await refreshToken('my-refresh-token')

      expect(capturedBody).toEqual({ refresh_token: 'my-refresh-token' })
    })

    it('returns new tokens on success', async () => {
      server.use(
        http.post('/api/v1/auth/refresh', () => HttpResponse.json(mockRefreshResponse))
      )

      const result = await refreshToken('my-refresh-token')
      expect(result).toEqual(mockRefreshResponse)
    })

    it('returns a new access token and refresh token', async () => {
      server.use(
        http.post('/api/v1/auth/refresh', () => HttpResponse.json(mockRefreshResponse))
      )

      const result = await refreshToken('my-refresh-token')
      expect(result.token).toBe('new-access-token')
      expect(result.refresh_token).toBe('new-refresh-token')
    })

    it('propagates errors when refresh token is expired', async () => {
      server.use(
        http.post('/api/v1/auth/refresh', () =>
          HttpResponse.json({ detail: 'Refresh token expired' }, { status: 401 })
        )
      )

      await expect(refreshToken('expired-token')).rejects.toThrow()
    })

    it('propagates errors when refresh token is invalid', async () => {
      server.use(
        http.post('/api/v1/auth/refresh', () =>
          HttpResponse.json({ detail: 'Invalid refresh token' }, { status: 401 })
        )
      )

      await expect(refreshToken('invalid-token')).rejects.toThrow()
    })
  })

  describe('getCurrentUser()', () => {
    it('sends GET to /auth/me', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/auth/me', () => {
          requestReceived = true
          return HttpResponse.json(mockCurrentUser)
        })
      )

      await getCurrentUser()
      expect(requestReceived).toBe(true)
    })

    it('returns user info on success', async () => {
      server.use(
        http.get('/api/v1/auth/me', () => HttpResponse.json(mockCurrentUser))
      )

      const result = await getCurrentUser()
      expect(result).toEqual(mockCurrentUser)
    })

    it('returns correct user fields', async () => {
      server.use(
        http.get('/api/v1/auth/me', () => HttpResponse.json(mockCurrentUser))
      )

      const result = await getCurrentUser()
      expect(result.user_id).toBe('user-1')
      expect(result.account_id).toBe('SY0000')
      expect(result.email).toBe('admin@example.com')
      expect(result.role).toBe('superadmin')
    })

    it('propagates errors when unauthenticated', async () => {
      server.use(
        http.get('/api/v1/auth/me', () =>
          HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 })
        )
      )

      await expect(getCurrentUser()).rejects.toThrow()
    })
  })

  describe('logout()', () => {
    it('removes auth-storage from localStorage', () => {
      localStorage.setItem(
        'auth-storage',
        JSON.stringify({ state: { token: 'abc', refreshToken: 'xyz' } })
      )

      logout()

      expect(localStorage.getItem('auth-storage')).toBeNull()
    })

    it('does not throw when auth-storage does not exist', () => {
      expect(() => logout()).not.toThrow()
    })

    it('clears auth-storage even when other localStorage keys exist', () => {
      localStorage.setItem('auth-storage', JSON.stringify({ state: { token: 'abc' } }))
      localStorage.setItem('other-key', 'other-value')

      logout()

      expect(localStorage.getItem('auth-storage')).toBeNull()
      expect(localStorage.getItem('other-key')).toBe('other-value')
    })
  })
})
