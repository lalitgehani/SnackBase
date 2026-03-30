/**
 * Tests for DeleteRoleDialog component
 *
 * Verifies:
 * - Returns null when role is null
 * - Renders dialog with role name
 * - Shows "cannot be deleted" message for default roles (admin, user)
 * - Does not show Delete button for default roles
 * - Calls onConfirm with role ID on confirm
 * - Calls onOpenChange(false) after successful deletion
 * - Cancel/Close button works
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeleteRoleDialog from '@/components/roles/DeleteRoleDialog'
import type { RoleListItem } from '@/services/roles.service'

const customRole: RoleListItem = {
  id: 10,
  name: 'editor',
  description: 'Can edit content',
  collections_count: 3,
}

const adminRole: RoleListItem = {
  id: 1,
  name: 'admin',
  description: 'System admin',
  collections_count: 0,
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  role: RoleListItem | null
  onConfirm: (roleId: number) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    role = customRole,
    onConfirm = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <DeleteRoleDialog
      open={open}
      onOpenChange={onOpenChange}
      role={role}
      onConfirm={onConfirm}
    />
  )
}

describe('DeleteRoleDialog', () => {
  describe('null role', () => {
    it('renders nothing when role is null', () => {
      const { container } = renderDialog({ role: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('custom role', () => {
    it('renders Delete Role heading', () => {
      renderDialog({ role: customRole })
      expect(screen.getByRole('heading', { name: /delete role/i })).toBeInTheDocument()
    })

    it('renders Delete Role button for non-default roles', () => {
      renderDialog({ role: customRole })
      expect(screen.getByRole('button', { name: /delete role/i })).toBeInTheDocument()
    })

    it('shows warning with role name', () => {
      renderDialog({ role: customRole })
      expect(screen.getByText('editor')).toBeInTheDocument()
    })

    it('calls onConfirm with role ID on confirm', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ role: customRole, onConfirm })

      await user.click(screen.getByRole('button', { name: /delete role/i }))

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith(10)
      })
    })

    it('calls onOpenChange(false) after successful deletion', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ role: customRole, onConfirm, onOpenChange })

      await user.click(screen.getByRole('button', { name: /delete role/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })
  })

  describe('default role protection', () => {
    it('shows "cannot be deleted" message for default role', () => {
      renderDialog({ role: adminRole })
      expect(screen.getAllByText(/cannot be deleted/i).length).toBeGreaterThan(0)
    })

    it('does not show Delete Role button for default role', () => {
      renderDialog({ role: adminRole })
      expect(screen.queryByRole('button', { name: /delete role/i })).not.toBeInTheDocument()
    })

    it('shows Close button for default role', () => {
      renderDialog({ role: adminRole })
      // AppDialog has X close and footer Close button
      expect(screen.getAllByRole('button', { name: /close/i }).length).toBeGreaterThan(0)
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
