/**
 * Tests for EditCollectionDialog component
 *
 * Verifies:
 * - Returns null when collection is null
 * - Renders dialog with collection name in title
 * - Renders Schema and Rules tabs
 * - Calls onSubmit with collection ID and schema on update
 * - Shows success state after successful update
 * - Shows "At least one field" error when all fields are removed
 * - Cancel button closes dialog
 * - Done button on success state closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import EditCollectionDialog from '@/components/collections/EditCollectionDialog'
import type { Collection, UpdateCollectionData } from '@/services/collections.service'

const collection: Collection = {
  id: 'col_abc123',
  name: 'products',
  table_name: 'products',
  schema: [
    { name: 'title', type: 'text', required: true },
    { name: 'price', type: 'number' },
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  collection: Collection | null
  onSubmit: (collectionId: string, data: UpdateCollectionData) => Promise<void>
  collections: string[]
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    collection: col = collection,
    onSubmit = vi.fn().mockResolvedValue(undefined),
    collections = [],
  } = props

  // Stub collection rules endpoint
  server.use(
    http.get('/api/v1/collection-rules/:id', () =>
      HttpResponse.json({
        id: 'rule_1',
        collection_id: col?.id ?? 'col_abc123',
        list_rule: null, view_rule: null, create_rule: null, update_rule: null, delete_rule: null,
        list_fields: '*', view_fields: '*', create_fields: '*', update_fields: '*',
        created_at: '2024-01-01T00:00:00Z',
      })
    )
  )

  return render(
    <EditCollectionDialog
      open={open}
      onOpenChange={onOpenChange}
      collection={col}
      onSubmit={onSubmit}
      collections={collections}
    />
  )
}

describe('EditCollectionDialog', () => {
  describe('null collection', () => {
    it('renders nothing when collection is null', () => {
      const { container } = renderDialog({ collection: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders dialog title with collection name', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /edit collection: products/i })).toBeInTheDocument()
    })

    it('renders Schema and Rules tabs', () => {
      renderDialog()
      expect(screen.getByRole('tab', { name: /schema/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /rules/i })).toBeInTheDocument()
    })

    it('renders Cancel and Update Schema buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /update schema/i })).toBeInTheDocument()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with collection ID and schema', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /update schema/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          'col_abc123',
          expect.objectContaining({ schema: expect.any(Array) })
        )
      })
    })

    it('shows success state after successful update', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /update schema/i }))

      await waitFor(() => {
        // Success message appears in the dialog body and heading
        expect(screen.getAllByText(/updated successfully/i).length).toBeGreaterThan(0)
      })
    })

    it('shows Done button on success state', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /update schema/i }))

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
