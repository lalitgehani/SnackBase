/**
 * Dashboard service
 * Handles API calls for dashboard statistics
 */

import { apiClient } from '@/lib/api';

import type { AuditLogItem } from './audit.service';

export type DashboardRange = '7d' | '30d' | '90d';

export const DASHBOARD_RANGES: DashboardRange[] = ['7d', '30d', '90d'];

export function isDashboardRange(value: string): value is DashboardRange {
  return DASHBOARD_RANGES.includes(value as DashboardRange);
}

export interface SystemHealthStats {
  database_status: string;
  storage_usage_mb: number;
}

export interface RecentRegistration {
  id: string;
  email: string;
  account_id: string;
  account_code: string;
  account_name: string;
  created_at: string;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
}

export interface AuditOperationPoint {
  date: string;
  create: number;
  update: number;
  delete: number;
}

export interface CollectionRecordCount {
  name: string;
  count: number;
}

export interface PreviousPeriodStats {
  new_accounts: number;
  new_users: number;
}

export interface TimeSeriesStats {
  accounts_created: TimeSeriesPoint[];
  users_created: TimeSeriesPoint[];
  audit_by_operation: AuditOperationPoint[];
}

export interface DashboardStats {
  total_accounts: number;
  total_users: number;
  total_collections: number;
  total_records: number;
  /** New accounts in the selected range (name kept for API compatibility). */
  new_accounts_7d: number;
  /** New users in the selected range (name kept for API compatibility). */
  new_users_7d: number;
  range: DashboardRange;
  previous_period: PreviousPeriodStats;
  time_series: TimeSeriesStats;
  recent_registrations: RecentRegistration[];
  system_health: SystemHealthStats;
  active_sessions: number;
  public_collections_count: number;
  records_by_collection: CollectionRecordCount[];
  recent_audit_logs: AuditLogItem[];
}

/**
 * Get dashboard statistics for the given time range.
 */
export const getDashboardStats = async (
  range: DashboardRange = '7d',
): Promise<DashboardStats> => {
  const response = await apiClient.get<DashboardStats>('/dashboard/stats', {
    params: { range },
  });
  return response.data;
};

/**
 * Format storage usage with an appropriate unit.
 */
export function formatStorageUsage(mb: number): string {
  if (!Number.isFinite(mb) || mb < 0) {
    return '0 MB';
  }
  if (mb < 0.01 && mb > 0) {
    const kb = mb * 1024;
    return `${kb.toFixed(1)} KB`;
  }
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  return `${mb.toFixed(2)} MB`;
}

/**
 * Format period-over-period delta for KPI cards.
 */
export function formatPeriodDelta(
  current: number,
  previous: number,
  range: DashboardRange,
): string {
  const delta = current - previous;
  const sign = delta > 0 ? '+' : '';
  return `${sign}${delta} vs previous ${range}`;
}
