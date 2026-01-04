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
 * Field type options for the schema builder
 */
export const FIELD_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'datetime', label: 'DateTime' },
  { value: 'email', label: 'Email' },
  { value: 'url', label: 'URL' },
  { value: 'json', label: 'JSON' },
  { value: 'reference', label: 'Reference' },
  { value: 'file', label: 'File' },
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
