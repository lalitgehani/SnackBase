/**
 * Client-side collection starter templates for the create flow.
 * No backend dependency — templates pre-fill name suggestion + schema fields.
 */

import type { FieldDefinition } from '@/services/collections.service';

export const BLANK_TEMPLATE_ID = 'blank' as const;

export interface CollectionTemplate {
  id: string;
  label: string;
  description: string;
  suggestedName: string;
  fields: FieldDefinition[];
}

function field(overrides: FieldDefinition): FieldDefinition {
  return {
    required: false,
    unique: false,
    pii: false,
    ...overrides,
  };
}

/** Starter templates available on create empty state and /new. */
export const COLLECTION_TEMPLATES: CollectionTemplate[] = [
  {
    id: 'posts',
    label: 'Posts',
    description: 'Blog posts or articles with status and publish date',
    suggestedName: 'posts',
    fields: [
      field({ name: 'title', type: 'text', required: true }),
      field({ name: 'slug', type: 'text', unique: true }),
      field({ name: 'body', type: 'text' }),
      field({ name: 'status', type: 'text', default: 'draft' }),
      field({ name: 'published_at', type: 'datetime' }),
    ],
  },
  {
    id: 'products',
    label: 'Products',
    description: 'Catalog items with SKU, price, and active flag',
    suggestedName: 'products',
    fields: [
      field({ name: 'name', type: 'text', required: true }),
      field({ name: 'sku', type: 'text', unique: true }),
      field({ name: 'price', type: 'number', required: true }),
      field({ name: 'description', type: 'text' }),
      field({ name: 'is_active', type: 'boolean', default: true }),
    ],
  },
  {
    id: 'contacts',
    label: 'Contacts',
    description: 'People with email, phone (PII), and company',
    suggestedName: 'contacts',
    fields: [
      field({ name: 'full_name', type: 'text', required: true }),
      field({ name: 'email', type: 'email', unique: true }),
      field({ name: 'phone', type: 'text', pii: true, mask_type: 'phone' }),
      field({ name: 'company', type: 'text' }),
      field({ name: 'notes', type: 'text' }),
    ],
  },
];

export function getTemplateById(id: string): CollectionTemplate | undefined {
  if (id === BLANK_TEMPLATE_ID) return undefined;
  return COLLECTION_TEMPLATES.find((t) => t.id === id);
}

/**
 * Apply a template (or blank). Returns deep-cloned fields so edits do not
 * mutate template constants.
 */
export function applyTemplate(id: string): {
  templateId: string;
  suggestedName: string;
  fields: FieldDefinition[];
} {
  if (id === BLANK_TEMPLATE_ID) {
    return { templateId: BLANK_TEMPLATE_ID, suggestedName: '', fields: [] };
  }

  const template = getTemplateById(id);
  if (!template) {
    return { templateId: BLANK_TEMPLATE_ID, suggestedName: '', fields: [] };
  }

  return {
    templateId: template.id,
    suggestedName: template.suggestedName,
    fields: template.fields.map((f) => ({ ...f })),
  };
}
