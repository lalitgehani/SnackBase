import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from '@/components/ui/tabs';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';
import {
    workflowsService,
    type Workflow,
    type WorkflowInstance,
    type WorkflowStepLog,
    type WorkflowInstanceDetail,
} from '@/services/workflows.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
    workflow: Workflow;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

// ---------------------------------------------------------------------------
// Instance status badge
// ---------------------------------------------------------------------------

type InstanceStatus = WorkflowInstance['status'];

function InstanceStatusBadge({ status }: { status: InstanceStatus }) {
    const map: Record<InstanceStatus, string> = {
        pending: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
        running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
        waiting: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
        completed: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
        failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
        cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
    };
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${map[status] ?? ''}`}>
            {status}
        </span>
    );
}

function StepLogStatusBadge({ status }: { status: string }) {
    const cls =
        status === 'completed'
            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
            : status === 'failed'
              ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
              : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300';
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
            {status}
        </span>
    );
}

// ---------------------------------------------------------------------------
// Copyable text
// ---------------------------------------------------------------------------

function CopyText({ value }: { value: string }) {
    const [copied, setCopied] = useState(false);
    const copy = () => {
        navigator.clipboard.writeText(value).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        });
    };
    return (
        <span className="flex items-center gap-1.5 flex-wrap">
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded break-all">{value}</code>
            <Button variant="ghost" size="icon" className="h-5 w-5" onClick={copy}>
                {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
            </Button>
        </span>
    );
}

// ---------------------------------------------------------------------------
// Details tab
// ---------------------------------------------------------------------------

function DetailsTab({ workflow }: { workflow: Workflow }) {
    const tc = workflow.trigger_config;
    const webhookToken = tc.type === 'webhook' ? (tc as { type: 'webhook'; token?: string }).token : null;

    return (
        <div className="space-y-4 pt-3">
            {workflow.description && (
                <p className="text-sm text-muted-foreground">{workflow.description}</p>
            )}

            <div className="grid grid-cols-[120px_1fr] gap-y-2.5 text-sm">
                <span className="text-muted-foreground font-medium">Status</span>
                <Badge variant={workflow.enabled ? 'default' : 'secondary'}>
                    {workflow.enabled ? 'Enabled' : 'Disabled'}
                </Badge>

                <span className="text-muted-foreground font-medium">Trigger</span>
                <span>
                    <Badge variant="outline" className="text-xs capitalize">
                        {workflow.trigger_type}
                    </Badge>
                    {tc.type === 'event' && (
                        <span className="ml-2 text-xs text-muted-foreground">
                            <code className="bg-muted px-1 py-0.5 rounded">{tc.event}</code>
                            {tc.collection && <> on <strong>{tc.collection}</strong></>}
                        </span>
                    )}
                    {tc.type === 'schedule' && (
                        <code className="ml-2 text-xs bg-muted px-1.5 py-0.5 rounded">{tc.cron}</code>
                    )}
                </span>

                {webhookToken && (
                    <>
                        <span className="text-muted-foreground font-medium">Webhook URL</span>
                        <CopyText value={`/api/v1/workflow-webhooks/${webhookToken}`} />
                    </>
                )}

                <span className="text-muted-foreground font-medium">Created</span>
                <span className="text-sm">{formatDate(workflow.created_at)}</span>
            </div>

            {/* Steps */}
            {workflow.steps.length > 0 && (
                <div className="space-y-2">
                    <p className="text-sm font-medium">Steps ({workflow.steps.length})</p>
                    <div className="space-y-1.5">
                        {workflow.steps.map((step, i) => (
                            <div
                                key={i}
                                className="flex items-start gap-2 border rounded-md p-2.5 text-xs"
                            >
                                <span className="font-medium text-muted-foreground w-5 shrink-0">
                                    {i + 1}.
                                </span>
                                <div className="flex-1 min-w-0 space-y-0.5">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                        <code className="font-mono font-medium">{String(step.name)}</code>
                                        <Badge variant="secondary" className="text-xs">{String(step.type)}</Badge>
                                    </div>
                                    {step.type === 'action' && step.action_type && (
                                        <p className="text-muted-foreground">action: {String(step.action_type)}</p>
                                    )}
                                    {step.type === 'condition' && step.expression && (
                                        <p className="text-muted-foreground font-mono truncate">if: {String(step.expression)}</p>
                                    )}
                                    {step.type === 'wait_delay' && step.duration && (
                                        <p className="text-muted-foreground">delay: {String(step.duration)}</p>
                                    )}
                                    {step.type === 'wait_event' && step.event && (
                                        <p className="text-muted-foreground">event: {String(step.event)}</p>
                                    )}
                                    {step.next && (
                                        <p className="text-muted-foreground">next: <code className="font-mono">{String(step.next)}</code></p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Instance row (expandable)
// ---------------------------------------------------------------------------

interface InstanceRowProps {
    instance: WorkflowInstance;
    onCancel: (id: string) => void;
    onResume: (id: string) => void;
    cancellingId: string | null;
    resumingId: string | null;
}

function InstanceRow({ instance, onCancel, onResume, cancellingId, resumingId }: InstanceRowProps) {
    const [expanded, setExpanded] = useState(false);
    const [detail, setDetail] = useState<WorkflowInstanceDetail | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);

    const handleExpand = async () => {
        if (!expanded && !detail) {
            setDetailLoading(true);
            try {
                const d = await workflowsService.getInstance(instance.id);
                setDetail(d);
            } catch {
                // ignore
            } finally {
                setDetailLoading(false);
            }
        }
        setExpanded((v) => !v);
    };

    const canCancel = instance.status === 'running' || instance.status === 'waiting' || instance.status === 'pending';
    const canResume = instance.status === 'failed' || instance.status === 'waiting';

    return (
        <>
            <TableRow className="cursor-pointer hover:bg-muted/40" onClick={handleExpand}>
                <TableCell>
                    {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                </TableCell>
                <TableCell>
                    <InstanceStatusBadge status={instance.status} />
                </TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                    {instance.current_step ?? '—'}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                    {formatDate(instance.started_at)}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                    {formatDate(instance.completed_at)}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-1">
                        {canCancel && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="h-6 text-xs"
                                disabled={cancellingId === instance.id}
                                onClick={() => onCancel(instance.id)}
                            >
                                Cancel
                            </Button>
                        )}
                        {canResume && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="h-6 text-xs"
                                disabled={resumingId === instance.id}
                                onClick={() => onResume(instance.id)}
                            >
                                Resume
                            </Button>
                        )}
                    </div>
                </TableCell>
            </TableRow>

            {expanded && (
                <TableRow>
                    <TableCell colSpan={6} className="bg-muted/20 p-0">
                        <div className="px-4 py-3">
                            {detailLoading ? (
                                <div className="space-y-1">
                                    {[1, 2].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
                                </div>
                            ) : detail && detail.step_logs.length > 0 ? (
                                <StepLogsTable logs={detail.step_logs} />
                            ) : (
                                <p className="text-xs text-muted-foreground">No step logs yet.</p>
                            )}
                            {instance.error_message && (
                                <p className="text-xs text-destructive mt-2">{instance.error_message}</p>
                            )}
                        </div>
                    </TableCell>
                </TableRow>
            )}
        </>
    );
}

function StepLogsTable({ logs }: { logs: WorkflowStepLog[] }) {
    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead className="text-xs">Step</TableHead>
                    <TableHead className="text-xs">Type</TableHead>
                    <TableHead className="text-xs">Status</TableHead>
                    <TableHead className="text-xs">Started</TableHead>
                    <TableHead className="text-xs">Completed</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {logs.map((log) => (
                    <TableRow key={log.id}>
                        <TableCell className="text-xs font-mono">{log.step_name}</TableCell>
                        <TableCell>
                            <Badge variant="secondary" className="text-xs">{log.step_type}</Badge>
                        </TableCell>
                        <TableCell>
                            <StepLogStatusBadge status={log.status} />
                            {log.error_message && (
                                <p className="text-xs text-muted-foreground mt-0.5 max-w-[200px] truncate">
                                    {log.error_message}
                                </p>
                            )}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDate(log.started_at)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDate(log.completed_at)}</TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
}

// ---------------------------------------------------------------------------
// Instances tab
// ---------------------------------------------------------------------------

function InstancesTab({ workflow }: { workflow: Workflow }) {
    const { toast } = useToast();
    const [instances, setInstances] = useState<WorkflowInstance[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [cancellingId, setCancellingId] = useState<string | null>(null);
    const [resumingId, setResumingId] = useState<string | null>(null);
    const [offset, setOffset] = useState(0);
    const limit = 50;

    const fetchInstances = async (off = 0) => {
        setLoading(true);
        setError(null);
        try {
            const res = await workflowsService.listInstances(workflow.id, { limit, offset: off });
            setInstances(res.items);
            setTotal(res.total);
            setOffset(off);
        } catch {
            setError('Failed to load instances.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInstances(0);
    }, [workflow.id]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleCancel = async (id: string) => {
        setCancellingId(id);
        try {
            await workflowsService.cancelInstance(id);
            toast({ title: 'Instance cancelled' });
            fetchInstances(offset);
        } catch {
            toast({ title: 'Error', description: 'Failed to cancel instance', variant: 'destructive' });
        } finally {
            setCancellingId(null);
        }
    };

    const handleResume = async (id: string) => {
        setResumingId(id);
        try {
            await workflowsService.resumeInstance(id);
            toast({ title: 'Resume started' });
            setTimeout(() => fetchInstances(offset), 800);
        } catch {
            toast({ title: 'Error', description: 'Failed to resume instance', variant: 'destructive' });
        } finally {
            setResumingId(null);
        }
    };

    if (loading) {
        return (
            <div className="space-y-2 pt-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
        );
    }

    if (error) {
        return <p className="text-sm text-destructive pt-3">{error}</p>;
    }

    if (instances.length === 0) {
        return (
            <p className="text-sm text-muted-foreground text-center py-8 pt-3">
                No instances yet. Trigger the workflow to start one.
            </p>
        );
    }

    return (
        <div className="pt-3 space-y-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{total} total instance{total !== 1 ? 's' : ''}</span>
                <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => fetchInstances(offset)}>
                    Refresh
                </Button>
            </div>

            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-6"></TableHead>
                        <TableHead className="text-xs">Status</TableHead>
                        <TableHead className="text-xs">Current Step</TableHead>
                        <TableHead className="text-xs">Started</TableHead>
                        <TableHead className="text-xs">Completed</TableHead>
                        <TableHead className="text-xs">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {instances.map((inst) => (
                        <InstanceRow
                            key={inst.id}
                            instance={inst}
                            onCancel={handleCancel}
                            onResume={handleResume}
                            cancellingId={cancellingId}
                            resumingId={resumingId}
                        />
                    ))}
                </TableBody>
            </Table>

            {/* Pagination */}
            {total > limit && (
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7"
                        disabled={offset === 0}
                        onClick={() => fetchInstances(Math.max(0, offset - limit))}
                    >
                        Previous
                    </Button>
                    <span>
                        {offset + 1}–{Math.min(offset + limit, total)} of {total}
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7"
                        disabled={offset + limit >= total}
                        onClick={() => fetchInstances(offset + limit)}
                    >
                        Next
                    </Button>
                </div>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main dialog
// ---------------------------------------------------------------------------

export function ViewWorkflowDialog({ workflow, open, onOpenChange }: Props) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{workflow.name}</DialogTitle>
                </DialogHeader>

                <Tabs defaultValue="details">
                    <TabsList className="w-full">
                        <TabsTrigger value="details" className="flex-1">Details</TabsTrigger>
                        <TabsTrigger value="instances" className="flex-1">Instances</TabsTrigger>
                    </TabsList>

                    <TabsContent value="details">
                        <DetailsTab workflow={workflow} />
                    </TabsContent>

                    <TabsContent value="instances">
                        <InstancesTab workflow={workflow} />
                    </TabsContent>
                </Tabs>

                <div className="flex justify-end pt-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
