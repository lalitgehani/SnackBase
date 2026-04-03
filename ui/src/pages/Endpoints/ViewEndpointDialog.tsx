import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { Copy, Plus, X, Send } from 'lucide-react';
import { endpointsService, type Endpoint, type EndpointExecution } from '@/services/endpoints.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
    endpoint: Endpoint;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    accountSlug?: string;
    token?: string | null;
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

function MethodBadge({ method }: { method: string }) {
    const colors: Record<string, string> = {
        GET: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200',
        POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200',
        PUT: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
        PATCH: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200',
        DELETE: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200',
    };
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold font-mono ${colors[method] ?? 'bg-muted text-muted-foreground'}`}>
            {method}
        </span>
    );
}

function StatusBadge({ status }: { status: EndpointExecution['status'] }) {
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

function HttpStatusBadge({ status }: { status: number }) {
    const color =
        status < 300
            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200'
            : status < 400
            ? 'bg-blue-100 text-blue-700'
            : status < 500
            ? 'bg-yellow-100 text-yellow-700'
            : 'bg-red-100 text-red-700';
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold ${color}`}>
            {status}
        </span>
    );
}

interface KVRow {
    key: string;
    value: string;
}

function KVEditor({ rows, onChange, placeholder }: { rows: KVRow[]; onChange: (rows: KVRow[]) => void; placeholder?: string }) {
    return (
        <div className="space-y-1.5">
            {rows.map((row, i) => (
                <div key={i} className="flex gap-2 items-center">
                    <Input
                        className="h-7 text-xs flex-1"
                        placeholder="Key"
                        value={row.key}
                        onChange={(e) => {
                            const next = [...rows];
                            next[i] = { ...row, key: e.target.value };
                            onChange(next);
                        }}
                    />
                    <Input
                        className="h-7 text-xs flex-1"
                        placeholder={placeholder ?? 'Value'}
                        value={row.value}
                        onChange={(e) => {
                            const next = [...rows];
                            next[i] = { ...row, value: e.target.value };
                            onChange(next);
                        }}
                    />
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        onClick={() => onChange(rows.filter((_, j) => j !== i))}
                    >
                        <X className="h-3.5 w-3.5" />
                    </Button>
                </div>
            ))}
            <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => onChange([...rows, { key: '', value: '' }])}
            >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Add
            </Button>
        </div>
    );
}

