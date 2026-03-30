/**
 * Tests for ViewRecordDialog component
 *
 * Verifies:
 * - Renders dialog with collection name and record ID
 * - Renders schema fields with their values
 * - Shows "No record data available" when record is null
 * - Shows system fields (ID, created_at, etc.)
 * - Renders boolean fields as Yes/No badges
 * - Renders JSON fields as preformatted text
 * - Shows Close button that calls onOpenChange(false)
 * - Shows field type badges
 * - Shows PII badge for PII fields
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import ViewRecordDialog from '@/components/records/ViewRecordDialog'
import type { FieldDefinition } from '@/services/collections.service'
import type { RecordData } from '@/types/records.types'

const schema: FieldDefinition[] = [
  { name: 'title', type: 'text' },
  { name: 'price', type: 'number' },
  { name: 'active', type: 'boolean' },
  { name: 'metadata', type: 'json' },
]

const record: RecordData = {
  id: 'rec_abc123def456',
  account_id: 'acc_xyz',
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-16T12:00:00Z',
  created_by: 'user_admin',
  updated_by: 'user_admin',
  title: 'Test Product',
  price: 29.99,
  active: true,
  metadata: '{"key": "value"}',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  schema: FieldDefinition[]
  collectionName: string
  record: RecordData | null
  hasPiiAccess: boolean
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    schema: s = schema,
    collectionName = 'products',
    record: r = record,
    hasPiiAccess = false,
  } = props

  return render(
    <ViewRecordDialog
      open={open}
      onOpenChange={onOpenChange}
      schema={s}
      collectionName={collectionName}
      record={r}
      hasPiiAccess={hasPiiAccess}
    />
  )
}

describe('ViewRecordDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /record details/i })).toBeInTheDocument()
    })

    it('renders collection name in description', () => {
      renderDialog({ collectionName: 'products' })
      expect(screen.getByText(/products/i)).toBeInTheDocument()
    })

    it('renders all schema field names', () => {
      renderDialog()
      expect(screen.getByText('title')).toBeInTheDocument()
      expect(screen.getByText('price')).toBeInTheDocument()
      expect(screen.getByText('active')).toBeInTheDocument()
      expect(screen.getByText('metadata')).toBeInTheDocument()
    })

    it('renders text field value', () => {
      renderDialog()
      expect(screen.getByText('Test Product')).toBeInTheDocument()
    })

    it('renders number field value', () => {
      renderDialog()
      expect(screen.getByText('29.99')).toBeInTheDocument()
    })

    it('renders boolean true as Yes badge', () => {
      renderDialog()
      expect(screen.getByText('Yes')).toBeInTheDocument()
    })

    it('renders boolean false as No badge', () => {
      const recordWithFalse = { ...record, active: false }
      renderDialog({ record: recordWithFalse })
      expect(screen.getByText('No')).toBeInTheDocument()
    })

    it('renders JSON field in preformatted block', () => {
      renderDialog()
      expect(screen.getByText('{"key": "value"}')).toBeInTheDocument()
    })

    it('renders Close button', () => {
      renderDialog()
      // AppDialog has both a dismiss X button and the footer Close button
      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      expect(closeButtons.length).toBeGreaterThan(0)
    })

    it('shows "No record data available" when record is null', () => {
      renderDialog({ record: null })
      expect(screen.getByText(/no record data available/i)).toBeInTheDocument()
    })

    it('shows system fields section', () => {
      renderDialog()
      expect(screen.getByText(/system fields/i)).toBeInTheDocument()
    })

    it('shows PII badge for pii fields', () => {
      const piiSchema: FieldDefinition[] = [
        { name: 'ssn', type: 'text', pii: true },
      ]
      renderDialog({ schema: piiSchema })
      expect(screen.getByText('PII')).toBeInTheDocument()
    })

    it('renders null field value as italic null text', () => {
      const schemaWithOptional: FieldDefinition[] = [{ name: 'optional', type: 'text' }]
      const recordWithNull: RecordData = { ...record, optional: null }
      renderDialog({ schema: schemaWithOptional, record: recordWithNull })
      expect(screen.getByText('null')).toBeInTheDocument()
    })
  })

  describe('close behavior', () => {
    it('calls onOpenChange(false) when Close is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      // Click the last Close button (footer button, not X dismiss button)
      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      await user.click(closeButtons[closeButtons.length - 1])
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
