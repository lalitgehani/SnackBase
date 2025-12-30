/**
 * Audit logs service
 */

import { apiClient } from '@/lib/api';

export interface AuditLogItem {
    id: number;
    account_id: string;
    operation: 'CREATE' | 'UPDATE' | 'DELETE';
    table_name: string;
    record_id: string;
    column_name: string;
    old_value: string | null;
    new_value: string | null;
    user_id: string;
    user_email: string;
    user_name: string;
    es_username: string | null;
    es_reason: string | null;
    es_timestamp: string | null;
    ip_address: string | null;
    user_agent: string | null;
    request_id: string | null;
    occurred_at: string;
    checksum: string | null;
    previous_hash: string | null;
    extra_metadata: Record<string, any> | null;
}

export interface AuditLogListResponse {
    items: AuditLogItem[];
    total: number;
    skip: number;
    limit: number;
}

export interface AuditLogFilters {
    account_id?: string;
    table_name?: string;
    record_id?: string;
    user_id?: string;
    operation?: string;
    from_date?: string;
    to_date?: string;
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
}

/**
 * Get audit logs with filtering and pagination
 */
export const getAuditLogs = async (filters: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await apiClient.get<AuditLogListResponse>('/audit-logs/', { params: filters });
    return response.data;
};

/**
 * Get a single audit log entry
 */
export const getAuditLog = async (id: number): Promise<AuditLogItem> => {
    const response = await apiClient.get<AuditLogItem>(`/audit-logs/${id}`);
    return response.data;
};

/**
 * Export audit logs
 */
export const exportAuditLogs = async (format: 'csv' | 'json', filters: AuditLogFilters) => {
    const response = await apiClient.get('/audit-logs/export', {
        params: { ...filters, format },
        responseType: 'blob',
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const filename = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
};
