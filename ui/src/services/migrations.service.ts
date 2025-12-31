/**
 * Migrations service for querying Alembic migration status
 */

import { apiClient } from '@/lib/api';
import type {
    MigrationListResponse,
    CurrentRevisionResponse,
    MigrationHistoryResponse,
} from '@/types/migrations';

/**
 * List all Alembic revisions
 */
export const listMigrations = async (): Promise<MigrationListResponse> => {
    const response = await apiClient.get<MigrationListResponse>('/migrations');
    return response.data;
};

/**
 * Get current database revision
 */
export const getCurrentMigration = async (): Promise<CurrentRevisionResponse | null> => {
    try {
        const response = await apiClient.get<CurrentRevisionResponse>('/migrations/current');
        return response.data;
    } catch (error: any) {
        // Return null if no current revision (404)
        if (error.response?.status === 404) {
            return null;
        }
        throw error;
    }
};

/**
 * Get full migration history
 */
export const getMigrationHistory = async (): Promise<MigrationHistoryResponse> => {
    const response = await apiClient.get<MigrationHistoryResponse>('/migrations/history');
    return response.data;
};
