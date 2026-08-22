/**
 * Audit logs service
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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
  extra_metadata: Record<string, unknown> | null;
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

function downloadBlob(content: Blob, filename: string): void {
  const url = window.URL.createObjectURL(content);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function createAuditService(client: SnackBaseClient) {
  return {
    getAuditLogs: (filters: AuditLogFilters) => client.auditLogs.list(filters),
    getAuditLog: (id: number) => client.auditLogs.get(id),
    exportAuditLogs: async (format: 'csv' | 'json', filters: AuditLogFilters) => {
      const data = await client.auditLogs.export(filters, format);
      const mimeType = format === 'csv' ? 'text/csv' : 'application/json';
      const blob = new Blob([data], { type: mimeType });
      const filename = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
      downloadBlob(blob, filename);
    },
  };
}

export const useAuditService = createServiceHook(createAuditService);

const auditService = bindService(createAuditService);
export const getAuditLogs = auditService.getAuditLogs;
export const getAuditLog = auditService.getAuditLog;
export const exportAuditLogs = auditService.exportAuditLogs;
