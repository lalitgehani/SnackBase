/**
 * Tests for DeactivateUserDialog component
 *
 * Verifies:
 * - Renders dialog with user email in description
 * - Deactivate button is disabled until email is typed correctly
 * - Deactivate button is enabled when email matches
 * - Calls onSubmit with user ID on confirm
 * - Calls onOpenChange(false) after success
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeactivateUserDialog from '@/components/users/DeactivateUserDialog'
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
  onSubmit: (userId: string) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    user: u = user,
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <DeactivateUserDialog
      open={open}
      onOpenChange={onOpenChange}
      user={u}
      onSubmit={onSubmit}
    />
  )
}

describe('DeactivateUserDialog', () => {
  describe('rendering', () => {
    it('renders Deactivate User title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /deactivate user/i })).toBeInTheDocument()
    })

    it('renders user email in description', () => {
      renderDialog()
      // Email appears in description and confirmation input placeholder
      expect(screen.getAllByText(/john@example.com/i).length).toBeGreaterThan(0)
    })

    it('renders Cancel and Deactivate User buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /deactivate user/i })).toBeInTheDocument()
    })
  })

  describe('confirmation input', () => {
    it('Deactivate button is disabled when confirmation is empty', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /deactivate user/i })).toBeDisabled()
    })

    it('Deactivate button is disabled when confirmation is wrong', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'wrong@email.com')
      expect(screen.getByRole('button', { name: /deactivate user/i })).toBeDisabled()
    })

    it('Deactivate button is enabled when email matches', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'john@example.com')
      expect(screen.getByRole('button', { name: /deactivate user/i })).not.toBeDisabled()
    })
  })

  describe('confirm action', () => {
    it('calls onSubmit with user ID after typing correct email', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'john@example.com')
      await user.click(screen.getByRole('button', { name: /deactivate user/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('usr_abc123')
      })
    })

    it('calls onOpenChange(false) after successful deactivation', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'john@example.com')
      await user.click(screen.getByRole('button', { name: /deactivate user/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
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
