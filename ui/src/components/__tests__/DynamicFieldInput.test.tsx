/**
 * Tests for DynamicFieldInput component
 *
 * Verifies:
 * - Renders correct input type for each field type (text, number, boolean, email, url, json, datetime)
 * - Shows field name label
 * - Shows required indicator for required fields
 * - Shows unique badge for unique fields
 * - Shows PII badge for PII fields
 * - Shows field type badge
 * - Calls onChange with correct value for each input type
 * - Shows error message
 * - Shows default value hint when no value set
 * - JSON field shows validation error for invalid JSON
 * - Reference field shows combobox and no-records message
 * - date field shows calendar picker button
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { render } from '@/test/utils'
import DynamicFieldInput from '@/components/records/DynamicFieldInput'
import type { FieldDefinition } from '@/services/collections.service'

function renderField(
  field: Partial<FieldDefinition> & { name: string; type: string },
  value: unknown = '',
  onChange = vi.fn(),
  extra: { error?: string; disabled?: boolean } = {},
) {
  const fullField: FieldDefinition = { name: field.name, type: field.type, ...field }
  return render(
    <DynamicFieldInput
      field={fullField}
      value={value}
      onChange={onChange}
      error={extra.error}
      disabled={extra.disabled}
    />
  )
}

describe('DynamicFieldInput', () => {
  describe('text field', () => {
    it('renders a text input', () => {
      renderField({ name: 'title', type: 'text' })
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('calls onChange when user types', () => {
      const onChange = vi.fn()
      renderField({ name: 'title', type: 'text' }, '', onChange)
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hello' } })
      expect(onChange).toHaveBeenCalledWith('hello')
    })

    it('shows field label', () => {
      renderField({ name: 'title', type: 'text' })
      expect(screen.getByText('title')).toBeInTheDocument()
    })
  })

  describe('email field', () => {
    it('renders an email input', () => {
      renderField({ name: 'email', type: 'email' })
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('type', 'email')
    })

    it('shows Text type badge for Email', () => {
      renderField({ name: 'email', type: 'email' })
      expect(screen.getByText('Email')).toBeInTheDocument()
    })
  })

  describe('url field', () => {
    it('renders a url input', () => {
      renderField({ name: 'website', type: 'url' })
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('type', 'url')
    })
  })

  describe('number field', () => {
    it('renders a number input', () => {
      renderField({ name: 'price', type: 'number' })
      const input = screen.getByRole('spinbutton')
      expect(input).toHaveAttribute('type', 'number')
    })

    it('calls onChange with numeric value', () => {
      const onChange = vi.fn()
      renderField({ name: 'price', type: 'number' }, '', onChange)
      fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '42' } })
      expect(onChange).toHaveBeenCalledWith(42)
    })
  })

  describe('boolean field', () => {
    it('renders a checkbox', () => {
      renderField({ name: 'active', type: 'boolean' }, false)
      expect(screen.getByRole('checkbox')).toBeInTheDocument()
    })

    it('calls onChange with boolean value', () => {
      const onChange = vi.fn()
      renderField({ name: 'active', type: 'boolean' }, false, onChange)
      fireEvent.click(screen.getByRole('checkbox'))
      expect(onChange).toHaveBeenCalledWith(true)
    })

    it('shows Boolean type badge', () => {
      renderField({ name: 'active', type: 'boolean' })
      expect(screen.getByText('Boolean')).toBeInTheDocument()
    })
  })

  describe('datetime field', () => {
    it('renders a datetime-local input', () => {
      renderField({ name: 'created_at', type: 'datetime' })
      const input = document.querySelector('input[type="datetime-local"]')
      expect(input).toBeInTheDocument()
    })
  })

  describe('date field', () => {
    it('renders a date picker button', () => {
      renderField({ name: 'birth_date', type: 'date' })
      expect(screen.getByText('Pick a date')).toBeInTheDocument()
    })

    it('shows Date type badge', () => {
      renderField({ name: 'birth_date', type: 'date' })
      expect(screen.getByText('Date')).toBeInTheDocument()
    })
  })

  describe('json field', () => {
    it('renders a textarea', () => {
      renderField({ name: 'metadata', type: 'json' })
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('shows JSON hint text', () => {
      renderField({ name: 'metadata', type: 'json' })
      expect(screen.getByText(/enter valid json/i)).toBeInTheDocument()
    })

    it('shows JSON validation error when invalid JSON is blurred', () => {
      // Pass invalid JSON as initial value so the controlled input displays it
      renderField({ name: 'metadata', type: 'json' }, '{invalid json}', vi.fn())
      const textarea = screen.getByRole('textbox')
      fireEvent.blur(textarea)
      expect(screen.getByText(/invalid json format/i)).toBeInTheDocument()
    })

    it('does not show error for valid JSON on blur', () => {
      renderField({ name: 'metadata', type: 'json' }, '{"key": "value"}', vi.fn())
      const textarea = screen.getByRole('textbox')
      fireEvent.blur(textarea)
      expect(screen.queryByText(/invalid json format/i)).not.toBeInTheDocument()
    })
  })

  describe('reference field', () => {
    it('renders a combobox button', () => {
      renderField({ name: 'author', type: 'reference', collection: 'users' })
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('shows no records message when reference records are empty', () => {
      renderField({ name: 'author', type: 'reference', collection: 'users' })
      expect(screen.getByText(/no records found in target collection/i)).toBeInTheDocument()
    })

    it('shows collection name in combobox placeholder', () => {
      renderField({ name: 'author', type: 'reference', collection: 'users' })
      expect(screen.getByText(/select users/i)).toBeInTheDocument()
    })
  })

  describe('field decorators', () => {
    it('shows required asterisk for required fields', () => {
      renderField({ name: 'title', type: 'text', required: true })
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('shows Unique badge for unique fields', () => {
      renderField({ name: 'email', type: 'email', unique: true })
      expect(screen.getByText('Unique')).toBeInTheDocument()
    })

    it('shows PII badge for PII fields', () => {
      renderField({ name: 'ssn', type: 'text', pii: true })
      expect(screen.getByText('PII')).toBeInTheDocument()
    })

    it('shows field type badge', () => {
      renderField({ name: 'title', type: 'text' })
      expect(screen.getByText('Text')).toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when error prop is provided', () => {
      renderField({ name: 'title', type: 'text' }, '', vi.fn(), { error: 'This field is required' })
      expect(screen.getByText('This field is required')).toBeInTheDocument()
    })
  })

  describe('default value hint', () => {
    it('shows default value hint when value is empty and default is set', () => {
      renderField({ name: 'status', type: 'text', default: 'active' })
      expect(screen.getByText(/default: active/i)).toBeInTheDocument()
    })
  })

  describe('disabled state', () => {
    it('disables input when disabled prop is true', () => {
      renderField({ name: 'title', type: 'text' }, 'hello', vi.fn(), { disabled: true })
      expect(screen.getByRole('textbox')).toBeDisabled()
    })
  })
})
