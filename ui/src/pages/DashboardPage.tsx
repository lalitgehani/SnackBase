/**
 * Dashboard page - main landing page after login
 * Shows system overview metrics, recent activity, and quick actions
 */

import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LayoutDashboard,
  Users,
  Database,
  FileText,
  RefreshCw,
  Plus,
  Activity,
  HardDrive,
  Globe,
  Building2,
  Layers,
} from 'lucide-react';
import AuditLogsTable from '@/components/audit-logs/AuditLogsTable';
import { DataTable, type Column } from '@/components/common/DataTable';
import { Sparkline } from '@/components/charts';
import { CHART_COLORS } from '@/components/charts/theme';
import type { AuditLogItem } from '@/services/audit.service';
import {
  getDashboardStats,
  formatPeriodDelta,
  formatStorageUsage,
  isDashboardRange,
  type DashboardRange,
  type DashboardStats,
  type RecentRegistration,
} from '@/services/dashboard.service';
import { handleApiError } from '@/lib/api';
import { cn } from '@/lib/utils';

const REFRESH_OPTIONS = [
  { value: '0', label: 'No refresh' },
  { value: '10', label: '10 seconds' },
  { value: '30', label: '30 seconds' },
  { value: '60', label: '60 seconds' },
  { value: '300', label: '5 minutes' },
];

const RANGE_OPTIONS: { value: DashboardRange; label: string }[] = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
];

const REFRESH_STORAGE_KEY = 'dashboard-refresh-frequency';
const RANGE_STORAGE_KEY = 'dashboard-range';

function readStoredRange(): DashboardRange {
  const stored = localStorage.getItem(RANGE_STORAGE_KEY);
  if (stored && isDashboardRange(stored)) {
    return stored;
  }
  return '7d';
}

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  onClick?: () => void;
  delta?: string;
  sparklineData?: { date: string; count: number }[];
  sparklineColor?: string;
  badge?: ReactNode;
  subtitle?: string;
  isLoading?: boolean;
}

