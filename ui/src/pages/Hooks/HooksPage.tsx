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
    Zap,
    Plus,
    RefreshCw,
    MoreHorizontal,
    Pencil,
    Trash2,
    Play,
    Eye,
} from 'lucide-react';
import { hooksService, type Hook } from '@/services/hooks.service';
import { CreateHookDialog } from './CreateHookDialog';
import { EditHookDialog } from './EditHookDialog';
import { ViewHookDialog } from './ViewHookDialog';
import { DeleteHookDialog } from './DeleteHookDialog';
import { useToast } from '@/hooks/use-toast';

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

function TriggerCell({ hook }: { hook: Hook }) {
    if (hook.trigger.type === 'manual') {
        return <Badge variant="outline" className="text-xs">Manual</Badge>;
    }
    const t = hook.trigger as { type: 'event'; event: string; collection?: string };
    return (
        <div>
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{t.event}</code>
            {t.collection && (
                <p className="text-xs text-muted-foreground mt-0.5">
                    on <strong>{t.collection}</strong>
                </p>
            )}
        </div>
    );
}

export default function HooksPage() {
    const { toast } = useToast();
    const [hooks, setHooks] = useState<Hook[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const [triggeringId, setTriggeringId] = useState<string | null>(null);

    const [createOpen, setCreateOpen] = useState(false);
    const [viewHook, setViewHook] = useState<Hook | null>(null);
    const [editHook, setEditHook] = useState<Hook | null>(null);
    const [deleteHook, setDeleteHook] = useState<Hook | null>(null);

    const fetchHooks = useCallback(async () => {
        setError(null);
        try {
            const response = await hooksService.list();
            setHooks(response.items);
            setTotal(response.total);
        } catch {
            setError('Failed to load hooks. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchHooks();
    }, [fetchHooks]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchHooks();
        setRefreshing(false);
    };

    const handleToggle = async (hook: Hook) => {
        setTogglingId(hook.id);
        try {
            const updated = await hooksService.toggle(hook.id);
            setHooks((prev) => prev.map((h) => (h.id === hook.id ? updated : h)));
        } catch {
            toast({ title: 'Error', description: 'Failed to toggle hook', variant: 'destructive' });
        } finally {
            setTogglingId(null);
        }
    };

    const handleTrigger = async (hook: Hook) => {
        setTriggeringId(hook.id);
        try {
            const result = await hooksService.trigger(hook.id);
            toast({
                title: result.status === 'success' ? 'Hook executed' : 'Hook triggered',
                description: result.error ?? result.message ?? `${result.actions_executed} action(s) executed`,
            });
        } catch {
            toast({ title: 'Error', description: 'Failed to trigger hook', variant: 'destructive' });
        } finally {
            setTriggeringId(null);
        }
    };

    const enabledCount = hooks.filter((h) => h.enabled).length;
    const disabledCount = hooks.length - enabledCount;

    return (
        <div className="p-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Zap className="h-8 w-8" />
                        Hooks
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Automate business logic with event-driven and manual hooks
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button size="sm" onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Hook
                    </Button>
                </div>
            </div>

            {/* Stats row */}
            {!loading && hooks.length > 0 && (
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
                    <Button variant="outline" className="mt-4" onClick={fetchHooks}>
                        Try Again
                    </Button>
                </div>
            ) : loading ? (
                <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-14 w-full" />
                    ))}
                </div>
            ) : hooks.length === 0 ? (
                <div className="text-center py-24 border rounded-lg">
                    <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-medium mb-1">No hooks yet</p>
                    <p className="text-muted-foreground text-sm mb-6">
                        Create a hook to run actions when events occur or trigger them manually.
                    </p>
                    <Button onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Hook
                    </Button>
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Trigger</TableHead>
                            <TableHead>Condition</TableHead>
                            <TableHead>Actions</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Last Run</TableHead>
                            <TableHead className="w-10"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {hooks.map((hook) => (
                            <TableRow key={hook.id}>
                                <TableCell>
                                    <div>
                                        <p className="font-medium">{hook.name}</p>
                                        {hook.description && (
                                            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                                {hook.description}
                                            </p>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <TriggerCell hook={hook} />
                                </TableCell>
                                <TableCell>
                                    {hook.condition ? (
                                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded max-w-[160px] truncate block">
                                            {hook.condition}
                                        </code>
                                    ) : (
                                        <span className="text-muted-foreground text-sm">—</span>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <Badge variant="secondary" className="text-xs">
                                        {hook.actions.length} action{hook.actions.length !== 1 ? 's' : ''}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-2">
                                        <Switch
                                            checked={hook.enabled}
                                            disabled={togglingId === hook.id}
                                            onCheckedChange={() => handleToggle(hook)}
                                        />
                                        <Badge variant={hook.enabled ? 'default' : 'secondary'}>
                                            {hook.enabled ? 'Enabled' : 'Disabled'}
                                        </Badge>
                                    </div>
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                    {formatDate(hook.last_run_at)}
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
                                                onClick={() => handleTrigger(hook)}
                                                disabled={triggeringId === hook.id}
                                            >
                                                <Play className="h-4 w-4 mr-2" />
                                                Run Now
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setViewHook(hook)}>
                                                <Eye className="h-4 w-4 mr-2" />
                                                View
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setEditHook(hook)}>
                                                <Pencil className="h-4 w-4 mr-2" />
                                                Edit
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem
                                                className="text-destructive focus:text-destructive"
                                                onClick={() => setDeleteHook(hook)}
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
            <CreateHookDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCreated={fetchHooks}
            />

            {viewHook && (
                <ViewHookDialog
                    hook={viewHook}
                    open={viewHook !== null}
                    onOpenChange={(open) => { if (!open) setViewHook(null); }}
                />
            )}

            {editHook && (
                <EditHookDialog
                    hook={editHook}
                    open={editHook !== null}
                    onOpenChange={(open) => { if (!open) setEditHook(null); }}
                    onUpdated={() => { setEditHook(null); fetchHooks(); }}
                />
            )}

            {deleteHook && (
                <DeleteHookDialog
                    hook={deleteHook}
                    open={deleteHook !== null}
                    onOpenChange={(open) => { if (!open) setDeleteHook(null); }}
                    onDeleted={() => { setDeleteHook(null); fetchHooks(); }}
                />
            )}
        </div>
    );
}
