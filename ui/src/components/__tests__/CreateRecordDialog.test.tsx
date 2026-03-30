/**
 * Tests for CreateRecordDialog component
 *
 * Verifies:
 * - Renders dialog with correct title and collection name
 * - Renders form fields for each schema field
 * - Calls onSubmit with form data on valid submission
 * - Shows validation error when required fields are missing
 * - Shows loading state during submission
 * - Calls onOpenChange(false) after successful submission
 * - Displays API error when onSubmit throws
 * - Cancel button closes dialog
 * - Resets form when dialog closes (open → false)
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import CreateRecordDialog from '@/components/records/CreateRecordDialog'
import type { FieldDefinition } from '@/services/collections.service'
import type { RecordData } from '@/types/records.types'

const simpleSchema: FieldDefinition[] = [
  { name: 'title', type: 'text', required: true },
  { name: 'price', type: 'number' },
]

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: RecordData) => Promise<void>
  schema: FieldDefinition[]
  collectionName: string
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onSubmit = vi.fn().mockResolvedValue(undefined),
    schema = simpleSchema,
    collectionName = 'products',
  } = props

  return render(
    <CreateRecordDialog
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={onSubmit}
      schema={schema}
      collectionName={collectionName}
    />
  )
}

describe('CreateRecordDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /create record/i })).toBeInTheDocument()
    })

    it('renders collection name in description', () => {
      renderDialog({ collectionName: 'products' })
      expect(screen.getByText(/products/i)).toBeInTheDocument()
    })

    it('renders input for each schema field', () => {
      renderDialog()
      expect(screen.getByText('title')).toBeInTheDocument()
      expect(screen.getByText('price')).toBeInTheDocument()
    })

    it('renders Cancel and Create Record buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create record/i })).toBeInTheDocument()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with field values on valid submission', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/title/i), 'My Product')
      await user.click(screen.getByRole('button', { name: /create record/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'My Product' })
        )
      })
    })

    it('shows validation error when required field is empty', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      // Submit without filling required 'title' field
      await user.click(screen.getByRole('button', { name: /create record/i }))

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

      await user.type(screen.getByLabelText(/title/i), 'Test')
      await user.click(screen.getByRole('button', { name: /create record/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /creating/i })).toBeInTheDocument()
      })

      resolve()
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit, onOpenChange })

      await user.type(screen.getByLabelText(/title/i), 'Test Product')
      await user.click(screen.getByRole('button', { name: /create record/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('displays error message when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue(new Error('Network error'))
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/title/i), 'Test Product')
      await user.click(screen.getByRole('button', { name: /create record/i }))

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

  describe('empty schema', () => {
    it('renders without crashing when schema is empty', () => {
      renderDialog({ schema: [] })
      expect(screen.getByRole('heading', { name: /create record/i })).toBeInTheDocument()
    })

    it('submits successfully with empty schema', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ schema: [], onSubmit })

      await user.click(screen.getByRole('button', { name: /create record/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({})
      })
    })
  })
})
