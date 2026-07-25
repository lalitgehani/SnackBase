/**
 * Types for SnackBase codelists API
 */

export type CodelistScope = 'system' | 'account';
export type OverrideVisibility = 'visible' | 'hidden';

export interface Codelist {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  definition?: string | null;
  scope: CodelistScope;
  account_id: string;
  is_system: boolean;
  is_extensible: boolean;
  is_active: boolean;
  is_builtin: boolean;
  external_code?: string | null;
  version?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CodelistCreate {
  code: string;
  name: string;
  description?: string | null;
  definition?: string | null;
  scope?: CodelistScope;
  is_extensible?: boolean;
  is_active?: boolean;
  external_code?: string | null;
  version?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface CodelistUpdate {
  name?: string;
  description?: string | null;
  definition?: string | null;
  is_extensible?: boolean;
  is_active?: boolean;
  external_code?: string | null;
  version?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface CodelistLabel {
  id?: string;
  value_id?: string;
  language: string;
  label: string;
  description?: string | null;
  is_preferred?: boolean;
}

export interface CodelistValue {
  id: string;
  codelist_id: string;
  code: string;
  external_code?: string | null;
  sort_order: number;
  is_active: boolean;
  scope: CodelistScope;
  account_id: string;
  is_system: boolean;
  definition?: string | null;
  metadata?: Record<string, unknown> | null;
  labels?: CodelistLabel[];
}

export interface CodelistValueCreate {
  code: string;
  definition?: string | null;
  sort_order?: number;
  is_active?: boolean;
  external_code?: string | null;
  metadata?: Record<string, unknown> | null;
  labels?: Array<{
    language: string;
    label: string;
    description?: string | null;
    is_preferred?: boolean;
  }>;
}

export interface CodelistValueUpdate {
  definition?: string | null;
  sort_order?: number;
  is_active?: boolean;
  external_code?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface EffectiveCodelistValue {
  code: string;
  label: string;
  definition?: string | null;
  metadata?: Record<string, unknown> | null;
  is_default: boolean;
  sort_order: number;
  scope: string;
  is_active: boolean;
  value_id?: string | null;
}

export interface CodelistOverride {
  id: string;
  account_id: string;
  codelist_id: string;
  value_id: string;
  visibility: OverrideVisibility;
  is_default: boolean;
  sort_order?: number | null;
  metadata_override?: Record<string, unknown> | null;
}

export interface OverridePayload {
  visibility?: OverrideVisibility;
  is_default?: boolean;
  sort_order?: number | null;
  metadata_override?: Record<string, unknown> | null;
}
