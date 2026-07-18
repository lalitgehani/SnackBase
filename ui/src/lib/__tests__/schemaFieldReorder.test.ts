/**
 * Unit tests for schema field reorder helpers.
 */

import { describe, it, expect } from 'vitest'
import type { FieldDefinition } from '@/services/collections.service'
import {
  canMoveField,
  moveFieldByDirection,
  remapExpandedAfterReorder,
  remapExpandedAfterSwap,
  reorderFields,
} from '@/lib/schemaFieldReorder'

function f(name: string): FieldDefinition {
  return { name, type: 'text', required: false, unique: false, pii: false }
}

describe('schemaFieldReorder', () => {
  describe('canMoveField', () => {
    it('allows free reorder in create mode', () => {
      expect(canMoveField(3, 0, 'down', 0)).toBe(true)
      expect(canMoveField(3, 0, 'up', 0)).toBe(false)
      expect(canMoveField(3, 2, 'down', 0)).toBe(false)
    })

    it('blocks moving existing fields in edit mode', () => {
      // 2 existing, 1 new
      expect(canMoveField(3, 0, 'down', 2)).toBe(false)
      expect(canMoveField(3, 1, 'up', 2)).toBe(false)
      expect(canMoveField(3, 2, 'up', 2)).toBe(false) // would swap with existing
    })

    it('allows reordering among new fields only', () => {
      // 1 existing, 2 new
      expect(canMoveField(3, 1, 'down', 1)).toBe(true)
      expect(canMoveField(3, 2, 'up', 1)).toBe(true)
    })
  })

  describe('moveFieldByDirection', () => {
    it('swaps adjacent fields', () => {
      const fields = [f('a'), f('b'), f('c')]
      const next = moveFieldByDirection(fields, 0, 'down', 0)
      expect(next.map((x) => x.name)).toEqual(['b', 'a', 'c'])
    })

    it('returns same reference when blocked', () => {
      const fields = [f('a'), f('b')]
      expect(moveFieldByDirection(fields, 0, 'up', 0)).toBe(fields)
      expect(moveFieldByDirection(fields, 0, 'down', 1)).toBe(fields)
    })
  })

  describe('reorderFields', () => {
    it('moves item from fromIndex to toIndex', () => {
      const fields = [f('a'), f('b'), f('c'), f('d')]
      const next = reorderFields(fields, 0, 2, 0)
      expect(next.map((x) => x.name)).toEqual(['b', 'c', 'a', 'd'])
    })

    it('blocks reorder into existing range in edit mode', () => {
      const fields = [f('locked1'), f('locked2'), f('new1'), f('new2')]
      expect(reorderFields(fields, 2, 0, 2)).toBe(fields)
      expect(reorderFields(fields, 0, 2, 2)).toBe(fields)
    })

    it('allows reorder among new fields in edit mode', () => {
      const fields = [f('locked1'), f('new1'), f('new2')]
      const next = reorderFields(fields, 1, 2, 1)
      expect(next.map((x) => x.name)).toEqual(['locked1', 'new2', 'new1'])
    })

    it('returns same reference for no-op', () => {
      const fields = [f('a'), f('b')]
      expect(reorderFields(fields, 1, 1, 0)).toBe(fields)
    })
  })

  describe('remap expanded sets', () => {
    it('remapExpandedAfterSwap swaps membership', () => {
      const expanded = new Set([0, 2])
      const next = remapExpandedAfterSwap(expanded, 0, 1)
      expect(next.has(0)).toBe(false)
      expect(next.has(1)).toBe(true)
      expect(next.has(2)).toBe(true)
    })

    it('remapExpandedAfterReorder updates indices after splice move', () => {
      // move index 0 -> 2; expanded was {0, 1}
      const next = remapExpandedAfterReorder(new Set([0, 1]), 0, 2)
      expect([...next].sort()).toEqual([0, 2])
    })
  })
})
