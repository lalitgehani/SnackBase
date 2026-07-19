/**
 * Dashboard page - main landing page after login
 * Phase 3: automation health (jobs/hooks/webhooks), feature counts, alert strip
 */

import { useEffect, useMemo, useState, type ReactNode } from 'react';
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  LayoutDashboard,
  Users,
  Database,
  FileText,
  RefreshCw,
  Activity,
  HardDrive,
  Globe,
  Building2,
  Layers,
  Webhook,
  Workflow,
  Zap,
  UserPlus,
  KeyRound,
  Terminal,
  Route,
  AlertTriangle,
  X,
} from 'lucide-react';
import {
  ChartContainer,
  DonutChart,
  HorizontalBarChart,
  Sparkline,
  StackedBarChart,
  TimeSeriesAreaChart,
} from '@/components/charts';
import { CHART_COLORS } from '@/components/charts/theme';
import {
  getDashboardStats,
  formatPeriodDelta,
  formatStorageUsage,
  isDashboardRange,
  EMPTY_FEATURE_COUNTS,
  EMPTY_JOBS_BY_STATUS,
  EMPTY_HOOK_EXECUTIONS,
  EMPTY_WEBHOOK_DELIVERIES,
  type DashboardRange,
  type DashboardStats,
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

const RANGE_LABELS: Record<DashboardRange, string> = {
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
};

const REFRESH_STORAGE_KEY = 'dashboard-refresh-frequency';
const RANGE_STORAGE_KEY = 'dashboard-range';
const ALERT_DISMISS_KEY = 'dashboard-automation-alert-dismissed';

const QUICK_ACTIONS = [
  { label: 'Create Account', path: '/admin/accounts', icon: Building2 },
  { label: 'Create Collection', path: '/admin/collections/new', icon: Database },
  { label: 'Invite User', path: '/admin/invitations', icon: UserPlus },
  { label: 'Create Hook', path: '/admin/hooks', icon: Zap },
  { label: 'Create Webhook', path: '/admin/webhooks', icon: Webhook },
  { label: 'Create Workflow', path: '/admin/workflows', icon: Workflow },
] as const;

const FEATURE_COUNT_ITEMS = [
  {
    key: 'hooks',
    label: 'Hooks',
    path: '/admin/hooks',
    icon: Zap,
    value: (s: DashboardStats) => s.feature_counts.hooks,
    subtitle: (s: DashboardStats) => `${s.feature_counts.hooks_enabled} enabled`,
  },
  {
    key: 'webhooks',
    label: 'Webhooks',
    path: '/admin/webhooks',
    icon: Webhook,
    value: (s: DashboardStats) => s.feature_counts.webhooks,
    subtitle: (s: DashboardStats) => `${s.feature_counts.webhooks_enabled} enabled`,
  },
  {
    key: 'workflows',
    label: 'Workflows',
    path: '/admin/workflows',
    icon: Workflow,
    value: (s: DashboardStats) => s.feature_counts.workflows,
  },
  {
    key: 'endpoints',
    label: 'Endpoints',
    path: '/admin/endpoints',
    icon: Route,
    value: (s: DashboardStats) => s.feature_counts.endpoints,
  },
  {
    key: 'macros',
    label: 'Macros',
    path: '/admin/macros',
    icon: Terminal,
    value: (s: DashboardStats) => s.feature_counts.macros,
  },
  {
    key: 'api_keys',
    label: 'API Keys',
    path: '/admin/api-keys',
    icon: KeyRound,
    value: (s: DashboardStats) => s.feature_counts.api_keys_active,
  },
  {
    key: 'invitations',
    label: 'Invitations',
    path: '/admin/invitations',
    icon: UserPlus,
    value: (s: DashboardStats) => s.feature_counts.invitations_pending,
    subtitle: () => 'pending',
  },
] as const;

function readStoredRange(): DashboardRange {
  const stored = localStorage.getItem(RANGE_STORAGE_KEY);
  if (stored && isDashboardRange(stored)) {
    return stored;
  }
  return '7d';
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString();
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
  const [alertDismissed, setAlertDismissed] = useState(() => {
    return sessionStorage.getItem(ALERT_DISMISS_KEY) === '1';
  });

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

  useEffect(() => {
    localStorage.setItem(REFRESH_STORAGE_KEY, refreshFrequency);
  }, [refreshFrequency]);

  useEffect(() => {
    localStorage.setItem(RANGE_STORAGE_KEY, range);
  }, [range]);

  const errorMessage = isError ? handleApiError(error) : null;
  const showFullPageError = isError && !stats;
  const showKpiSkeletons = isLoading && !stats;
  const rangeLabel = RANGE_LABELS[stats?.range ?? range];

  const featureCounts = stats?.feature_counts ?? EMPTY_FEATURE_COUNTS;
  const jobsByStatus = stats?.jobs_by_status ?? EMPTY_JOBS_BY_STATUS;
  const hookExecutions = stats?.hook_executions_summary ?? EMPTY_HOOK_EXECUTIONS;
  const webhookDeliveries = stats?.webhook_deliveries_summary ?? EMPTY_WEBHOOK_DELIVERIES;

  const deadJobs = jobsByStatus.dead;
  const failedWebhooks = webhookDeliveries.failed;
  const showAutomationAlert =
    !alertDismissed && !showKpiSkeletons && (deadJobs > 0 || failedWebhooks > 0);

  const dismissAlert = () => {
    sessionStorage.setItem(ALERT_DISMISS_KEY, '1');
    setAlertDismissed(true);
  };

  const growthChartData = useMemo(() => {
    if (!stats) return [];
    const accounts = stats.time_series.accounts_created;
    const users = stats.time_series.users_created;
    const userByDate = new Map(users.map((p) => [p.date, p.count]));
    return accounts.map((p) => ({
      date: p.date,
      accounts: p.count,
      users: userByDate.get(p.date) ?? 0,
    }));
  }, [stats]);

  const growthIsEmpty = useMemo(
    () =>
      growthChartData.length > 0 &&
      growthChartData.every((d) => d.accounts === 0 && d.users === 0),
    [growthChartData],
  );

  const auditChartData = useMemo(() => {
    if (!stats?.time_series.audit_by_operation) return [];
    return stats.time_series.audit_by_operation.map((p) => ({
      name: p.date,
      create: p.create,
      update: p.update,
      delete: p.delete,
    }));
  }, [stats]);

  const auditIsEmpty = useMemo(
    () =>
      auditChartData.length > 0 &&
      auditChartData.every((d) => d.create === 0 && d.update === 0 && d.delete === 0),
    [auditChartData],
  );

  const recordsChartData = useMemo(() => {
    if (!stats?.records_by_collection) return [];
    return stats.records_by_collection.map((item) => ({
      name: item.name,
      value: item.count,
    }));
  }, [stats]);

  const accessMixData = useMemo(() => {
    if (!stats || stats.total_collections === 0) return [];
    const publicCount = stats.public_collections_count;
    const protectedCount = Math.max(0, stats.total_collections - publicCount);
    return [
      { name: 'Public', value: publicCount, color: CHART_COLORS.chart2 },
      { name: 'Protected', value: protectedCount, color: CHART_COLORS.chart1 },
    ].filter((d) => d.value > 0);
  }, [stats]);

  const jobsChartData = useMemo(
    () => [
      { name: 'Pending', value: jobsByStatus.pending, color: CHART_COLORS.chart3 },
      { name: 'Running', value: jobsByStatus.running, color: CHART_COLORS.chart1 },
      { name: 'Completed', value: jobsByStatus.completed, color: CHART_COLORS.chart2 },
      { name: 'Failed', value: jobsByStatus.failed, color: CHART_COLORS.chart4 },
      { name: 'Retrying', value: jobsByStatus.retrying, color: CHART_COLORS.chart3 },
      { name: 'Dead', value: jobsByStatus.dead, color: CHART_COLORS.chart5 },
    ],
    [jobsByStatus],
  );

  const hooksChartData = useMemo(
    () => [
      { name: 'Success', value: hookExecutions.success, color: CHART_COLORS.chart2 },
      { name: 'Partial', value: hookExecutions.partial, color: CHART_COLORS.chart3 },
      { name: 'Failed', value: hookExecutions.failed, color: CHART_COLORS.chart5 },
    ],
    [hookExecutions],
  );

  const webhooksChartData = useMemo(
    () => [
      { name: 'Delivered', value: webhookDeliveries.delivered, color: CHART_COLORS.chart2 },
      { name: 'Pending', value: webhookDeliveries.pending, color: CHART_COLORS.chart3 },
      { name: 'Retrying', value: webhookDeliveries.retrying, color: CHART_COLORS.chart4 },
      { name: 'Failed', value: webhookDeliveries.failed, color: CHART_COLORS.chart5 },
    ],
    [webhookDeliveries],
  );

  const jobsIsEmpty = jobsChartData.every((d) => d.value === 0);
  const hooksIsEmpty = hooksChartData.every((d) => d.value === 0);
  const webhooksIsEmpty = webhooksChartData.every((d) => d.value === 0);

  const recentRegistrations = stats?.recent_registrations?.slice(0, 10) ?? [];
  const recentAuditLogs = stats?.recent_audit_logs?.slice(0, 10) ?? [];

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

      {/* Automation health alert strip */}
      {showAutomationAlert ? (
        <Alert
          variant="destructive"
          className="relative"
          data-testid="automation-alert"
        >
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Automation attention needed</AlertTitle>
          <AlertDescription>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1 text-sm">
                {deadJobs > 0 ? (
                  <p>
                    {deadJobs} dead job{deadJobs === 1 ? '' : 's'} need attention
                  </p>
                ) : null}
                {failedWebhooks > 0 ? (
                  <p>
                    {failedWebhooks} failed webhook deliver
                    {failedWebhooks === 1 ? 'y' : 'ies'} in this period
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {deadJobs > 0 ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate('/admin/jobs')}
                  >
                    View Jobs
                  </Button>
                ) : null}
                {failedWebhooks > 0 ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate('/admin/webhooks')}
                  >
                    View Webhooks
                  </Button>
                ) : null}
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={dismissAlert}
                  aria-label="Dismiss automation alert"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
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

      {/* Feature counts strip */}
      <div data-testid="feature-counts-strip">
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          Platform features
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
          {FEATURE_COUNT_ITEMS.map((item) => {
            const Icon = item.icon;
            const value = stats ? item.value(stats) : 0;
            const subtitle =
              stats && 'subtitle' in item && item.subtitle
                ? item.subtitle(stats)
                : undefined;
            return (
              <Card
                key={item.key}
                className="cursor-pointer transition-colors hover:bg-muted/50"
                onClick={() => navigate(item.path)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(item.path);
                  }
                }}
                data-testid={`feature-count-${item.key}`}
              >
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3">
                  <CardTitle className="text-xs font-medium text-muted-foreground">
                    {item.label}
                  </CardTitle>
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pb-3">
                  {showKpiSkeletons ? (
                    <Skeleton className="h-7 w-10" />
                  ) : (
                    <>
                      <div className="text-xl font-bold">{value}</div>
                      {subtitle ? (
                        <p className="text-[11px] text-muted-foreground">{subtitle}</p>
                      ) : null}
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Growth + Access mix */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartContainer
          className="lg:col-span-2"
          title="Growth"
          description={`Accounts and users created · ${rangeLabel}`}
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && (growthChartData.length === 0 || growthIsEmpty)}
          emptyMessage="No growth in this period"
          emptyHint="Create accounts or users, or try a wider time range."
        >
          <TimeSeriesAreaChart
            data={growthChartData}
            series={[
              { key: 'accounts', label: 'Accounts', color: CHART_COLORS.chart1 },
              { key: 'users', label: 'Users', color: CHART_COLORS.chart2 },
            ]}
            height={280}
          />
        </ChartContainer>

        <ChartContainer
          title="Collection Access"
          description="Public vs protected collections"
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && accessMixData.length === 0}
          emptyMessage="No collections yet"
          emptyHint="Create a collection to see access mix."
          headerAction={
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => navigate('/admin/collections')}
            >
              View all
            </Button>
          }
        >
          <div
            className="cursor-pointer"
            onClick={() => navigate('/admin/collections')}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate('/admin/collections');
              }
            }}
          >
            <DonutChart data={accessMixData} height={240} />
          </div>
        </ChartContainer>
      </div>

      {/* Audit activity + Records by collection */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartContainer
          title="Audit Activity"
          description={`CREATE / UPDATE / DELETE · ${rangeLabel}`}
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && (auditChartData.length === 0 || auditIsEmpty)}
          emptyMessage="No audit activity in this period"
          emptyHint="Write operations will appear here once audit logging is active."
          headerAction={
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => navigate('/admin/audit-logs')}
            >
              View all
            </Button>
          }
        >
          <StackedBarChart
            data={auditChartData}
            series={[
              { key: 'create', label: 'CREATE', color: CHART_COLORS.chart2 },
              { key: 'update', label: 'UPDATE', color: CHART_COLORS.chart3 },
              { key: 'delete', label: 'DELETE', color: CHART_COLORS.chart5 },
            ]}
            height={280}
          />
        </ChartContainer>

        <ChartContainer
          title="Records by Collection"
          description="Top collections by row count"
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && recordsChartData.length === 0}
          emptyMessage="No records yet"
          emptyHint="Add data to collections to see distribution."
        >
          <HorizontalBarChart
            data={recordsChartData}
            height={280}
            color={CHART_COLORS.chart1}
            onBarClick={(datum) => {
              if (datum.name === 'Other') return;
              navigate(`/admin/collections/${encodeURIComponent(datum.name)}/data`);
            }}
          />
        </ChartContainer>
      </div>

      {/* Automation health: Jobs / Hooks / Webhooks */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3" data-testid="automation-health">
        <ChartContainer
          title="Jobs"
          description="Queue status composition"
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && jobsIsEmpty}
          emptyMessage="No jobs yet"
          emptyHint="Background jobs will appear here when enqueued."
          headerAction={
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => navigate('/admin/jobs')}
            >
              View all
            </Button>
          }
        >
          <div
            className="cursor-pointer"
            onClick={() => navigate('/admin/jobs')}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate('/admin/jobs');
              }
            }}
          >
            <DonutChart data={jobsChartData} height={220} />
          </div>
        </ChartContainer>

        <ChartContainer
          title="Hook Executions"
          description={`Success vs failure · ${rangeLabel}`}
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && hooksIsEmpty}
          emptyMessage="No hook executions in this period"
          emptyHint={
            featureCounts.hooks_enabled > 0
              ? `${featureCounts.hooks_enabled} hooks enabled — waiting for activity.`
              : 'Create and enable hooks to track execution health.'
          }
          headerAction={
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => navigate('/admin/hooks')}
            >
              View all
            </Button>
          }
        >
          <div
            className="cursor-pointer"
            onClick={() => navigate('/admin/hooks')}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate('/admin/hooks');
              }
            }}
          >
            <DonutChart data={hooksChartData} height={220} />
          </div>
        </ChartContainer>

        <ChartContainer
          title="Webhook Deliveries"
          description={`Delivery health · ${rangeLabel}`}
          isLoading={showKpiSkeletons}
          isEmpty={!showKpiSkeletons && webhooksIsEmpty}
          emptyMessage="No webhook deliveries in this period"
          emptyHint="Outbound webhook deliveries will show delivery status here."
          headerAction={
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => navigate('/admin/webhooks')}
            >
              View all
            </Button>
          }
        >
          <div
            className="cursor-pointer"
            onClick={() => navigate('/admin/webhooks')}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate('/admin/webhooks');
              }
            }}
          >
            <DonutChart data={webhooksChartData} height={220} />
          </div>
        </ChartContainer>
      </div>

      {/* System Health */}
      <Card data-testid="system-health-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            System Health
          </CardTitle>
          <CardDescription>Database connectivity and file storage</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {showKpiSkeletons ? (
            <>
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-6 w-48" />
            </>
          ) : (
            <>
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
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <HardDrive className="h-4 w-4" />
                  Storage
                </span>
                <span className="text-sm font-medium">
                  {formatStorageUsage(stats?.system_health.storage_usage_mb ?? 0)}
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Compact activity feed */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Users className="h-5 w-5 text-primary" />
                  Recent Registrations
                </CardTitle>
                <CardDescription>Latest user signups</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => navigate('/admin/users')}
              >
                View all
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showKpiSkeletons ? (
              <div className="space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : recentRegistrations.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No recent registrations
              </p>
            ) : (
              <ul className="divide-y" data-testid="registrations-feed">
                {recentRegistrations.map((reg) => (
                  <li key={reg.id} className="flex items-start justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{reg.email}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {reg.account_name} · {reg.account_code}
                      </p>
                    </div>
                    <time className="shrink-0 text-xs text-muted-foreground">
                      {formatDate(reg.created_at)}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileText className="h-5 w-5 text-primary" />
                  Recent Audit Activity
                </CardTitle>
                <CardDescription>Latest write operations</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => navigate('/admin/audit-logs')}
              >
                View all
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showKpiSkeletons ? (
              <div className="space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : recentAuditLogs.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No recent audit logs
              </p>
            ) : (
              <ul className="divide-y" data-testid="audit-feed">
                {recentAuditLogs.map((log) => (
                  <li key={log.id} className="flex items-start justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px] font-normal">
                          {log.operation}
                        </Badge>
                        <span className="truncate text-sm font-medium">{log.table_name}</span>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {log.user_email || log.user_name || '—'}
                      </p>
                    </div>
                    <time className="shrink-0 text-xs text-muted-foreground">
                      {formatDate(log.occurred_at)}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LayoutDashboard className="h-5 w-5 text-primary" />
            Quick Actions
          </CardTitle>
          <CardDescription>Jump into common platform workflows</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon;
              return (
                <Button
                  key={action.path}
                  variant="outline"
                  className="h-auto flex-col gap-2 py-4"
                  onClick={() => navigate(action.path)}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{action.label}</span>
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
