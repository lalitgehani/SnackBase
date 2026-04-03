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
    Route,
    Plus,
    RefreshCw,
    MoreHorizontal,
    Pencil,
    Trash2,
    Eye,
} from 'lucide-react';
import { endpointsService, type Endpoint } from '@/services/endpoints.service';
import { CreateEndpointDialog } from './CreateEndpointDialog';
import { EditEndpointDialog } from './EditEndpointDialog';
import { ViewEndpointDialog } from './ViewEndpointDialog';
import { DeleteEndpointDialog } from './DeleteEndpointDialog';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/stores/auth.store';

function MethodBadge({ method }: { method: string }) {
    const colors: Record<string, string> = {
        GET: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200',
        POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200',
        PUT: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
        PATCH: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200',
        DELETE: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200',
    };
    return (
        <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold font-mono ${
                colors[method] ?? 'bg-muted text-muted-foreground'
            }`}
        >
            {method}
        </span>
    );
}

export default function EndpointsPage() {
    const { toast } = useToast();
    const { account, token } = useAuthStore();

    const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [togglingId, setTogglingId] = useState<string | null>(null);

    const [createOpen, setCreateOpen] = useState(false);
    const [viewEndpoint, setViewEndpoint] = useState<Endpoint | null>(null);
    const [editEndpoint, setEditEndpoint] = useState<Endpoint | null>(null);
    const [deleteEndpoint, setDeleteEndpoint] = useState<Endpoint | null>(null);

    const fetchEndpoints = useCallback(async () => {
        setError(null);
        try {
            const response = await endpointsService.list();
            setEndpoints(response.items);
            setTotal(response.total);
        } catch {
            setError('Failed to load endpoints. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchEndpoints();
    }, [fetchEndpoints]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchEndpoints();
        setRefreshing(false);
    };

    const handleToggle = async (endpoint: Endpoint) => {
        setTogglingId(endpoint.id);
        try {
            const updated = await endpointsService.toggle(endpoint.id);
            setEndpoints((prev) => prev.map((e) => (e.id === endpoint.id ? updated : e)));
        } catch {
            toast({ title: 'Error', description: 'Failed to toggle endpoint', variant: 'destructive' });
        } finally {
            setTogglingId(null);
        }
    };

    const enabledCount = endpoints.filter((e) => e.enabled).length;
    const disabledCount = endpoints.length - enabledCount;

    return (
        <div className="p-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Route className="h-8 w-8" />
                        Endpoints
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Serverless HTTP endpoints that run actions and return custom responses
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button size="sm" onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Endpoint
                    </Button>
                </div>
            </div>

            {/* Stats row */}
            {!loading && endpoints.length > 0 && (
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
                    <Button variant="outline" className="mt-4" onClick={fetchEndpoints}>
                        Try Again
                    </Button>
                </div>
            ) : loading ? (
                <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-14 w-full" />
                    ))}
                </div>
            ) : endpoints.length === 0 ? (
                <div className="text-center py-24 border rounded-lg">
                    <Route className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-medium mb-1">No endpoints yet</p>
                    <p className="text-muted-foreground text-sm mb-6">
                        Create a serverless endpoint to handle HTTP requests with custom actions and responses.
                    </p>
                    <Button onClick={() => setCreateOpen(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Endpoint
                    </Button>
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-20">Method</TableHead>
                            <TableHead>Path</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead>Auth</TableHead>
                            <TableHead>Actions</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="w-10"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {endpoints.map((endpoint) => (
                            <TableRow key={endpoint.id}>
                                <TableCell>
                                    <MethodBadge method={endpoint.method} />
                                </TableCell>
                                <TableCell>
                                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
                                        {endpoint.path}
                                    </code>
                                </TableCell>
                                <TableCell>
                                    <div>
                                        <p className="font-medium">{endpoint.name}</p>
                                        {endpoint.description && (
                                            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                                {endpoint.description}
                                            </p>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    {endpoint.auth_required ? (
                                        <Badge variant="secondary" className="text-xs">Auth Required</Badge>
                                    ) : (
                                        <Badge variant="outline" className="text-xs text-green-600 border-green-300">
                                            Public
                                        </Badge>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <Badge variant="secondary" className="text-xs">
                                        {endpoint.actions.length} action{endpoint.actions.length !== 1 ? 's' : ''}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-2">
                                        <Switch
                                            checked={endpoint.enabled}
                                            disabled={togglingId === endpoint.id}
                                            onCheckedChange={() => handleToggle(endpoint)}
                                        />
                                        <Badge variant={endpoint.enabled ? 'default' : 'secondary'}>
                                            {endpoint.enabled ? 'Enabled' : 'Disabled'}
                                        </Badge>
                                    </div>
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
                                            <DropdownMenuItem onClick={() => setViewEndpoint(endpoint)}>
                                                <Eye className="h-4 w-4 mr-2" />
                                                View
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => setEditEndpoint(endpoint)}>
                                                <Pencil className="h-4 w-4 mr-2" />
                                                Edit
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem
                                                className="text-destructive focus:text-destructive"
                                                onClick={() => setDeleteEndpoint(endpoint)}
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
            <CreateEndpointDialog
                open={createOpen}
                onOpenChange={setCreateOpen}
                onCreated={fetchEndpoints}
                accountSlug={account?.slug}
            />

            {viewEndpoint && (
                <ViewEndpointDialog
                    endpoint={viewEndpoint}
                    open={viewEndpoint !== null}
                    onOpenChange={(open) => { if (!open) setViewEndpoint(null); }}
                    accountSlug={account?.slug}
                    token={token}
                />
            )}

            {editEndpoint && (
                <EditEndpointDialog
                    endpoint={editEndpoint}
                    open={editEndpoint !== null}
                    onOpenChange={(open) => { if (!open) setEditEndpoint(null); }}
                    onUpdated={() => { setEditEndpoint(null); fetchEndpoints(); }}
                    accountSlug={account?.slug}
                />
            )}

            {deleteEndpoint && (
                <DeleteEndpointDialog
                    endpoint={deleteEndpoint}
                    open={deleteEndpoint !== null}
                    onOpenChange={(open) => { if (!open) setDeleteEndpoint(null); }}
                    onDeleted={() => { setDeleteEndpoint(null); fetchEndpoints(); }}
                />
            )}
        </div>
    );
}
