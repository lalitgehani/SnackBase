import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getInvitations,
  createInvitation,
  cancelInvitation,
  resendInvitation,
  getInvitation,
  acceptInvitation,
} from '../invitations.service'
import type { Invitation, InvitationListResponse, InvitationPublicResponse } from '../invitations.service'

const mockInvitation: Invitation = {
  id: 'inv-1',
  account_id: 'AB1234',
  account_code: 'AB1234',
  email: 'newuser@acme.com',
  invited_by: 'admin@acme.com',
  expires_at: '2026-04-30T00:00:00Z',
  accepted_at: null,
  created_at: '2026-03-29T00:00:00Z',
  email_sent: true,
  email_sent_at: '2026-03-29T00:01:00Z',
  status: 'pending',
  token: 'invite-token-abc123',
}

const mockInvitationListResponse: InvitationListResponse = {
  invitations: [mockInvitation],
  total: 1,
}

const mockPublicInvitation: InvitationPublicResponse = {
  email: 'newuser@acme.com',
  account_name: 'Acme Corp',
  invited_by_name: 'Admin User',
  expires_at: '2026-04-30T00:00:00Z',
  is_valid: true,
}

const mockAuthResponse = {
  token: 'access-token-abc',
  refresh_token: 'refresh-token-xyz',
  expires_in: 3600,
  account: { id: 'AB1234', slug: 'acme', name: 'Acme Corp', created_at: '2024-01-01T00:00:00Z' },
  user: { id: 'user-2', email: 'newuser@acme.com', role: 'member', is_active: true, created_at: '2026-03-29T00:00:00Z' },
}

