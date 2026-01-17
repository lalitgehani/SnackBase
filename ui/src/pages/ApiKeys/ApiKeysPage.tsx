import { useEffect, useState } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2, Key, Clock, Calendar } from 'lucide-react';
import { apiKeysService } from '@/services/api-keys.service';
import type { APIKeyListItem } from '@/services/api-keys.service';
import { CreateApiKeyDialog } from './CreateApiKeyDialog';
import { RevokeApiKeyDialog } from './RevokeApiKeyDialog';
import { format } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export const ApiKeysPage = () => {
    const [keys, setKeys] = useState<APIKeyListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
    const [selectedKey, setSelectedKey] = useState<APIKeyListItem | null>(null);

    const fetchKeys = async () => {
        setLoading(true);
        try {
            const response = await apiKeysService.getApiKeys();
            setKeys(response.items);
        } catch (error) {
            console.error('Failed to fetch API keys', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchKeys();
    }, []);

    const handleRevokeClick = (key: APIKeyListItem) => {
        setSelectedKey(key);
        setRevokeDialogOpen(true);
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'Never';
        return format(new Date(dateStr), 'MMM d, yyyy HH:mm');
    };

    const isExpired = (expiry: string | null) => {
        if (!expiry) return false;
        return new Date(expiry) < new Date();
    };

    return (
        <div className="p-8 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Superadmin API Keys</h1>
                    <p className="text-muted-foreground">
                        Manage persistent keys for programmatic access to the SnackBase API.
                    </p>
                </div>
                <Button onClick={() => setCreateDialogOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Create API Key
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Your API Keys</CardTitle>
                    <CardDescription>
                        These keys provide full superadmin access. Manage them carefully.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : keys.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Key className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
                            <h3 className="text-lg font-medium">No API keys found</h3>
                            <p className="text-muted-foreground mb-6">
                                You haven't created any API keys yet.
                            </p>
                            <Button variant="outline" onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="mr-2 h-4 w-4" /> Create your first key
                            </Button>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead>Key</TableHead>
                                    <TableHead>Last Used</TableHead>
                                    <TableHead>Expires</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {keys.map((key) => (
                                    <TableRow key={key.id} className={!key.is_active ? 'opacity-50' : ''}>
                                        <TableCell className="font-medium">{key.name}</TableCell>
                                        <TableCell>
                                            <code className="bg-muted px-1 py-0.5 rounded text-xs select-all">
                                                {key.key}
                                            </code>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center text-xs text-muted-foreground">
                                                <Clock className="mr-1 h-3 w-3" />
                                                {key.last_used_at ? formatDate(key.last_used_at) : 'Never'}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center text-xs text-muted-foreground">
                                                <Calendar className="mr-1 h-3 w-3" />
                                                {formatDate(key.expires_at)}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {!key.is_active ? (
                                                <Badge variant="outline">Revoked</Badge>
                                            ) : isExpired(key.expires_at) ? (
                                                <Badge variant="destructive">Expired</Badge>
                                            ) : (
                                                <Badge variant="success">
                                                    Active
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {key.is_active && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                    onClick={() => handleRevokeClick(key)}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <CreateApiKeyDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onCreated={fetchKeys}
            />

            <RevokeApiKeyDialog
                apiKey={selectedKey}
                open={revokeDialogOpen}
                onOpenChange={setRevokeDialogOpen}
                onRevoked={fetchKeys}
            />
        </div>
    );
};

export default ApiKeysPage;
