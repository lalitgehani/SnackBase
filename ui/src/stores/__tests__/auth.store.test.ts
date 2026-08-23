import { describe, it, expect, beforeEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { act } from '@testing-library/react'
import { server } from '@/test/mocks/server'
import { SnackBaseClient } from '@snackbase/sdk'
import { setInstanceClientForTests } from '@/lib/snackbase/instanceClientRef'
import { AUTH_STORAGE_KEY } from '@/lib/snackbase/constants'
import { useAuthStore } from '../auth.store'
import type { AuthResponse } from '@/types/auth.types'
import { isSuperadminAccount, SYSTEM_ACCOUNT_ID } from '@/lib/auth'

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

const initialState = {
  user: null,
  account: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
}

function resetStore() {
  useAuthStore.setState(initialState)
}

describe('Auth Store', () => {
  beforeEach(() => {
    localStorage.clear()
    resetStore()
    vi.clearAllMocks()
    setInstanceClientForTests(
      new SnackBaseClient({
        baseUrl: 'http://localhost',
        storageBackend: 'memory',
        authStorageKey: AUTH_STORAGE_KEY,
        defaultAccount: 'SY0000',
      }),
    )
  })

  describe('initial state', () => {
    it('has isAuthenticated: false', () => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })
  })

  describe('login()', () => {
    it('calls SDK login and sets user/token/account on success', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockAuthResponse.user)
      expect(state.account).toEqual(mockAuthResponse.account)
      expect(state.token).toBe('access-token-abc')
      expect(state.refreshToken).toBe('refresh-token-xyz')
      expect(state.isAuthenticated).toBe(true)
    })

    it('stores tokens in SDK auth manager, not Zustand persist payload', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      const persisted = localStorage.getItem('auth-storage')
      expect(persisted).toBeTruthy()
      const { state } = JSON.parse(persisted!)
      expect(state.token).toBeUndefined()
      expect(state.refreshToken).toBeUndefined()
      expect(state.isAuthenticated).toBe(true)
      expect(useAuthStore.getState().token).toBe('access-token-abc')
    })

    it('sets error state on API failure', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 }),
        ),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'wrong').catch(() => {})
      })

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().error).not.toBeNull()
    })
  })

  describe('logout()', () => {
    it('clears user, token, account, and sets isAuthenticated: false', async () => {
      useAuthStore.setState({
        user: mockAuthResponse.user,
        account: mockAuthResponse.account,
        token: 'access-token-abc',
        refreshToken: 'refresh-token-xyz',
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })

      act(() => {
        useAuthStore.getState().logout()
      })

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.token).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })

    it('persists identity without tokens after logout', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
        http.post('http://localhost/api/v1/auth/logout', () => HttpResponse.json({ success: true })),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      act(() => {
        useAuthStore.getState().logout()
      })

      const persisted = localStorage.getItem('auth-storage')
      expect(persisted).toBeTruthy()
      const { state } = JSON.parse(persisted!)
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
      expect(state.account).toBeNull()
      expect(state.token).toBeUndefined()
      expect(state.refreshToken).toBeUndefined()
    })
  })

  describe('restoreSession()', () => {
    it('does nothing when there is no token', async () => {
      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('maps /auth/me onto the system account and keeps the SDK token', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
        http.get('http://localhost/api/v1/auth/me', () =>
          HttpResponse.json({
            user_id: 'user-1',
            account_id: SYSTEM_ACCOUNT_ID,
            email: 'admin@example.com',
            role: 'admin',
          }),
        ),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.token).toBe('access-token-abc')
      expect(state.token).not.toBe('')
      expect(isSuperadminAccount(state.account)).toBe(true)
      expect(state.account?.id).toBe(SYSTEM_ACCOUNT_ID)
      expect(state.account?.slug).toBe('system')
      expect(state.user?.email).toBe('admin@example.com')
    })

    it('does not treat a tenant /auth/me account as superadmin', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
        http.get('http://localhost/api/v1/auth/me', () =>
          HttpResponse.json({
            user_id: 'user-1',
            account_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
            email: 'owner@acme.example.com',
            role: 'admin',
          }),
        ),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(isSuperadminAccount(state.account)).toBe(false)
      expect(state.account?.id).toBe('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
    })

    it('does not clobber persisted account when /auth/me has no account_id', async () => {
      server.use(
        http.post('http://localhost/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse)),
        http.get('http://localhost/api/v1/auth/me', () =>
          HttpResponse.json({
            user_id: 'user-1',
            email: 'admin@example.com',
            role: 'admin',
          }),
        ),
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.account).toEqual(mockAuthResponse.account)
    })
  })

  describe('clearError()', () => {
    it('resets error state to null', () => {
      useAuthStore.setState({ error: 'Login failed' })
      act(() => {
        useAuthStore.getState().clearError()
      })
      expect(useAuthStore.getState().error).toBeNull()
    })
  })
})
