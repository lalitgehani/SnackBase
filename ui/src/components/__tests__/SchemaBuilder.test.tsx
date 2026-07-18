/**
 * Compatibility tests: SchemaBuilder re-exports SchemaColumnTable.
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import SchemaBuilder from '@/components/collections/SchemaBuilder'
import type { FieldDefinition } from '@/services/collections.service'

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

describe('SchemaBuilder (compat wrapper)', () => {
  it('renders SchemaColumnTable UI', () => {
    render(
      <SchemaBuilder fields={[makeField({ name: 'title' })]} onChange={vi.fn()} />,
    )
    expect(screen.getByTestId('schema-column-table')).toBeInTheDocument()
    expect(screen.getByDisplayValue('title')).toBeInTheDocument()
  })

  it('supports add field', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<SchemaBuilder fields={[]} onChange={onChange} />)
    await user.click(screen.getByRole('button', { name: /add field/i }))
    expect(onChange).toHaveBeenCalled()
  })
})
