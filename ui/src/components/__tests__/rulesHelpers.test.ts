/**
 * Unit tests for rulesHelpers (Phase 3)
 */

import { describe, it, expect } from 'vitest'
import {
  getCustomOperations,
  getLockedOperations,
  getPublicOperations,
  isRulesDirty,
  normalizeRulesForCompare,
  toRulesSnapshot,
  type RulesSnapshot,
} from '@/components/collections/rulesHelpers'

const locked: RulesSnapshot = {
  list_rule: null,
  view_rule: null,
  create_rule: null,
  update_rule: null,
  delete_rule: null,
  list_fields: '*',
  view_fields: '*',
  create_fields: '*',
  update_fields: '*',
}

describe('rulesHelpers', () => {
  it('toRulesSnapshot picks rule fields only', () => {
    const snap = toRulesSnapshot({
      ...locked,
      list_rule: '',
      // extra fields should be ignored by Pick usage in real CollectionRule
    })
    expect(snap.list_rule).toBe('')
    expect(snap.list_fields).toBe('*')
  })

  it('detects dirty when a rule changes', () => {
    const draft = { ...locked, list_rule: '' }
    expect(isRulesDirty(draft, locked)).toBe(true)
    expect(isRulesDirty(locked, locked)).toBe(false)
  })

  it('normalize is stable for same values', () => {
    expect(normalizeRulesForCompare(locked)).toBe(
      normalizeRulesForCompare({ ...locked }),
    )
  })

  it('classifies public / locked / custom ops', () => {
    const mixed: RulesSnapshot = {
      ...locked,
      list_rule: '',
      view_rule: 'created_by = @request.auth.id',
      create_rule: null,
    }
    expect(getPublicOperations(mixed)).toEqual(['List'])
    expect(getCustomOperations(mixed)).toEqual(['View'])
    expect(getLockedOperations(mixed)).toEqual(['Create', 'Update', 'Delete'])
  })
})
