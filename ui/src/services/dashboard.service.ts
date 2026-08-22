/**
 * Dashboard service
 * Handles API calls for dashboard statistics
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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

/** Platform feature adoption counts (global, not range-scoped). */
export interface FeatureCounts {
  hooks: number;
  hooks_enabled: number;
  webhooks: number;
  webhooks_enabled: number;
  workflows: number;
  endpoints: number;
  macros: number;
  api_keys_active: number;
  invitations_pending: number;
}

/** Live job queue composition (current snapshot). */
export interface JobsByStatus {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  retrying: number;
  dead: number;
}

/** Hook execution outcomes for the selected range. */
export interface HookExecutionsSummary {
  success: number;
  failed: number;
  partial: number;
}

/** Webhook delivery outcomes for the selected range. */
export interface WebhookDeliveriesSummary {
  delivered: number;
  failed: number;
  pending: number;
  retrying: number;
}

export const EMPTY_FEATURE_COUNTS: FeatureCounts = {
  hooks: 0,
  hooks_enabled: 0,
  webhooks: 0,
  webhooks_enabled: 0,
  workflows: 0,
  endpoints: 0,
  macros: 0,
  api_keys_active: 0,
  invitations_pending: 0,
};

export const EMPTY_JOBS_BY_STATUS: JobsByStatus = {
  pending: 0,
  running: 0,
  completed: 0,
  failed: 0,
  retrying: 0,
  dead: 0,
};

export const EMPTY_HOOK_EXECUTIONS: HookExecutionsSummary = {
  success: 0,
  failed: 0,
  partial: 0,
};

export const EMPTY_WEBHOOK_DELIVERIES: WebhookDeliveriesSummary = {
  delivered: 0,
  failed: 0,
  pending: 0,
  retrying: 0,
};

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
  feature_counts: FeatureCounts;
  jobs_by_status: JobsByStatus;
  hook_executions_summary: HookExecutionsSummary;
  webhook_deliveries_summary: WebhookDeliveriesSummary;
  recent_audit_logs: AuditLogItem[];
}

export function createDashboardService(client: SnackBaseClient) {
  return {
    getDashboardStats: (range: DashboardRange = '7d') =>
      client.dashboard.getStats({ range }),
  };
}

export const useDashboardService = createServiceHook(createDashboardService);

const dashboardService = bindService(createDashboardService);
export const getDashboardStats = dashboardService.getDashboardStats;

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
