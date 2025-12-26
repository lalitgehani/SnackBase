/**
 * Dashboard service
 * Handles API calls for dashboard statistics
 */

import { apiClient } from '@/lib/api';

export interface SystemHealthStats {
  database_status: string;
  storage_usage_mb: number;
}

export interface RecentRegistration {
  id: string;
  email: string;
  account_id: string;
  account_name: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  operation: string;
  table_name: string;
  user_email: string;
  occurred_at: string;
}

export interface DashboardStats {
  total_accounts: number;
  total_users: number;
  total_collections: number;
  total_records: number;
  new_accounts_7d: number;
  new_users_7d: number;
  recent_registrations: RecentRegistration[];
  system_health: SystemHealthStats;
  active_sessions: number;
  recent_audit_logs: AuditLogEntry[];
}

/**
 * Get dashboard statistics
 */
export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await apiClient.get<DashboardStats>('/dashboard/stats');
  return response.data;
};
