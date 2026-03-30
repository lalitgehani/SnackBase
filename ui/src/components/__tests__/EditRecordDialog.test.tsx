/**
 * Tests for EditRecordDialog component
 *
 * Verifies:
 * - Renders dialog with correct title and collection name
 * - Pre-populates form fields with existing record data
 * - Calls onSubmit with (recordId, updatedData) on valid submission
 * - Shows validation error for required fields cleared to empty
 * - Shows loading state during submission
 * - Calls onOpenChange(false) after successful submission
 * - Displays API error when onSubmit throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import EditRecordDialog from '@/components/records/EditRecordDialog'
import type { FieldDefinition } from '@/services/collections.service'
import type { RecordData } from '@/types/records.types'

const schema: FieldDefinition[] = [
  { name: 'title', type: 'text', required: true },
  { name: 'description', type: 'text' },
]

const existingRecord: RecordData = {
  id: 'rec_abc123',
  title: 'Original Title',
  description: 'Original description',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (recordId: string, data: RecordData) => Promise<void>
  schema: FieldDefinition[]
  collectionName: string
  record: RecordData | null
  recordId: string
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onSubmit = vi.fn().mockResolvedValue(undefined),
    schema: s = schema,
    collectionName = 'articles',
    record = existingRecord,
    recordId = 'rec_abc123',
  } = props

  return render(
    <EditRecordDialog
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={onSubmit}
      schema={s}
      collectionName={collectionName}
      record={record}
      recordId={recordId}
    />
  )
}

describe('EditRecordDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /edit record/i })).toBeInTheDocument()
    })

    it('renders collection name in description', () => {
      renderDialog({ collectionName: 'articles' })
      expect(screen.getByText(/articles/i)).toBeInTheDocument()
    })

    it('renders Cancel and Save Changes buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })

    it('pre-populates fields with existing record values', () => {
      renderDialog()
      const titleInput = screen.getByDisplayValue('Original Title')
      expect(titleInput).toBeInTheDocument()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with recordId and updated data', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, recordId: 'rec_abc123' })

      // Clear and retype the title
      const titleInput = screen.getByDisplayValue('Original Title')
      await user.clear(titleInput)
      await user.type(titleInput, 'Updated Title')
      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          'rec_abc123',
          expect.objectContaining({ title: 'Updated Title' })
        )
      })
    })

    it('shows validation error when required field is cleared', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      const titleInput = screen.getByDisplayValue('Original Title')
      await user.clear(titleInput)
      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByText(/please fix the validation errors/i)).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows loading state during submission', async () => {
      const user = userEvent.setup()
      let resolve!: () => void
      const onSubmit = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /saving/i })).toBeInTheDocument()
      })

      resolve()
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

    it('displays error message when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Network error'))
      renderDialog({ onSubmit })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(screen.getByText(/an unexpected error occurred/i)).toBeInTheDocument()
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

  describe('null record', () => {
    it('renders without crashing when record is null', () => {
      renderDialog({ record: null })
      expect(screen.getByRole('heading', { name: /edit record/i })).toBeInTheDocument()
    })
  })
})
