/**
 * Tests for BulkDeleteConfirmDialog component
 *
 * Verifies:
 * - Renders dialog with correct count and collection name
 * - Pluralizes title and button correctly for count > 1
 * - Uses singular form for count = 1
 * - Calls onConfirm on Delete button click
 * - Shows loading state during deletion
 * - Calls onOpenChange(false) after successful deletion
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import BulkDeleteConfirmDialog from '@/components/records/BulkDeleteConfirmDialog'

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => Promise<void>
  count: number
  collectionName: string
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onConfirm = vi.fn().mockResolvedValue(undefined),
    count = 3,
    collectionName = 'products',
  } = props

  return render(
    <BulkDeleteConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      onConfirm={onConfirm}
      count={count}
      collectionName={collectionName}
    />
  )
}

describe('BulkDeleteConfirmDialog', () => {
  describe('rendering', () => {
    it('renders dialog title with record count', () => {
      renderDialog({ count: 3 })
      expect(screen.getByRole('heading', { name: /delete 3 records/i })).toBeInTheDocument()
    })

    it('uses singular "Record" for count = 1', () => {
      renderDialog({ count: 1 })
      expect(screen.getByRole('heading', { name: /delete 1 record$/i })).toBeInTheDocument()
    })

    it('renders collection name in warning', () => {
      renderDialog({ collectionName: 'orders' })
      expect(screen.getAllByText(/orders/i).length).toBeGreaterThan(0)
    })

    it('renders Cancel and Delete buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /delete 3 records/i })).toBeInTheDocument()
    })

    it('shows warning icon and text', () => {
      renderDialog()
      expect(screen.getByText(/warning/i)).toBeInTheDocument()
    })
  })

  describe('confirm action', () => {
    it('calls onConfirm when Delete button is clicked', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete 3 records/i }))

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalled()
      })
    })

    it('shows loading state during deletion', async () => {
      const user = userEvent.setup()
      let resolve!: () => void
      const onConfirm = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete 3 records/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /deleting/i })).toBeInTheDocument()
      })

      resolve()
    })

    it('disables buttons during deletion', async () => {
      const user = userEvent.setup()
      let resolve!: () => void
      const onConfirm = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete 3 records/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
      })

      resolve()
    })

    it('calls onOpenChange(false) after successful deletion', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm, onOpenChange })

      await user.click(screen.getByRole('button', { name: /delete 3 records/i }))

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
