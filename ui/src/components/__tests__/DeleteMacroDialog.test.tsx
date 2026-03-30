/**
 * Tests for DeleteMacroDialog component
 *
 * Verifies:
 * - Returns null when macro is null
 * - Renders dialog with macro name in warning
 * - Cancel button closes dialog
 * - Calls onConfirm with macro ID on confirm
 * - Calls onOpenChange(false) after successful deletion
 * - Shows error when onConfirm throws
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeleteMacroDialog from '@/components/macros/DeleteMacroDialog'
import type { Macro } from '@/types/macro'

const macro: Macro = {
  id: 42,
  name: 'is_admin',
  description: 'Check if user is admin',
  sql_query: 'SELECT 1 FROM roles WHERE id = @user.role_id AND name = "admin"',
  parameters: '[]',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  created_by: 'user_abc',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  macro: Macro | null
  onConfirm: (macroId: number) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    macro: m = macro,
    onConfirm = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <DeleteMacroDialog
      open={open}
      onOpenChange={onOpenChange}
      macro={m}
      onConfirm={onConfirm}
    />
  )
}

describe('DeleteMacroDialog', () => {
  describe('null macro', () => {
    it('renders nothing when macro is null', () => {
      const { container } = renderDialog({ macro: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders Delete Macro title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /delete macro/i })).toBeInTheDocument()
    })

    it('shows macro name in warning', () => {
      renderDialog()
      expect(screen.getAllByText(/@is_admin/i).length).toBeGreaterThan(0)
    })

    it('renders Cancel and Delete Macro buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /delete macro/i })).toBeInTheDocument()
    })
  })

  describe('confirm action', () => {
    it('calls onConfirm with macro ID', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete macro/i }))

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith(42)
      })
    })

    it('calls onOpenChange(false) after successful deletion', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm, onOpenChange })

      await user.click(screen.getByRole('button', { name: /delete macro/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('shows error when onConfirm throws', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockRejectedValue({
        response: { data: { detail: 'Macro is in use' } },
      })
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete macro/i }))

      await waitFor(() => {
        expect(screen.getByText('Macro is in use')).toBeInTheDocument()
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
