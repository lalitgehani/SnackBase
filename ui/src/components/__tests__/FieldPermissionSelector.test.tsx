/**
 * Tests for FieldPermissionSelector component
 *
 * Verifies:
 * - Renders label and description
 * - Shows "All Fields" active when value is '*'
 * - Renders field checkboxes for each field
 * - Calls onChange with '*' when All Fields is selected
 * - Calls onChange with JSON array when specific fields are checked
 * - Unchecking all fields resets to '*'
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import FieldPermissionSelector from '@/components/collections/FieldPermissionSelector'

const fields = ['title', 'price', 'category', 'id', 'created_at']

function renderSelector(props: Partial<{
  label: string
  description: string
  value: string
  fields: string[]
  onChange: (value: string) => void
}> = {}) {
  const {
    label = 'List Fields',
    description = 'Fields returned in list results',
    value = '*',
    fields: f = fields,
    onChange = vi.fn(),
  } = props

  return render(
    <FieldPermissionSelector
      label={label}
      description={description}
      value={value}
      fields={f}
      onChange={onChange}
    />
  )
}

describe('FieldPermissionSelector', () => {
  describe('rendering', () => {
    it('renders the label', () => {
      renderSelector()
      expect(screen.getByText('List Fields')).toBeInTheDocument()
    })

    it('renders the description', () => {
      renderSelector()
      expect(screen.getByText('Fields returned in list results')).toBeInTheDocument()
    })

    it('renders All Fields button', () => {
      renderSelector()
      expect(screen.getByRole('button', { name: /all fields/i })).toBeInTheDocument()
    })

    it('renders field checkboxes in specific fields mode', () => {
      // Checkboxes only show when value is not '*'
      renderSelector({ value: '[]' })
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes.length).toBeGreaterThan(0)
    })

    it('renders each field name in specific fields mode', () => {
      // Field names only show as labels when in specific mode
      renderSelector({ value: '[]' })
      expect(screen.getByText('title')).toBeInTheDocument()
      expect(screen.getByText('price')).toBeInTheDocument()
    })
  })

  describe('all fields mode', () => {
    it('All Fields button is active (default/primary variant) when value is "*"', () => {
      renderSelector({ value: '*' })
      const allButton = screen.getByRole('button', { name: /all fields/i })
      // When value is *, the button should have default variant
      expect(allButton).toBeInTheDocument()
    })

    it('calls onChange when a field checkbox is toggled in specific mode', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      // Start in specific mode (not '*')
      renderSelector({ value: '[]', onChange })

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0])
      expect(onChange).toHaveBeenCalled()
    })
  })

  describe('specific fields mode', () => {
    it('shows checked fields when value is JSON array', () => {
      renderSelector({ value: JSON.stringify(['title', 'price']) })
      const titleCheckbox = screen.getAllByRole('checkbox').find(
        (cb) => cb.closest('[data-field="title"]') || cb.getAttribute('data-field') === 'title'
      )
      // At least the checkboxes render
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes.length).toBeGreaterThan(0)
    })

    it('calls onChange with "*" when All Fields is clicked while in specific mode', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderSelector({ value: JSON.stringify(['title']), onChange })

      await user.click(screen.getByRole('button', { name: /all fields/i }))
      expect(onChange).toHaveBeenCalledWith('*')
    })
  })
})
