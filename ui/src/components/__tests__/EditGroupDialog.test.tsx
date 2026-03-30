/**
 * Tests for EditGroupDialog component
 *
 * Verifies:
 * - Renders dialog pre-populated with group data
 * - Save Changes button disabled when name is empty
 * - Calls onSubmit with group ID and updated data on submit
 * - Calls onOpenChange(false) after successful submission
 * - Shows error message when onSubmit throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import EditGroupDialog from '@/components/groups/EditGroupDialog'
import type { Group } from '@/services/groups.service'

const group: Group = {
  id: 'grp_abc123',
  account_id: 'acc_abc123',
  name: 'Administrators',
  description: 'Admin group',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  group: Group | null
  onSubmit: (groupId: string, data: { name: string; description?: string | null }) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    group: g = group,
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <EditGroupDialog
      open={open}
      onOpenChange={onOpenChange}
      group={g}
      onSubmit={onSubmit}
    />
  )
}

describe('EditGroupDialog', () => {
  describe('rendering', () => {
    it('renders Edit Group heading', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /edit group/i })).toBeInTheDocument()
    })

    it('pre-populates name field with group name', () => {
      renderDialog()
      expect(screen.getByLabelText(/name \*/i)).toHaveValue('Administrators')
    })

    it('pre-populates description field with group description', () => {
      renderDialog()
      expect(screen.getByLabelText(/description/i)).toHaveValue('Admin group')
    })

    it('renders Cancel and Save Changes buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })
  })

  describe('form validation', () => {
    it('Save Changes button is disabled when name is cleared', async () => {
      renderDialog()
      const nameInput = screen.getByLabelText(/name \*/i)
      fireEvent.change(nameInput, { target: { value: '' } })
      expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with group ID and updated name', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      const nameInput = screen.getByLabelText(/name \*/i)
      fireEvent.change(nameInput, { target: { value: 'New Name' } })
      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('grp_abc123', expect.objectContaining({ name: 'New Name' }))
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
        response: { data: { detail: 'Group name already exists' } },
      })
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Group name already exists')).toBeInTheDocument()
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
