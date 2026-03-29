import { describe, it, expect, beforeEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { act } from '@testing-library/react'
import { server } from '@/test/mocks/server'
import { useAuthStore } from '../auth.store'
import type { AuthResponse } from '@/types/auth.types'

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

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

const mockCurrentUser = {
  user_id: 'user-1',
  account_id: 'SY0000',
  email: 'admin@example.com',
  role: 'superadmin',
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Reset the store to its initial state before each test (preserves actions). */
function resetStore() {
  useAuthStore.setState(initialState)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Auth Store', () => {
  beforeEach(() => {
    localStorage.clear()
    resetStore()
    vi.clearAllMocks()
  })

  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  describe('initial state', () => {
    it('has isAuthenticated: false', () => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('has user: null', () => {
      expect(useAuthStore.getState().user).toBeNull()
    })

    it('has token: null', () => {
      expect(useAuthStore.getState().token).toBeNull()
    })

    it('has refreshToken: null', () => {
      expect(useAuthStore.getState().refreshToken).toBeNull()
    })

    it('has account: null', () => {
      expect(useAuthStore.getState().account).toBeNull()
    })

    it('has error: null', () => {
      expect(useAuthStore.getState().error).toBeNull()
    })

    it('has isLoading: false', () => {
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // login()
  // -------------------------------------------------------------------------

  describe('login()', () => {
    it('calls auth service and sets user/token/account on success', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockAuthResponse.user)
      expect(state.account).toEqual(mockAuthResponse.account)
      expect(state.token).toBe('access-token-abc')
      expect(state.refreshToken).toBe('refresh-token-xyz')
    })

    it('sets isAuthenticated: true on success', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })

    it('stores auth state in localStorage via persist middleware', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      const stored = localStorage.getItem('auth-storage')
      expect(stored).not.toBeNull()

      const parsed = JSON.parse(stored!)
      expect(parsed.state.token).toBe('access-token-abc')
      expect(parsed.state.refreshToken).toBe('refresh-token-xyz')
      expect(parsed.state.isAuthenticated).toBe(true)
    })

    it('clears isLoading after successful login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      expect(useAuthStore.getState().isLoading).toBe(false)
    })

    it('sets error state and keeps isAuthenticated: false on API failure', async () => {
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 })
        )
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'wrong').catch(() => {})
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.error).not.toBeNull()
      expect(state.token).toBeNull()
      expect(state.user).toBeNull()
    })

    it('re-throws the error so callers can handle it', async () => {
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
        )
      )

      await expect(
        act(async () => {
          await useAuthStore.getState().login('admin@example.com', 'wrong')
        })
      ).rejects.toThrow()
    })

    it('clears isLoading after a failed login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () =>
          HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
        )
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'wrong').catch(() => {})
      })

      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // logout()
  // -------------------------------------------------------------------------

  describe('logout()', () => {
    it('clears user, token, account, and sets isAuthenticated: false', async () => {
      // Seed an authenticated state
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
      expect(state.account).toBeNull()
      expect(state.token).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })

    it('clears auth data from localStorage (token and user become null)', () => {
      // Pre-seed localStorage with auth data
      localStorage.setItem(
        'auth-storage',
        JSON.stringify({
          state: { token: 'abc', isAuthenticated: true, user: { id: 'u1' } },
          version: 0,
        })
      )

      act(() => {
        useAuthStore.getState().logout()
      })

      // The persist middleware keeps the key but writes cleared state back
      const stored = localStorage.getItem('auth-storage')
      expect(stored).not.toBeNull()
      const { state } = JSON.parse(stored!)
      expect(state.token).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
    })

    it('does not throw when localStorage has no auth-storage', () => {
      expect(() => {
        act(() => {
          useAuthStore.getState().logout()
        })
      }).not.toThrow()
    })
  })

  // -------------------------------------------------------------------------
  // restoreSession()
  // -------------------------------------------------------------------------

  describe('restoreSession()', () => {
    it('does nothing when there is no token', async () => {
      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('keeps session active when token is valid', async () => {
      server.use(
        http.get('/api/v1/auth/me', () => HttpResponse.json(mockCurrentUser))
      )

      useAuthStore.setState({
        token: 'valid-token',
        isAuthenticated: true,
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      expect(useAuthStore.getState().isAuthenticated).toBe(true)
      expect(useAuthStore.getState().token).toBe('valid-token')
    })

    it('clears session when token validation fails (expired token)', async () => {
      server.use(
        http.get('/api/v1/auth/me', () =>
          HttpResponse.json({ detail: 'Token expired' }, { status: 401 })
        )
      )

      useAuthStore.setState({
        token: 'expired-token',
        isAuthenticated: true,
        user: mockAuthResponse.user,
        account: mockAuthResponse.account,
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.token).toBeNull()
      expect(state.user).toBeNull()
    })

    it('sets isLoading: false after session is verified', async () => {
      server.use(
        http.get('/api/v1/auth/me', () => HttpResponse.json(mockCurrentUser))
      )

      useAuthStore.setState({ token: 'valid-token', isAuthenticated: true })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // clearError()
  // -------------------------------------------------------------------------

  describe('clearError()', () => {
    it('resets error state to null', () => {
      useAuthStore.setState({ error: 'Login failed' })

      act(() => {
        useAuthStore.getState().clearError()
      })

      expect(useAuthStore.getState().error).toBeNull()
    })

    it('is a no-op when error is already null', () => {
      act(() => {
        useAuthStore.getState().clearError()
      })

      expect(useAuthStore.getState().error).toBeNull()
    })
  })

  // -------------------------------------------------------------------------
  // setAuth()
  // -------------------------------------------------------------------------

  describe('setAuth()', () => {
    it('sets user, account, token, refreshToken, and isAuthenticated: true', () => {
      act(() => {
        useAuthStore.getState().setAuth(mockAuthResponse)
      })

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockAuthResponse.user)
      expect(state.account).toEqual(mockAuthResponse.account)
      expect(state.token).toBe('access-token-abc')
      expect(state.refreshToken).toBe('refresh-token-xyz')
      expect(state.isAuthenticated).toBe(true)
    })

    it('clears error and isLoading when called', () => {
      useAuthStore.setState({ error: 'previous error', isLoading: true })

      act(() => {
        useAuthStore.getState().setAuth(mockAuthResponse)
      })

      expect(useAuthStore.getState().error).toBeNull()
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  // -------------------------------------------------------------------------
  // Persistence (simulated page reload)
  // -------------------------------------------------------------------------

  describe('store persistence', () => {
    it('persists auth state to localStorage after login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      const stored = localStorage.getItem('auth-storage')
      expect(stored).not.toBeNull()

      const { state } = JSON.parse(stored!)
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).toEqual(mockAuthResponse.user)
      expect(state.account).toEqual(mockAuthResponse.account)
    })

    it('restores persisted state after simulated page reload', async () => {
      // Step 1: reset in-memory state first (beforeEach already does this, but
      //         be explicit). The persist middleware writes empty state to localStorage
      //         as a side-effect of setState.
      useAuthStore.setState(initialState)
      expect(useAuthStore.getState().isAuthenticated).toBe(false)

      // Step 2: now overwrite localStorage with a valid session, simulating what
      //         the previous page visit left behind.
      const persistedSession = {
        state: {
          user: mockAuthResponse.user,
          account: mockAuthResponse.account,
          token: 'access-token-abc',
          refreshToken: 'refresh-token-xyz',
          isAuthenticated: true,
        },
        version: 0,
      }
      localStorage.setItem('auth-storage', JSON.stringify(persistedSession))

      // Step 3: re-hydrate from localStorage (simulates app bootstrap)
      await act(async () => {
        await useAuthStore.persist.rehydrate()
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.token).toBe('access-token-abc')
      expect(state.user?.email).toBe('admin@example.com')
    })

    it('does not persist isLoading or error to localStorage', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => HttpResponse.json(mockAuthResponse))
      )

      await act(async () => {
        await useAuthStore.getState().login('admin@example.com', 'secret123')
      })

      const stored = localStorage.getItem('auth-storage')
      const { state } = JSON.parse(stored!)

      expect(state).not.toHaveProperty('isLoading')
      expect(state).not.toHaveProperty('error')
    })
  })
})
