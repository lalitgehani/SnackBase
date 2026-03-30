/**
 * Tests for CreateRoleDialog component
 *
 * Verifies:
 * - Renders dialog with title
 * - Create Role button is disabled when name is empty
 * - Calls onSubmit with name (and optional description)
 * - Shows error when onSubmit throws
 * - Closes dialog after successful submission
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import CreateRoleDialog from '@/components/roles/CreateRoleDialog'

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: { name: string; description?: string }) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <CreateRoleDialog open={open} onOpenChange={onOpenChange} onSubmit={onSubmit} />
  )
}

describe('CreateRoleDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /create role/i })).toBeInTheDocument()
    })

    it('renders Name and Description fields', () => {
      renderDialog()
      expect(screen.getByLabelText(/name \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    })

    it('renders Cancel and Create Role buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create role/i })).toBeInTheDocument()
    })
  })

  describe('submit button state', () => {
    it('Create Role button is disabled when name is empty', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /create role/i })).toBeDisabled()
    })

    it('Create Role button is enabled when name is provided', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.type(screen.getByLabelText(/name \*/i), 'editor')
      expect(screen.getByRole('button', { name: /create role/i })).not.toBeDisabled()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with name and optional description', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'editor')
      await user.type(screen.getByLabelText(/description/i), 'Can edit content')
      await user.click(screen.getByRole('button', { name: /create role/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({
          name: 'editor',
          description: 'Can edit content',
        })
      })
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await user.type(screen.getByLabelText(/name \*/i), 'editor')
      await user.click(screen.getByRole('button', { name: /create role/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Role already exists'))
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'editor')
      await user.click(screen.getByRole('button', { name: /create role/i }))

      await waitFor(() => {
        expect(screen.getByText('Role already exists')).toBeInTheDocument()
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
