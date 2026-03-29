import { http, HttpResponse } from 'msw'

/**
 * Default MSW handlers shared across all tests.
 * Test files can override these with server.use() for specific scenarios.
 */
export const handlers = [
  // Auth: get current user (commonly needed for authenticated page renders)
  http.get('/api/v1/auth/me', () => {
    return HttpResponse.json({
      id: 'user-1',
      email: 'admin@example.com',
      name: 'Test Admin',
      is_superadmin: true,
    })
  }),
]