export function ViewEndpointDialog({ endpoint, open, onOpenChange, accountSlug, token }: Props) {
    const { toast } = useToast();

    // Execution history state
    const [executions, setExecutions] = useState<EndpointExecution[]>([]);
    const [execLoading, setExecLoading] = useState(false);
    const [execError, setExecError] = useState<string | null>(null);

    // Request tester state
    const [queryParams, setQueryParams] = useState<KVRow[]>([]);
    const [headers, setHeaders] = useState<KVRow[]>(
        token ? [{ key: 'Authorization', value: `Bearer ${token}` }] : []
    );
    const [body, setBody] = useState('');
    const [sending, setSending] = useState(false);
    const [testResponse, setTestResponse] = useState<{ status: number; body: string } | null>(null);

    useEffect(() => {
        if (!open) return;
        setExecLoading(true);
        setExecError(null);
        endpointsService
            .listExecutions(endpoint.id)
            .then((res) => setExecutions(res.items))
            .catch(() => setExecError('Failed to load execution history.'))
            .finally(() => setExecLoading(false));
    }, [open, endpoint.id]);

    // Reset tester on dialog open
    useEffect(() => {
        if (open) {
            setTestResponse(null);
            setHeaders(token ? [{ key: 'Authorization', value: `Bearer ${token}` }] : []);
            setQueryParams([]);
            setBody('');
        }
    }, [open, token]);

    const dispatcherUrl = accountSlug
        ? `/api/v1/x/${accountSlug}${endpoint.path}`
        : `/api/v1/x/{account_slug}${endpoint.path}`;

    const fullUrl = (() => {
        const base = window.location.origin;
        const url = new URL(`${base}${dispatcherUrl}`);
        queryParams.filter((r) => r.key).forEach((r) => url.searchParams.set(r.key, r.value));
        return url.toString();
    })();

    const handleCopyUrl = () => {
        navigator.clipboard.writeText(fullUrl);
        toast({ title: 'URL copied' });
    };

    const handleSendRequest = async () => {
        setSending(true);
        setTestResponse(null);
        try {
            const headersObj: Record<string, string> = {};
            headers.filter((h) => h.key).forEach((h) => { headersObj[h.key] = h.value; });
            if (!headersObj['Content-Type'] && endpoint.method !== 'GET') {
                headersObj['Content-Type'] = 'application/json';
            }

            const options: RequestInit = {
                method: endpoint.method,
                headers: headersObj,
            };
            if (endpoint.method !== 'GET' && body.trim()) {
                options.body = body.trim();
            }

            const res = await fetch(fullUrl, options);
            let responseBody = '';
            try {
                const json = await res.json();
                responseBody = JSON.stringify(json, null, 2);
            } catch {
                responseBody = await res.text();
            }
            setTestResponse({ status: res.status, body: responseBody });
        } catch (err: unknown) {
            setTestResponse({ status: 0, body: String(err) });
        } finally {
            setSending(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[680px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <MethodBadge method={endpoint.method} />
                        {endpoint.name}
                    </DialogTitle>
                </DialogHeader>

                <Tabs defaultValue="details">
                    <TabsList className="w-full">
                        <TabsTrigger value="details" className="flex-1">Details</TabsTrigger>
                        <TabsTrigger value="tester" className="flex-1">Request Tester</TabsTrigger>
                        <TabsTrigger value="executions" className="flex-1">Execution Log</TabsTrigger>
                    </TabsList>

                    {/* Details tab */}
                    <TabsContent value="details" className="space-y-3 pt-3">
                        {endpoint.description && (
                            <p className="text-sm text-muted-foreground">{endpoint.description}</p>
                        )}

                        <div className="grid grid-cols-[120px_1fr] gap-y-2.5 text-sm">
                            <span className="text-muted-foreground font-medium">Status</span>
                            <Badge variant={endpoint.enabled ? 'default' : 'secondary'}>
                                {endpoint.enabled ? 'Enabled' : 'Disabled'}
                            </Badge>

                            <span className="text-muted-foreground font-medium">Method</span>
                            <MethodBadge method={endpoint.method} />

                            <span className="text-muted-foreground font-medium">URL</span>
                            <div className="flex items-center gap-1.5 min-w-0">
                                <code className="text-xs bg-muted px-1.5 py-0.5 rounded truncate">
                                    {dispatcherUrl}
                                </code>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 shrink-0"
                                    onClick={handleCopyUrl}
                                >
                                    <Copy className="h-3.5 w-3.5" />
                                </Button>
                            </div>

                            <span className="text-muted-foreground font-medium">Auth</span>
                            <span>
                                {endpoint.auth_required ? (
                                    <Badge variant="secondary">Auth Required</Badge>
                                ) : (
                                    <Badge variant="outline" className="text-green-600 border-green-300">Public</Badge>
                                )}
                            </span>

                            <span className="text-muted-foreground font-medium">Condition</span>
                            <span>
                                {endpoint.condition ? (
                                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded break-all">
                                        {endpoint.condition}
                                    </code>
                                ) : (
                                    <span className="text-muted-foreground">—</span>
                                )}
                            </span>

                            <span className="text-muted-foreground font-medium">Created</span>
                            <span>{formatDate(endpoint.created_at)}</span>
                        </div>

                        {endpoint.actions.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-sm font-medium">
                                    Actions ({endpoint.actions.length})
                                </p>
                                <div className="space-y-1.5">
                                    {endpoint.actions.map((action, i) => (
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

                        {endpoint.response_template && (
                            <div className="space-y-1.5">
                                <p className="text-sm font-medium">Response template</p>
                                <pre className="text-xs bg-muted rounded-md p-3 overflow-x-auto">
                                    {JSON.stringify(endpoint.response_template, null, 2)}
                                </pre>
                            </div>
                        )}
                    </TabsContent>

                    {/* Request tester tab */}
                    <TabsContent value="tester" className="space-y-4 pt-3">
                        <div className="space-y-1.5">
                            <Label className="text-xs">URL</Label>
                            <div className="flex items-center gap-2">
                                <Input
                                    readOnly
                                    className="text-xs font-mono bg-muted"
                                    value={dispatcherUrl}
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="icon"
                                    className="shrink-0"
                                    onClick={handleCopyUrl}
                                >
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <Label className="text-xs">Query parameters</Label>
                            <KVEditor rows={queryParams} onChange={setQueryParams} />
                        </div>

                        <div className="space-y-1.5">
                            <Label className="text-xs">Headers</Label>
                            <KVEditor rows={headers} onChange={setHeaders} placeholder="Value" />
                        </div>

                        {endpoint.method !== 'GET' && (
                            <div className="space-y-1.5">
                                <Label className="text-xs">Body (JSON)</Label>
                                <Textarea
                                    className="text-xs font-mono"
                                    rows={4}
                                    placeholder='{"key": "value"}'
                                    value={body}
                                    onChange={(e) => setBody(e.target.value)}
                                />
                            </div>
                        )}

                        <Button
                            type="button"
                            onClick={handleSendRequest}
                            disabled={sending}
                            className="w-full"
                        >
                            <Send className="h-4 w-4 mr-2" />
                            {sending ? 'Sending…' : 'Send Request'}
                        </Button>

                        {testResponse && (
                            <div className="space-y-2 border rounded-md p-3">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium">Response</span>
                                    {testResponse.status > 0 && (
                                        <HttpStatusBadge status={testResponse.status} />
                                    )}
                                </div>
                                <pre className="text-xs bg-muted rounded p-2.5 overflow-x-auto max-h-48">
                                    {testResponse.body || '(empty)'}
                                </pre>
                            </div>
                        )}
                    </TabsContent>

                    {/* Execution log tab */}
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
                                        <TableHead>HTTP</TableHead>
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
                                            <TableCell>
                                                <HttpStatusBadge status={exec.http_status} />
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
