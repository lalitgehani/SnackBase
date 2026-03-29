/**
 * Tests for EditRoleDialog component (FT2.4)
 *
 * Verifies:
 * - Returns null (renders nothing) when role prop is null
 * - Pre-fills name input with existing role name
 * - Pre-fills description textarea with existing role description
 * - Save Changes button is disabled when name is cleared
 * - Calls onSubmit with correct roleId and updated data
 * - Re-populates form when opened with a different role
 * - Shows error message when onSubmit throws
 * - Calls onOpenChange(false) after successful submission
 * - Calls onOpenChange(false) when Cancel is clicked
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import EditRoleDialog from '@/components/roles/EditRoleDialog'
import type { RoleListItem } from '@/services/roles.service'

const MOCK_ROLE: RoleListItem = {
  id: 42,
  name: 'Editor',
  description: 'Can edit content',
  permissions: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const MOCK_ROLE_NO_DESC: RoleListItem = {
  id: 7,
  name: 'Viewer',
  description: undefined as unknown as string,
  permissions: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function renderDialog(props: {
  open?: boolean
  role?: RoleListItem | null
  onSubmit?: (roleId: number, data: { name: string; description?: string }) => Promise<void>
  onOpenChange?: (open: boolean) => void
}) {
  const {
    open = true,
    role = MOCK_ROLE,
    onSubmit = vi.fn().mockResolvedValue(undefined),
    onOpenChange = vi.fn(),
  } = props

  return render(
    <EditRoleDialog
      open={open}
      onOpenChange={onOpenChange}
      role={role}
      onSubmit={onSubmit}
    />
  )
}

describe('EditRoleDialog', () => {
  describe('null role guard', () => {
    it('renders nothing when role is null', () => {
      const { container } = renderDialog({ role: null })
      // Dialog content should not be in the DOM
      expect(screen.queryByText('Edit Role')).not.toBeInTheDocument()
      expect(container.firstChild).toBeNull()
    })
  })

  describe('rendering', () => {
    it('renders Edit Role dialog title', () => {
      renderDialog({})
      expect(screen.getByText('Edit Role')).toBeInTheDocument()
    })

    it('pre-fills name input with existing role name', () => {
      renderDialog({})
      expect(screen.getByLabelText(/name \*/i)).toHaveValue('Editor')
    })

    it('pre-fills description with existing role description', () => {
      renderDialog({})
      expect(screen.getByLabelText(/description/i)).toHaveValue('Can edit content')
    })

    it('leaves description empty when role has no description', () => {
      renderDialog({ role: MOCK_ROLE_NO_DESC })
      expect(screen.getByLabelText(/description/i)).toHaveValue('')
    })

    it('renders Cancel and Save Changes buttons', () => {
      renderDialog({})
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })
  })

  describe('submit button state', () => {
    it('is enabled when name is pre-filled', () => {
      renderDialog({})
      expect(screen.getByRole('button', { name: /save changes/i })).not.toBeDisabled()
    })

    it('is disabled when name is cleared', async () => {
      const user = userEvent.setup()
      renderDialog({})

      const nameInput = screen.getByLabelText(/name \*/i)
      await user.clear(nameInput)

      expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with roleId and updated name and description', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      const nameInput = screen.getByLabelText(/name \*/i)
      await user.clear(nameInput)
      await user.type(nameInput, 'Senior Editor')

      const descInput = screen.getByLabelText(/description/i)
      await user.clear(descInput)
      await user.type(descInput, 'Updated description')

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(42, {
          name: 'Senior Editor',
          description: 'Updated description',
        })
      })
    })

    it('passes undefined for description when description is cleared', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      const descInput = screen.getByLabelText(/description/i)
      await user.clear(descInput)

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(42, {
          name: 'Editor',
          description: undefined,
        })
      })
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onOpenChange, onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error message when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Role name already taken'))
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Role name already taken')).toBeInTheDocument()
      })
    })

    it('does not close dialog when submission fails', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Server error'))
      renderDialog({ onOpenChange, onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Server error')).toBeInTheDocument()
      })
      expect(onOpenChange).not.toHaveBeenCalledWith(false)
    })
  })

  describe('re-population', () => {
    it('updates form fields when role prop changes', async () => {
      const DIFFERENT_ROLE: RoleListItem = {
        id: 99,
        name: 'SuperAdmin',
        description: 'Has all permissions',
        permissions: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const { rerender } = renderDialog({ role: MOCK_ROLE })
      expect(screen.getByLabelText(/name \*/i)).toHaveValue('Editor')

      rerender(
        <EditRoleDialog
          open={true}
          onOpenChange={vi.fn()}
          role={DIFFERENT_ROLE}
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText(/name \*/i)).toHaveValue('SuperAdmin')
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
