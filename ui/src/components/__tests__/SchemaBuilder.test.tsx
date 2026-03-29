/**
 * Tests for SchemaBuilder component (FT2.5)
 *
 * Verifies:
 * - Renders existing schema fields on load
 * - "Add Field" button creates a new empty field row
 * - Field name input is editable for new fields
 * - Field type dropdown shows all supported types
 * - Selecting "reference" type shows additional collection picker
 * - "required" toggle works
 * - "unique" toggle works
 * - "pii" toggle shows/hides mask type selector
 * - Remove field button deletes the field row
 * - Remove button is disabled for existing fields (originalFieldCount)
 * - Reordering fields via Move Up / Move Down
 * - Existing fields show "(existing)" label and are read-only
 * - Empty state renders when no fields exist
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import SchemaBuilder from '@/components/collections/SchemaBuilder'
import type { FieldDefinition } from '@/services/collections.service'
import { FIELD_TYPES } from '@/services/collections.service'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeField(overrides: Partial<FieldDefinition> = {}): FieldDefinition {
  return { name: 'field_a', type: 'text', required: false, unique: false, pii: false, ...overrides }
}

interface RenderProps {
  fields?: FieldDefinition[]
  onChange?: (fields: FieldDefinition[]) => void
  originalFieldCount?: number
  collections?: string[]
}

function renderBuilder({
  fields = [],
  onChange = vi.fn(),
  originalFieldCount = 0,
  collections = [],
}: RenderProps = {}) {
  return render(
    <SchemaBuilder
      fields={fields}
      onChange={onChange}
      originalFieldCount={originalFieldCount}
      collections={collections}
    />
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SchemaBuilder', () => {
  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------
  describe('empty state', () => {
    it('renders empty-state message when no fields exist', () => {
      renderBuilder({ fields: [] })
      expect(
        screen.getByText(/no fields yet/i)
      ).toBeInTheDocument()
    })

    it('renders "Add Field" button regardless of empty state', () => {
      renderBuilder({ fields: [] })
      expect(screen.getByRole('button', { name: /add field/i })).toBeInTheDocument()
    })
  })

  // -------------------------------------------------------------------------
  // Adding fields
  // -------------------------------------------------------------------------
  describe('adding fields', () => {
    it('calls onChange with a new default field when "Add Field" is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [], onChange })

      await user.click(screen.getByRole('button', { name: /add field/i }))

      expect(onChange).toHaveBeenCalledOnce()
      const [newFields] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(newFields).toHaveLength(1)
      expect(newFields[0]).toMatchObject({
        name: '',
        type: 'text',
        required: false,
        unique: false,
        pii: false,
      })
    })
  })

  // -------------------------------------------------------------------------
  // Rendering existing fields
  // -------------------------------------------------------------------------
  describe('rendering fields', () => {
    it('renders a row for each field in the fields array', () => {
      const fields = [
        makeField({ name: 'title' }),
        makeField({ name: 'body', type: 'text' }),
      ]
      renderBuilder({ fields })

      expect(screen.getByText('Field 1')).toBeInTheDocument()
      expect(screen.getByText('Field 2')).toBeInTheDocument()
    })

    it('displays the correct field name in the input', () => {
      renderBuilder({ fields: [makeField({ name: 'email_address' })] })
      const input = screen.getByDisplayValue('email_address')
      expect(input).toBeInTheDocument()
    })

    it('marks fields within originalFieldCount as "(existing)"', () => {
      const fields = [makeField({ name: 'existing_field' }), makeField({ name: 'new_field' })]
      renderBuilder({ fields, originalFieldCount: 1 })

      expect(screen.getByText('(existing)')).toBeInTheDocument()
    })

    it('disables the name input for existing fields', () => {
      const fields = [makeField({ name: 'locked' })]
      renderBuilder({ fields, originalFieldCount: 1 })

      const input = screen.getByDisplayValue('locked')
      expect(input).toBeDisabled()
    })

    it('enables the name input for new fields', () => {
      const fields = [makeField({ name: 'editable' })]
      renderBuilder({ fields, originalFieldCount: 0 })

      const input = screen.getByDisplayValue('editable')
      expect(input).not.toBeDisabled()
    })
  })

  // -------------------------------------------------------------------------
  // Field type dropdown
  // -------------------------------------------------------------------------
  describe('field type dropdown', () => {
    it('shows all supported field types in the dropdown', async () => {
      const user = userEvent.setup()
      renderBuilder({ fields: [makeField({ name: 'f', type: 'text' })] })

      // Open the Select
      await user.click(screen.getByRole('combobox'))

      for (const ft of FIELD_TYPES) {
        expect(
          screen.getByRole('option', { name: ft.label })
        ).toBeInTheDocument()
      }
    })

    it('calls onChange with updated type when a type is selected', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [makeField({ name: 'f', type: 'text' })], onChange })

      await user.click(screen.getByRole('combobox'))
      await user.click(screen.getByRole('option', { name: 'Number' }))

      expect(onChange).toHaveBeenCalledOnce()
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].type).toBe('number')
    })
  })

  // -------------------------------------------------------------------------
  // Required / Unique / PII toggles
  // -------------------------------------------------------------------------
  describe('required toggle', () => {
    it('calls onChange with required: true when "Required" checkbox is checked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [makeField({ name: 'f', required: false })], onChange })

      await user.click(screen.getByRole('checkbox', { name: /required/i }))

      expect(onChange).toHaveBeenCalledOnce()
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].required).toBe(true)
    })

    it('calls onChange with required: false when "Required" checkbox is unchecked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [makeField({ name: 'f', required: true })], onChange })

      await user.click(screen.getByRole('checkbox', { name: /required/i }))

      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].required).toBe(false)
    })
  })

  describe('unique toggle', () => {
    it('calls onChange with unique: true when "Unique" checkbox is checked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [makeField({ name: 'f', unique: false })], onChange })

      await user.click(screen.getByRole('checkbox', { name: /unique/i }))

      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].unique).toBe(true)
    })
  })

  describe('PII toggle', () => {
    it('calls onChange with pii: true when "PII" checkbox is checked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [makeField({ name: 'f', pii: false })], onChange })

      await user.click(screen.getByRole('checkbox', { name: /pii/i }))

      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].pii).toBe(true)
    })

    it('shows Mask Type selector when pii is true', () => {
      renderBuilder({ fields: [makeField({ name: 'f', pii: true })] })
      expect(screen.getByLabelText(/mask type/i)).toBeInTheDocument()
    })

    it('hides Mask Type selector when pii is false', () => {
      renderBuilder({ fields: [makeField({ name: 'f', pii: false })] })
      expect(screen.queryByLabelText(/mask type/i)).not.toBeInTheDocument()
    })

    it('clears mask_type from field when PII is unchecked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({
        fields: [makeField({ name: 'f', pii: true, mask_type: 'email' })],
        onChange,
      })

      await user.click(screen.getByRole('checkbox', { name: /pii/i }))

      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].pii).toBe(false)
      expect(updated[0].mask_type).toBeUndefined()
    })
  })

  // -------------------------------------------------------------------------
  // Reference type — collection picker
  // -------------------------------------------------------------------------
  describe('reference type', () => {
    it('shows Target Collection and On Delete selects when type is "reference"', () => {
      renderBuilder({
        fields: [makeField({ name: 'user_id', type: 'reference' })],
        collections: ['users', 'posts'],
      })

      expect(screen.getByLabelText(/target collection \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/on delete/i)).toBeInTheDocument()
    })

    it('does not show Target Collection select when type is not "reference"', () => {
      renderBuilder({ fields: [makeField({ name: 'f', type: 'text' })] })
      expect(screen.queryByLabelText(/target collection/i)).not.toBeInTheDocument()
    })

    it('lists available collections in the Target Collection dropdown', async () => {
      const user = userEvent.setup()
      renderBuilder({
        fields: [makeField({ name: 'user_id', type: 'reference' })],
        collections: ['users', 'posts'],
      })

      // There are multiple comboboxes (type + target collection + on delete); find Target Collection trigger
      const collectionTrigger = screen.getByLabelText(/target collection \*/i)
      await user.click(collectionTrigger)

      expect(screen.getByRole('option', { name: 'users' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'posts' })).toBeInTheDocument()
    })

    it('clears collection and on_delete when type changes away from "reference"', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({
        fields: [makeField({ name: 'ref', type: 'reference', collection: 'users', on_delete: 'cascade' })],
        collections: ['users'],
        onChange,
      })

      // The first combobox is the field type selector
      const typeCombobox = screen.getAllByRole('combobox')[0]
      await user.click(typeCombobox)
      await user.click(screen.getByRole('option', { name: 'Text' }))

      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].type).toBe('text')
      expect(updated[0].collection).toBeUndefined()
      expect(updated[0].on_delete).toBeUndefined()
    })
  })

  // -------------------------------------------------------------------------
  // Removing fields
  // -------------------------------------------------------------------------
  describe('removing fields', () => {
    it('calls onChange with field removed when the remove button is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      const fields = [makeField({ name: 'keep' }), makeField({ name: 'remove_me' })]
      renderBuilder({ fields, onChange, originalFieldCount: 0 })

      // Each field row has its own remove button; click the second one
      const removeButtons = screen.getAllByRole('button', { name: '' }).filter(
        (btn) => btn.querySelector('svg') // icon-only buttons
      )
      // The remove (trash) button is the 3rd icon-only button per row (up, down, trash)
      // Find by querying within each field card
      const cards = screen.getAllByText(/^Field \d+$/).map((el) => el.closest('.border') as HTMLElement)
      const secondCard = cards[1]
      const trashBtn = within(secondCard).getAllByRole('button').at(-1)!
      await user.click(trashBtn)

      expect(onChange).toHaveBeenCalledOnce()
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated).toHaveLength(1)
      expect(updated[0].name).toBe('keep')
    })

    it('disables the remove button for existing fields', () => {
      const fields = [makeField({ name: 'locked' })]
      renderBuilder({ fields, originalFieldCount: 1 })

      const card = screen.getByText('Field 1').closest('.border') as HTMLElement
      const trashBtn = within(card).getAllByRole('button').at(-1)!
      expect(trashBtn).toBeDisabled()
    })

    it('enables the remove button for new fields', () => {
      const fields = [makeField({ name: 'new_f' })]
      renderBuilder({ fields, originalFieldCount: 0 })

      const card = screen.getByText('Field 1').closest('.border') as HTMLElement
      const trashBtn = within(card).getAllByRole('button').at(-1)!
      expect(trashBtn).not.toBeDisabled()
    })
  })

  // -------------------------------------------------------------------------
  // Reordering fields
  // -------------------------------------------------------------------------
  describe('reordering fields', () => {
    it('disables Move Up button for the first field', () => {
      const fields = [makeField({ name: 'first' }), makeField({ name: 'second' })]
      renderBuilder({ fields })

      const firstCard = screen.getByText('Field 1').closest('.border') as HTMLElement
      const moveUpBtn = within(firstCard).getAllByRole('button')[0]
      expect(moveUpBtn).toBeDisabled()
    })

    it('disables Move Down button for the last field', () => {
      const fields = [makeField({ name: 'first' }), makeField({ name: 'second' })]
      renderBuilder({ fields })

      const lastCard = screen.getByText('Field 2').closest('.border') as HTMLElement
      const moveDownBtn = within(lastCard).getAllByRole('button')[1]
      expect(moveDownBtn).toBeDisabled()
    })

    it('calls onChange with swapped fields when Move Down is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      const fields = [makeField({ name: 'alpha' }), makeField({ name: 'beta' })]
      renderBuilder({ fields, onChange })

      const firstCard = screen.getByText('Field 1').closest('.border') as HTMLElement
      const moveDownBtn = within(firstCard).getAllByRole('button')[1]
      await user.click(moveDownBtn)

      expect(onChange).toHaveBeenCalledOnce()
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].name).toBe('beta')
      expect(updated[1].name).toBe('alpha')
    })

    it('calls onChange with swapped fields when Move Up is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      const fields = [makeField({ name: 'alpha' }), makeField({ name: 'beta' })]
      renderBuilder({ fields, onChange })

      const secondCard = screen.getByText('Field 2').closest('.border') as HTMLElement
      const moveUpBtn = within(secondCard).getAllByRole('button')[0]
      await user.click(moveUpBtn)

      expect(onChange).toHaveBeenCalledOnce()
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].name).toBe('beta')
      expect(updated[1].name).toBe('alpha')
    })
  })

  // -------------------------------------------------------------------------
  // Field name editing
  // -------------------------------------------------------------------------
  describe('field name editing', () => {
    it('calls onChange with updated name when field name input changes', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderBuilder({ fields: [makeField({ name: '' })], onChange })

      const input = screen.getByPlaceholderText('field_name')
      // The component is controlled — each keystroke fires onChange with the
      // new single-char value relative to the (static) empty prop.
      await user.type(input, 'x')

      expect(onChange).toHaveBeenCalledOnce()
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].name).toBe('x')
    })
  })
})
