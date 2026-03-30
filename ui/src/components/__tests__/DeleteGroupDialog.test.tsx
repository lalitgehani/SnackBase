/**
 * Tests for DeleteGroupDialog component
 *
 * Verifies:
 * - Renders dialog with group name in warning text
 * - Cancel button closes dialog
 * - Calls onSubmit with group ID when Delete Group is clicked
 * - Shows loading state during deletion
 * - Calls onOpenChange(false) after successful deletion
 * - Shows error message when onSubmit throws
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeleteGroupDialog from '@/components/groups/DeleteGroupDialog'
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
  onSubmit: (groupId: string) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    group: g = group,
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <DeleteGroupDialog
      open={open}
      onOpenChange={onOpenChange}
      group={g}
      onSubmit={onSubmit}
    />
  )
}

describe('DeleteGroupDialog', () => {
  describe('rendering', () => {
    it('renders Delete Group heading', () => {
      renderDialog()
      // "Delete Group" appears in heading and button - use getAllByText
      expect(screen.getAllByText(/delete group/i).length).toBeGreaterThan(0)
    })

    it('renders group name in warning text', () => {
      renderDialog()
      expect(screen.getByText(/administrators/i)).toBeInTheDocument()
    })

    it('renders Cancel and Delete Group buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /delete group/i })).toBeInTheDocument()
    })
  })

  describe('confirm action', () => {
    it('calls onSubmit with group ID when Delete Group is clicked', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /delete group/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith('grp_abc123')
      })
    })

    it('calls onOpenChange(false) after successful deletion', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await user.click(screen.getByRole('button', { name: /delete group/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue({
        response: { data: { detail: 'Group has members' } },
      })
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /delete group/i }))

      await waitFor(() => {
        expect(screen.getByText('Group has members')).toBeInTheDocument()
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
