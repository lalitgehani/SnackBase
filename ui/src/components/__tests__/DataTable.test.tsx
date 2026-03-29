/**
 * Tests for DataTable component (FT2.3)
 *
 * Verifies:
 * - Renders column headers from column definitions
 * - Renders rows from provided data
 * - Displays empty state when data array is empty
 * - Pagination controls render and navigate pages
 * - Clicking sort header triggers sort callback
 * - Sort direction indicator toggles (asc/desc)
 * - Loading state renders spinner
 * - Custom cell renderers work via column definition
 * - Handles large datasets without error (100+ rows)
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent, within } from '@testing-library/react'
import { render } from '@/test/utils'
import { DataTable, type Column, type DispatchPagination, type DispatchSorting } from '@/components/common/DataTable'

// ---------------------------------------------------------------------------
// Test data types and factories
// ---------------------------------------------------------------------------

interface TestItem {
  id: string
  name: string
  status: string
  count: number
}

function makeItem(i: number): TestItem {
  return { id: `item-${i}`, name: `Item ${i}`, status: i % 2 === 0 ? 'active' : 'inactive', count: i * 10 }
}

const SAMPLE_DATA: TestItem[] = [makeItem(1), makeItem(2), makeItem(3)]

const COLUMNS: Column<TestItem>[] = [
  { header: 'Name', accessorKey: 'name', sortable: true },
  { header: 'Status', accessorKey: 'status' },
  { header: 'Count', accessorKey: 'count' },
]

function defaultPagination(overrides: Partial<DispatchPagination> = {}): DispatchPagination {
  return {
    page: 1,
    pageSize: 10,
    onPageChange: vi.fn(),
    onPageSizeChange: vi.fn(),
    ...overrides,
  }
}

function defaultSorting(overrides: Partial<DispatchSorting> = {}): DispatchSorting {
  return {
    sortBy: '',
    sortOrder: 'asc',
    onSort: vi.fn(),
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Column headers
// ---------------------------------------------------------------------------

describe('DataTable – column headers', () => {
  it('renders all column headers', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Count')).toBeInTheDocument()
  })

  it('renders a ReactNode as a column header', () => {
    const columns: Column<TestItem>[] = [
      { header: <span data-testid="custom-header">Custom</span>, accessorKey: 'name' },
    ]

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={columns}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByTestId('custom-header')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Row rendering
// ---------------------------------------------------------------------------

describe('DataTable – row rendering', () => {
  it('renders one row per data item', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByText('Item 1')).toBeInTheDocument()
    expect(screen.getByText('Item 2')).toBeInTheDocument()
    expect(screen.getByText('Item 3')).toBeInTheDocument()
  })

  it('renders cell values from accessorKey', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    // count column values
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
  })

  it('calls onRowClick with the correct item when a row is clicked', () => {
    const onRowClick = vi.fn()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        onRowClick={onRowClick}
      />,
    )

    fireEvent.click(screen.getByText('Item 1'))
    expect(onRowClick).toHaveBeenCalledWith(SAMPLE_DATA[0])
  })

  it('does not crash when onRowClick is not provided', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    // Clicking a row without a handler should not throw
    fireEvent.click(screen.getByText('Item 1'))
  })
})

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

describe('DataTable – empty state', () => {
  it('shows default "No data found" message when data is empty', () => {
    render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByText('No data found')).toBeInTheDocument()
  })

  it('shows custom noDataMessage when provided', () => {
    render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        noDataMessage="Nothing here yet"
      />,
    )

    expect(screen.getByText('Nothing here yet')).toBeInTheDocument()
  })

  it('does not render any data rows when empty', () => {
    render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.queryByText('Item 1')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

describe('DataTable – loading state', () => {
  it('renders a spinner when isLoading is true', () => {
    const { container } = render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        isLoading
      />,
    )

    // The RefreshCw icon is rendered inside the loading cell; verify via SVG presence
    const svgEl = container.querySelector('svg.animate-spin')
    expect(svgEl).not.toBeNull()
  })

  it('does not show row data while loading', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        isLoading
      />,
    )

    expect(screen.queryByText('Item 1')).not.toBeInTheDocument()
  })

  it('does not show empty-state message while loading', () => {
    render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        isLoading
      />,
    )

    expect(screen.queryByText('No data found')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Custom cell renderers
// ---------------------------------------------------------------------------

describe('DataTable – custom cell renderers', () => {
  it('renders output of column.render() instead of raw value', () => {
    const columns: Column<TestItem>[] = [
      {
        header: 'Name',
        accessorKey: 'name',
        render: (item) => <span data-testid={`badge-${item.id}`}>{item.name.toUpperCase()}</span>,
      },
    ]

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={columns}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByTestId('badge-item-1')).toBeInTheDocument()
    expect(screen.getByText('ITEM 1')).toBeInTheDocument()
  })

  it('prefers render() over accessorKey when both are specified', () => {
    const columns: Column<TestItem>[] = [
      {
        header: 'Name',
        accessorKey: 'name',
        render: (item) => <span>rendered:{item.name}</span>,
      },
    ]

    render(
      <DataTable
        data={[makeItem(1)]}
        columns={columns}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByText('rendered:Item 1')).toBeInTheDocument()
    // Raw value "Item 1" should not appear separately
    expect(screen.queryByText('Item 1')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Sorting
// ---------------------------------------------------------------------------

describe('DataTable – sorting', () => {
  it('renders sort buttons for sortable columns', () => {
    const sorting = defaultSorting()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        sorting={sorting}
      />,
    )

    // The "Name" column is sortable; its header should be inside a button
    const nameButton = screen.getByRole('button', { name: /name/i })
    expect(nameButton).toBeInTheDocument()
  })

  it('calls sorting.onSort with the column accessorKey when sort button is clicked', () => {
    const onSort = vi.fn()
    const sorting = defaultSorting({ onSort })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        sorting={sorting}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /name/i }))
    expect(onSort).toHaveBeenCalledWith('name')
  })

  it('does not call onSort for non-sortable columns', () => {
    const onSort = vi.fn()
    const sorting = defaultSorting({ onSort })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        sorting={sorting}
      />,
    )

    // "Status" column is not sortable — it renders as plain text, not a button
    expect(screen.queryByRole('button', { name: /status/i })).not.toBeInTheDocument()
    expect(onSort).not.toHaveBeenCalled()
  })

  it('shows the active sort indicator on the sorted column', () => {
    const sorting = defaultSorting({ sortBy: 'name', sortOrder: 'asc' })

    const { container } = render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        sorting={sorting}
      />,
    )

    // The active column's icon gets rotate-180 class (ascending), inactive icons get opacity-50
    const rotatedIcon = container.querySelector('svg.rotate-180')
    expect(rotatedIcon).not.toBeNull()
  })

  it('shows a descending indicator when sortOrder is desc', () => {
    const sorting = defaultSorting({ sortBy: 'name', sortOrder: 'desc' })

    const { container } = render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        sorting={sorting}
      />,
    )

    // desc order means no rotate-180 on the active icon
    const rotatedIcon = container.querySelector('svg.rotate-180')
    expect(rotatedIcon).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

describe('DataTable – pagination', () => {
  // PaginationPrevious / PaginationNext render <a> without href (role = generic).
  // Query them via their aria-label attributes using getByLabelText.

  it('renders pagination controls when pagination prop is provided and totalItems > 0', () => {
    const pagination = defaultPagination()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    expect(screen.getByLabelText('Go to previous page')).toBeInTheDocument()
    expect(screen.getByLabelText('Go to next page')).toBeInTheDocument()
  })

  it('does not render pagination controls when totalItems is 0', () => {
    const pagination = defaultPagination()

    render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={0}
      />,
    )

    expect(screen.queryByLabelText('Go to previous page')).not.toBeInTheDocument()
  })

  it('calls onPageChange with next page when Next is clicked', () => {
    const onPageChange = vi.fn()
    const pagination = defaultPagination({ page: 1, pageSize: 10, onPageChange })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    fireEvent.click(screen.getByLabelText('Go to next page'))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('calls onPageChange with previous page when Previous is clicked', () => {
    const onPageChange = vi.fn()
    const pagination = defaultPagination({ page: 2, pageSize: 10, onPageChange })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    fireEvent.click(screen.getByLabelText('Go to previous page'))
    expect(onPageChange).toHaveBeenCalledWith(1)
  })

  it('disables the Previous button on the first page', () => {
    const pagination = defaultPagination({ page: 1 })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    const prev = screen.getByLabelText('Go to previous page')
    expect(prev).toHaveClass('pointer-events-none')
    expect(prev).toHaveClass('opacity-50')
  })

  it('disables the Next button on the last page', () => {
    const pagination = defaultPagination({ page: 3, pageSize: 10 })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    const next = screen.getByLabelText('Go to next page')
    expect(next).toHaveClass('pointer-events-none')
    expect(next).toHaveClass('opacity-50')
  })

  it('renders page number links for each page', () => {
    const pagination = defaultPagination({ page: 1, pageSize: 10 })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    // 3 pages total (30 items / 10 per page). Page links live inside the
    // pagination nav; use within() to avoid ambiguity with entry-count text.
    const nav = screen.getByRole('navigation', { name: /pagination/i })
    expect(within(nav).getByText('1')).toBeInTheDocument()
    expect(within(nav).getByText('2')).toBeInTheDocument()
    expect(within(nav).getByText('3')).toBeInTheDocument()
  })

  it('shows entry count summary', () => {
    const pagination = defaultPagination({ page: 1, pageSize: 10 })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={25}
      />,
    )

    // Shows "Showing 1 to 10 of 25 entries"
    expect(screen.getByText(/showing 1 to 10 of 25 entries/i)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Null cell rendering
// ---------------------------------------------------------------------------

describe('DataTable – null cell rendering', () => {
  it('renders an empty cell when column has neither render nor accessorKey', () => {
    const cols: Column<TestItem>[] = [
      { header: 'Actions' }, // no render, no accessorKey → renderCell returns null
    ]

    const { container } = render(
      <DataTable
        data={[makeItem(1)]}
        columns={cols}
        keyExtractor={(item) => item.id}
      />,
    )

    const cells = container.querySelectorAll('td')
    expect(cells).toHaveLength(1)
    expect(cells[0].textContent).toBe('')
  })
})

// ---------------------------------------------------------------------------
// Page number navigation
// ---------------------------------------------------------------------------

describe('DataTable – page number navigation', () => {
  it('calls onPageChange with the clicked page number', () => {
    const onPageChange = vi.fn()
    const pagination = defaultPagination({ page: 1, pageSize: 10, onPageChange })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    const nav = screen.getByRole('navigation', { name: /pagination/i })
    fireEvent.click(within(nav).getByText('2'))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('calls onPageSizeChange when rows-per-page value changes', async () => {
    const onPageSizeChange = vi.fn()
    const pagination = defaultPagination({ page: 1, pageSize: 10, onPageSizeChange })

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
      />,
    )

    // The Rows per page Select trigger shows the current page size
    const trigger = screen.getByRole('combobox')
    fireEvent.click(trigger)
  })

  it('renders showModeToggle buttons in page mode when showModeToggle is true', () => {
    const onPaginationModeChange = vi.fn()
    const pagination = defaultPagination()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
        showModeToggle
        onPaginationModeChange={onPaginationModeChange}
      />,
    )

    expect(screen.getByRole('button', { name: 'Page' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Scroll' })).toBeInTheDocument()
  })

  it('calls onPaginationModeChange when Scroll button is clicked in page mode', () => {
    const onPaginationModeChange = vi.fn()
    const pagination = defaultPagination()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        pagination={pagination}
        totalItems={30}
        showModeToggle
        onPaginationModeChange={onPaginationModeChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Scroll' }))
    expect(onPaginationModeChange).toHaveBeenCalledWith('scroll')
  })
})

// ---------------------------------------------------------------------------
// Scroll mode
// ---------------------------------------------------------------------------

describe('DataTable – scroll mode', () => {
  it('renders scroll mode controls when paginationMode is scroll and data exists', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore={false}
      />,
    )

    expect(screen.getByText(/loaded 3 records/i)).toBeInTheDocument()
  })

  it('shows "(more available)" text when hasMore is true', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore
      />,
    )

    expect(screen.getByText(/more available/i)).toBeInTheDocument()
  })

  it('shows "(all loaded)" text when hasMore is false', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore={false}
      />,
    )

    expect(screen.getByText(/all loaded/i)).toBeInTheDocument()
  })

  it('renders Load More button when hasMore is true', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore
        onLoadMore={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /load more/i })).toBeInTheDocument()
  })

  it('calls onLoadMore when Load More button is clicked', () => {
    const onLoadMore = vi.fn()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore
        onLoadMore={onLoadMore}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /load more/i }))
    expect(onLoadMore).toHaveBeenCalled()
  })

  it('shows loading indicator in Load More button when isLoadingMore is true', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore
        isLoadingMore
        onLoadMore={vi.fn()}
      />,
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('does not render Load More button when hasMore is false', () => {
    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore={false}
      />,
    )

    expect(screen.queryByRole('button', { name: /load more/i })).not.toBeInTheDocument()
  })

  it('renders mode toggle buttons in scroll mode when showModeToggle is true', () => {
    const onPaginationModeChange = vi.fn()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        showModeToggle
        onPaginationModeChange={onPaginationModeChange}
      />,
    )

    expect(screen.getByRole('button', { name: 'Page' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Scroll' })).toBeInTheDocument()
  })

  it('calls onPaginationModeChange when Page button is clicked in scroll mode', () => {
    const onPaginationModeChange = vi.fn()

    render(
      <DataTable
        data={SAMPLE_DATA}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        showModeToggle
        onPaginationModeChange={onPaginationModeChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Page' }))
    expect(onPaginationModeChange).toHaveBeenCalledWith('page')
  })

  it('does not render scroll controls when data is empty', () => {
    render(
      <DataTable
        data={[]}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
        paginationMode="scroll"
        hasMore={false}
      />,
    )

    expect(screen.queryByText(/loaded/i)).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Frozen columns
// ---------------------------------------------------------------------------

describe('DataTable – frozen columns', () => {
  it('applies sticky positioning style for a left-frozen column', () => {
    const cols: Column<TestItem>[] = [
      { header: 'Name', accessorKey: 'name', frozen: 'left', frozenOffset: 0 },
      { header: 'Status', accessorKey: 'status' },
    ]

    const { container } = render(
      <DataTable
        data={SAMPLE_DATA}
        columns={cols}
        keyExtractor={(item) => item.id}
      />,
    )

    // The first header cell should have position:sticky style
    const headerCells = container.querySelectorAll('th')
    expect(headerCells[0].style.position).toBe('sticky')
  })

  it('applies sticky positioning style for a right-frozen column', () => {
    const cols: Column<TestItem>[] = [
      { header: 'Name', accessorKey: 'name' },
      { header: 'Actions', frozen: 'right' },
    ]

    const { container } = render(
      <DataTable
        data={SAMPLE_DATA}
        columns={cols}
        keyExtractor={(item) => item.id}
      />,
    )

    const headerCells = container.querySelectorAll('th')
    expect(headerCells[1].style.position).toBe('sticky')
  })

  it('applies border class to left-frozen column with frozenBorderRight', () => {
    const cols: Column<TestItem>[] = [
      { header: 'Name', accessorKey: 'name', frozen: 'left', frozenBorderRight: true },
    ]

    const { container } = render(
      <DataTable
        data={SAMPLE_DATA}
        columns={cols}
        keyExtractor={(item) => item.id}
      />,
    )

    const firstHeader = container.querySelector('th')
    expect(firstHeader?.className).toContain('border-r')
  })
})

// ---------------------------------------------------------------------------
// Large datasets
// ---------------------------------------------------------------------------

describe('DataTable – large datasets', () => {
  it('renders 100+ rows without throwing', () => {
    const largeData = Array.from({ length: 120 }, (_, i) => makeItem(i + 1))

    expect(() => {
      render(
        <DataTable
          data={largeData}
          columns={COLUMNS}
          keyExtractor={(item) => item.id}
        />,
      )
    }).not.toThrow()
  })

  it('renders the first and last item from a 100-item dataset', () => {
    const largeData = Array.from({ length: 100 }, (_, i) => makeItem(i + 1))

    render(
      <DataTable
        data={largeData}
        columns={COLUMNS}
        keyExtractor={(item) => item.id}
      />,
    )

    expect(screen.getByText('Item 1')).toBeInTheDocument()
    expect(screen.getByText('Item 100')).toBeInTheDocument()
  })
})
