import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { emailService } from '../email.service'
import type {
  EmailTemplate,
  EmailLog,
  EmailLogListResponse,
  EmailTemplateRenderResponse,
} from '../email.service'

const mockEmailTemplate: EmailTemplate = {
  id: 'tmpl-1',
  account_id: 'AB1234',
  template_type: 'welcome',
  locale: 'en',
  subject: 'Welcome to SnackBase!',
  html_body: '<p>Welcome!</p>',
  text_body: 'Welcome!',
  enabled: true,
  is_builtin: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockEmailLog: EmailLog = {
  id: 'log-1',
  account_id: 'AB1234',
  template_type: 'welcome',
  recipient_email: 'user@example.com',
  provider: 'smtp',
  status: 'sent',
  error_message: null,
  variables: { name: 'Alice' },
  sent_at: '2024-01-01T00:00:00Z',
}

const mockEmailLogListResponse: EmailLogListResponse = {
  logs: [mockEmailLog],
  total: 1,
  page: 1,
  page_size: 20,
}

const mockRenderResponse: EmailTemplateRenderResponse = {
  subject: 'Welcome to SnackBase!',
  html_body: '<p>Welcome, Alice!</p>',
  text_body: 'Welcome, Alice!',
}

// ─────────────────────────────────────────────────────────────────────────────
// listEmailTemplates()
// ─────────────────────────────────────────────────────────────────────────────

describe('Email Service', () => {
  describe('listEmailTemplates()', () => {
    it('sends GET to /admin/email/templates', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/email/templates', () => {
          requestReceived = true
          return HttpResponse.json([mockEmailTemplate])
        })
      )

      await emailService.listEmailTemplates()
      expect(requestReceived).toBe(true)
    })

    it('returns list of email templates on success', async () => {
      server.use(
        http.get('/api/v1/admin/email/templates', () => HttpResponse.json([mockEmailTemplate]))
      )

      const result = await emailService.listEmailTemplates()
      expect(result).toEqual([mockEmailTemplate])
    })

    it('passes template_type filter as query param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/templates', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockEmailTemplate])
        })
      )

      await emailService.listEmailTemplates({ template_type: 'welcome' })

      expect(capturedUrl).toContain('template_type=welcome')
    })

    it('passes locale filter as query param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/templates', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockEmailTemplate])
        })
      )

      await emailService.listEmailTemplates({ locale: 'fr' })

      expect(capturedUrl).toContain('locale=fr')
    })

    it('passes enabled filter as query param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/templates', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockEmailTemplate])
        })
      )

      await emailService.listEmailTemplates({ enabled: true })

      expect(capturedUrl).toContain('enabled=true')
    })

    it('omits params not provided', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/templates', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([mockEmailTemplate])
        })
      )

      await emailService.listEmailTemplates()

      expect(capturedUrl).not.toContain('template_type')
      expect(capturedUrl).not.toContain('locale')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/admin/email/templates', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(emailService.listEmailTemplates()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getEmailTemplate()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getEmailTemplate()', () => {
    it('sends GET to /admin/email/templates/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/email/templates/tmpl-1', () => {
          requestReceived = true
          return HttpResponse.json(mockEmailTemplate)
        })
      )

      await emailService.getEmailTemplate('tmpl-1')
      expect(requestReceived).toBe(true)
    })

    it('returns email template detail on success', async () => {
      server.use(
        http.get('/api/v1/admin/email/templates/tmpl-1', () =>
          HttpResponse.json(mockEmailTemplate)
        )
      )

      const result = await emailService.getEmailTemplate('tmpl-1')
      expect(result).toEqual(mockEmailTemplate)
    })

    it('propagates 404 when template not found', async () => {
      server.use(
        http.get('/api/v1/admin/email/templates/missing', () =>
          HttpResponse.json({ detail: 'Template not found' }, { status: 404 })
        )
      )

      await expect(emailService.getEmailTemplate('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateEmailTemplate()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateEmailTemplate()', () => {
    it('sends PUT to /admin/email/templates/{id} with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.put('/api/v1/admin/email/templates/tmpl-1', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockEmailTemplate)
        })
      )

      await emailService.updateEmailTemplate('tmpl-1', {
        subject: 'Updated Subject',
        enabled: false,
      })

      expect(capturedBody).toEqual({ subject: 'Updated Subject', enabled: false })
    })

    it('returns updated template on success', async () => {
      const updatedTemplate = { ...mockEmailTemplate, subject: 'Updated Subject' }

      server.use(
        http.put('/api/v1/admin/email/templates/tmpl-1', () =>
          HttpResponse.json(updatedTemplate)
        )
      )

      const result = await emailService.updateEmailTemplate('tmpl-1', {
        subject: 'Updated Subject',
      })
      expect(result.subject).toBe('Updated Subject')
    })

    it('propagates 404 when template not found', async () => {
      server.use(
        http.put('/api/v1/admin/email/templates/missing', () =>
          HttpResponse.json({ detail: 'Template not found' }, { status: 404 })
        )
      )

      await expect(
        emailService.updateEmailTemplate('missing', { subject: 'Test' })
      ).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // renderEmailTemplate()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('renderEmailTemplate()', () => {
    it('sends POST to /admin/email/templates/render with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/admin/email/templates/render', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockRenderResponse)
        })
      )

      await emailService.renderEmailTemplate({
        template_type: 'welcome',
        variables: { name: 'Alice' },
      })

      expect(capturedBody).toMatchObject({
        template_type: 'welcome',
        variables: { name: 'Alice' },
      })
    })

    it('returns rendered template content on success', async () => {
      server.use(
        http.post('/api/v1/admin/email/templates/render', () =>
          HttpResponse.json(mockRenderResponse)
        )
      )

      const result = await emailService.renderEmailTemplate({
        template_type: 'welcome',
        variables: { name: 'Alice' },
      })
      expect(result).toEqual(mockRenderResponse)
      expect(result.html_body).toContain('Alice')
    })

    it('propagates API errors', async () => {
      server.use(
        http.post('/api/v1/admin/email/templates/render', () =>
          HttpResponse.json({ detail: 'Template not found' }, { status: 404 })
        )
      )

      await expect(
        emailService.renderEmailTemplate({ template_type: 'missing', variables: {} })
      ).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // sendTestEmail()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('sendTestEmail()', () => {
    it('sends POST to /admin/email/templates/{id}/test with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/admin/email/templates/tmpl-1/test', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ status: 'sent', message: 'Test email sent' })
        })
      )

      await emailService.sendTestEmail('tmpl-1', {
        recipient_email: 'test@example.com',
      })

      expect(capturedBody).toMatchObject({ recipient_email: 'test@example.com' })
    })

    it('returns status and message on success', async () => {
      server.use(
        http.post('/api/v1/admin/email/templates/tmpl-1/test', () =>
          HttpResponse.json({ status: 'sent', message: 'Test email sent successfully' })
        )
      )

      const result = await emailService.sendTestEmail('tmpl-1', {
        recipient_email: 'test@example.com',
      })
      expect(result.status).toBe('sent')
      expect(result.message).toBe('Test email sent successfully')
    })

    it('propagates API errors', async () => {
      server.use(
        http.post('/api/v1/admin/email/templates/tmpl-1/test', () =>
          HttpResponse.json({ detail: 'No email provider configured' }, { status: 500 })
        )
      )

      await expect(
        emailService.sendTestEmail('tmpl-1', { recipient_email: 'test@example.com' })
      ).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // listEmailLogs()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('listEmailLogs()', () => {
    it('sends GET to /admin/email/logs', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/email/logs', () => {
          requestReceived = true
          return HttpResponse.json(mockEmailLogListResponse)
        })
      )

      await emailService.listEmailLogs()
      expect(requestReceived).toBe(true)
    })

    it('returns email log list on success', async () => {
      server.use(
        http.get('/api/v1/admin/email/logs', () =>
          HttpResponse.json(mockEmailLogListResponse)
        )
      )

      const result = await emailService.listEmailLogs()
      expect(result).toEqual(mockEmailLogListResponse)
    })

    it('passes status_filter as query param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/logs', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockEmailLogListResponse)
        })
      )

      await emailService.listEmailLogs({ status_filter: 'sent' })

      expect(capturedUrl).toContain('status_filter=sent')
    })

    it('passes pagination params as query params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/logs', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockEmailLogListResponse)
        })
      )

      await emailService.listEmailLogs({ page: 2, page_size: 50 })

      expect(capturedUrl).toContain('page=2')
      expect(capturedUrl).toContain('page_size=50')
    })

    it('passes date range params as query params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/admin/email/logs', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockEmailLogListResponse)
        })
      )

      await emailService.listEmailLogs({ start_date: '2024-01-01', end_date: '2024-12-31' })

      expect(capturedUrl).toContain('start_date=2024-01-01')
      expect(capturedUrl).toContain('end_date=2024-12-31')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/admin/email/logs', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(emailService.listEmailLogs()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getEmailLog()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getEmailLog()', () => {
    it('sends GET to /admin/email/logs/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/admin/email/logs/log-1', () => {
          requestReceived = true
          return HttpResponse.json(mockEmailLog)
        })
      )

      await emailService.getEmailLog('log-1')
      expect(requestReceived).toBe(true)
    })

    it('returns email log detail on success', async () => {
      server.use(
        http.get('/api/v1/admin/email/logs/log-1', () => HttpResponse.json(mockEmailLog))
      )

      const result = await emailService.getEmailLog('log-1')
      expect(result).toEqual(mockEmailLog)
    })

    it('returns correct status and recipient', async () => {
      server.use(
        http.get('/api/v1/admin/email/logs/log-1', () => HttpResponse.json(mockEmailLog))
      )

      const result = await emailService.getEmailLog('log-1')
      expect(result.status).toBe('sent')
      expect(result.recipient_email).toBe('user@example.com')
    })

    it('propagates 404 when log not found', async () => {
      server.use(
        http.get('/api/v1/admin/email/logs/missing', () =>
          HttpResponse.json({ detail: 'Email log not found' }, { status: 404 })
        )
      )

      await expect(emailService.getEmailLog('missing')).rejects.toThrow()
    })
  })
})
