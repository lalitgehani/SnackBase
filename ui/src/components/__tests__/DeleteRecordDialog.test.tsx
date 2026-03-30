/**
 * Tests for DeleteRecordDialog component
 *
 * Verifies:
 * - Renders dialog with collection name in description
 * - Shows warning message
 * - Displays record summary (up to 4 fields)
 * - Shows truncated record ID
 * - Calls onConfirm with correct record ID on confirm
 * - Shows loading state during deletion
 * - Calls onOpenChange(false) after successful deletion
 * - Cancel button closes dialog
 * - Handles null record gracefully
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DeleteRecordDialog from '@/components/records/DeleteRecordDialog'
import type { FieldDefinition } from '@/services/collections.service'
import type { RecordData } from '@/types/records.types'

const defaultSchema: FieldDefinition[] = [
  { name: 'title', type: 'text' },
  { name: 'description', type: 'text' },
  { name: 'price', type: 'number' },
]

const defaultRecord: RecordData = {
  id: 'rec_abc123def456ghi789',
  title: 'Test Product',
  description: 'A product description',
  price: 9.99,
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (recordId: string) => Promise<void>
  schema: FieldDefinition[]
  collectionName: string
  record: RecordData | null
  recordId: string
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onConfirm = vi.fn().mockResolvedValue(undefined),
    schema = defaultSchema,
    collectionName = 'products',
    record = defaultRecord,
    recordId = 'rec_abc123def456ghi789',
  } = props

  return render(
    <DeleteRecordDialog
      open={open}
      onOpenChange={onOpenChange}
      onConfirm={onConfirm}
      schema={schema}
      collectionName={collectionName}
      record={record}
      recordId={recordId}
    />
  )
}

describe('DeleteRecordDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /delete record/i })).toBeInTheDocument()
    })

    it('renders collection name in description', () => {
      renderDialog({ collectionName: 'products' })
      expect(screen.getByText(/products/i)).toBeInTheDocument()
    })

    it('renders warning message', () => {
      renderDialog()
      expect(screen.getByText(/warning/i)).toBeInTheDocument()
      expect(screen.getByText(/permanently remove/i)).toBeInTheDocument()
    })

    it('renders Cancel and Delete Record buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /delete record/i })).toBeInTheDocument()
    })

    it('shows record field summary', () => {
      renderDialog()
      expect(screen.getByText('title:')).toBeInTheDocument()
      expect(screen.getByText('Test Product')).toBeInTheDocument()
    })

    it('shows truncated record ID', () => {
      renderDialog({ recordId: 'rec_abc123def456ghi789' })
      expect(screen.getByText(/ID:/)).toBeInTheDocument()
    })

    it('handles null record without crashing', () => {
      renderDialog({ record: null })
      expect(screen.getByRole('heading', { name: /delete record/i })).toBeInTheDocument()
    })

    it('shows "and N more fields" when schema has more than 4 fields', () => {
      const largeSchema: FieldDefinition[] = [
        { name: 'f1', type: 'text' },
        { name: 'f2', type: 'text' },
        { name: 'f3', type: 'text' },
        { name: 'f4', type: 'text' },
        { name: 'f5', type: 'text' },
        { name: 'f6', type: 'text' },
      ]
      const largeRecord: RecordData = { f1: 'a', f2: 'b', f3: 'c', f4: 'd', f5: 'e', f6: 'f' }
      renderDialog({ schema: largeSchema, record: largeRecord })
      expect(screen.getByText(/more fields/i)).toBeInTheDocument()
    })
  })

  describe('confirm action', () => {
    it('calls onConfirm with the recordId when Delete Record is clicked', async () => {
      const user = userEvent.setup()
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onConfirm, recordId: 'rec_abc123def456ghi789' })

      await user.click(screen.getByRole('button', { name: /delete record/i }))

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith('rec_abc123def456ghi789')
      })
    })

    it('shows loading state during deletion', async () => {
      const user = userEvent.setup()
      let resolve!: () => void
      const onConfirm = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete record/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /deleting/i })).toBeInTheDocument()
      })

      resolve()
    })

    it('disables both buttons during deletion', async () => {
      const user = userEvent.setup()
      let resolve!: () => void
      const onConfirm = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
      renderDialog({ onConfirm })

      await user.click(screen.getByRole('button', { name: /delete record/i }))

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

      await user.click(screen.getByRole('button', { name: /delete record/i }))

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
