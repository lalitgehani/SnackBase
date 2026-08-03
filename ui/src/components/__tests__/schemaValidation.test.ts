/**
 * Tests for schema field validation helper.
 */

import { describe, it, expect } from 'vitest'
import {
  validateSchemaFields,
  prepareSchemaPayload,
  normalizeSchemaForCompare,
} from '@/components/collections/schemaValidation'
import type { FieldDefinition } from '@/services/collections.service'

function field(overrides: Partial<FieldDefinition> = {}): FieldDefinition {
  return {
    name: 'title',
    type: 'text',
    required: false,
    unique: false,
    pii: false,
    ...overrides,
  }
}

describe('validateSchemaFields', () => {
  it('fails when no fields', () => {
    const result = validateSchemaFields([])
    expect(result.valid).toBe(false)
    expect(result.formError).toMatch(/at least one field/i)
  })

  it('passes for a simple valid field', () => {
    const result = validateSchemaFields([field()])
    expect(result.valid).toBe(true)
    expect(result.formError).toBeUndefined()
  })

  it('requires field name', () => {
    const result = validateSchemaFields([field({ name: '  ' })])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[0]?.name).toMatch(/required/i)
  })

  it('rejects duplicate names case-insensitively', () => {
    const result = validateSchemaFields([
      field({ name: 'Email' }),
      field({ name: 'email' }),
    ])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[1]?.name).toMatch(/duplicate/i)
  })

  it('rejects reserved system field names', () => {
    const result = validateSchemaFields([field({ name: 'account_id' })])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[0]?.name).toMatch(/reserved/i)
  })

  it('requires target collection for reference fields', () => {
    const result = validateSchemaFields([
      field({ name: 'user_id', type: 'reference' }),
    ])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[0]?.collection).toBeTruthy()
  })

  it('requires mask type when PII is enabled', () => {
    const result = validateSchemaFields([
      field({ name: 'ssn', pii: true }),
    ])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[0]?.mask_type).toBeTruthy()
  })

  it('requires expression and return_type for computed fields', () => {
    const result = validateSchemaFields([
      field({ name: 'full_name', type: 'computed' }),
    ])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[0]?.expression).toBeTruthy()
    expect(result.fieldErrors[0]?.return_type).toBeTruthy()
  })

  it('accepts valid computed and reference fields', () => {
    const result = validateSchemaFields([
      field({
        name: 'user_id',
        type: 'reference',
        collection: 'users',
        on_delete: 'restrict',
      }),
      field({
        name: 'full_name',
        type: 'computed',
        expression: "concat(first, ' ', last)",
        return_type: 'text',
      }),
      field({ name: 'email', pii: true, mask_type: 'email' }),
    ])
    expect(result.valid).toBe(true)
  })

  it('accepts encrypted text and json fields', () => {
    const result = validateSchemaFields([
      field({ name: 'api_token', type: 'text', encrypted: true }),
      field({ name: 'creds', type: 'json', encrypted: true }),
    ])
    expect(result.valid).toBe(true)
  })

  it('rejects encrypted fields on unsupported types', () => {
    const result = validateSchemaFields([
      field({ name: 'secret_num', type: 'number', encrypted: true }),
    ])
    expect(result.valid).toBe(false)
    expect(result.fieldErrors[0]?.type).toMatch(/text and json/i)
  })

  it('rejects encrypted unique fields', () => {
    const result = validateSchemaFields([
      field({ name: 'token', type: 'text', encrypted: true, unique: true }),
    ])
    expect(result.valid).toBe(false)
  })
})

describe('prepareSchemaPayload', () => {
  it('omits empty default and trims names', () => {
    const payload = prepareSchemaPayload([
      field({ name: '  title  ', default: '' }),
    ])
    expect(payload[0].name).toBe('title')
    expect(payload[0].default).toBeUndefined()
  })

  it('keeps computed expression without required/unique', () => {
    const payload = prepareSchemaPayload([
      field({
        name: 'total',
        type: 'computed',
        expression: 'a + b',
        return_type: 'number',
        required: true,
      }),
    ])
    expect(payload[0]).toMatchObject({
      name: 'total',
      type: 'computed',
      expression: 'a + b',
      return_type: 'number',
    })
  })
})

describe('normalizeSchemaForCompare', () => {
  it('treats equivalent schemas as equal', () => {
    const a = [field({ required: false })]
    const b = [field()]
    expect(normalizeSchemaForCompare(a)).toBe(normalizeSchemaForCompare(b))
  })

  it('detects changes', () => {
    const a = [field({ name: 'a' })]
    const b = [field({ name: 'b' })]
    expect(normalizeSchemaForCompare(a)).not.toBe(normalizeSchemaForCompare(b))
  })
})