function KpiCard({
  title,
  value,
  icon,
  onClick,
  delta,
  sparklineData,
  sparklineColor,
  badge,
  subtitle,
  isLoading,
}: KpiCardProps) {
  return (
    <Card
      className={cn(
        'transition-colors',
        onClick && 'cursor-pointer hover:bg-muted/50',
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <>
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-3 w-28" />
            {sparklineData !== undefined && <Skeleton className="h-10 w-full" />}
          </>
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <div className="text-2xl font-bold">{value}</div>
              {badge}
            </div>
            {delta ? (
              <p className="text-xs text-muted-foreground">{delta}</p>
            ) : null}
            {subtitle ? (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            ) : null}
            {sparklineData !== undefined ? (
              <Sparkline
                data={sparklineData}
                color={sparklineColor ?? CHART_COLORS.chart1}
                height={40}
              />
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [refreshFrequency, setRefreshFrequency] = useState<string>(() => {
    return localStorage.getItem(REFRESH_STORAGE_KEY) || '0';
  });
  const [range, setRange] = useState<DashboardRange>(() => readStoredRange());
  const [auditPage, setAuditPage] = useState(1);
  const [auditPageSize, setAuditPageSize] = useState(10);
  const [regPage, setRegPage] = useState(1);
  const [regPageSize, setRegPageSize] = useState(10);

  const {
    data: stats,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats', range],
    queryFn: () => getDashboardStats(range),
    refetchInterval:
      parseInt(refreshFrequency, 10) > 0 ? parseInt(refreshFrequency, 10) * 1000 : false,
  });

  // Persist preferences
  useEffect(() => {
    localStorage.setItem(REFRESH_STORAGE_KEY, refreshFrequency);
  }, [refreshFrequency]);

  useEffect(() => {
    localStorage.setItem(RANGE_STORAGE_KEY, range);
  }, [range]);

  const errorMessage = isError ? handleApiError(error) : null;
  const showFullPageError = isError && !stats;
  const showKpiSkeletons = isLoading && !stats;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const registrationColumns: Column<RecentRegistration>[] = [
    {
      header: 'Email',
      accessorKey: 'email',
      className: 'font-medium',
    },
    {
      header: 'Account',
      render: (reg) => (
        <div className="flex flex-col">
          <span className="text-sm">{reg.account_name}</span>
          <span className="text-xs text-muted-foreground">{reg.account_code}</span>
        </div>
      ),
    },
    {
      header: 'Registered At',
      accessorKey: 'created_at',
      render: (reg) => (
        <span className="text-sm text-muted-foreground">{formatDate(reg.created_at)}</span>
      ),
    },
  ];

  if (showFullPageError) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
          <p className="font-medium text-destructive">Failed to load dashboard</p>
          <p className="mt-1 text-sm text-muted-foreground">{errorMessage}</p>
          <Button onClick={() => refetch()} className="mt-4" size="sm">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const accountDelta =
    stats != null
      ? formatPeriodDelta(
          stats.new_accounts_7d,
          stats.previous_period.new_accounts,
          stats.range,
        )
      : undefined;
  const userDelta =
    stats != null
      ? formatPeriodDelta(stats.new_users_7d, stats.previous_period.new_users, stats.range)
      : undefined;

  return (
    <div className="space-y-6">
      {/* Header with range + refresh controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="mt-1 text-muted-foreground">System overview and metrics</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Select
            value={range}
            onValueChange={(value) => {
              if (isDashboardRange(value)) {
                setRange(value);
              }
            }}
          >
            <SelectTrigger className="w-40" aria-label="Time range">
              <SelectValue placeholder="Time range" />
            </SelectTrigger>
            <SelectContent>
              {RANGE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={refreshFrequency} onValueChange={setRefreshFrequency}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Refresh frequency" />
            </SelectTrigger>
            <SelectContent>
              {REFRESH_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={() => refetch()}
            disabled={isFetching}
            size="icon"
            variant="outline"
            aria-label="Refresh dashboard"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Inline error when prior data exists */}
      {isError && stats ? (
        <div className="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3">
          <p className="text-sm text-destructive">
            Failed to refresh: {errorMessage}
          </p>
          <Button onClick={() => refetch()} size="sm" variant="outline">
            Retry
          </Button>
        </div>
      ) : null}

      {/* Hero KPI strip */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <KpiCard
          title="Total Accounts"
          value={stats?.total_accounts ?? 0}
          icon={<Building2 className="h-4 w-4" />}
          onClick={() => navigate('/admin/accounts')}
          delta={accountDelta}
          sparklineData={stats?.time_series.accounts_created}
          sparklineColor={CHART_COLORS.chart1}
          isLoading={showKpiSkeletons}
        />
        <KpiCard
          title="Total Users"
          value={stats?.total_users ?? 0}
          icon={<Users className="h-4 w-4" />}
          onClick={() => navigate('/admin/users')}
          delta={userDelta}
          sparklineData={stats?.time_series.users_created}
          sparklineColor={CHART_COLORS.chart2}
          isLoading={showKpiSkeletons}
        />
        <KpiCard
          title="Total Collections"
          value={stats?.total_collections ?? 0}
          icon={<Database className="h-4 w-4" />}
          onClick={() => navigate('/admin/collections')}
          badge={
            stats != null ? (
              <Badge variant="secondary" className="gap-1 text-xs font-normal">
                <Globe className="h-3 w-3 text-green-600" />
                {stats.public_collections_count} public
              </Badge>
            ) : undefined
          }
          isLoading={showKpiSkeletons}
        />
        <KpiCard
          title="Total Records"
          value={stats?.total_records ?? 0}
          icon={<Layers className="h-4 w-4" />}
          isLoading={showKpiSkeletons}
        />
        <KpiCard
          title="Active Sessions"
          value={stats?.active_sessions ?? 0}
          icon={<Activity className="h-4 w-4" />}
          subtitle="Currently active user sessions"
          isLoading={showKpiSkeletons}
        />
        <KpiCard
          title="Storage"
          value={formatStorageUsage(stats?.system_health.storage_usage_mb ?? 0)}
          icon={<HardDrive className="h-4 w-4" />}
          isLoading={showKpiSkeletons}
        />
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-1">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              System Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {showKpiSkeletons ? (
              <Skeleton className="h-6 w-40" />
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Database</span>
                <Badge
                  variant={
                    stats?.system_health.database_status === 'connected'
                      ? 'default'
                      : 'destructive'
                  }
                >
                  {stats?.system_health.database_status || 'Unknown'}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Registrations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Recent Registrations
          </CardTitle>
          <CardDescription>Last 10 user registrations</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            data={stats?.recent_registrations || []}
            columns={registrationColumns}
            keyExtractor={(reg) => reg.id}
            isLoading={showKpiSkeletons}
            totalItems={stats?.recent_registrations?.length || 0}
            pagination={{
              page: regPage,
              pageSize: regPageSize,
              onPageChange: setRegPage,
              onPageSizeChange: (size) => {
                setRegPageSize(size);
                setRegPage(1);
              },
            }}
            noDataMessage="No recent registrations"
          />
        </CardContent>
      </Card>

      {/* Recent Audit Logs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Recent Audit Logs
              </CardTitle>
              <CardDescription>Last 20 audit log entries</CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/admin/audit-logs')}
              className="text-xs"
            >
              View All
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {(() => {
            const logs = stats?.recent_audit_logs || [];
            const total = logs.length;
            const startIndex = (auditPage - 1) * auditPageSize;
            const paginatedLogs = logs.slice(startIndex, startIndex + auditPageSize);

            return (
              <AuditLogsTable
                logs={paginatedLogs}
                totalItems={total}
                page={auditPage}
                pageSize={auditPageSize}
                onPageChange={setAuditPage}
                onPageSizeChange={(newSize) => {
                  setAuditPageSize(newSize);
                  setAuditPage(1);
                }}
                sortBy="occurred_at"
                sortOrder="desc"
                onSort={() => {}}
                onView={(log: AuditLogItem) => navigate(`/admin/audit-logs?id=${log.id}`)}
                isLoading={showKpiSkeletons}
              />
            );
          })()}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LayoutDashboard className="h-5 w-5 text-primary" />
            Quick Actions
          </CardTitle>
          <CardDescription>Common administrative tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button onClick={() => navigate('/admin/accounts')} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Account
            </Button>
            <Button
              onClick={() => navigate('/admin/collections/new')}
              variant="outline"
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Create Collection
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
