/**
 * Tests for DeleteAccountDialog component
 *
 * Verifies:
 * - Returns null when account is null
 * - Renders Delete Account heading with account name
 * - Delete button disabled until account name typed correctly
 * - Delete button enabled when name matches
 * - Calls onConfirm with account ID on confirm
 * - Calls onOpenChange(false) after successful deletion
 * - Shows error when onConfirm throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeleteAccountDialog from '@/components/accounts/DeleteAccountDialog'
import type { AccountListItem } from '@/services/accounts.service'

const account: AccountListItem = {
  id: 'acc_abc123',
  account_code: 'AC1234',
  slug: 'acme-corp',
  name: 'Acme Corp',
  user_count: 5,
  status: 'active',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  account: AccountListItem | null
  onConfirm: (accountId: string) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    account: a = account,
    onConfirm = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <DeleteAccountDialog
      open={open}
      onOpenChange={onOpenChange}
      account={a}
      onConfirm={onConfirm}
    />
  )
}

describe('DeleteAccountDialog', () => {
  describe('null account', () => {
    it('renders nothing when account is null', () => {
      const { container } = renderDialog({ account: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders Delete Account heading', () => {
      renderDialog()
      expect(screen.getAllByText(/delete account/i).length).toBeGreaterThan(0)
    })

    it('shows account name in description', () => {
      renderDialog()
      expect(screen.getAllByText(/acme corp/i).length).toBeGreaterThan(0)
    })

    it('renders Cancel and Delete Account buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /delete account/i })).toBeInTheDocument()
    })
  })

  describe('confirmation input', () => {
    it('Delete Account button is disabled when confirmation is empty', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /delete account/i })).toBeDisabled()
    })

    it('Delete Account button is disabled when wrong name is typed', async () => {
      const user = userEvent.setup()
      renderDialog()

      const input = screen.getByLabelText(/type.*to confirm/i)
      fireEvent.change(input, { target: { value: 'Wrong Name' } })
      expect(screen.getByRole('button', { name: /delete account/i })).toBeDisabled()
    })

    it('Delete Account button is enabled when correct name is typed', () => {
      renderDialog()
      const input = screen.getByLabelText(/type.*to confirm/i)
      fireEvent.change(input, { target: { value: 'Acme Corp' } })
      expect(screen.getByRole('button', { name: /delete account/i })).not.toBeDisabled()
    })
  })

  describe('confirm action', () => {
    it('calls onConfirm with account ID when confirmed', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm })

      const input = screen.getByLabelText(/type.*to confirm/i)
      fireEvent.change(input, { target: { value: 'Acme Corp' } })
      await user.click(screen.getByRole('button', { name: /delete account/i }))

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith('acc_abc123')
      })
    })

    it('calls onOpenChange(false) after successful deletion', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm, onOpenChange })

      const input = screen.getByLabelText(/type.*to confirm/i)
      fireEvent.change(input, { target: { value: 'Acme Corp' } })
      await user.click(screen.getByRole('button', { name: /delete account/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error when onConfirm throws', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockRejectedValue({
        response: { data: { detail: 'Cannot delete system account' } },
      })
      renderDialog({ onConfirm })

      const input = screen.getByLabelText(/type.*to confirm/i)
      fireEvent.change(input, { target: { value: 'Acme Corp' } })
      await user.click(screen.getByRole('button', { name: /delete account/i }))

      await waitFor(() => {
        expect(screen.getByText('Cannot delete system account')).toBeInTheDocument()
      })
    })
  })

  describe('cancel behavior', () => {
    it('calls onOpenChange when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalled()
    })
  })
})
