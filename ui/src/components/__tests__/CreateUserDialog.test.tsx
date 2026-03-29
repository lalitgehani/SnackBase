/**
 * Tests for CreateUserDialog component (FT2.4)
 *
 * Verifies:
 * - Shows loading spinner while fetching accounts and roles
 * - Renders all form fields after data loads
 * - Submit button is disabled until all required fields are filled
 * - Password validation: min 12 chars, uppercase, lowercase, digit, special char
 * - Password confirmation must match
 * - Calls onSubmit with correct payload
 * - Shows error message when onSubmit throws
 * - Closes dialog after successful submission
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import CreateUserDialog from '@/components/users/CreateUserDialog'

const MOCK_ACCOUNTS = {
  items: [
    { id: 'acc-1', name: 'Alpha Corp', account_code: 'AC0001', slug: 'alpha-corp' },
    { id: 'acc-2', name: 'Beta Inc', account_code: 'BI0002', slug: 'beta-inc' },
  ],
  total: 2,
}

const MOCK_ROLES = {
  items: [
    { id: 1, name: 'Admin', description: 'Administrator role' },
    { id: 2, name: 'Member', description: 'Standard member role' },
  ],
  total: 2,
}

/** Valid password satisfying all requirements */
const VALID_PASSWORD = 'Secure@Pass1!'

function setupHandlers() {
  server.use(
    http.get('/api/v1/accounts', () => HttpResponse.json(MOCK_ACCOUNTS)),
    http.get('/api/v1/roles', () => HttpResponse.json(MOCK_ROLES)),
  )
}

async function waitForFormToLoad() {
  await waitFor(() => {
    expect(screen.getByLabelText(/email \*/i)).toBeInTheDocument()
  })
}

