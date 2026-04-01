import { useCallback, useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
    Clock,
    Plus,
    RefreshCw,
    MoreHorizontal,
    Pencil,
    Trash2,
    Play,
} from 'lucide-react';
import { scheduledTasksService, type ScheduledTask } from '@/services/scheduledTasks.service';
import { CreateScheduledTaskDialog } from './CreateScheduledTaskDialog';
import { EditScheduledTaskDialog } from './EditScheduledTaskDialog';
import { DeleteScheduledTaskDialog } from './DeleteScheduledTaskDialog';
import { useToast } from '@/hooks/use-toast';

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

export default function ScheduledTasksPage() {
    const { toast } = useToast();
    const [tasks, setTasks] = useState<ScheduledTask[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const [triggeringId, setTriggeringId] = useState<string | null>(null);

    const [createOpen, setCreateOpen] = useState(false);
    const [editTask, setEditTask] = useState<ScheduledTask | null>(null);
    const [deleteTask, setDeleteTask] = useState<ScheduledTask | null>(null);

    const fetchTasks = useCallback(async () => {
        setError(null);
        try {
            const response = await scheduledTasksService.list();
            setTasks(response.items);
            setTotal(response.total);
        } catch {
            setError('Failed to load scheduled tasks. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchTasks();
        setRefreshing(false);
    };

    const handleToggle = async (task: ScheduledTask) => {
        setTogglingId(task.id);
        try {
            const updated = await scheduledTasksService.toggle(task.id);
            setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
        } catch {
            toast({ title: 'Error', description: 'Failed to toggle task', variant: 'destructive' });
        } finally {
            setTogglingId(null);
        }
    };

    const handleTrigger = async (task: ScheduledTask) => {
        setTriggeringId(task.id);
        try {
            const result = await scheduledTasksService.trigger(task.id);
            toast({ title: 'Job enqueued', description: result.message });
        } catch {
            toast({ title: 'Error', description: 'Failed to trigger task', variant: 'destructive' });
        } finally {
            setTriggeringId(null);
        }
    };

    const enabledCount = tasks.filter((t) => t.enabled).length;
    const disabledCount = tasks.length - enabledCount;

    return (
        <div className="p-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Clock className="h-8 w-8" />
                        Scheduled Tasks
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Manage recurring background tasks with cron expressions
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button size="sm" onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Task
                    </Button>
                </div>
            </div>

            {/* Stats row */}
            {!loading && tasks.length > 0 && (
                <div className="flex gap-4 text-sm text-muted-foreground">
                    <span>{total} total</span>
                    <span className="text-green-600 dark:text-green-400">{enabledCount} enabled</span>
                    <span>{disabledCount} disabled</span>
                </div>
            )}

            {/* Table */}
            {error ? (
                <div className="text-center py-8">
                    <p className="text-destructive">{error}</p>
                    <Button variant="outline" className="mt-4" onClick={fetchTasks}>
                        Try Again
                    </Button>
                </div>
            ) : loading ? (
                <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-14 w-full" />
                    ))}
                </div>
            ) : tasks.length === 0 ? (
                <div className="text-center py-24 border rounded-lg">
                    <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-medium mb-1">No scheduled tasks</p>
                    <p className="text-muted-foreground text-sm mb-6">
                        Create a task to run recurring background jobs on a cron schedule.
                    </p>
                    <Button onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Task
                    </Button>
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Schedule</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Last Run</TableHead>
                            <TableHead>Next Run</TableHead>
                            <TableHead className="w-10"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {tasks.map((task) => (
                            <TableRow key={task.id}>
                                <TableCell>
                                    <div>
                                        <p className="font-medium">{task.name}</p>
                                        {task.description && (
                                            <p className="text-xs text-muted-foreground truncate max-w-[240px]">
                                                {task.description}
                                            </p>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <div>
                                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                                            {task.cron ?? '—'}
                                        </code>
                                        {task.cron_description && (
                                            <p className="text-xs text-muted-foreground mt-0.5">
                                                {task.cron_description}
                                            </p>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-2">
                                        <Switch
                                            checked={task.enabled}
                                            disabled={togglingId === task.id}
                                            onCheckedChange={() => handleToggle(task)}
                                        />
                                        <Badge variant={task.enabled ? 'default' : 'secondary'}>
                                            {task.enabled ? 'Enabled' : 'Disabled'}
                                        </Badge>
                                    </div>
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                    {formatDate(task.last_run_at)}
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                    {task.enabled ? formatDate(task.next_run_at) : '—'}
                                </TableCell>
                                <TableCell>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon">
                                                <MoreHorizontal className="h-4 w-4" />
                                                <span className="sr-only">Actions</span>
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem
                                                onClick={() => handleTrigger(task)}
                                                disabled={triggeringId === task.id}
                                            >
                                                <Play className="h-4 w-4 mr-2" />
                                                Run Now
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setEditTask(task)}>
                                                <Pencil className="h-4 w-4 mr-2" />
                                                Edit
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem
                                                className="text-destructive focus:text-destructive"
                                                onClick={() => setDeleteTask(task)}
                                            >
                                                <Trash2 className="h-4 w-4 mr-2" />
                                                Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}

            {/* Dialogs */}
            <CreateScheduledTaskDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCreated={fetchTasks}
            />

            {editTask && (
                <EditScheduledTaskDialog
                    task={editTask}
                    open={editTask !== null}
                    onOpenChange={(open) => { if (!open) setEditTask(null); }}
                    onUpdated={() => { setEditTask(null); fetchTasks(); }}
                />
            )}

            {deleteTask && (
                <DeleteScheduledTaskDialog
                    task={deleteTask}
                    open={deleteTask !== null}
                    onOpenChange={(open) => { if (!open) setDeleteTask(null); }}
                    onDeleted={() => { setDeleteTask(null); fetchTasks(); }}
                />
            )}
        </div>
    );
}
