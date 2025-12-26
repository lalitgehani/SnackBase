/**
 * Records API service
 * Handles API calls for record CRUD operations
 */

import { apiClient } from '@/lib/api';
import type {
	RecordDetail,
	RecordData,
	RecordListResponse,
	GetRecordsParams,
} from '@/types/records.types';

// Re-export commonly used types
export type { RecordData, RecordListItem } from '@/types/records.types';

/**
 * Get list of records for a collection
 */
export const getRecords = async (params: GetRecordsParams): Promise<RecordListResponse> => {
	const { collection, ...queryParams } = params;
	const response = await apiClient.get<RecordListResponse>(`/records/${collection}`, {
		params: queryParams,
	});
	return response.data;
};

/**
 * Get a single record by ID
 */
export const getRecordById = async (collection: string, recordId: string): Promise<RecordDetail> => {
	const response = await apiClient.get<RecordDetail>(`/records/${collection}/${recordId}`);
	return response.data;
};

/**
 * Create a new record
 */
export const createRecord = async (collection: string, data: RecordData): Promise<RecordDetail> => {
	const response = await apiClient.post<RecordDetail>(`/records/${collection}`, data);
	return response.data;
};

/**
 * Update a record (full replacement)
 */
export const updateRecord = async (
	collection: string,
	recordId: string,
	data: RecordData,
): Promise<RecordDetail> => {
	const response = await apiClient.put<RecordDetail>(`/records/${collection}/${recordId}`, data);
	return response.data;
};

/**
 * Partially update a record
 */
export const patchRecord = async (
	collection: string,
	recordId: string,
	data: Partial<RecordData>,
): Promise<RecordDetail> => {
	const response = await apiClient.patch<RecordDetail>(`/records/${collection}/${recordId}`, data);
	return response.data;
};

/**
 * Delete a record
 */
export const deleteRecord = async (collection: string, recordId: string): Promise<void> => {
	await apiClient.delete(`/records/${collection}/${recordId}`);
};
