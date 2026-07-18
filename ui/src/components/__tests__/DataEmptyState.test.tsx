/**
 * Tests for DataEmptyState variants and CTAs (Phase 4)
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import DataEmptyState from '@/components/records/DataEmptyState'

describe('DataEmptyState', () => {
  describe('no-schema', () => {
    it('renders no-schema messaging and Open Schema CTA', async () => {
      const user = userEvent.setup()
      const onOpenSchema = vi.fn()
      render(
        <DataEmptyState
          variant="no-schema"
          collectionName="posts"
          onOpenSchema={onOpenSchema}
        />,
      )

      expect(screen.getByTestId('data-empty-no-schema')).toBeInTheDocument()
      expect(screen.getByText(/no schema defined/i)).toBeInTheDocument()
      await user.click(screen.getByTestId('data-empty-open-schema'))
      expect(onOpenSchema).toHaveBeenCalled()
    })
  })

  describe('filtered', () => {
    it('offers Clear Filters and does not mention rules', async () => {
      const user = userEvent.setup()
      const onClearFilters = vi.fn()
      render(
        <DataEmptyState
          variant="filtered"
          collectionName="posts"
          onClearFilters={onClearFilters}
        />,
      )

      expect(screen.getByTestId('data-empty-filtered')).toBeInTheDocument()
      expect(screen.getByText(/no records match your filters/i)).toBeInTheDocument()
      expect(screen.queryByText(/access rules/i)).not.toBeInTheDocument()
      await user.click(screen.getByTestId('data-empty-clear-filters'))
      expect(onClearFilters).toHaveBeenCalled()
    })
  })

  describe('search', () => {
    it('offers Clear Search', async () => {
      const user = userEvent.setup()
      const onClearSearch = vi.fn()
      render(
        <DataEmptyState
          variant="search"
          collectionName="posts"
          onClearSearch={onClearSearch}
          onCreateRecord={vi.fn()}
        />,
      )

      expect(screen.getByTestId('data-empty-search')).toBeInTheDocument()
      await user.click(screen.getByTestId('data-empty-clear-search'))
      expect(onClearSearch).toHaveBeenCalled()
    })
  })

  describe('no-records', () => {
    it('offers Create Record, Open Schema, and soft Rules link', async () => {
      const user = userEvent.setup()
      const onCreateRecord = vi.fn()
      const onOpenSchema = vi.fn()
      const onOpenRules = vi.fn()
      render(
        <DataEmptyState
          variant="no-records"
          collectionName="posts"
          onCreateRecord={onCreateRecord}
          onOpenSchema={onOpenSchema}
          onOpenRules={onOpenRules}
        />,
      )

      expect(screen.getByTestId('data-empty-no-records')).toBeInTheDocument()
      expect(screen.getByText(/no records yet/i)).toBeInTheDocument()

      await user.click(screen.getByTestId('data-empty-create-record'))
      expect(onCreateRecord).toHaveBeenCalled()

      await user.click(screen.getByTestId('data-empty-open-schema'))
      expect(onOpenSchema).toHaveBeenCalled()

      await user.click(screen.getByTestId('data-empty-open-rules'))
      expect(onOpenRules).toHaveBeenCalled()
    })
  })
})