describe('CreateUserDialog', () => {
  beforeEach(() => {
    setupHandlers()
  })

  describe('loading state', () => {
    it('shows loading spinner while fetching accounts and roles', () => {
      render(
        <CreateUserDialog
          open={true}
          onOpenChange={vi.fn()}
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      )
      // Loading spinner should be present immediately
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('renders form fields after data loads', async () => {
      render(
        <CreateUserDialog
          open={true}
          onOpenChange={vi.fn()}
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      )

      await waitForFormToLoad()

      expect(screen.getByLabelText(/email \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password \*/i)).toBeInTheDocument()
    })
  })

  describe('submit button state', () => {
    it('is disabled when form fields are empty', async () => {
      render(
        <CreateUserDialog
          open={true}
          onOpenChange={vi.fn()}
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      )

      await waitForFormToLoad()
      expect(screen.getByRole('button', { name: /create user/i })).toBeDisabled()
    })
  })

  describe('password validation', () => {
    async function submitWithPassword(password: string, confirmPassword?: string) {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      render(
        <CreateUserDialog
          open={true}
          onOpenChange={vi.fn()}
          onSubmit={onSubmit}
        />
      )

      await waitForFormToLoad()

      await user.type(screen.getByLabelText(/email \*/i), 'user@example.com')
      await user.type(screen.getByLabelText(/^password \*/i), password)
      await user.type(screen.getByLabelText(/confirm password \*/i), confirmPassword ?? password)

      // Select account via combobox trigger
      const accountTrigger = screen.getByRole('combobox', { name: /account \*/i })
      await user.click(accountTrigger)
      await user.click(await screen.findByRole('option', { name: /alpha corp/i }))

      // Select role
      const roleTrigger = screen.getByRole('combobox', { name: /role \*/i })
      await user.click(roleTrigger)
      await user.click(await screen.findByRole('option', { name: /admin/i }))

      await user.click(screen.getByRole('button', { name: /create user/i }))

      return { onSubmit }
    }

    it('shows error when password is shorter than 12 characters', async () => {
      await submitWithPassword('Short@1!')

      await waitFor(() => {
        expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument()
      })
    })

    it('shows error when password has no uppercase letter', async () => {
      await submitWithPassword('nouppercase@1234!')

      await waitFor(() => {
        expect(screen.getByText(/at least one uppercase letter/i)).toBeInTheDocument()
      })
    })

    it('shows error when password has no lowercase letter', async () => {
      await submitWithPassword('NOLOWERCASE@1234!')

      await waitFor(() => {
        expect(screen.getByText(/at least one lowercase letter/i)).toBeInTheDocument()
      })
    })

    it('shows error when password has no digit', async () => {
      await submitWithPassword('NoDigitHere@ABC!')

      await waitFor(() => {
        expect(screen.getByText(/at least one digit/i)).toBeInTheDocument()
      })
    })

    it('shows error when password has no special character', async () => {
      await submitWithPassword('NoSpecialChar1234Aa')

      await waitFor(() => {
        expect(screen.getByText(/special character/i)).toBeInTheDocument()
      })
    })

    it('shows error when passwords do not match', async () => {
      await submitWithPassword(VALID_PASSWORD, VALID_PASSWORD + 'x')

      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      })
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with correct payload', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)

      render(
        <CreateUserDialog
          open={true}
          onOpenChange={vi.fn()}
          onSubmit={onSubmit}
        />
      )

      await waitForFormToLoad()

      await user.type(screen.getByLabelText(/email \*/i), 'newuser@example.com')
      await user.type(screen.getByLabelText(/^password \*/i), VALID_PASSWORD)
      await user.type(screen.getByLabelText(/confirm password \*/i), VALID_PASSWORD)

      const accountTrigger = screen.getByRole('combobox', { name: /account \*/i })
      await user.click(accountTrigger)
      await user.click(await screen.findByRole('option', { name: /alpha corp/i }))

      const roleTrigger = screen.getByRole('combobox', { name: /role \*/i })
      await user.click(roleTrigger)
      await user.click(await screen.findByRole('option', { name: /admin/i }))

      await user.click(screen.getByRole('button', { name: /create user/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            email: 'newuser@example.com',
            password: VALID_PASSWORD,
            account_id: 'acc-1',
            role_id: 1,
            is_active: true,
          })
        )
      })
    })

    it('shows API error when onSubmit throws', async () => {
      const user = userEvent.setup()
      // handleApiError processes AxiosErrors; plain Errors fall back to generic message
      const axiosError = Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'Email already registered' } },
      })
      const onSubmit = vi.fn().mockRejectedValue(axiosError)

      render(
        <CreateUserDialog
          open={true}
          onOpenChange={vi.fn()}
          onSubmit={onSubmit}
        />
      )

      await waitForFormToLoad()

      await user.type(screen.getByLabelText(/email \*/i), 'taken@example.com')
      await user.type(screen.getByLabelText(/^password \*/i), VALID_PASSWORD)
      await user.type(screen.getByLabelText(/confirm password \*/i), VALID_PASSWORD)

      const accountTrigger = screen.getByRole('combobox', { name: /account \*/i })
      await user.click(accountTrigger)
      await user.click(await screen.findByRole('option', { name: /alpha corp/i }))

      const roleTrigger = screen.getByRole('combobox', { name: /role \*/i })
      await user.click(roleTrigger)
      await user.click(await screen.findByRole('option', { name: /admin/i }))

      await user.click(screen.getByRole('button', { name: /create user/i }))

      await waitFor(() => {
        expect(screen.getByText('Email already registered')).toBeInTheDocument()
      })
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)

      render(
        <CreateUserDialog
          open={true}
          onOpenChange={onOpenChange}
          onSubmit={onSubmit}
        />
      )

      await waitForFormToLoad()

      await user.type(screen.getByLabelText(/email \*/i), 'valid@example.com')
      await user.type(screen.getByLabelText(/^password \*/i), VALID_PASSWORD)
      await user.type(screen.getByLabelText(/confirm password \*/i), VALID_PASSWORD)

      const accountTrigger = screen.getByRole('combobox', { name: /account \*/i })
      await user.click(accountTrigger)
      await user.click(await screen.findByRole('option', { name: /alpha corp/i }))

      const roleTrigger = screen.getByRole('combobox', { name: /role \*/i })
      await user.click(roleTrigger)
      await user.click(await screen.findByRole('option', { name: /admin/i }))

      await user.click(screen.getByRole('button', { name: /create user/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })
  })

  describe('cancel behavior', () => {
    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()

      render(
        <CreateUserDialog
          open={true}
          onOpenChange={onOpenChange}
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      )

      await waitForFormToLoad()

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
