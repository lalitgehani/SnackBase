/**
 * Collections API service
 * Handles API calls for collection management
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface FieldDefinition {
  name: string;
  type: string;
  required?: boolean;
  default?: unknown;
  unique?: boolean;
  options?: Record<string, unknown>;
  collection?: string;
  on_delete?: string;
  pii?: boolean;
  mask_type?: string;
  /** Server-only encryption; text/json only; non-queryable. */
  encrypted?: boolean;
  expression?: string;
  return_type?: string;
}

export interface Collection {
  id: string;
  name: string;
  table_name: string;
  schema: FieldDefinition[];
  created_at: string;
  updated_at: string;
}

export interface CollectionListItem {
  id: string;
  name: string;
  table_name: string;
  fields_count: number;
  records_count: number;
  has_public_access: boolean;
  created_at: string;
}

export interface CollectionListResponse {
  items: CollectionListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateCollectionData {
  name: string;
  schema: FieldDefinition[];
}

export interface UpdateCollectionData {
  schema: FieldDefinition[];
}

export interface CollectionRule {
  id: string;
  collection_id: string;
  list_rule: string | null;
  view_rule: string | null;
  create_rule: string | null;
  update_rule: string | null;
  delete_rule: string | null;
  list_fields: string;
  view_fields: string;
  create_fields: string;
  update_fields: string;
  created_at: string;
  updated_at: string;
}

export interface UpdateCollectionRulesData {
  list_rule?: string | null;
  view_rule?: string | null;
  create_rule?: string | null;
  update_rule?: string | null;
  delete_rule?: string | null;
  list_fields?: string;
  view_fields?: string;
  create_fields?: string;
  update_fields?: string;
}

export interface GetCollectionsParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

export interface CollectionExportRules {
  list_rule: string | null;
  view_rule: string | null;
  create_rule: string | null;
  update_rule: string | null;
  delete_rule: string | null;
  list_fields: string;
  view_fields: string;
  create_fields: string;
  update_fields: string;
}

export interface CollectionExportItem {
  name: string;
  schema: FieldDefinition[];
  rules: CollectionExportRules;
}

export interface CollectionExportData {
  version: string;
  exported_at: string;
  exported_by: string;
  collections: CollectionExportItem[];
}

export type ImportStrategy = 'error' | 'skip' | 'update';

export interface CollectionImportRequest {
  data: CollectionExportData;
  strategy: ImportStrategy;
  generate_migrations: boolean;
}

export interface CollectionImportItemResult {
  name: string;
  status: 'imported' | 'skipped' | 'updated' | 'error';
  message: string;
}

export interface CollectionImportResult {
  success: boolean;
  imported_count: number;
  skipped_count: number;
  updated_count: number;
  failed_count: number;
  collections: CollectionImportItemResult[];
  migrations_created: string[];
}

function toUiCollection(raw: Record<string, unknown>): Collection {
  const schema = (raw.schema ?? raw.fields ?? []) as FieldDefinition[];
  return {
    id: raw.id as string,
    name: raw.name as string,
    table_name: (raw.table_name as string) ?? (raw.name as string),
    schema,
    created_at: raw.created_at as string,
    updated_at: raw.updated_at as string,
  };
}

function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export function createCollectionsService(client: SnackBaseClient) {
  return {
    getCollections: (params: GetCollectionsParams = {}) =>
      client.collections.listPaginated(params) as Promise<CollectionListResponse>,

    getCollectionById: async (collectionId: string): Promise<Collection> => {
      const raw = await client.collections.get(collectionId);
      return toUiCollection(raw as unknown as Record<string, unknown>);
    },

    getCollectionByName: async (collectionName: string): Promise<Collection> => {
      const list = await client.collections.listPaginated({ search: collectionName });
      const collection = list.items.find((c) => c.name === collectionName);
      if (!collection) {
        throw new Error(`Collection '${collectionName}' not found`);
      }
      const raw = await client.collections.get(collection.id);
      return toUiCollection(raw as unknown as Record<string, unknown>);
    },

    createCollection: async (data: CreateCollectionData): Promise<Collection> => {
      const raw = await client.collections.create({ name: data.name, fields: data.schema });
      return toUiCollection(raw as unknown as Record<string, unknown>);
    },

    updateCollection: async (collectionId: string, data: UpdateCollectionData): Promise<Collection> => {
      const raw = await client.collections.update(collectionId, { fields: data.schema });
      return toUiCollection(raw as unknown as Record<string, unknown>);
    },

    deleteCollection: async (collectionId: string): Promise<void> => {
      await client.collections.delete(collectionId);
    },

    getCollectionRules: (collectionName: string) =>
      client.collectionRules.get(collectionName) as Promise<CollectionRule>,

    updateCollectionRules: (collectionName: string, data: UpdateCollectionRulesData) =>
      client.collectionRules.update(collectionName, data) as Promise<CollectionRule>,

    exportCollections: async (collectionIds?: string[]): Promise<void> => {
      const data = await client.collections.export(
        collectionIds?.length ? { collection_ids: collectionIds } : undefined,
      );
      const filename = `collections_export_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.json`;
      downloadJson(data, filename);
    },

    importCollections: (
      data: CollectionExportData,
      strategy: ImportStrategy = 'error',
    ): Promise<CollectionImportResult> =>
      client.collections.import({ data, strategy, generate_migrations: true }),
  };
}

export const useCollectionsService = createServiceHook(createCollectionsService);

const collectionsService = bindService(createCollectionsService);
export const getCollections = collectionsService.getCollections;
export const getCollectionById = collectionsService.getCollectionById;
export const getCollectionByName = collectionsService.getCollectionByName;
export const createCollection = collectionsService.createCollection;
export const updateCollection = collectionsService.updateCollection;
export const deleteCollection = collectionsService.deleteCollection;
export const getCollectionRules = collectionsService.getCollectionRules;
export const updateCollectionRules = collectionsService.updateCollectionRules;
export const exportCollections = collectionsService.exportCollections;
export const importCollections = collectionsService.importCollections;

export const FIELD_TYPES = [
  { value: 'boolean', label: 'Boolean' },
  { value: 'computed', label: 'Computed' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'DateTime' },
  { value: 'email', label: 'Email' },
  { value: 'file', label: 'File' },
  { value: 'json', label: 'JSON' },
  { value: 'number', label: 'Number' },
  { value: 'reference', label: 'Reference' },
  { value: 'text', label: 'Text' },
  { value: 'url', label: 'URL' },
] as const;

export const ON_DELETE_OPTIONS = [
  { value: 'cascade', label: 'Cascade' },
  { value: 'set_null', label: 'Set Null' },
  { value: 'restrict', label: 'Restrict' },
] as const;

export const MASK_TYPE_OPTIONS = [
  { value: 'email', label: 'Email' },
  { value: 'ssn', label: 'SSN' },
  { value: 'phone', label: 'Phone' },
  { value: 'name', label: 'Name' },
  { value: 'full', label: 'Full' },
  { value: 'custom', label: 'Custom' },
] as const;

export const RETURN_TYPE_OPTIONS = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'datetime', label: 'DateTime' },
] as const;

export const IMPORT_STRATEGY_OPTIONS = [
  {
    value: 'error' as ImportStrategy,
    label: 'Error on Conflict',
    description: 'Fail if any collection already exists (safest)',
  },
  {
    value: 'skip' as ImportStrategy,
    label: 'Skip Existing',
    description: 'Skip existing collections, import only new ones',
  },
  {
    value: 'update' as ImportStrategy,
    label: 'Update Existing',
    description: 'Update existing collections with new schema (add fields only)',
  },
] as const;
