/**
 * Tests for DeleteCollectionDialog component
 *
 * Verifies:
 * - Returns null when collection is null
 * - Renders dialog with collection name
 * - Shows warning when collection has records
 * - Delete button is disabled until name is typed correctly
 * - Delete button is enabled after typing correct name
 * - Calls onConfirm with collection ID on confirm
 * - Shows success state after deletion
 * - Cancel button calls onOpenChange(false)
 * - Done button is shown on success
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeleteCollectionDialog from '@/components/collections/DeleteCollectionDialog'
import type { CollectionListItem } from '@/services/collections.service'

const collection: CollectionListItem = {
  id: 'col_abc123',
  name: 'products',
  table_name: 'products',
  fields_count: 3,
  records_count: 5,
  has_public_access: false,
  created_at: '2024-01-01T00:00:00Z',
}

const emptyCollection: CollectionListItem = {
  ...collection,
  records_count: 0,
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  collection: CollectionListItem | null
  onConfirm: (collectionId: string) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    collection: col = collection,
    onConfirm = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <DeleteCollectionDialog
      open={open}
      onOpenChange={onOpenChange}
      collection={col}
      onConfirm={onConfirm}
    />
  )
}

describe('DeleteCollectionDialog', () => {
  describe('null collection', () => {
    it('renders nothing when collection is null', () => {
      const { container } = renderDialog({ collection: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders delete collection title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /delete collection/i })).toBeInTheDocument()
    })

    it('renders collection name in description', () => {
      renderDialog()
      // Collection name appears multiple times (description, confirm label, warning)
      expect(screen.getAllByText(/products/i).length).toBeGreaterThan(0)
    })

    it('shows warning when collection has records', () => {
      renderDialog({ collection })
      expect(screen.getAllByText(/5 record/i).length).toBeGreaterThan(0)
    })

    it('does not show records warning when collection is empty', () => {
      renderDialog({ collection: emptyCollection })
      expect(screen.queryByText(/warning.*record/i)).not.toBeInTheDocument()
    })

    it('renders Cancel and Delete Collection buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /delete collection/i })).toBeInTheDocument()
    })

    it('renders confirmation name input', () => {
      renderDialog()
      expect(screen.getByLabelText(/type.*to confirm/i)).toBeInTheDocument()
    })
  })

  describe('confirmation input', () => {
    it('Delete Collection button is disabled when confirm text is empty', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /delete collection/i })).toBeDisabled()
    })

    it('Delete Collection button is disabled when confirm text is wrong', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'wrong-name')
      expect(screen.getByRole('button', { name: /delete collection/i })).toBeDisabled()
    })

    it('Delete Collection button is enabled after typing correct name', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'products')
      expect(screen.getByRole('button', { name: /delete collection/i })).not.toBeDisabled()
    })
  })

  describe('confirm action', () => {
    it('calls onConfirm with collection ID after typing correct name', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm })

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'products')
      await user.click(screen.getByRole('button', { name: /delete collection/i }))

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith('col_abc123')
      })
    })

    it('shows success state after deletion', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm })

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'products')
      await user.click(screen.getByRole('button', { name: /delete collection/i }))

      await waitFor(() => {
        expect(screen.getByText(/deleted successfully/i)).toBeInTheDocument()
      })
    })

    it('shows Done button after successful deletion', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm })

      await user.type(screen.getByLabelText(/type.*to confirm/i), 'products')
      await user.click(screen.getByRole('button', { name: /delete collection/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
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
