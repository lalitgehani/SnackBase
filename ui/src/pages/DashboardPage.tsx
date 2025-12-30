/**
 * Dashboard page - main landing page after login
 * Shows system overview metrics, recent activity, and quick actions
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
    LayoutDashboard,
    Users,
    Database,
    FileText,
    TrendingUp,
    RefreshCw,
    Plus,
    Activity,
    HardDrive,
} from 'lucide-react';
import AuditLogsTable from '@/components/audit-logs/AuditLogsTable';
import type { AuditLogItem } from '@/services/audit.service';
import { getDashboardStats, type DashboardStats } from '@/services/dashboard.service';
import { handleApiError } from '@/lib/api';

const REFRESH_OPTIONS = [
    { value: '0', label: 'No refresh' },
    { value: '10', label: '10 seconds' },
    { value: '30', label: '30 seconds' },
    { value: '60', label: '60 seconds' },
    { value: '300', label: '5 minutes' },
];

const STORAGE_KEY = 'dashboard-refresh-frequency';

export default function DashboardPage() {
    const navigate = useNavigate();
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [refreshFrequency, setRefreshFrequency] = useState<string>(() => {
        return localStorage.getItem(STORAGE_KEY) || '0';
    });
    const [auditPage, setAuditPage] = useState(1);
    const [auditPageSize, setAuditPageSize] = useState(10);

    const fetchStats = async (isManualRefresh = false) => {
        if (isManualRefresh) {
            setRefreshing(true);
        } else {
            setLoading(true);
        }
        setError(null);

        try {
            const data = await getDashboardStats();
            setStats(data);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    // Initial load
    useEffect(() => {
        fetchStats();
    }, []);

    // Auto-refresh based on selected frequency
    useEffect(() => {
        const frequency = parseInt(refreshFrequency);
        if (frequency === 0) return;

        const interval = setInterval(() => {
            fetchStats();
        }, frequency * 1000);

        return () => clearInterval(interval);
    }, [refreshFrequency]);

    // Persist refresh frequency preference
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, refreshFrequency);
    }, [refreshFrequency]);

    const handleManualRefresh = () => {
        fetchStats(true);
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    if (loading && !stats) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error && !stats) {
        return (
            <div className="space-y-4">
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                    <p className="text-destructive font-medium">Failed to load dashboard</p>
                    <p className="text-sm text-muted-foreground mt-1">{error}</p>
                    <Button onClick={() => fetchStats()} className="mt-4" size="sm">
                        Try Again
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header with refresh controls */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Dashboard</h1>
                    <p className="text-muted-foreground mt-1">System overview and metrics</p>
                </div>
                <div className="flex items-center gap-3">
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
                        onClick={handleManualRefresh}
                        disabled={refreshing}
                        size="icon"
                        variant="outline"
                    >
                        <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                    </Button>
                </div>
            </div>

            {/* Metrics Grid - Total Counts */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Accounts</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_accounts || 0}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Users</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_users || 0}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Collections</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_collections || 0}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Records</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_records || 0}</div>
                    </CardContent>
                </Card>
            </div>

            {/* Growth Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">New Accounts (7 days)</CardTitle>
                        <TrendingUp className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            +{stats?.new_accounts_7d || 0}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">New Users (7 days)</CardTitle>
                        <TrendingUp className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            +{stats?.new_users_7d || 0}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* System Health & Active Sessions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Activity className="h-5 w-5 text-primary" />
                            System Health
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
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
                            <span className="text-sm text-muted-foreground">Storage Usage</span>
                            <span className="text-sm font-medium">
                                {stats?.system_health.storage_usage_mb.toFixed(2) || 0} MB
                            </span>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <HardDrive className="h-5 w-5 text-primary" />
                            Active Sessions
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{stats?.active_sessions || 0}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Currently active user sessions
                        </p>
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
                    {stats?.recent_registrations && stats.recent_registrations.length > 0 ? (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Email</TableHead>
                                    <TableHead>Account</TableHead>
                                    <TableHead>Registered At</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {stats.recent_registrations.map((registration) => (
                                    <TableRow key={registration.id}>
                                        <TableCell className="font-medium">{registration.email}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-col">
                                                <span className="text-sm">{registration.account_name}</span>
                                                <span className="text-xs text-muted-foreground">
                                                    {registration.account_code}
                                                </span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {formatDate(registration.created_at)}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                            <p>No recent registrations</p>
                        </div>
                    )}
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
                                onSort={() => { }}
                                onView={(log: AuditLogItem) => navigate(`/admin/audit-logs?id=${log.id}`)}
                                isLoading={loading && !stats}
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
                        <Button onClick={() => navigate('/admin/collections')} variant="outline" className="gap-2">
                            <Plus className="h-4 w-4" />
                            Create Collection
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
