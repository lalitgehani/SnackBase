/**
 * Tests for SchemaColumnTable (Phase 2 dense schema editor)
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import SchemaColumnTable from '@/components/collections/SchemaColumnTable'
import type { FieldDefinition } from '@/services/collections.service'
import { FIELD_TYPES } from '@/services/collections.service'

function makeField(overrides: Partial<FieldDefinition> = {}): FieldDefinition {
  return {
    name: 'field_a',
    type: 'text',
    required: false,
    unique: false,
    pii: false,
    ...overrides,
  }
}

interface RenderProps {
  fields?: FieldDefinition[]
  onChange?: (fields: FieldDefinition[]) => void
  originalFieldCount?: number
  collections?: string[]
  readOnly?: boolean
}

function renderTable({
  fields = [],
  onChange = vi.fn(),
  originalFieldCount = 0,
  collections = [],
  readOnly = false,
}: RenderProps = {}) {
  return render(
    <SchemaColumnTable
      fields={fields}
      onChange={onChange}
      originalFieldCount={originalFieldCount}
      collections={collections}
      readOnly={readOnly}
    />,
  )
}

describe('SchemaColumnTable', () => {
  describe('empty state', () => {
    it('renders empty-state message when no fields exist', () => {
      renderTable({ fields: [] })
      expect(screen.getByText(/no fields yet/i)).toBeInTheDocument()
    })

    it('renders Add Field button', () => {
      renderTable({ fields: [] })
      expect(screen.getByRole('button', { name: /add field/i })).toBeInTheDocument()
    })
  })

  describe('adding fields', () => {
    it('calls onChange with a new default field when Add Field is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({ fields: [], onChange })

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

  describe('rendering fields', () => {
    it('renders a row for each field', () => {
      renderTable({
        fields: [makeField({ name: 'title' }), makeField({ name: 'body' })],
      })
      expect(screen.getByTestId('schema-field-row-0')).toBeInTheDocument()
      expect(screen.getByTestId('schema-field-row-1')).toBeInTheDocument()
      expect(screen.getByDisplayValue('title')).toBeInTheDocument()
      expect(screen.getByDisplayValue('body')).toBeInTheDocument()
    })

    it('marks existing fields and disables name input', () => {
      renderTable({
        fields: [makeField({ name: 'locked' }), makeField({ name: 'new_f' })],
        originalFieldCount: 1,
      })
      expect(screen.getByText('(existing)')).toBeInTheDocument()
      expect(screen.getByDisplayValue('locked')).toBeDisabled()
      expect(screen.getByDisplayValue('new_f')).not.toBeDisabled()
      expect(screen.getByText('New')).toBeInTheDocument()
    })
  })

  describe('field type dropdown', () => {
    it('shows all supported field types', async () => {
      const user = userEvent.setup()
      renderTable({ fields: [makeField({ name: 'f', type: 'text' })] })

      await user.click(screen.getByRole('combobox', { name: /field 1 type/i }))

      for (const ft of FIELD_TYPES) {
        expect(screen.getByRole('option', { name: ft.label })).toBeInTheDocument()
      }
    })

    it('calls onChange when type changes', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({ fields: [makeField({ name: 'f', type: 'text' })], onChange })

      await user.click(screen.getByRole('combobox', { name: /field 1 type/i }))
      await user.click(screen.getByRole('option', { name: 'Number' }))

      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].type).toBe('number')
    })
  })

  describe('toggles', () => {
    it('toggles required', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({ fields: [makeField({ name: 'f' })], onChange })
      await user.click(screen.getByRole('checkbox', { name: /field 1 required/i }))
      expect((onChange.mock.calls[0] as [FieldDefinition[]])[0][0].required).toBe(true)
    })

    it('toggles unique', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({ fields: [makeField({ name: 'f' })], onChange })
      await user.click(screen.getByRole('checkbox', { name: /field 1 unique/i }))
      expect((onChange.mock.calls[0] as [FieldDefinition[]])[0][0].unique).toBe(true)
    })

    it('shows mask type when pii is true', () => {
      renderTable({ fields: [makeField({ name: 'f', pii: true })] })
      expect(screen.getByLabelText(/mask type/i)).toBeInTheDocument()
    })

    it('clears mask_type when PII unchecked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({
        fields: [makeField({ name: 'f', pii: true, mask_type: 'email' })],
        onChange,
      })
      await user.click(screen.getByRole('checkbox', { name: /field 1 pii/i }))
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].pii).toBe(false)
      expect(updated[0].mask_type).toBeUndefined()
    })
  })

  describe('reference type', () => {
    it('shows target collection and on delete when type is reference', () => {
      renderTable({
        fields: [makeField({ name: 'user_id', type: 'reference' })],
        collections: ['users', 'posts'],
      })
      expect(screen.getByLabelText(/target collection \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/on delete/i)).toBeInTheDocument()
    })

    it('lists collections in target dropdown', async () => {
      const user = userEvent.setup()
      renderTable({
        fields: [makeField({ name: 'user_id', type: 'reference' })],
        collections: ['users', 'posts'],
      })
      await user.click(screen.getByLabelText(/target collection \*/i))
      expect(screen.getByRole('option', { name: 'users' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'posts' })).toBeInTheDocument()
    })

    it('clears collection when type changes away from reference', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({
        fields: [
          makeField({
            name: 'ref',
            type: 'reference',
            collection: 'users',
            on_delete: 'cascade',
          }),
        ],
        collections: ['users'],
        onChange,
      })
      await user.click(screen.getByRole('combobox', { name: /field 1 type/i }))
      await user.click(screen.getByRole('option', { name: 'Text' }))
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].type).toBe('text')
      expect(updated[0].collection).toBeUndefined()
    })
  })

  describe('computed type', () => {
    it('shows expression and return type', () => {
      renderTable({
        fields: [
          makeField({
            name: 'full',
            type: 'computed',
            expression: 'a',
            return_type: 'text',
          }),
        ],
      })
      expect(screen.getByLabelText(/expression \*/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/return type \*/i)).toBeInTheDocument()
      expect(screen.getAllByText('Computed').length).toBeGreaterThan(0)
    })
  })

  describe('default value', () => {
    it('updates default via input', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({ fields: [makeField({ name: 'f' })], onChange })
      const input = screen.getByLabelText(/field 1 default/i)
      await user.type(input, 'x')
      expect(onChange).toHaveBeenCalled()
      const last = onChange.mock.calls.at(-1)![0] as FieldDefinition[]
      expect(last[0].default).toBe('x')
    })
  })

  describe('removing fields', () => {
    it('removes a new field', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({
        fields: [makeField({ name: 'keep' }), makeField({ name: 'remove_me' })],
        onChange,
        originalFieldCount: 0,
      })
      await user.click(screen.getByRole('button', { name: /delete field 2/i }))
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated).toHaveLength(1)
      expect(updated[0].name).toBe('keep')
    })

    it('disables delete for existing fields', () => {
      renderTable({
        fields: [makeField({ name: 'locked' })],
        originalFieldCount: 1,
      })
      expect(
        screen.getByRole('button', { name: /cannot delete existing field 1/i }),
      ).toBeDisabled()
    })
  })

  describe('reordering', () => {
    it('disables move up on first field', () => {
      renderTable({
        fields: [makeField({ name: 'first' }), makeField({ name: 'second' })],
      })
      expect(screen.getByRole('button', { name: /move field 1 up/i })).toBeDisabled()
    })

    it('swaps fields on move down', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderTable({
        fields: [makeField({ name: 'alpha' }), makeField({ name: 'beta' })],
        onChange,
      })
      await user.click(screen.getByRole('button', { name: /move field 1 down/i }))
      const [updated] = onChange.mock.calls[0] as [FieldDefinition[]]
      expect(updated[0].name).toBe('beta')
      expect(updated[1].name).toBe('alpha')
    })

    it('does not allow reordering existing fields in edit mode', () => {
      renderTable({
        fields: [
          makeField({ name: 'e1' }),
          makeField({ name: 'e2' }),
          makeField({ name: 'n1' }),
        ],
        originalFieldCount: 2,
      })
      expect(screen.getByRole('button', { name: /move field 1 down/i })).toBeDisabled()
      expect(screen.getByRole('button', { name: /move field 3 up/i })).toBeDisabled()
    })
  })

  describe('readOnly', () => {
    it('hides add and delete controls', () => {
      renderTable({
        fields: [makeField({ name: 'f' })],
        readOnly: true,
      })
      expect(screen.queryByRole('button', { name: /add field/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /delete field/i })).not.toBeInTheDocument()
      expect(screen.getByDisplayValue('f')).toBeDisabled()
    })
  })
})
