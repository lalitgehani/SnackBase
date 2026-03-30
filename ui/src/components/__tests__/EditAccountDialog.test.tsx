/**
 * Tests for EditAccountDialog component
 *
 * Verifies:
 * - Returns null when account is null
 * - Renders dialog pre-populated with account data
 * - Save Changes disabled when name is empty
 * - Calls onSubmit with account ID and updated name
 * - Calls onOpenChange(false) after successful submission
 * - Shows error when onSubmit throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import EditAccountDialog from '@/components/accounts/EditAccountDialog'
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
  onSubmit: (accountId: string, data: { name: string }) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    account: a = account,
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <EditAccountDialog
      open={open}
      onOpenChange={onOpenChange}
      account={a}
      onSubmit={onSubmit}
    />
  )
}

describe('EditAccountDialog', () => {
  describe('null account', () => {
    it('renders nothing when account is null', () => {
      const { container } = renderDialog({ account: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders Edit Account heading', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /edit account/i })).toBeInTheDocument()
    })

    it('pre-populates name field with account name', () => {
      renderDialog()
      expect(screen.getByLabelText(/name \*/i)).toHaveValue('Acme Corp')
    })

    it('shows account code as read-only', () => {
      renderDialog()
      expect(screen.getByLabelText(/account code/i)).toHaveValue('AC1234')
      expect(screen.getByLabelText(/account code/i)).toBeDisabled()
    })

    it('renders Cancel and Save Changes buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })
  })

  describe('form validation', () => {
    it('Save Changes is disabled when name is cleared', () => {
      renderDialog()
      const nameInput = screen.getByLabelText(/name \*/i)
      fireEvent.change(nameInput, { target: { value: '' } })
      expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with account ID and updated name', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      const nameInput = screen.getByLabelText(/name \*/i)
      fireEvent.change(nameInput, { target: { value: 'New Corp Name' } })
      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('acc_abc123', { name: 'New Corp Name' })
      })
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue({
        response: { data: { detail: 'Account name already taken' } },
      })
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Account name already taken')).toBeInTheDocument()
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
