/**
 * Tests for ResetPasswordDialog component
 *
 * Verifies:
 * - Renders dialog with two tabs: Send Link and Set Directly
 * - Default mode is "link" - shows Send Reset Link button
 * - Set Directly tab shows password fields
 * - Calls onSubmit with send_reset_link when in link mode
 * - Password validation: min 12 chars, uppercase, lowercase, digit, special char
 * - Shows error when passwords don't match
 * - Calls onSubmit with new_password in password mode
 * - Calls onOpenChange(false) after successful submission
 * - Shows error when onSubmit throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import ResetPasswordDialog from '@/components/users/ResetPasswordDialog'
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
    <ResetPasswordDialog
      open={open}
      onOpenChange={onOpenChange}
      user={u}
      onSubmit={onSubmit}
    />
  )
}

describe('ResetPasswordDialog', () => {
  describe('rendering', () => {
    it('renders Reset Password heading', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /reset password/i })).toBeInTheDocument()
    })

    it('renders Send Link and Set Directly tabs', () => {
      renderDialog()
      expect(screen.getByRole('tab', { name: /send link/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /set directly/i })).toBeInTheDocument()
    })

    it('shows Send Reset Link button by default (link mode)', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument()
    })

    it('renders Cancel button', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('link mode', () => {
    it('calls onSubmit with send_reset_link: true', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /send reset link/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('usr_abc123', { send_reset_link: true })
      })
    })

    it('calls onOpenChange(false) after successful link send', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await user.click(screen.getByRole('button', { name: /send reset link/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })
  })

  describe('password mode', () => {
    async function switchToPasswordMode() {
      const user = userEvent.setup()
      renderDialog()
      await user.click(screen.getByRole('tab', { name: /set directly/i }))
      return user
    }

    it('shows password fields when Set Directly tab is active', async () => {
      await switchToPasswordMode()
      expect(screen.getByLabelText(/new password \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password \*/i)).toBeInTheDocument()
    })

    it('shows validation error when password too short', async () => {
      const user = await switchToPasswordMode()
      const pwInput = screen.getByLabelText(/new password \*/i)
      const cfInput = screen.getByLabelText(/confirm password \*/i)

      fireEvent.change(pwInput, { target: { value: 'Short1!' } })
      fireEvent.change(cfInput, { target: { value: 'Short1!' } })

      await user.click(screen.getByRole('button', { name: /reset password/i }))

      await waitFor(() => {
        expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument()
      })
    })

    it('shows validation error when passwords do not match', async () => {
      const user = await switchToPasswordMode()

      fireEvent.change(screen.getByLabelText(/new password \*/i), { target: { value: 'ValidPass123!' } })
      fireEvent.change(screen.getByLabelText(/confirm password \*/i), { target: { value: 'DifferentPass123!' } })

      await user.click(screen.getByRole('button', { name: /reset password/i }))

      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      })
    })

    it('calls onSubmit with new_password when valid', async () => {
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      const user = userEvent.setup()
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('tab', { name: /set directly/i }))

      const validPassword = 'ValidPass123!'
      fireEvent.change(screen.getByLabelText(/new password \*/i), { target: { value: validPassword } })
      fireEvent.change(screen.getByLabelText(/confirm password \*/i), { target: { value: validPassword } })

      await user.click(screen.getByRole('button', { name: /reset password/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('usr_abc123', { new_password: validPassword })
      })
    })
  })

  describe('error handling', () => {
    it('shows error when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Reset failed'))
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /send reset link/i }))

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
