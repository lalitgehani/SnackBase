import { useEffect, useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { webhooksService, type WebhookListItem, type WebhookDelivery } from '@/services/webhooks.service';
import { useToast } from '@/hooks/use-toast';
import { format, formatDistanceToNow } from 'date-fns';
import { CheckCircle, XCircle, Clock, AlertCircle, ChevronDown, ChevronUp, Zap } from 'lucide-react';

interface ViewWebhookDialogProps {
    webhook: WebhookListItem | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

function DeliveryStatusBadge({ status }: { status: string }) {
    if (status === 'delivered') {
        return <Badge variant="success" className="gap-1"><CheckCircle className="h-3 w-3" />Delivered</Badge>;
    }
    if (status === 'failed') {
        return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" />Failed</Badge>;
    }
    if (status === 'retrying') {
        return <Badge className="gap-1 border-transparent bg-amber-100 text-amber-800"><AlertCircle className="h-3 w-3" />Retrying</Badge>;
    }
    return <Badge variant="outline" className="gap-1 text-muted-foreground"><Clock className="h-3 w-3" />Pending</Badge>;
}

function DeliveryRow({ delivery }: { delivery: WebhookDelivery }) {
    const [expanded, setExpanded] = useState(false);

    return (
        <>
            <TableRow
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => setExpanded((v) => !v)}
            >
                <TableCell className="font-mono text-xs">{delivery.event}</TableCell>
                <TableCell><DeliveryStatusBadge status={delivery.status} /></TableCell>
                <TableCell className="text-center">
                    {delivery.response_status ? (
                        <span className={delivery.response_status < 300 ? 'text-green-600' : 'text-red-600'}>
                            {delivery.response_status}
                        </span>
                    ) : '—'}
                </TableCell>
                <TableCell className="text-center">{delivery.attempt_number}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                    {delivery.delivered_at
                        ? formatDistanceToNow(new Date(delivery.delivered_at), { addSuffix: true })
                        : '—'}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                    {expanded ? <ChevronUp className="h-4 w-4 ml-auto" /> : <ChevronDown className="h-4 w-4 ml-auto" />}
                </TableCell>
            </TableRow>
            {expanded && (
                <TableRow>
                    <TableCell colSpan={6} className="bg-muted/30 p-4 space-y-3">
                        <div>
                            <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">Request Payload</p>
                            <pre className="bg-background border rounded p-3 text-xs overflow-x-auto max-h-48 overflow-y-auto">
                                {JSON.stringify(delivery.payload, null, 2)}
                            </pre>
                        </div>
                        {delivery.response_body && (
                            <div>
                                <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">Response Body</p>
                                <pre className="bg-background border rounded p-3 text-xs overflow-x-auto max-h-32 overflow-y-auto">
                                    {delivery.response_body}
                                </pre>
                            </div>
                        )}
                        {delivery.next_retry_at && delivery.status === 'retrying' && (
                            <p className="text-xs text-muted-foreground">
                                Next retry: {format(new Date(delivery.next_retry_at), 'MMM d, yyyy HH:mm')}
                            </p>
                        )}
                    </TableCell>
                </TableRow>
            )}
        </>
    );
}

export function ViewWebhookDialog({ webhook, open, onOpenChange }: ViewWebhookDialogProps) {
    const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
    const [deliveriesLoading, setDeliveriesLoading] = useState(false);
    const [deliveriesTotal, setDeliveriesTotal] = useState(0);
    const [isTesting, setIsTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; status_code: number | null; error: string | null } | null>(null);
    const { toast } = useToast();

    useEffect(() => {
        if (open && webhook) {
            setDeliveries([]);
            setTestResult(null);
            setDeliveriesLoading(true);
            webhooksService.getDeliveries(webhook.id, { limit: 20 })
                .then((r) => {
                    setDeliveries(r.items);
                    setDeliveriesTotal(r.total);
                })
                .catch(() => {})
                .finally(() => setDeliveriesLoading(false));
        }
    }, [open, webhook]);

    const handleTest = async () => {
        if (!webhook) return;
        setIsTesting(true);
        setTestResult(null);
        try {
            const result = await webhooksService.test(webhook.id);
            setTestResult(result);
            if (result.success) {
                toast({ title: `Test successful (${result.status_code})` });
            } else {
                toast({
                    title: `Test failed`,
                    description: result.error || `Status ${result.status_code}`,
                    variant: 'destructive',
                });
            }
        } catch (error: any) {
            toast({
                title: 'Test request failed',
                description: error.response?.data?.detail || 'Something went wrong',
                variant: 'destructive',
            });
        } finally {
            setIsTesting(false);
        }
    };

    if (!webhook) return null;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Webhook Details"
            className="sm:max-w-2xl"
            footer={
                <div className="flex items-center gap-2 w-full">
                    <Button
                        variant="outline"
                        onClick={handleTest}
                        disabled={isTesting}
                        className="gap-2"
                    >
                        <Zap className="h-4 w-4" />
                        {isTesting ? 'Sending...' : 'Test Webhook'}
                    </Button>
                    {testResult && (
                        <span className={`text-sm ${testResult.success ? 'text-green-600' : 'text-red-600'}`}>
                            {testResult.success
                                ? `Success (${testResult.status_code})`
                                : testResult.error || `Failed (${testResult.status_code})`}
                        </span>
                    )}
                    <Button variant="ghost" onClick={() => onOpenChange(false)} className="ml-auto">
                        Close
                    </Button>
                </div>
            }
        >
            <Tabs defaultValue="details">
                <TabsList className="mb-4">
                    <TabsTrigger value="details">Details</TabsTrigger>
                    <TabsTrigger value="deliveries">
                        Delivery History {deliveriesTotal > 0 && `(${deliveriesTotal})`}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="details" className="space-y-3">
                    <dl className="space-y-3 text-sm">
                        <div className="flex justify-between gap-4">
                            <dt className="text-muted-foreground shrink-0">URL</dt>
                            <dd className="text-right break-all font-mono text-xs">{webhook.url}</dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="text-muted-foreground shrink-0">Collection</dt>
                            <dd><Badge variant="outline">{webhook.collection}</Badge></dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="text-muted-foreground shrink-0">Events</dt>
                            <dd className="flex gap-1 flex-wrap justify-end">
                                {webhook.events.map((e) => (
                                    <Badge key={e} variant="secondary" className="capitalize">{e}</Badge>
                                ))}
                            </dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="text-muted-foreground shrink-0">Status</dt>
                            <dd>
                                {webhook.enabled
                                    ? <Badge variant="success">Enabled</Badge>
                                    : <Badge variant="outline">Disabled</Badge>}
                            </dd>
                        </div>
                        {webhook.filter && (
                            <div>
                                <dt className="text-muted-foreground mb-1">Filter</dt>
                                <dd>
                                    <code className="bg-muted px-2 py-1 rounded text-xs break-all">
                                        {webhook.filter}
                                    </code>
                                </dd>
                            </div>
                        )}
                        {webhook.headers && Object.keys(webhook.headers).length > 0 && (
                            <div>
                                <dt className="text-muted-foreground mb-1">Custom Headers</dt>
                                <dd className="space-y-1">
                                    {Object.entries(webhook.headers).map(([k, v]) => (
                                        <div key={k} className="flex gap-2 text-xs font-mono">
                                            <span className="text-muted-foreground">{k}:</span>
                                            <span>{v}</span>
                                        </div>
                                    ))}
                                </dd>
                            </div>
                        )}
                        <div className="flex justify-between gap-4">
                            <dt className="text-muted-foreground shrink-0">Created</dt>
                            <dd className="text-xs text-muted-foreground">
                                {format(new Date(webhook.created_at), 'MMM d, yyyy HH:mm')}
                            </dd>
                        </div>
                    </dl>
                </TabsContent>

                <TabsContent value="deliveries">
                    {deliveriesLoading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : deliveries.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground text-sm">
                            No deliveries yet.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Event</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-center">Code</TableHead>
                                    <TableHead className="text-center">Attempt</TableHead>
                                    <TableHead>Delivered</TableHead>
                                    <TableHead />
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {deliveries.map((d) => (
                                    <DeliveryRow key={d.id} delivery={d} />
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </TabsContent>
            </Tabs>
        </AppDialog>
    );
}
