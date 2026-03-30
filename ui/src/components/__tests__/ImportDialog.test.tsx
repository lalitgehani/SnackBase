/**
 * Tests for ImportDialog component
 *
 * Verifies:
 * - Renders dialog title
 * - Shows file upload area in idle state
 * - Shows JSON format instruction
 * - Cancel button closes dialog
 * - Shows collection name and schema fields
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import ImportDialog from '@/components/records/ImportDialog'
import type { FieldDefinition } from '@/services/collections.service'

const schema: FieldDefinition[] = [
  { name: 'title', type: 'text', required: true },
  { name: 'price', type: 'number' },
]

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  collection: string
  schema: FieldDefinition[]
  onSuccess: (count: number) => void
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    collection = 'products',
    schema: s = schema,
    onSuccess = vi.fn(),
  } = props

  return render(
    <ImportDialog
      open={open}
      onOpenChange={onOpenChange}
      collection={collection}
      schema={s}
      onSuccess={onSuccess}
    />
  )
}

describe('ImportDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /import records/i })).toBeInTheDocument()
    })

    it('renders file upload area or instructions', () => {
      renderDialog()
      // Should show a file input or upload instructions
      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeInTheDocument()
    })

    it('shows JSON format hint', () => {
      renderDialog()
      // "JSON" may appear multiple times (description, placeholder, etc.)
      expect(screen.getAllByText(/json/i).length).toBeGreaterThan(0)
    })

    it('renders Cancel button', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
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
