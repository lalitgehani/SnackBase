/**
 * Tests for ViewCollectionDialog component
 *
 * Verifies:
 * - Returns null when collection is null
 * - Renders dialog with collection name as title
 * - Shows schema field count in description
 * - Renders all field names and types
 * - Shows Required badge for required fields
 * - Shows Unique badge for unique fields
 * - Shows PII badge for PII fields
 * - Shows system fields section
 * - Close button calls onOpenChange(false)
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import ViewCollectionDialog from '@/components/collections/ViewCollectionDialog'
import type { Collection } from '@/services/collections.service'

const collection: Collection = {
  id: 'col_abc123',
  name: 'products',
  table_name: 'products',
  schema: [
    { name: 'title', type: 'text', required: true },
    { name: 'price', type: 'number', unique: true },
    { name: 'ssn', type: 'text', pii: true, mask_type: 'full' },
    { name: 'category', type: 'reference', collection: 'categories' },
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  collection: Collection | null
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    collection: col = collection,
  } = props

  return render(
    <ViewCollectionDialog
      open={open}
      onOpenChange={onOpenChange}
      collection={col}
    />
  )
}

describe('ViewCollectionDialog', () => {
  describe('null collection', () => {
    it('renders nothing when collection is null', () => {
      const { container } = renderDialog({ collection: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders dialog title with collection name', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: 'products' })).toBeInTheDocument()
    })

    it('shows field count in description', () => {
      renderDialog()
      expect(screen.getByText(/4 fields/i)).toBeInTheDocument()
    })

    it('renders all field names', () => {
      renderDialog()
      expect(screen.getByText('title')).toBeInTheDocument()
      expect(screen.getByText('price')).toBeInTheDocument()
      expect(screen.getByText('ssn')).toBeInTheDocument()
      expect(screen.getByText('category')).toBeInTheDocument()
    })

    it('renders field type badges', () => {
      renderDialog()
      // Multiple "text" badges may exist (title and ssn are both 'text' type)
      expect(screen.getAllByText('text').length).toBeGreaterThan(0)
      expect(screen.getByText('number')).toBeInTheDocument()
      expect(screen.getByText('reference')).toBeInTheDocument()
    })

    it('shows Required badge for required fields', () => {
      renderDialog()
      expect(screen.getByText('Required')).toBeInTheDocument()
    })

    it('shows Unique badge for unique fields', () => {
      renderDialog()
      expect(screen.getByText('Unique')).toBeInTheDocument()
    })

    it('shows PII badge for PII fields', () => {
      renderDialog()
      expect(screen.getByText('PII')).toBeInTheDocument()
    })

    it('shows reference collection name', () => {
      renderDialog()
      expect(screen.getByText('categories')).toBeInTheDocument()
    })

    it('shows system fields section', () => {
      renderDialog()
      expect(screen.getByText(/system fields/i)).toBeInTheDocument()
    })

    it('renders Close button', () => {
      renderDialog()
      // AppDialog may have both a dismiss X and the footer Close button
      expect(screen.getAllByRole('button', { name: /close/i }).length).toBeGreaterThan(0)
    })
  })

  describe('close behavior', () => {
    it('calls onOpenChange(false) when Close is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      // Click the footer Close button (last Close button)
      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      await user.click(closeButtons[closeButtons.length - 1])
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
