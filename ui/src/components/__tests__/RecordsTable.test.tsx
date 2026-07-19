/**
 * Tests for RecordsTable component
 *
 * Verifies:
 * - Renders table with records
 * - Shows empty state when no records
 * - Renders schema field columns
 * - Shows null values as "null"
 * - Renders boolean fields as Yes/No badges
 * - Renders long text truncated
 * - Calls onView, onEdit, onDelete when action buttons clicked
 * - Multi-select checkbox column renders when onSelectionChange provided
 * - Selecting all records works
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import RecordsTable from '@/components/records/RecordsTable'
import type { RecordListItem } from '@/types/records.types'
import type { FieldDefinition } from '@/services/collections.service'

const schema: FieldDefinition[] = [
  { name: 'title', type: 'text' },
  { name: 'published', type: 'boolean' },
  { name: 'count', type: 'number' },
]

const records: RecordListItem[] = [
  {
    id: 'rec_001',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    title: 'Hello World',
    published: true,
    count: 42,
  },
  {
    id: 'rec_002',
    created_at: '2024-01-16T10:00:00Z',
    updated_at: '2024-01-16T10:00:00Z',
    title: 'Second Post',
    published: false,
    count: null,
  },
]

const defaultProps = {
  records,
  schema,
  sortBy: 'created_at',
  sortOrder: 'desc' as const,
  onSort: vi.fn(),
  onView: vi.fn(),
  onEdit: vi.fn(),
  onDelete: vi.fn(),
  totalItems: 2,
  page: 1,
  pageSize: 10,
  onPageChange: vi.fn(),
  onPageSizeChange: vi.fn(),
}

function renderTable(props = {}) {
  return render(<RecordsTable {...defaultProps} {...props} />)
}

describe('RecordsTable', () => {
  describe('rendering', () => {
    it('renders schema column headers', () => {
      renderTable()
      expect(screen.getByText('title')).toBeInTheDocument()
      expect(screen.getByText('published')).toBeInTheDocument()
      expect(screen.getByText('count')).toBeInTheDocument()
    })

    it('renders text field values', () => {
      renderTable()
      expect(screen.getByText('Hello World')).toBeInTheDocument()
      expect(screen.getByText('Second Post')).toBeInTheDocument()
    })

    it('renders boolean fields as Yes/No badges', () => {
      renderTable()
      expect(screen.getByText('Yes')).toBeInTheDocument()
      expect(screen.getByText('No')).toBeInTheDocument()
    })

    it('renders null values as "null"', () => {
      renderTable()
      expect(screen.getAllByText('null').length).toBeGreaterThan(0)
    })

    it('renders Created column', () => {
      renderTable()
      expect(screen.getByText('Created')).toBeInTheDocument()
    })

    it('shows empty state when no records', () => {
      renderTable({ records: [] })
      expect(screen.getByText(/no records found/i)).toBeInTheDocument()
    })
  })

  describe('action buttons', () => {
    it('calls onView when view button clicked', async () => {
      const user = userEvent.setup()
      const onView = vi.fn()
      renderTable({ onView })

      const viewBtns = screen.getAllByTitle('View record')
      await user.click(viewBtns[0])
      expect(onView).toHaveBeenCalledWith(records[0])
    })

    it('calls onEdit when edit button clicked', async () => {
      const user = userEvent.setup()
      const onEdit = vi.fn()
      renderTable({ onEdit })

      const editBtns = screen.getAllByTitle('Edit record')
      await user.click(editBtns[0])
      expect(onEdit).toHaveBeenCalledWith(records[0])
    })

    it('calls onDelete when delete button clicked', async () => {
      const user = userEvent.setup()
      const onDelete = vi.fn()
      renderTable({ onDelete })

      const deleteBtns = screen.getAllByTitle('Delete record')
      await user.click(deleteBtns[0])
      expect(onDelete).toHaveBeenCalledWith(records[0])
    })
  })

  describe('multi-select', () => {
    it('renders select all checkbox when onSelectionChange provided', () => {
      renderTable({
        selectedIds: new Set(),
        onSelectionChange: vi.fn(),
      })
      expect(screen.getByLabelText('Select all')).toBeInTheDocument()
    })

    it('renders individual checkboxes for each record', () => {
      renderTable({
        selectedIds: new Set(),
        onSelectionChange: vi.fn(),
      })
      expect(screen.getByLabelText('Select record rec_001')).toBeInTheDocument()
      expect(screen.getByLabelText('Select record rec_002')).toBeInTheDocument()
    })

    it('calls onSelectionChange with all IDs when select all clicked', async () => {
      const user = userEvent.setup()
      const onSelectionChange = vi.fn()
      renderTable({
        selectedIds: new Set(),
        onSelectionChange,
      })

      await user.click(screen.getByLabelText('Select all'))
      expect(onSelectionChange).toHaveBeenCalled()
    })
  })

  describe('long text truncation', () => {
    it('truncates text fields longer than 50 chars', () => {
      const longText = 'a'.repeat(60)
      const longRecords: RecordListItem[] = [{
        id: 'rec_long',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        title: longText,
      }]
      renderTable({ records: longRecords })
      // Should show truncated version with ...
      expect(screen.getByText(`${'a'.repeat(50)}...`)).toBeInTheDocument()
    })
  })

  describe('column visibility', () => {
    beforeEach(() => {
      localStorage.clear()
    })

    it('renders Columns toggle when schema has fields', () => {
      renderTable({ collectionName: 'posts' })
      expect(screen.getByTestId('column-visibility-trigger')).toBeInTheDocument()
    })

    it('hides a user schema column when unchecked', async () => {
      const user = userEvent.setup()
      renderTable({ collectionName: 'posts' })

      await user.click(screen.getByTestId('column-visibility-trigger'))
      await user.click(screen.getByTestId('column-toggle-title'))

      // Header for title should no longer appear in the table (menu still open may show it)
      // Close by checking data cells: Hello World was under title
      expect(screen.queryByText('Hello World')).not.toBeInTheDocument()
      // Actions still work
      expect(screen.getAllByTitle('View record').length).toBeGreaterThan(0)
    })

    it('persists hidden columns to localStorage', async () => {
      const user = userEvent.setup()
      renderTable({ collectionName: 'posts' })

      await user.click(screen.getByTestId('column-visibility-trigger'))
      await user.click(screen.getByTestId('column-toggle-title'))

      const stored = localStorage.getItem('column_visibility_posts')
      expect(stored).toBeTruthy()
      expect(JSON.parse(stored!)).toContain('title')
    })

    it('restores hidden columns from localStorage on mount', () => {
      localStorage.setItem('column_visibility_posts', JSON.stringify(['published']))
      renderTable({ collectionName: 'posts' })

      // published header should not be in the table headers
      // Yes/No badges come from published field — should be gone
      expect(screen.queryByText('Yes')).not.toBeInTheDocument()
      expect(screen.queryByText('No')).not.toBeInTheDocument()
      // title values still visible
      expect(screen.getByText('Hello World')).toBeInTheDocument()
    })

    it('show all restores columns', async () => {
      const user = userEvent.setup()
      localStorage.setItem('column_visibility_posts', JSON.stringify(['title']))
      renderTable({ collectionName: 'posts' })

      expect(screen.queryByText('Hello World')).not.toBeInTheDocument()

      await user.click(screen.getByTestId('column-visibility-trigger'))
      await user.click(screen.getByTestId('column-show-all'))

      expect(screen.getByText('Hello World')).toBeInTheDocument()
    })
  })
})
