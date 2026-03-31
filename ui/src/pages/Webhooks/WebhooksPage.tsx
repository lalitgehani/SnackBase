import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import { webhooksService, type WebhookListItem } from '@/services/webhooks.service';
import { CreateWebhookDialog } from './CreateWebhookDialog';
import { EditWebhookDialog } from './EditWebhookDialog';
import { ViewWebhookDialog } from './ViewWebhookDialog';
import { DeleteWebhookDialog } from './DeleteWebhookDialog';
import { useToast } from '@/hooks/use-toast';
import { Plus, Eye, Pencil, Trash2, Webhook, RefreshCw } from 'lucide-react';

export function WebhooksPage() {
    const [webhooks, setWebhooks] = useState<WebhookListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [createOpen, setCreateOpen] = useState(false);
    const [editOpen, setEditOpen] = useState(false);
    const [viewOpen, setViewOpen] = useState(false);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [selected, setSelected] = useState<WebhookListItem | null>(null);
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const { toast } = useToast();

    const fetchWebhooks = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await webhooksService.list();
            setWebhooks(response.items);
        } catch {
            setError('Failed to load webhooks. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWebhooks();
    }, []);

    const handleToggleEnabled = async (webhook: WebhookListItem) => {
        setTogglingId(webhook.id);
        try {
            await webhooksService.update(webhook.id, { enabled: !webhook.enabled });
            setWebhooks((prev) =>
                prev.map((w) => (w.id === webhook.id ? { ...w, enabled: !w.enabled } : w))
            );
        } catch {
            toast({
                title: 'Failed to update webhook',
                variant: 'destructive',
            });
        } finally {
            setTogglingId(null);
        }
    };

    const openEdit = (webhook: WebhookListItem) => {
        setSelected(webhook);
        setEditOpen(true);
    };

    const openView = (webhook: WebhookListItem) => {
        setSelected(webhook);
        setViewOpen(true);
    };

    const openDelete = (webhook: WebhookListItem) => {
        setSelected(webhook);
        setDeleteOpen(true);
    };

    return (
        <div className="p-8 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
                    <p className="text-muted-foreground">
                        Configure outbound webhooks to notify external services on record changes.
                    </p>
                </div>
                <Button onClick={() => setCreateOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Create Webhook
                </Button>
            </div>

            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Outbound Webhooks</CardTitle>
                        <CardDescription>
                            Webhooks fire an HTTP POST when matching record events occur.
                        </CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={fetchWebhooks} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : error ? (
                        <div className="text-center py-8 text-destructive">
                            <p>{error}</p>
                            <Button variant="outline" className="mt-4" onClick={fetchWebhooks}>
                                Try again
                            </Button>
                        </div>
                    ) : webhooks.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Webhook className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
                            <h3 className="text-lg font-medium">No webhooks configured</h3>
                            <p className="text-muted-foreground mb-6">
                                Create a webhook to start sending record events to external services.
                            </p>
                            <Button variant="outline" onClick={() => setCreateOpen(true)}>
                                <Plus className="mr-2 h-4 w-4" /> Create your first webhook
                            </Button>
                        </div>
                    ) : (
                        <>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>URL</TableHead>
                                        <TableHead>Collection</TableHead>
                                        <TableHead>Events</TableHead>
                                        <TableHead>Enabled</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {webhooks.map((webhook) => (
                                        <TableRow key={webhook.id}>
                                            <TableCell className="max-w-xs">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <span className="font-mono text-xs truncate block max-w-[200px] cursor-default">
                                                                {webhook.url}
                                                            </span>
                                                        </TooltipTrigger>
                                                        <TooltipContent className="max-w-sm break-all">
                                                            {webhook.url}
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline">{webhook.collection}</Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex gap-1 flex-wrap">
                                                    {webhook.events.map((e) => (
                                                        <Badge key={e} variant="secondary" className="capitalize text-xs">
                                                            {e}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <Switch
                                                    checked={webhook.enabled}
                                                    onCheckedChange={() => handleToggleEnabled(webhook)}
                                                    disabled={togglingId === webhook.id}
                                                />
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => openView(webhook)}
                                                        title="View details"
                                                    >
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => openEdit(webhook)}
                                                        title="Edit"
                                                    >
                                                        <Pencil className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                        onClick={() => openDelete(webhook)}
                                                        title="Delete"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                            <p className="text-sm text-muted-foreground mt-2">
                                {webhooks.length} webhook{webhooks.length !== 1 ? 's' : ''} configured
                            </p>
                        </>
                    )}
                </CardContent>
            </Card>

            <CreateWebhookDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCreated={fetchWebhooks}
            />
            <EditWebhookDialog
                webhook={selected}
                open={editOpen}
                onOpenChange={setEditOpen}
                onUpdated={fetchWebhooks}
            />
            <ViewWebhookDialog
                webhook={selected}
                open={viewOpen}
                onOpenChange={setViewOpen}
            />
            <DeleteWebhookDialog
                webhook={selected}
                open={deleteOpen}
                onOpenChange={setDeleteOpen}
                onDeleted={fetchWebhooks}
            />
        </div>
    );
}

export default WebhooksPage;
