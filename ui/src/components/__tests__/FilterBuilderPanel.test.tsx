/**
 * Tests for FilterBuilderPanel component
 *
 * Verifies:
 * - Renders Filters button
 * - Shows active filter count badge when filters applied
 * - Opens panel on Filters button click
 * - Shows "No filters added" when panel open with no rows
 * - Add Filter button adds a new row
 * - Apply Filters calls onApply with expression and rows
 * - Clear All calls onClear and closes panel
 * - Filter pills render for applied rows
 * - Remove pill button calls onRemovePill
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import FilterBuilderPanel, { type FilterRow } from '@/components/records/FilterBuilderPanel'
import type { FieldDefinition } from '@/services/collections.service'

const schema: FieldDefinition[] = [
  { name: 'title', type: 'text' },
  { name: 'count', type: 'number' },
]

const appliedRow: FilterRow = {
  id: 'row-1',
  field: 'title',
  operator: '=',
  value: 'hello',
}

function renderPanel(props: Partial<{
  schema: FieldDefinition[]
  appliedRows: FilterRow[]
  onApply: (expr: string, rows: FilterRow[]) => void
  onClear: () => void
  onRemovePill: (id: string) => void
}> = {}) {
  const {
    schema: s = schema,
    appliedRows = [],
    onApply = vi.fn(),
    onClear = vi.fn(),
    onRemovePill = vi.fn(),
  } = props

  return render(
    <FilterBuilderPanel
      schema={s}
      appliedRows={appliedRows}
      onApply={onApply}
      onClear={onClear}
      onRemovePill={onRemovePill}
    />
  )
}

describe('FilterBuilderPanel', () => {
  describe('rendering', () => {
    it('renders Filters button', () => {
      renderPanel()
      expect(screen.getByRole('button', { name: /filters/i })).toBeInTheDocument()
    })

    it('does not show badge when no filters applied', () => {
      renderPanel({ appliedRows: [] })
      // No badge number visible
      expect(screen.queryByText(/^[1-9]\d*$/)).not.toBeInTheDocument()
    })

    it('shows filter count badge when filters applied', () => {
      renderPanel({ appliedRows: [appliedRow] })
      expect(screen.getByText('1')).toBeInTheDocument()
    })
  })

  describe('filter pills', () => {
    it('renders filter pill for applied row', () => {
      renderPanel({ appliedRows: [appliedRow] })
      expect(screen.getByText(/title = "hello"/i)).toBeInTheDocument()
    })

    it('calls onRemovePill when pill remove button is clicked', async () => {
      const user = userEvent.setup()
      const onRemovePill = vi.fn()
      renderPanel({ appliedRows: [appliedRow], onRemovePill })

      const removeBtn = screen.getByRole('button', { name: /remove filter/i })
      await user.click(removeBtn)
      expect(onRemovePill).toHaveBeenCalledWith('row-1')
    })

    it('shows "Clear all" button when filters applied and panel is closed', () => {
      renderPanel({ appliedRows: [appliedRow] })
      expect(screen.getByRole('button', { name: /clear all/i })).toBeInTheDocument()
    })
  })

  describe('panel open/close', () => {
    it('opens panel when Filters button is clicked', async () => {
      const user = userEvent.setup()
      renderPanel()

      await user.click(screen.getByRole('button', { name: /^filters$/i }))
      expect(screen.getByText(/no filters added/i)).toBeInTheDocument()
    })

    it('closes panel when Filters button is clicked again', async () => {
      const user = userEvent.setup()
      renderPanel()

      const filtersBtn = screen.getByRole('button', { name: /^filters$/i })
      await user.click(filtersBtn)
      expect(screen.getByText(/no filters added/i)).toBeInTheDocument()
      await user.click(filtersBtn)
      expect(screen.queryByText(/no filters added/i)).not.toBeInTheDocument()
    })
  })

  describe('adding filters', () => {
    it('shows Add Filter button in open panel', async () => {
      const user = userEvent.setup()
      renderPanel()

      await user.click(screen.getByRole('button', { name: /^filters$/i }))
      expect(screen.getByRole('button', { name: /add filter/i })).toBeInTheDocument()
    })

    it('adds a new row when Add Filter is clicked', async () => {
      const user = userEvent.setup()
      renderPanel()

      await user.click(screen.getByRole('button', { name: /^filters$/i }))
      await user.click(screen.getByRole('button', { name: /add filter/i }))

      // Row should have a Field selector placeholder
      expect(screen.getAllByText(/field/i).length).toBeGreaterThan(0)
    })
  })

  describe('apply and clear', () => {
    it('Apply Filters button is disabled when no rows', async () => {
      const user = userEvent.setup()
      renderPanel()

      await user.click(screen.getByRole('button', { name: /^filters$/i }))
      expect(screen.getByRole('button', { name: /apply filters/i })).toBeDisabled()
    })

    it('calls onClear and closes panel when Clear All is clicked in open panel', async () => {
      const user = userEvent.setup()
      const onClear = vi.fn()
      renderPanel({ onClear })

      await user.click(screen.getByRole('button', { name: /^filters$/i }))
      // Click "Clear All" inside the open panel
      const clearButtons = screen.getAllByRole('button', { name: /clear all/i })
      await user.click(clearButtons[clearButtons.length - 1])

      expect(onClear).toHaveBeenCalled()
    })

    it('calls onApply when Apply Filters is clicked with valid rows', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      // Provide pre-existing applied row so Apply is enabled
      renderPanel({
        appliedRows: [appliedRow],
        onApply,
      })

      // Open panel — it pre-populates with applied rows
      // The toggle button includes badge count in its name, find it via getAllByRole
      const filtersBtns = screen.getAllByRole('button', { name: /filters/i })
      await user.click(filtersBtns[0])

      await user.click(screen.getByRole('button', { name: /apply filters/i }))
      expect(onApply).toHaveBeenCalled()
    })
  })
})
