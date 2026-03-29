/**
 * Tests for EmailTemplatesTab component (FT3.5)
 *
 * Verifies:
 * - Renders email template list from API
 * - Loading state while fetching
 * - Empty state when no templates
 * - Filter by type and locale dropdowns
 * - Row click opens edit dialog
 * - Email Logs section renders
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import EmailTemplatesTab from '../EmailTemplatesTab'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockTemplates = [
  {
    id: 'tmpl-1',
    account_id: '00000000-0000-0000-0000-000000000000',
    template_type: 'email_verification',
    locale: 'en',
    subject: 'Verify your email address',
    html_body: '<p>Please verify your email.</p>',
    text_body: 'Please verify your email.',
    enabled: true,
    is_builtin: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-03-28T10:00:00Z',
  },
  {
    id: 'tmpl-2',
    account_id: '00000000-0000-0000-0000-000000000000',
    template_type: 'password_reset',
    locale: 'en',
    subject: 'Reset your password',
    html_body: '<p>Reset your password here.</p>',
    text_body: 'Reset your password.',
    enabled: true,
    is_builtin: false,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-03-27T08:00:00Z',
  },
  {
    id: 'tmpl-3',
    account_id: '00000000-0000-0000-0000-000000000000',
    template_type: 'invitation',
    locale: 'es',
    subject: 'Te han invitado',
    html_body: '<p>Has sido invitado.</p>',
    text_body: 'Has sido invitado.',
    enabled: false,
    is_builtin: false,
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-03-25T06:00:00Z',
  },
]

const mockEmailLogs = {
  logs: [
    {
      id: 'log-1',
      account_id: 'AB1234',
      template_type: 'email_verification',
      recipient_email: 'user@example.com',
      provider: 'sendgrid',
      status: 'sent',
      error_message: null,
      variables: null,
      sent_at: '2026-03-29T09:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderTab() {
  return render(<EmailTemplatesTab />)
}

function setupSuccessHandlers(
  templatesOverride: typeof mockTemplates = mockTemplates,
) {
  server.use(
    http.get('/api/v1/admin/email/templates', () =>
      HttpResponse.json(templatesOverride),
    ),
    http.get('/api/v1/admin/email/logs', () =>
      HttpResponse.json(mockEmailLogs),
    ),
  )
}

function setupErrorHandler() {
  server.use(
    http.get('/api/v1/admin/email/templates', () =>
      HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
    ),
    http.get('/api/v1/admin/email/logs', () =>
      HttpResponse.json({ logs: [], total: 0, page: 1, page_size: 10 }),
    ),
  )
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  setupSuccessHandlers()
})

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('EmailTemplatesTab', () => {
  // -------------------------------------------------------------------------
  // Section headings
  // -------------------------------------------------------------------------

  describe('section headings', () => {
    it('renders the Email Templates section heading', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Email Templates')).toBeInTheDocument()
      })
    })

    it('renders the Email Logs section heading', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Email Logs')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    it('shows a loading indicator while templates are fetching', () => {
      server.use(
        http.get('/api/v1/admin/email/templates', async () => {
          await new Promise(() => {}) // never resolves
        }),
        http.get('/api/v1/admin/email/logs', () =>
          HttpResponse.json(mockEmailLogs),
        ),
      )
      renderTab()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('removes loading indicator after data loads', async () => {
      renderTab()
      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Template list rendering
  // -------------------------------------------------------------------------

  describe('template list rendering', () => {
    it('renders a row for each template', async () => {
      // Note: template_type.replace(/_/g,' ') renders as lowercase DOM text;
      // CSS `capitalize` only changes visual appearance, not the actual text.
      // "email verification" also appears in EmailLogList, so use getAllByText.
      renderTab()
      await waitFor(() => {
        expect(screen.getAllByText('email verification').length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('password reset').length).toBeGreaterThanOrEqual(1)
        expect(screen.getByText('invitation')).toBeInTheDocument()
      })
    })

    it('renders template subjects', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Verify your email address')).toBeInTheDocument()
        expect(screen.getByText('Reset your password')).toBeInTheDocument()
      })
    })

    it('renders locale codes in uppercase font-mono', async () => {
      renderTab()
      await waitFor(() => {
        // locale is rendered with `uppercase` CSS class — DOM text is lowercase "en"
        const locales = screen.getAllByText('en')
        expect(locales.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('renders Built-in badge for builtin templates', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('Built-in')).toBeInTheDocument()
      })
    })

    it('renders Enabled / Disabled status badges', async () => {
      renderTab()
      await waitFor(() => {
        const enabledBadges = screen.getAllByText('Enabled')
        expect(enabledBadges.length).toBeGreaterThanOrEqual(1)
        expect(screen.getByText('Disabled')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('empty state', () => {
    it('renders empty state message when no templates exist', async () => {
      setupSuccessHandlers([])
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('No email templates found.')).toBeInTheDocument()
      })
    })
  })

  // -------------------------------------------------------------------------
  // Filter dropdowns
  // -------------------------------------------------------------------------

  describe('filter dropdowns', () => {
    it('renders the type filter dropdown', async () => {
      renderTab()
      await waitFor(() => {
        // EmailTemplatesTab has "All Types"; EmailLogList also renders "All Types"
        expect(screen.getAllByText('All Types').length).toBeGreaterThanOrEqual(1)
      })
    })

    it('renders the locale filter dropdown', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getByText('All Locales')).toBeInTheDocument()
      })
    })

    it('calls API with template_type param when type filter is changed', async () => {
      let capturedParams: URLSearchParams | null = null
      server.use(
        http.get('/api/v1/admin/email/templates', ({ request }) => {
          capturedParams = new URL(request.url).searchParams
          return HttpResponse.json(mockTemplates)
        }),
      )

      renderTab()
      await waitFor(() => {
        expect(screen.getAllByText('All Types').length).toBeGreaterThanOrEqual(1)
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      // Click the combobox role=select trigger buttons; first one is the type filter
      const comboboxes = screen.getAllByRole('combobox')
      await user.click(comboboxes[0])

      await waitFor(() => {
        // 'Password Reset' option text in dropdown
        expect(screen.getByText('Password Reset')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Password Reset'))

      await waitFor(() => {
        expect(capturedParams?.get('template_type')).toBe('password_reset')
      })
    })
  })

  // -------------------------------------------------------------------------
  // Row click opens dialog
  // -------------------------------------------------------------------------

  describe('row click behavior', () => {
    it('opens edit dialog when a template row is clicked', async () => {
      renderTab()
      await waitFor(() => {
        expect(screen.getAllByText('email verification').length).toBeGreaterThanOrEqual(1)
      })

      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const rows = document.querySelectorAll('tbody tr')
      expect(rows.length).toBeGreaterThan(0)
      await user.click(rows[0] as HTMLElement)

      // Dialog should open - look for dialog or modal indicator
      await waitFor(() => {
        const dialogs = document.querySelectorAll('[role="dialog"]')
        expect(dialogs.length).toBeGreaterThan(0)
      })
    })
  })
})
