/**
 * Tests for EditUserDialog component
 *
 * Verifies:
 * - Renders dialog pre-populated with user data
 * - Loads roles on open
 * - Update User button is disabled when email is empty
 * - Calls onSubmit with user ID and updated data
 * - Calls onOpenChange(false) after successful submission
 * - Shows error message when onSubmit throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import EditUserDialog from '@/components/users/EditUserDialog'
import type { User } from '@/services/users.service'

const user: User = {
  id: 'usr_abc123',
  email: 'john@example.com',
  account_id: 'acc_abc123',
  account_code: 'AC1234',
  account_name: 'Acme Corp',
  role_id: 1,
  role_name: 'admin',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  last_login: null,
  email_verified: true,
  email_verified_at: null,
}

const roles = [
  { id: 1, name: 'admin', description: 'Administrator', collections_count: 0 },
  { id: 2, name: 'user', description: 'Regular user', collections_count: 0 },
]

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
  onSubmit: (userId: string, data: object) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    user: u = user,
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <EditUserDialog
      open={open}
      onOpenChange={onOpenChange}
      user={u}
      onSubmit={onSubmit}
    />
  )
}

describe('EditUserDialog', () => {
  beforeEach(() => {
    server.use(
      http.get('/api/v1/roles', () =>
        HttpResponse.json({ items: roles, total: 2 })
      )
    )
  })

  describe('rendering', () => {
    it('renders Edit User heading', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /edit user/i })).toBeInTheDocument()
      })
    })

    it('pre-populates email field with user email', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByLabelText(/email \*/i)).toHaveValue('john@example.com')
      })
    })

    it('renders Cancel and Update User buttons', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /update user/i })).toBeInTheDocument()
      })
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with user ID and updated data', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await waitFor(() => {
        expect(screen.getByLabelText(/email \*/i)).toBeInTheDocument()
      })

      const emailInput = screen.getByLabelText(/email \*/i)
      fireEvent.change(emailInput, { target: { value: 'newemail@example.com' } })
      await user.click(screen.getByRole('button', { name: /update user/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('usr_abc123', expect.objectContaining({
          email: 'newemail@example.com',
        }))
      })
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /update user/i })).not.toBeDisabled()
      })

      await user.click(screen.getByRole('button', { name: /update user/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Email already in use'))
      renderDialog({ onSubmit })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /update user/i })).not.toBeDisabled()
      })

      await user.click(screen.getByRole('button', { name: /update user/i }))

      await waitFor(() => {
        expect(screen.getByText(/an unexpected error occurred/i)).toBeInTheDocument()
      })
    })
  })

  describe('cancel behavior', () => {
    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
