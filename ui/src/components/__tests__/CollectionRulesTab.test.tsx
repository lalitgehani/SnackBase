/**
 * Tests for CollectionRulesTab component
 *
 * Verifies:
 * - Shows loading state while fetching rules
 * - Renders rule editors after loading
 * - Shows error state when fetch fails
 * - Renders Save Rules button
 * - Shows success message after saving
 * - Shows error message when save fails
 * - Shows public access warning when rules are empty strings
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import CollectionRulesTab from '@/components/collections/CollectionRulesTab'
import type { Collection } from '@/services/collections.service'

const collection: Collection = {
  id: 'col_abc123',
  name: 'products',
  table_name: 'products',
  schema: [
    { name: 'title', type: 'text' },
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const defaultRules = {
  id: 'rule_1',
  collection_id: 'col_abc123',
  list_rule: null,
  view_rule: null,
  create_rule: null,
  update_rule: null,
  delete_rule: null,
  list_fields: '*',
  view_fields: '*',
  create_fields: '*',
  update_fields: '*',
  created_at: '2024-01-01T00:00:00Z',
}

function setupRulesHandler(rules = defaultRules) {
  server.use(
    http.get('/api/v1/collections/:name/rules', () => HttpResponse.json(rules)),
    http.put('/api/v1/collections/:name/rules', () => HttpResponse.json(rules)),
  )
}

function setupRulesError() {
  server.use(
    http.get('/api/v1/collections/:name/rules', () =>
      HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    )
  )
}

describe('CollectionRulesTab', () => {
  beforeEach(() => {
    setupRulesHandler()
  })

  describe('loading state', () => {
    it('shows loading spinner initially', () => {
      render(<CollectionRulesTab collection={collection} />)
      expect(screen.getByText(/loading collection rules/i)).toBeInTheDocument()
    })
  })

  describe('after loading', () => {
    it('renders Access Rules heading', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.getByText('Access Rules')).toBeInTheDocument()
      })
    })

    it('renders Save Rules button', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save rules/i })).toBeInTheDocument()
      })
    })

    it('renders rule editor labels', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.getByText('List Rule')).toBeInTheDocument()
        expect(screen.getByText('View Rule')).toBeInTheDocument()
        expect(screen.getByText('Create Rule')).toBeInTheDocument()
        expect(screen.getByText('Update Rule')).toBeInTheDocument()
        expect(screen.getByText('Delete Rule')).toBeInTheDocument()
      })
    })

    it('renders field permission selectors', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.getByText('List Fields')).toBeInTheDocument()
        expect(screen.getByText('View Fields')).toBeInTheDocument()
      })
    })
  })

  describe('public access warning', () => {
    it('shows public access warning when rules are empty strings', async () => {
      setupRulesHandler({ ...defaultRules, list_rule: '', view_rule: '' })
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.getByText(/public access enabled/i)).toBeInTheDocument()
      })
    })

    it('does not show warning when all rules are null', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.queryByText(/public access enabled/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('save rules', () => {
    it('shows success message after saving', async () => {
      const user = userEvent.setup()
      render(<CollectionRulesTab collection={collection} />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save rules/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /save rules/i }))

      await waitFor(() => {
        expect(screen.getByText(/rules saved successfully/i)).toBeInTheDocument()
      })
    })

    it('shows error when save fails', async () => {
      const user = userEvent.setup()
      server.use(
        http.put('/api/v1/collections/:name/rules', () =>
          HttpResponse.json({ detail: 'Save failed' }, { status: 500 })
        )
      )
      render(<CollectionRulesTab collection={collection} />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save rules/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /save rules/i }))

      await waitFor(() => {
        expect(screen.getByText('Save failed')).toBeInTheDocument()
      })
    })
  })

  describe('error state', () => {
    it('shows error message when fetch fails', async () => {
      setupRulesError()
      render(<CollectionRulesTab collection={collection} />)

      await waitFor(() => {
        expect(screen.getByText(/failed to load rules/i)).toBeInTheDocument()
      })
    })

    it('shows Try Again button on error', async () => {
      setupRulesError()
      render(<CollectionRulesTab collection={collection} />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      })
    })
  })
})
