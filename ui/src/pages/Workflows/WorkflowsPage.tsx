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
    GitMerge,
    Plus,
    RefreshCw,
    MoreHorizontal,
    Pencil,
    Trash2,
    Play,
    Eye,
} from 'lucide-react';
import { workflowsService, type Workflow } from '@/services/workflows.service';
import { CreateWorkflowDialog } from './CreateWorkflowDialog';
import { EditWorkflowDialog } from './EditWorkflowDialog';
import { ViewWorkflowDialog } from './ViewWorkflowDialog';
import { DeleteWorkflowDialog } from './DeleteWorkflowDialog';
import { useToast } from '@/hooks/use-toast';

function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

// ---------------------------------------------------------------------------
// Trigger badge
// ---------------------------------------------------------------------------

function TriggerBadge({ triggerType }: { triggerType: string }) {
    const map: Record<string, string> = {
        event: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
        schedule: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
        manual: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
        webhook: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
    };
    const cls = map[triggerType] ?? 'bg-gray-100 text-gray-700';
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${cls}`}>
            {triggerType}
        </span>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function WorkflowsPage() {
    const { toast } = useToast();
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const [triggeringId, setTriggeringId] = useState<string | null>(null);

    const [createOpen, setCreateOpen] = useState(false);
    const [viewWorkflow, setViewWorkflow] = useState<Workflow | null>(null);
    const [editWorkflow, setEditWorkflow] = useState<Workflow | null>(null);
    const [deleteWorkflow, setDeleteWorkflow] = useState<Workflow | null>(null);

    const fetchWorkflows = useCallback(async () => {
        setError(null);
        try {
            const res = await workflowsService.list();
            setWorkflows(res.items);
            setTotal(res.total);
        } catch {
            setError('Failed to load workflows. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchWorkflows();
    }, [fetchWorkflows]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchWorkflows();
        setRefreshing(false);
    };

    const handleToggle = async (workflow: Workflow) => {
        setTogglingId(workflow.id);
        try {
            const updated = await workflowsService.toggle(workflow.id);
            setWorkflows((prev) => prev.map((w) => (w.id === workflow.id ? updated : w)));
        } catch {
            toast({ title: 'Error', description: 'Failed to toggle workflow', variant: 'destructive' });
        } finally {
            setTogglingId(null);
        }
    };

    const handleTrigger = async (workflow: Workflow) => {
        setTriggeringId(workflow.id);
        try {
            const result = await workflowsService.trigger(workflow.id);
            toast({
                title: 'Workflow triggered',
                description: `Instance ${result.instance_id.slice(0, 8)}… started`,
            });
        } catch {
            toast({ title: 'Error', description: 'Failed to trigger workflow', variant: 'destructive' });
        } finally {
            setTriggeringId(null);
        }
    };

    const enabledCount = workflows.filter((w) => w.enabled).length;
    const disabledCount = workflows.length - enabledCount;

    return (
        <div className="p-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <GitMerge className="h-8 w-8" />
                        Workflows
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Automate multi-step business processes with conditional branching and waiting steps
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button size="sm" onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Workflow
                    </Button>
                </div>
            </div>

            {/* Stats row */}
            {!loading && workflows.length > 0 && (
                <div className="flex gap-4 text-sm text-muted-foreground">
                    <span>{total} total</span>
                    <span className="text-green-600 dark:text-green-400">{enabledCount} enabled</span>
                    <span>{disabledCount} disabled</span>
                </div>
            )}

            {/* Content */}
            {error ? (
                <div className="text-center py-8">
                    <p className="text-destructive">{error}</p>
                    <Button variant="outline" className="mt-4" onClick={fetchWorkflows}>
                        Try Again
                    </Button>
                </div>
            ) : loading ? (
                <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-14 w-full" />
                    ))}
                </div>
            ) : workflows.length === 0 ? (
                <div className="text-center py-24 border rounded-lg">
                    <GitMerge className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-medium mb-1">No workflows yet</p>
                    <p className="text-muted-foreground text-sm mb-6">
                        Create a workflow to automate multi-step processes triggered by events, schedules, or API calls.
                    </p>
                    <Button onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Workflow
                    </Button>
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Trigger</TableHead>
                            <TableHead>Steps</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Created</TableHead>
                            <TableHead className="w-10"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {workflows.map((wf) => (
                            <TableRow key={wf.id}>
                                <TableCell>
                                    <div>
                                        <p className="font-medium">{wf.name}</p>
                                        {wf.description && (
                                            <p className="text-xs text-muted-foreground truncate max-w-[220px]">
                                                {wf.description}
                                            </p>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <div className="space-y-0.5">
                                        <TriggerBadge triggerType={wf.trigger_type} />
                                        {wf.trigger_config.type === 'event' && (
                                            <p className="text-xs text-muted-foreground">
                                                <code>{wf.trigger_config.event}</code>
                                                {wf.trigger_config.collection && (
                                                    <> · {wf.trigger_config.collection}</>
                                                )}
                                            </p>
                                        )}
                                        {wf.trigger_config.type === 'schedule' && (
                                            <code className="text-xs text-muted-foreground">
                                                {wf.trigger_config.cron}
                                            </code>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <Badge variant="secondary" className="text-xs">
                                        {wf.steps.length} step{wf.steps.length !== 1 ? 's' : ''}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-2">
                                        <Switch
                                            checked={wf.enabled}
                                            disabled={togglingId === wf.id}
                                            onCheckedChange={() => handleToggle(wf)}
                                        />
                                        <Badge variant={wf.enabled ? 'default' : 'secondary'}>
                                            {wf.enabled ? 'Enabled' : 'Disabled'}
                                        </Badge>
                                    </div>
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                    {formatDate(wf.created_at)}
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
                                                onClick={() => handleTrigger(wf)}
                                                disabled={triggeringId === wf.id}
                                            >
                                                <Play className="h-4 w-4 mr-2" />
                                                Run Now
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setViewWorkflow(wf)}>
                                                <Eye className="h-4 w-4 mr-2" />
                                                View
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setEditWorkflow(wf)}>
                                                <Pencil className="h-4 w-4 mr-2" />
                                                Edit
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem
                                                className="text-destructive focus:text-destructive"
                                                onClick={() => setDeleteWorkflow(wf)}
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
            <CreateWorkflowDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCreated={fetchWorkflows}
            />

            {viewWorkflow && (
                <ViewWorkflowDialog
                    workflow={viewWorkflow}
                    open={viewWorkflow !== null}
                    onOpenChange={(open) => { if (!open) setViewWorkflow(null); }}
                />
            )}

            {editWorkflow && (
                <EditWorkflowDialog
                    workflow={editWorkflow}
                    open={editWorkflow !== null}
                    onOpenChange={(open) => { if (!open) setEditWorkflow(null); }}
                    onUpdated={() => { setEditWorkflow(null); fetchWorkflows(); }}
                />
            )}

            {deleteWorkflow && (
                <DeleteWorkflowDialog
                    workflow={deleteWorkflow}
                    open={deleteWorkflow !== null}
                    onOpenChange={(open) => { if (!open) setDeleteWorkflow(null); }}
                    onDeleted={() => { setDeleteWorkflow(null); fetchWorkflows(); }}
                />
            )}
        </div>
    );
}