describe('Invitations Service', () => {
  describe('getInvitations()', () => {
    it('sends GET to /invitations', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/invitations', () => {
          requestReceived = true
          return HttpResponse.json(mockInvitationListResponse)
        })
      )

      await getInvitations()
      expect(requestReceived).toBe(true)
    })

    it('returns invitation list response on success', async () => {
      server.use(
        http.get('/api/v1/invitations', () => HttpResponse.json(mockInvitationListResponse))
      )

      const result = await getInvitations()
      expect(result).toEqual(mockInvitationListResponse)
    })

    it('passes status_filter param when status is provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/invitations', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockInvitationListResponse)
        })
      )

      await getInvitations('pending')

      expect(capturedUrl).toContain('status_filter=pending')
    })

    it('passes account_id param when provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/invitations', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockInvitationListResponse)
        })
      )

      await getInvitations(undefined, 'AB1234')

      expect(capturedUrl).toContain('account_id=AB1234')
    })

    it('passes both status_filter and account_id when both provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/invitations', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockInvitationListResponse)
        })
      )

      await getInvitations('accepted', 'AB1234')

      expect(capturedUrl).toContain('status_filter=accepted')
      expect(capturedUrl).toContain('account_id=AB1234')
    })

    it('does not include status_filter or account_id when not provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/invitations', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockInvitationListResponse)
        })
      )

      await getInvitations()

      expect(capturedUrl).not.toContain('status_filter')
      expect(capturedUrl).not.toContain('account_id')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/invitations', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getInvitations()).rejects.toThrow()
    })
  })

  describe('createInvitation()', () => {
    it('sends POST to /invitations with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/invitations', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockInvitation, { status: 201 })
        })
      )

      await createInvitation({ email: 'newuser@acme.com' })

      expect(capturedBody).toEqual({ email: 'newuser@acme.com' })
    })

    it('sends role_id and groups when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/invitations', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockInvitation, { status: 201 })
        })
      )

      await createInvitation({
        email: 'newuser@acme.com',
        role_id: '2',
        groups: ['group-1', 'group-2'],
        account_id: 'AB1234',
      })

      expect(capturedBody).toEqual({
        email: 'newuser@acme.com',
        role_id: '2',
        groups: ['group-1', 'group-2'],
        account_id: 'AB1234',
      })
    })

    it('returns created invitation on success', async () => {
      server.use(
        http.post('/api/v1/invitations', () =>
          HttpResponse.json(mockInvitation, { status: 201 })
        )
      )

      const result = await createInvitation({ email: 'newuser@acme.com' })
      expect(result).toEqual(mockInvitation)
    })

    it('returns invitation with pending status', async () => {
      server.use(
        http.post('/api/v1/invitations', () =>
          HttpResponse.json(mockInvitation, { status: 201 })
        )
      )

      const result = await createInvitation({ email: 'newuser@acme.com' })
      expect(result.status).toBe('pending')
    })

    it('propagates API errors on duplicate email', async () => {
      server.use(
        http.post('/api/v1/invitations', () =>
          HttpResponse.json({ detail: 'Invitation already exists for this email' }, { status: 409 })
        )
      )

      await expect(createInvitation({ email: 'existing@acme.com' })).rejects.toThrow()
    })
  })

  describe('cancelInvitation()', () => {
    it('sends DELETE to /invitations/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/invitations/inv-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await cancelInvitation('inv-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/invitations/inv-1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await cancelInvitation('inv-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when invitation not found', async () => {
      server.use(
        http.delete('/api/v1/invitations/nonexistent', () =>
          HttpResponse.json({ detail: 'Invitation not found' }, { status: 404 })
        )
      )

      await expect(cancelInvitation('nonexistent')).rejects.toThrow()
    })
  })

  describe('resendInvitation()', () => {
    it('sends POST to /invitations/{id}/resend', async () => {
      let requestReceived = false

      server.use(
        http.post('/api/v1/invitations/inv-1/resend', () => {
          requestReceived = true
          return HttpResponse.json({ message: 'Invitation resent' })
        })
      )

      await resendInvitation('inv-1')
      expect(requestReceived).toBe(true)
    })

    it('returns message on success', async () => {
      server.use(
        http.post('/api/v1/invitations/inv-1/resend', () =>
          HttpResponse.json({ message: 'Invitation resent' })
        )
      )

      const result = await resendInvitation('inv-1')
      expect(result.message).toBe('Invitation resent')
    })

    it('propagates 404 when invitation not found', async () => {
      server.use(
        http.post('/api/v1/invitations/nonexistent/resend', () =>
          HttpResponse.json({ detail: 'Invitation not found' }, { status: 404 })
        )
      )

      await expect(resendInvitation('nonexistent')).rejects.toThrow()
    })
  })

  describe('getInvitation()', () => {
    it('sends GET to /invitations/{token}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/invitations/invite-token-abc123', () => {
          requestReceived = true
          return HttpResponse.json(mockPublicInvitation)
        })
      )

      await getInvitation('invite-token-abc123')
      expect(requestReceived).toBe(true)
    })

    it('returns public invitation info on success', async () => {
      server.use(
        http.get('/api/v1/invitations/invite-token-abc123', () =>
          HttpResponse.json(mockPublicInvitation)
        )
      )

      const result = await getInvitation('invite-token-abc123')
      expect(result).toEqual(mockPublicInvitation)
    })

    it('returns is_valid: true for a valid invitation', async () => {
      server.use(
        http.get('/api/v1/invitations/invite-token-abc123', () =>
          HttpResponse.json(mockPublicInvitation)
        )
      )

      const result = await getInvitation('invite-token-abc123')
      expect(result.is_valid).toBe(true)
    })

    it('returns is_valid: false for an expired invitation', async () => {
      server.use(
        http.get('/api/v1/invitations/expired-token', () =>
          HttpResponse.json({ ...mockPublicInvitation, is_valid: false })
        )
      )

      const result = await getInvitation('expired-token')
      expect(result.is_valid).toBe(false)
    })

    it('propagates 404 when token not found', async () => {
      server.use(
        http.get('/api/v1/invitations/bad-token', () =>
          HttpResponse.json({ detail: 'Invitation not found' }, { status: 404 })
        )
      )

      await expect(getInvitation('bad-token')).rejects.toThrow()
    })
  })

  describe('acceptInvitation()', () => {
    it('sends POST to /invitations/{token}/accept with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/invitations/invite-token-abc123/accept', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockAuthResponse)
        })
      )

      await acceptInvitation('invite-token-abc123', { password: 'mypassword123' })

      expect(capturedBody).toEqual({ password: 'mypassword123' })
    })

    it('sends POST with empty object when no password is provided', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/invitations/invite-token-abc123/accept', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockAuthResponse)
        })
      )

      await acceptInvitation('invite-token-abc123', {})

      expect(capturedBody).toEqual({})
    })

    it('returns auth response on successful acceptance', async () => {
      server.use(
        http.post('/api/v1/invitations/invite-token-abc123/accept', () =>
          HttpResponse.json(mockAuthResponse)
        )
      )

      const result = await acceptInvitation('invite-token-abc123', { password: 'mypassword123' })
      expect(result).toEqual(mockAuthResponse)
    })

    it('returns token and user info in the auth response', async () => {
      server.use(
        http.post('/api/v1/invitations/invite-token-abc123/accept', () =>
          HttpResponse.json(mockAuthResponse)
        )
      )

      const result = await acceptInvitation('invite-token-abc123', { password: 'mypassword123' })
      expect(result.token).toBe('access-token-abc')
      expect(result.user.email).toBe('newuser@acme.com')
    })

    it('propagates errors for expired or already-accepted token', async () => {
      server.use(
        http.post('/api/v1/invitations/expired-token/accept', () =>
          HttpResponse.json({ detail: 'Invitation has expired' }, { status: 400 })
        )
      )

      await expect(
        acceptInvitation('expired-token', { password: 'mypassword123' })
      ).rejects.toThrow()
    })
  })
})
