/**
 * Collections API service
 * Handles API calls for collection management
 */

import { apiClient } from '@/lib/api';

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

/**
 * Get list of collections with pagination and search
 */
export const getCollections = async (params: GetCollectionsParams = {}): Promise<CollectionListResponse> => {
  const response = await apiClient.get<CollectionListResponse>('/collections', { params });
  return response.data;
};

/**
 * Get collection by ID
 */
export const getCollectionById = async (collectionId: string): Promise<Collection> => {
  const response = await apiClient.get<Collection>(`/collections/${collectionId}`);
  return response.data;
};

/**
 * Get collection by name
 */
export const getCollectionByName = async (collectionName: string): Promise<Collection> => {
  const response = await apiClient.get<CollectionListResponse>('/collections', {
    params: { search: collectionName }
  });
  // Find exact match from results
  const collection = response.data.items.find((c: CollectionListItem) => c.name === collectionName);
  if (!collection) {
    throw new Error(`Collection '${collectionName}' not found`);
  }
  // Need to fetch full schema using getCollectionById
  return getCollectionById(collection.id);
};

/**
 * Create a new collection
 */
export const createCollection = async (data: CreateCollectionData): Promise<Collection> => {
  const response = await apiClient.post<Collection>('/collections', data);
  return response.data;
};

/**
 * Update a collection schema
 */
export const updateCollection = async (
  collectionId: string,
  data: UpdateCollectionData
): Promise<Collection> => {
  const response = await apiClient.put<Collection>(`/collections/${collectionId}`, data);
  return response.data;
};

/**
 * Delete a collection
 */
export const deleteCollection = async (collectionId: string): Promise<void> => {
  await apiClient.delete(`/collections/${collectionId}`);
};

/**
 * Get collection rules by collection name
 */
export const getCollectionRules = async (collectionName: string): Promise<CollectionRule> => {
  const response = await apiClient.get<CollectionRule>(`/collections/${collectionName}/rules`);
  return response.data;
};

/**
 * Update collection rules by collection name
 */
export const updateCollectionRules = async (
  collectionName: string,
  data: UpdateCollectionRulesData
): Promise<CollectionRule> => {
  const response = await apiClient.put<CollectionRule>(`/collections/${collectionName}/rules`, data);
  return response.data;
};

// ============================================================================
// Collection Export/Import Types and Functions
// ============================================================================

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

/**
 * Export collections to JSON file (triggers download)
 */
export const exportCollections = async (collectionIds?: string[]): Promise<void> => {
  const params = collectionIds?.length ? { collection_ids: collectionIds.join(',') } : {};
  
  const response = await apiClient.get('/collections/export', {
    params,
    responseType: 'blob',
  });

  // Get filename from Content-Disposition header or generate one
  const contentDisposition = response.headers['content-disposition'];
  let filename = `collections_export_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.json`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename=([^;]+)/);
    if (match) {
      filename = match[1].trim();
    }
  }

  // Create blob and download
  const blob = new Blob([response.data], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

/**
 * Import collections from export data
 * Migrations are always generated to ensure database tables are created
 */
export const importCollections = async (
  data: CollectionExportData,
  strategy: ImportStrategy = 'error'
): Promise<CollectionImportResult> => {
  const response = await apiClient.post<CollectionImportResult>('/collections/import', {
    data,
    strategy,
    generate_migrations: true,
  });
  return response.data;
};

/**
 * Field type options for the schema builder
 */
export const FIELD_TYPES = [
  { value: 'boolean', label: 'Boolean' },
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

/**
 * On delete action options for reference fields
 */
export const ON_DELETE_OPTIONS = [
  { value: 'cascade', label: 'Cascade' },
  { value: 'set_null', label: 'Set Null' },
  { value: 'restrict', label: 'Restrict' },
] as const;

/**
 * PII mask type options
 */
export const MASK_TYPE_OPTIONS = [
  { value: 'email', label: 'Email' },
  { value: 'ssn', label: 'SSN' },
  { value: 'phone', label: 'Phone' },
  { value: 'name', label: 'Name' },
  { value: 'full', label: 'Full' },
  { value: 'custom', label: 'Custom' },
] as const;

/**
 * Import strategy options for the import dialog
 */
export const IMPORT_STRATEGY_OPTIONS = [
  { 
    value: 'error' as ImportStrategy, 
    label: 'Error on Conflict', 
    description: 'Fail if any collection already exists (safest)' 
  },
  { 
    value: 'skip' as ImportStrategy, 
    label: 'Skip Existing', 
    description: 'Skip existing collections, import only new ones' 
  },
  { 
    value: 'update' as ImportStrategy, 
    label: 'Update Existing', 
    description: 'Update existing collections with new schema (add fields only)' 
  },
] as const;

