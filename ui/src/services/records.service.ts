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
	BatchUpdateItem,
	BatchCreateResponse,
	BatchUpdateResponse,
	BatchDeleteResponse,
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

/**
 * Batch create records (all succeed or all fail atomically)
 */
export const batchCreateRecords = async (
	collection: string,
	records: RecordData[],
): Promise<BatchCreateResponse> => {
	const response = await apiClient.post<BatchCreateResponse>(
		`/records/${collection}/batch`,
		{ records },
	);
	return response.data;
};

/**
 * Batch patch records (all succeed or all fail atomically)
 * Returns 404 if any ID does not exist — entire batch fails.
 */
export const batchUpdateRecords = async (
	collection: string,
	updates: BatchUpdateItem[],
): Promise<BatchUpdateResponse> => {
	const response = await apiClient.patch<BatchUpdateResponse>(
		`/records/${collection}/batch`,
		{ records: updates },
	);
	return response.data;
};

/**
 * Batch delete records (all succeed or all fail atomically)
 * Returns 404 if any ID does not exist — entire batch fails.
 */
export const batchDeleteRecords = async (
	collection: string,
	ids: string[],
): Promise<BatchDeleteResponse> => {
	// Axios requires { data: body } to send a body with DELETE
	const response = await apiClient.delete<BatchDeleteResponse>(
		`/records/${collection}/batch`,
		{ data: { ids } },
	);
	return response.data;
};
