/**
 * Shared schema field validation for create/edit collection flows.
 */

import type { FieldDefinition } from '@/services/collections.service';

export const SYSTEM_FIELD_NAMES = [
  'id',
  'account_id',
  'created_at',
  'created_by',
  'updated_at',
  'updated_by',
] as const;

export type SchemaFieldErrorKey =
  | 'name'
  | 'type'
  | 'collection'
  | 'mask_type'
  | 'expression'
  | 'return_type'
  | 'default';

export type SchemaFieldErrors = Record<
  number,
  Partial<Record<SchemaFieldErrorKey, string>>
>;

export interface SchemaValidationResult {
  valid: boolean;
  formError?: string;
  fieldErrors: SchemaFieldErrors;
}

const SYSTEM_NAME_SET = new Set<string>(
  SYSTEM_FIELD_NAMES.map((n) => n.toLowerCase()),
);

/**
 * Validate user-defined schema fields before create/update submit.
 * Does not include system fields — callers must never put them in the payload.
 */
export function validateSchemaFields(
  fields: FieldDefinition[],
): SchemaValidationResult {
  const fieldErrors: SchemaFieldErrors = {};

  if (fields.length === 0) {
    return {
      valid: false,
      formError: 'At least one field is required',
      fieldErrors,
    };
  }

  const seenNames = new Map<string, number>();

  for (let i = 0; i < fields.length; i++) {
    const field = fields[i];
    const errors: Partial<Record<SchemaFieldErrorKey, string>> = {};

    const name = field.name?.trim() ?? '';
    if (!name) {
      errors.name = 'Field name is required';
    } else if (SYSTEM_NAME_SET.has(name.toLowerCase())) {
      errors.name = `"${name}" is a reserved system field name`;
    } else {
      const normalized = name.toLowerCase();
      if (seenNames.has(normalized)) {
        errors.name = `Duplicate field name: "${field.name}"`;
      } else {
        seenNames.set(normalized, i);
      }
    }

    if (!field.type) {
      errors.type = 'Field type is required';
    }

    if (field.type === 'reference' && !field.collection) {
      errors.collection = 'Target collection is required for reference fields';
    }

    if (field.type === 'user' && field.on_delete === 'cascade') {
      errors.on_delete = `on_delete 'cascade' is not allowed for user field '${field.name}'`;
    }

    if (field.pii && !field.mask_type) {
      errors.mask_type = 'Mask type is required when PII is enabled';
    }

    if (field.encrypted) {
      if (field.type !== 'text' && field.type !== 'json') {
        errors.type =
          'Encrypted fields are only supported for text and json types';
      }
      if (field.unique) {
        errors.type =
          'Encrypted fields cannot be unique (they are non-queryable)';
      }
    }

    if (field.type === 'computed') {
      if (!field.expression?.trim()) {
        errors.expression = 'Expression is required for computed fields';
      }
      if (!field.return_type) {
        errors.return_type = 'Return type is required for computed fields';
      }
    }

    if (Object.keys(errors).length > 0) {
      fieldErrors[i] = errors;
    }
  }

  const hasFieldErrors = Object.keys(fieldErrors).length > 0;
  let formError: string | undefined;

  if (hasFieldErrors) {
    // Prefer a stable first-message summary for form-level display
    const firstIndex = Math.min(...Object.keys(fieldErrors).map(Number));
    const firstErrors = fieldErrors[firstIndex];
    formError = firstErrors
      ? (Object.values(firstErrors)[0] as string)
      : 'Schema validation failed';
  }

  return {
    valid: !hasFieldErrors,
    formError,
    fieldErrors,
  };
}

/**
 * Normalize field list for dirty comparison (stable key order).
 */
export function normalizeSchemaForCompare(fields: FieldDefinition[]): string {
  return JSON.stringify(
    fields.map((f) => ({
      name: f.name,
      type: f.type,
      required: f.required ?? false,
      unique: f.unique ?? false,
      pii: f.pii ?? false,
      encrypted: f.encrypted ?? false,
      default: f.default ?? null,
      collection: f.collection ?? null,
      on_delete: f.on_delete ?? null,
      mask_type: f.mask_type ?? null,
      expression: f.expression ?? null,
      return_type: f.return_type ?? null,
    })),
  );
}

/**
 * Strip empty default so payload omits unused defaults.
 */
export function prepareSchemaPayload(fields: FieldDefinition[]): FieldDefinition[] {
  return fields.map((field) => {
    const next: FieldDefinition = {
      name: field.name.trim(),
      type: field.type,
      required: field.required ?? false,
      unique: field.unique ?? false,
      pii: field.pii ?? false,
      encrypted: field.encrypted ?? false,
    };

    if (field.type === 'computed') {
      if (field.expression) next.expression = field.expression;
      if (field.return_type) next.return_type = field.return_type;
      return next;
    }

    if (field.default !== undefined && field.default !== null && field.default !== '') {
      next.default = field.default;
    }
    if (field.type === 'reference') {
      if (field.collection) next.collection = field.collection;
      if (field.on_delete) next.on_delete = field.on_delete;
    }
    if (field.pii && field.mask_type) {
      next.mask_type = field.mask_type;
    }
    if (field.options) {
      next.options = field.options;
    }

    return next;
  });
}
