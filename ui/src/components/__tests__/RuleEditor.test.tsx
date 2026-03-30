/**
 * Tests for RuleEditor component
 *
 * Verifies:
 * - Renders label and description
 * - Locked mode: shows "superadmins only" message, no input
 * - Public mode: shows "anyone can access" message, no input
 * - Custom mode: shows input field, hides status message
 * - Mode switching calls onChange with correct value
 * - Custom button from non-custom state sets default expression
 * - Test Rule button shown only in Custom mode when onTest provided
 * - Calls onTest when Test Rule is clicked
 * - Input onChange calls onChange with new value
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import RuleEditor from '@/components/collections/RuleEditor'

function renderEditor(props: Partial<{
  label: string
  description: string
  value: string | null
  onChange: (value: string | null) => void
  onTest?: () => void
  placeholder?: string
}> = {}) {
  const {
    label = 'Create Rule',
    description = 'Controls who can create records',
    value = null,
    onChange = vi.fn(),
    onTest,
    placeholder,
  } = props

  return render(
    <RuleEditor
      label={label}
      description={description}
      value={value}
      onChange={onChange}
      onTest={onTest}
      placeholder={placeholder}
    />
  )
}

describe('RuleEditor', () => {
  describe('rendering', () => {
    it('renders label and description', () => {
      renderEditor()
      expect(screen.getByText('Create Rule')).toBeInTheDocument()
      expect(screen.getByText('Controls who can create records')).toBeInTheDocument()
    })

    it('renders Locked, Public, and Custom buttons', () => {
      renderEditor()
      expect(screen.getByRole('button', { name: /locked/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /public/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /custom/i })).toBeInTheDocument()
    })
  })

  describe('Locked mode (value = null)', () => {
    it('shows superadmins message', () => {
      renderEditor({ value: null })
      expect(screen.getByText(/only superadmins can access/i)).toBeInTheDocument()
    })

    it('does not show input field', () => {
      renderEditor({ value: null })
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    })

    it('does not show Test Rule button', () => {
      renderEditor({ value: null, onTest: vi.fn() })
      expect(screen.queryByRole('button', { name: /test rule/i })).not.toBeInTheDocument()
    })
  })

  describe('Public mode (value = "")', () => {
    it('shows anyone can access message', () => {
      renderEditor({ value: '' })
      expect(screen.getByText(/anyone.*can access/i)).toBeInTheDocument()
    })

    it('does not show input field', () => {
      renderEditor({ value: '' })
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    })

    it('does not show Test Rule button', () => {
      renderEditor({ value: '', onTest: vi.fn() })
      expect(screen.queryByRole('button', { name: /test rule/i })).not.toBeInTheDocument()
    })
  })

  describe('Custom mode (value = non-empty string)', () => {
    it('shows input field with current value', () => {
      renderEditor({ value: 'created_by = @request.auth.id' })
      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
      expect(input).toHaveValue('created_by = @request.auth.id')
    })

    it('does not show locked or public messages', () => {
      renderEditor({ value: 'created_by = @request.auth.id' })
      expect(screen.queryByText(/only superadmins/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/anyone.*can access/i)).not.toBeInTheDocument()
    })

    it('shows Test Rule button when onTest is provided', () => {
      renderEditor({ value: 'created_by = @request.auth.id', onTest: vi.fn() })
      expect(screen.getByRole('button', { name: /test rule/i })).toBeInTheDocument()
    })

    it('does not show Test Rule button when onTest is not provided', () => {
      renderEditor({ value: 'created_by = @request.auth.id' })
      expect(screen.queryByRole('button', { name: /test rule/i })).not.toBeInTheDocument()
    })
  })

  describe('mode switching', () => {
    it('calls onChange(null) when Locked button is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderEditor({ value: '', onChange })

      await user.click(screen.getByRole('button', { name: /locked/i }))
      expect(onChange).toHaveBeenCalledWith(null)
    })

    it('calls onChange("") when Public button is clicked', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderEditor({ value: null, onChange })

      await user.click(screen.getByRole('button', { name: /public/i }))
      expect(onChange).toHaveBeenCalledWith('')
    })

    it('calls onChange with default expression when Custom button clicked from Locked mode', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderEditor({ value: null, onChange })

      await user.click(screen.getByRole('button', { name: /custom/i }))
      expect(onChange).toHaveBeenCalledWith('created_by = @request.auth.id')
    })

    it('calls onChange with default expression when Custom button clicked from Public mode', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderEditor({ value: '', onChange })

      await user.click(screen.getByRole('button', { name: /custom/i }))
      expect(onChange).toHaveBeenCalledWith('created_by = @request.auth.id')
    })

    it('does not call onChange when Custom button clicked while already in Custom mode', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      renderEditor({ value: 'created_by = @request.auth.id', onChange })

      await user.click(screen.getByRole('button', { name: /custom/i }))
      expect(onChange).not.toHaveBeenCalled()
    })
  })

  describe('input interaction', () => {
    it('calls onChange with new value when input changes', () => {
      const onChange = vi.fn()
      renderEditor({ value: 'created_by = @request.auth.id', onChange })

      const input = screen.getByRole('textbox')
      fireEvent.change(input, { target: { value: 'id = @request.auth.id' } })
      expect(onChange).toHaveBeenCalledWith('id = @request.auth.id')
    })
  })

  describe('Test Rule action', () => {
    it('calls onTest when Test Rule button is clicked', async () => {
      const user = userEvent.setup()
      const onTest = vi.fn()
      renderEditor({ value: 'created_by = @request.auth.id', onTest })

      await user.click(screen.getByRole('button', { name: /test rule/i }))
      expect(onTest).toHaveBeenCalled()
    })
  })
})
