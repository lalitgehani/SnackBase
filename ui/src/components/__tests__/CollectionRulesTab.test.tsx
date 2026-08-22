/**
 * Tests for CollectionRulesTab (Phase 3 first-class Rules tab)
 *
 * Verifies:
 * - Loading / error states
 * - Access education copy (multi-tenant, no Postgres RLS toggle)
 * - Public / locked status strip
 * - Dirty bar, discard, save success/failure
 * - readOnly superadmin-only message
 * - onRulesSaved callback after save
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
  schema: [{ name: 'title', type: 'text' }],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const defaultRules = {
  id: 'rule_1',
  collection_id: 'col_abc123',
  list_rule: null as string | null,
  view_rule: null as string | null,
  create_rule: null as string | null,
  update_rule: null as string | null,
  delete_rule: null as string | null,
  list_fields: '*',
  view_fields: '*',
  create_fields: '*',
  update_fields: '*',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function setupRulesHandler(rules = defaultRules) {
  server.use(
    http.get('*/api/v1/collections/:name/rules', () => HttpResponse.json(rules)),
    http.put('*/api/v1/collections/:name/rules', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>
      return HttpResponse.json({ ...rules, ...body })
    }),
  )
}

function setupRulesError() {
  server.use(
    http.get('*/api/v1/collections/:name/rules', () =>
      HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
    ),
  )
}

async function waitForRulesLoaded() {
  await waitFor(() => {
    expect(screen.getByText('Access Rules')).toBeInTheDocument()
  })
}

/** Open List rule as Public to dirty the form. */
async function makeListRulePublic(user: ReturnType<typeof userEvent.setup>) {
  await waitForRulesLoaded()
  // RuleEditor renders multiple "Public" buttons (one per op). First is List.
  const publicButtons = screen.getAllByRole('button', { name: /^public$/i })
  await user.click(publicButtons[0])
  await waitFor(() => {
    expect(screen.getByTestId('rules-dirty-bar')).toBeInTheDocument()
  })
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
      await waitForRulesLoaded()
    })

    it('renders multi-tenant access education', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitForRulesLoaded()
      const education = screen.getByTestId('rules-access-education')
      expect(education).toHaveTextContent(/account_id/i)
      expect(education).toHaveTextContent(/Locked/i)
      expect(education).toHaveTextContent(/Public/i)
      expect(education).toHaveTextContent(/Custom/i)
      expect(education).toHaveTextContent(/403/i)
      expect(education).not.toHaveTextContent(/Enable RLS/i)
    })

    it('does not use Postgres RLS card title', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitForRulesLoaded()
      expect(screen.getByText('Access rules by operation')).toBeInTheDocument()
      expect(screen.queryByText(/Row-Level Security \(RLS\)/i)).not.toBeInTheDocument()
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

    it('shows locked status strip when all rules are null', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitForRulesLoaded()
      const strip = screen.getByTestId('rules-status-strip')
      expect(strip).toHaveTextContent(/Locked: List, View, Create, Update, Delete/i)
    })
  })

  describe('public access warning', () => {
    it('shows public access warning when rules are empty strings', async () => {
      setupRulesHandler({ ...defaultRules, list_rule: '', view_rule: '' })
      render(<CollectionRulesTab collection={collection} />)
      await waitFor(() => {
        expect(screen.getByText(/public access enabled/i)).toBeInTheDocument()
      })
      expect(screen.getByTestId('rules-status-strip')).toHaveTextContent(
        /Public: List, View/i,
      )
    })

    it('does not show public warning when all rules are null', async () => {
      render(<CollectionRulesTab collection={collection} />)
      await waitForRulesLoaded()
      expect(screen.queryByText(/public access enabled/i)).not.toBeInTheDocument()
    })
  })

  describe('dirty state and save', () => {
    it('shows dirty bar after changing a rule', async () => {
      const user = userEvent.setup()
      render(<CollectionRulesTab collection={collection} />)
      await makeListRulePublic(user)
      expect(screen.getByText(/unsaved rule changes/i)).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /save rules/i }),
      ).toBeInTheDocument()
    })

    it('discards draft changes', async () => {
      const user = userEvent.setup()
      render(<CollectionRulesTab collection={collection} />)
      await makeListRulePublic(user)

      await user.click(screen.getByRole('button', { name: /discard/i }))

      await waitFor(() => {
        expect(screen.queryByTestId('rules-dirty-bar')).not.toBeInTheDocument()
      })
      expect(screen.queryByText(/public access enabled/i)).not.toBeInTheDocument()
    })

    it('saves rules and clears dirty bar', async () => {
      const user = userEvent.setup()
      const onRulesSaved = vi.fn()
      render(
        <CollectionRulesTab
          collection={collection}
          onRulesSaved={onRulesSaved}
        />,
      )
      await makeListRulePublic(user)

      await user.click(screen.getByRole('button', { name: /save rules/i }))

      await waitFor(() => {
        expect(screen.queryByTestId('rules-dirty-bar')).not.toBeInTheDocument()
      })
      expect(onRulesSaved).toHaveBeenCalled()
    })

    it('shows error when save fails and keeps dirty state', async () => {
      const user = userEvent.setup()
      server.use(
        http.get('*/api/v1/collections/:name/rules', () =>
          HttpResponse.json(defaultRules),
        ),
        http.put('*/api/v1/collections/:name/rules', () =>
          HttpResponse.json({ detail: 'Save failed' }, { status: 500 }),
        ),
      )
      render(<CollectionRulesTab collection={collection} />)
      await makeListRulePublic(user)

      await user.click(screen.getByRole('button', { name: /save rules/i }))

      await waitFor(() => {
        expect(screen.getByText('Save failed')).toBeInTheDocument()
      })
      expect(screen.getByTestId('rules-dirty-bar')).toBeInTheDocument()
    })
  })

  describe('readOnly', () => {
    it('shows superadmin-only message without fetching editors', async () => {
      render(
        <CollectionRulesTab collection={collection} readOnly hasPublicAccess />,
      )
      expect(screen.getByTestId('rules-readonly')).toBeInTheDocument()
      expect(screen.getByTestId('rules-superadmin-only')).toBeInTheDocument()
      expect(screen.getByText(/managed by superadmins/i)).toBeInTheDocument()
      expect(screen.getByText(/public access enabled/i)).toBeInTheDocument()
      expect(screen.queryByText(/loading collection rules/i)).not.toBeInTheDocument()
      expect(screen.queryByText('List Rule')).not.toBeInTheDocument()
      expect(
        screen.queryByRole('button', { name: /save rules/i }),
      ).not.toBeInTheDocument()
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
