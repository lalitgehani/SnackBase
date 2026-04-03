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
import { hooksService, type Hook, type HookExecution } from '@/services/hooks.service';

interface Props {
    hook: Hook;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

function TriggerLabel({ hook }: { hook: Hook }) {
    if (hook.trigger.type === 'manual') {
        return <Badge variant="outline">Manual</Badge>;
    }
    const t = hook.trigger as { type: 'event'; event: string; collection?: string };
    return (
        <span className="flex items-center gap-1.5 flex-wrap">
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{t.event}</code>
            {t.collection && (
                <span className="text-xs text-muted-foreground">on <strong>{t.collection}</strong></span>
            )}
        </span>
    );
}

function StatusBadge({ status }: { status: HookExecution['status'] }) {
    const map = {
        success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        partial: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    };
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${map[status]}`}>
            {status}
        </span>
    );
}

export function ViewHookDialog({ hook, open, onOpenChange }: Props) {
    const [executions, setExecutions] = useState<HookExecution[]>([]);
    const [execLoading, setExecLoading] = useState(false);
    const [execError, setExecError] = useState<string | null>(null);

    useEffect(() => {
        if (!open) return;
        setExecLoading(true);
        setExecError(null);
        hooksService
            .listExecutions(hook.id)
            .then((res) => setExecutions(res.items))
            .catch(() => setExecError('Failed to load execution history.'))
            .finally(() => setExecLoading(false));
    }, [open, hook.id]);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[620px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{hook.name}</DialogTitle>
                </DialogHeader>

                <Tabs defaultValue="details">
                    <TabsList className="w-full">
                        <TabsTrigger value="details" className="flex-1">Details</TabsTrigger>
                        <TabsTrigger value="executions" className="flex-1">Execution History</TabsTrigger>
                    </TabsList>

                    <TabsContent value="details" className="space-y-3 pt-3">
                        {hook.description && (
                            <p className="text-sm text-muted-foreground">{hook.description}</p>
                        )}

                        <div className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
                            <span className="text-muted-foreground font-medium">Status</span>
                            <Badge variant={hook.enabled ? 'default' : 'secondary'}>
                                {hook.enabled ? 'Enabled' : 'Disabled'}
                            </Badge>

                            <span className="text-muted-foreground font-medium">Trigger</span>
                            <TriggerLabel hook={hook} />

                            <span className="text-muted-foreground font-medium">Condition</span>
                            <span>
                                {hook.condition ? (
                                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded break-all">
                                        {hook.condition}
                                    </code>
                                ) : (
                                    <span className="text-muted-foreground">—</span>
                                )}
                            </span>

                            <span className="text-muted-foreground font-medium">Last run</span>
                            <span>{formatDate(hook.last_run_at)}</span>

                            <span className="text-muted-foreground font-medium">Created</span>
                            <span>{formatDate(hook.created_at)}</span>
                        </div>

                        {hook.actions.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-sm font-medium">
                                    Actions ({hook.actions.length})
                                </p>
                                <div className="space-y-1.5">
                                    {hook.actions.map((action, i) => (
                                        <div
                                            key={i}
                                            className="flex items-start gap-2 border rounded-md p-2.5 text-xs"
                                        >
                                            <span className="font-medium text-muted-foreground w-5 shrink-0">
                                                {i + 1}.
                                            </span>
                                            <div className="flex-1 min-w-0">
                                                <code className="bg-muted px-1.5 py-0.5 rounded">
                                                    {action.type}
                                                </code>
                                                {action.type === 'send_webhook' && action.url && (
                                                    <p className="text-muted-foreground truncate mt-0.5">
                                                        {String(action.method ?? 'POST')} {String(action.url)}
                                                    </p>
                                                )}
                                                {action.type === 'send_email' && action.to && (
                                                    <p className="text-muted-foreground mt-0.5">
                                                        to: {String(action.to)}
                                                    </p>
                                                )}
                                                {(action.type === 'create_record' ||
                                                    action.type === 'update_record' ||
                                                    action.type === 'delete_record') &&
                                                    action.collection && (
                                                        <p className="text-muted-foreground mt-0.5">
                                                            collection: {String(action.collection)}
                                                        </p>
                                                    )}
                                                {action.type === 'enqueue_job' && action.handler && (
                                                    <p className="text-muted-foreground mt-0.5">
                                                        handler: {String(action.handler)}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="executions" className="pt-3">
                        {execLoading ? (
                            <div className="space-y-2">
                                {[1, 2, 3].map((i) => (
                                    <Skeleton key={i} className="h-10 w-full" />
                                ))}
                            </div>
                        ) : execError ? (
                            <p className="text-sm text-destructive">{execError}</p>
                        ) : executions.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-8">
                                No executions yet.
                            </p>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Actions</TableHead>
                                        <TableHead>Duration</TableHead>
                                        <TableHead>Executed At</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {executions.map((exec) => (
                                        <TableRow key={exec.id}>
                                            <TableCell>
                                                <StatusBadge status={exec.status} />
                                                {exec.error_message && (
                                                    <p className="text-xs text-muted-foreground mt-0.5 max-w-[200px] truncate">
                                                        {exec.error_message}
                                                    </p>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-sm">
                                                {exec.actions_executed}
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {exec.duration_ms != null ? `${exec.duration_ms}ms` : '—'}
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {formatDate(exec.executed_at)}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
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
