/**
 * Unit tests for collection starter templates.
 */

import { describe, it, expect } from 'vitest'
import {
  applyTemplate,
  BLANK_TEMPLATE_ID,
  COLLECTION_TEMPLATES,
  getTemplateById,
} from '@/lib/collectionTemplates'
import { FIELD_TYPES } from '@/services/collections.service'

const VALID_TYPES = new Set(FIELD_TYPES.map((t) => t.value))

describe('collectionTemplates', () => {
  it('exposes at least three starter templates', () => {
    expect(COLLECTION_TEMPLATES.length).toBeGreaterThanOrEqual(3)
    expect(COLLECTION_TEMPLATES.map((t) => t.id)).toEqual(
      expect.arrayContaining(['posts', 'products', 'contacts']),
    )
  })

  it('each template has suggested name and non-empty fields with valid types', () => {
    for (const template of COLLECTION_TEMPLATES) {
      expect(template.suggestedName.length).toBeGreaterThan(0)
      expect(template.fields.length).toBeGreaterThan(0)
      for (const field of template.fields) {
        expect(field.name).toBeTruthy()
        expect(VALID_TYPES.has(field.type as (typeof FIELD_TYPES)[number]['value'])).toBe(
          true,
        )
      }
    }
  })

  it('applyTemplate returns deep-cloned fields (immutable constants)', () => {
    const applied = applyTemplate('posts')
    expect(applied.templateId).toBe('posts')
    expect(applied.suggestedName).toBe('posts')
    expect(applied.fields.length).toBeGreaterThan(0)

    applied.fields[0].name = 'mutated'
    const again = applyTemplate('posts')
    expect(again.fields[0].name).toBe('title')
  })

  it('applyTemplate blank clears fields', () => {
    const applied = applyTemplate(BLANK_TEMPLATE_ID)
    expect(applied.templateId).toBe(BLANK_TEMPLATE_ID)
    expect(applied.suggestedName).toBe('')
    expect(applied.fields).toEqual([])
  })

  it('applyTemplate unknown id falls back to blank', () => {
    const applied = applyTemplate('does-not-exist')
    expect(applied.templateId).toBe(BLANK_TEMPLATE_ID)
    expect(applied.fields).toEqual([])
  })

  it('getTemplateById returns template or undefined', () => {
    expect(getTemplateById('products')?.label).toBe('Products')
    expect(getTemplateById(BLANK_TEMPLATE_ID)).toBeUndefined()
    expect(getTemplateById('nope')).toBeUndefined()
  })

  it('contacts template includes PII phone field', () => {
    const contacts = getTemplateById('contacts')
    const phone = contacts?.fields.find((f) => f.name === 'phone')
    expect(phone?.pii).toBe(true)
    expect(phone?.mask_type).toBe('phone')
  })
})
