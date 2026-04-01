import { useEffect, useState, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { jobsService, type Job, type JobStats, type JobStatus } from '@/services/jobs.service';
import { ViewJobDialog } from './ViewJobDialog';
import { RefreshCw, Briefcase, Eye } from 'lucide-react';

type StatusFilter = 'all' | JobStatus;

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'pending', label: 'Pending' },
    { value: 'running', label: 'Running' },
    { value: 'failed', label: 'Failed' },
    { value: 'dead', label: 'Dead' },
];

function statusVariant(status: JobStatus): 'default' | 'secondary' | 'destructive' | 'outline' {
    switch (status) {
        case 'pending': return 'outline';
        case 'running': return 'secondary';
        case 'completed': return 'default';
        case 'failed': return 'destructive';
        case 'retrying': return 'secondary';
        case 'dead': return 'destructive';
        default: return 'outline';
    }
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

interface StatCardProps {
    title: string;
    value: number | undefined;
    loading: boolean;
}

function StatCard({ title, value, loading }: StatCardProps) {
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <Skeleton className="h-8 w-16" />
                ) : (
                    <p className="text-2xl font-bold">{value ?? 0}</p>
                )}
            </CardContent>
        </Card>
    );
}

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [stats, setStats] = useState<JobStats | null>(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [statsLoading, setStatsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
    const [selectedJob, setSelectedJob] = useState<Job | null>(null);
    const [viewOpen, setViewOpen] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    const fetchStats = useCallback(async () => {
        try {
            const s = await jobsService.getStats();
            setStats(s);
        } catch {
            // Stats fetch failure is non-blocking
        } finally {
            setStatsLoading(false);
        }
    }, []);

    const fetchJobs = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = statusFilter !== 'all' ? { status: statusFilter, limit: 100 } : { limit: 100 };
            const response = await jobsService.list(params);
            setJobs(response.items);
            setTotal(response.total);
        } catch {
            setError('Failed to load jobs. Please try again.');
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await Promise.all([fetchStats(), fetchJobs()]);
        setRefreshing(false);
    };

    // Initial load
    useEffect(() => {
        fetchStats();
        fetchJobs();
    }, [fetchStats, fetchJobs]);

    // Auto-refresh stats every 10 seconds
    useEffect(() => {
        const interval = setInterval(fetchStats, 10_000);
        return () => clearInterval(interval);
    }, [fetchStats]);

    // Refetch jobs when filter changes
    useEffect(() => {
        fetchJobs();
    }, [fetchJobs]);

    const openView = (job: Job) => {
        setSelectedJob(job);
        setViewOpen(true);
    };

    return (
        <div className="p-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Briefcase className="h-8 w-8" />
                        Background Jobs
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Monitor and manage the background job queue
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                <StatCard title="Pending" value={stats?.pending} loading={statsLoading} />
                <StatCard title="Running" value={stats?.running} loading={statsLoading} />
                <StatCard title="Completed" value={stats?.completed} loading={statsLoading} />
                <StatCard title="Failed" value={stats?.failed} loading={statsLoading} />
                <StatCard title="Dead" value={stats?.dead} loading={statsLoading} />
            </div>

            {/* Filter Tabs + Table */}
            <div className="space-y-4">
                <Tabs value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
                    <TabsList>
                        {STATUS_TABS.map((tab) => (
                            <TabsTrigger key={tab.value} value={tab.value}>
                                {tab.label}
                            </TabsTrigger>
                        ))}
                    </TabsList>
                </Tabs>

                {error ? (
                    <div className="text-center py-8">
                        <p className="text-destructive">{error}</p>
                        <Button variant="outline" className="mt-4" onClick={fetchJobs}>
                            Try Again
                        </Button>
                    </div>
                ) : loading ? (
                    <div className="space-y-2">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                        ))}
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="text-center py-16">
                        <Briefcase className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <p className="text-muted-foreground">
                            {statusFilter === 'all' ? 'No jobs in the queue' : `No ${statusFilter} jobs`}
                        </p>
                    </div>
                ) : (
                    <div>
                        <p className="text-sm text-muted-foreground mb-3">
                            Showing {jobs.length} of {total} jobs
                        </p>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Handler</TableHead>
                                    <TableHead>Queue</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Priority</TableHead>
                                    <TableHead>Attempt #</TableHead>
                                    <TableHead>Created At</TableHead>
                                    <TableHead>Run At</TableHead>
                                    <TableHead>Completed At</TableHead>
                                    <TableHead className="w-16"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {jobs.map((job) => (
                                    <TableRow
                                        key={job.id}
                                        className="cursor-pointer"
                                        onClick={() => openView(job)}
                                    >
                                        <TableCell className="font-mono text-sm">{job.handler}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline">{job.queue}</Badge>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={statusVariant(job.status)}>
                                                {job.status}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>{job.priority}</TableCell>
                                        <TableCell>{job.attempt_number}/{job.max_retries}</TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {formatDate(job.created_at)}
                                        </TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {formatDate(job.run_at)}
                                        </TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {formatDate(job.completed_at)}
                                        </TableCell>
                                        <TableCell>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={(e) => { e.stopPropagation(); openView(job); }}
                                            >
                                                <Eye className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </div>

            {/* View Job Dialog */}
            {selectedJob && (
                <ViewJobDialog
                    job={selectedJob}
                    open={viewOpen}
                    onOpenChange={setViewOpen}
                    onUpdated={() => {
                        fetchJobs();
                        fetchStats();
                    }}
                />
            )}
        </div>
    );
}
