import { describe, it, expect, beforeEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { apiClient, handleApiError } from '../index'
import { AxiosError, AxiosHeaders } from 'axios'

// Helper to set auth state in localStorage
function setAuthStorage(token?: string, refreshToken?: string) {
  const state: Record<string, unknown> = {}
  if (token !== undefined) state.token = token
  if (refreshToken !== undefined) state.refreshToken = refreshToken
  localStorage.setItem('auth-storage', JSON.stringify({ state }))
}

describe('API Client', () => {
  const originalLocation = window.location

  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    // Restore window.location if it was replaced
    if (window.location !== originalLocation) {
      window.location = originalLocation
    }
  })

  describe('Request Interceptor', () => {
    it('adds Authorization header when token exists in localStorage', async () => {
      setAuthStorage('test-token-123')

      let capturedAuth: string | undefined
      server.use(
        http.get('/api/v1/test-auth', ({ request }) => {
          capturedAuth = request.headers.get('Authorization') ?? undefined
          return HttpResponse.json({ ok: true })
        })
      )

      await apiClient.get('/test-auth')
      expect(capturedAuth).toBe('Bearer test-token-123')
    })

    it('sends no Authorization header when token is absent', async () => {
      let capturedAuth: string | null = null
      server.use(
        http.get('/api/v1/test-no-auth', ({ request }) => {
          capturedAuth = request.headers.get('Authorization')
          return HttpResponse.json({ ok: true })
        })
      )

      await apiClient.get('/test-no-auth')
      expect(capturedAuth).toBeNull()
    })

    it('sends no Authorization header when auth-storage has no token', async () => {
      localStorage.setItem('auth-storage', JSON.stringify({ state: {} }))

      let capturedAuth: string | null = null
      server.use(
        http.get('/api/v1/test-empty-token', ({ request }) => {
          capturedAuth = request.headers.get('Authorization')
          return HttpResponse.json({ ok: true })
        })
      )

      await apiClient.get('/test-empty-token')
      expect(capturedAuth).toBeNull()
    })

    it('handles malformed JSON in auth-storage gracefully', async () => {
      localStorage.setItem('auth-storage', '{invalid-json}')
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      server.use(
        http.get('/api/v1/test-bad-json', () => {
          return HttpResponse.json({ ok: true })
        })
      )

      await apiClient.get('/test-bad-json')
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to parse auth state:',
        expect.any(Error)
      )
    })
  })

  describe('Response Interceptor', () => {
    it('passes through successful responses unchanged', async () => {
      server.use(
        http.get('/api/v1/test-success', () => {
          return HttpResponse.json({ data: 'hello' })
        })
      )

      const response = await apiClient.get('/test-success')
      expect(response.status).toBe(200)
      expect(response.data).toEqual({ data: 'hello' })
    })

    it('does not retry non-401 errors', async () => {
      let requestCount = 0
      server.use(
        http.get('/api/v1/test-403', () => {
          requestCount++
          return HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        })
      )

      await expect(apiClient.get('/test-403')).rejects.toThrow()
      expect(requestCount).toBe(1)
    })

    it('does not retry 500 errors', async () => {
      let requestCount = 0
      server.use(
        http.get('/api/v1/test-500', () => {
          requestCount++
          return HttpResponse.json({ detail: 'Server Error' }, { status: 500 })
        })
      )

      await expect(apiClient.get('/test-500')).rejects.toThrow()
      expect(requestCount).toBe(1)
    })

    it('intercepts 401, refreshes token, and retries the original request', async () => {
      setAuthStorage('expired-token', 'valid-refresh-token')

      let requestCount = 0
      server.use(
        http.get('/api/v1/test-retry', ({ request }) => {
          requestCount++
          const auth = request.headers.get('Authorization')
          if (auth === 'Bearer expired-token') {
            return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
          }
          return HttpResponse.json({ data: 'success', token_used: auth })
        }),
        http.post('/api/v1/auth/refresh', async ({ request }) => {
          const body = (await request.json()) as Record<string, string>
          expect(body.refresh_token).toBe('valid-refresh-token')
          return HttpResponse.json({
            token: 'new-access-token',
            refresh_token: 'new-refresh-token',
          })
        })
      )

      const response = await apiClient.get('/test-retry')
      expect(response.data.data).toBe('success')
      expect(requestCount).toBe(2)

      // Verify tokens were updated in localStorage
      const stored = JSON.parse(localStorage.getItem('auth-storage')!)
      expect(stored.state.token).toBe('new-access-token')
      expect(stored.state.refreshToken).toBe('new-refresh-token')
    })

    it('clears auth and redirects when refresh token also fails', async () => {
      setAuthStorage('expired-token', 'expired-refresh-token')

      server.use(
        http.get('/api/v1/test-logout', () => {
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
        }),
        http.post('/api/v1/auth/refresh', () => {
          return HttpResponse.json(
            { detail: 'Invalid refresh token' },
            { status: 401 }
          )
        })
      )

      await expect(apiClient.get('/test-logout')).rejects.toThrow()

      // Auth storage should be cleared on failed refresh
      expect(localStorage.getItem('auth-storage')).toBeNull()
      // Note: window.location.href redirect to /admin/login is also triggered
      // but jsdom doesn't implement navigation, so we verify state cleanup only
    })

    it('clears auth when no refresh token exists in storage', async () => {
      setAuthStorage('expired-token') // no refresh token

      server.use(
        http.get('/api/v1/test-no-refresh', () => {
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
        })
      )

      await expect(apiClient.get('/test-no-refresh')).rejects.toThrow()
      // localStorage is cleared (proves catch block ran)
      expect(localStorage.getItem('auth-storage')).toBeNull()
    })

    it('clears auth when no auth-storage exists during 401', async () => {
      // localStorage is empty — no auth-storage at all
      server.use(
        http.get('/api/v1/test-no-storage', () => {
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
        })
      )

      // Should reject (interceptor tries refresh, fails, clears state)
      await expect(apiClient.get('/test-no-storage')).rejects.toThrow()
    })
  })

  describe('handleApiError', () => {
    it('extracts message from FastAPI detail string', () => {
      const error = new AxiosError('Bad Request', '400', undefined, undefined, {
        status: 400,
        statusText: 'Bad Request',
        headers: new AxiosHeaders(),
        config: { headers: new AxiosHeaders() },
        data: { detail: 'Account not found' },
      })

      expect(handleApiError(error)).toBe('Account not found')
    })

    it('extracts and joins messages from Pydantic validation error array', () => {
      const error = new AxiosError(
        'Unprocessable Entity',
        '422',
        undefined,
        undefined,
        {
          status: 422,
          statusText: 'Unprocessable Entity',
          headers: new AxiosHeaders(),
          config: { headers: new AxiosHeaders() },
          data: {
            detail: [
              { msg: 'field required', loc: ['body', 'email'] },
              { msg: 'invalid email format', loc: ['body', 'email'] },
            ],
          },
        }
      )

      expect(handleApiError(error)).toBe('field required, invalid email format')
    })

    it('extracts message field from validation errors', () => {
      const error = new AxiosError(
        'Unprocessable Entity',
        '422',
        undefined,
        undefined,
        {
          status: 422,
          statusText: 'Unprocessable Entity',
          headers: new AxiosHeaders(),
          config: { headers: new AxiosHeaders() },
          data: {
            detail: [
              { message: 'Name is required' },
              { message: 'Email is invalid' },
            ],
          },
        }
      )

      expect(handleApiError(error)).toBe('Name is required, Email is invalid')
    })

    it('handles detail array with string items', () => {
      const error = new AxiosError('Bad Request', '400', undefined, undefined, {
        status: 400,
        statusText: 'Bad Request',
        headers: new AxiosHeaders(),
        config: { headers: new AxiosHeaders() },
        data: { detail: ['Error one', 'Error two'] },
      })

      expect(handleApiError(error)).toBe('Error one, Error two')
    })

    it('extracts from details field (record validation errors)', () => {
      const error = new AxiosError('Bad Request', '400', undefined, undefined, {
        status: 400,
        statusText: 'Bad Request',
        headers: new AxiosHeaders(),
        config: { headers: new AxiosHeaders() },
        data: { details: [{ message: 'Field "name" is required' }] },
      })

      expect(handleApiError(error)).toBe('Field "name" is required')
    })

    it('falls back to message field', () => {
      const error = new AxiosError('Server Error', '500', undefined, undefined, {
        status: 500,
        statusText: 'Internal Server Error',
        headers: new AxiosHeaders(),
        config: { headers: new AxiosHeaders() },
        data: { message: 'Something went wrong on the server' },
      })

      expect(handleApiError(error)).toBe('Something went wrong on the server')
    })

    it('falls back to error field', () => {
      const error = new AxiosError('Bad Request', '400', undefined, undefined, {
        status: 400,
        statusText: 'Bad Request',
        headers: new AxiosHeaders(),
        config: { headers: new AxiosHeaders() },
        data: { error: 'Invalid request format' },
      })

      expect(handleApiError(error)).toBe('Invalid request format')
    })

    it('returns generic message for unknown error shapes', () => {
      expect(handleApiError(new Error('something'))).toBe(
        'An unexpected error occurred'
      )
      expect(handleApiError('string error')).toBe('An unexpected error occurred')
      expect(handleApiError(null)).toBe('An unexpected error occurred')
      expect(handleApiError(undefined)).toBe('An unexpected error occurred')
    })

    it('handles network errors (no response)', () => {
      const error = new AxiosError(
        'Network Error',
        'ERR_NETWORK',
        undefined,
        undefined,
        undefined
      )

      expect(handleApiError(error)).toBe('Network Error')
    })

    it('handles axios timeout error (no response)', () => {
      const error = new AxiosError(
        'Request Timeout',
        'ECONNABORTED',
        undefined,
        undefined,
        undefined
      )

      expect(handleApiError(error)).toBe('Request Timeout')
    })
  })
})
