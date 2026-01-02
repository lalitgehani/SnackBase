import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService, type Configuration } from '@/services/admin.service';
import { DataTable, type Column } from '@/components/common/DataTable';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Trash2, Edit, Plus, Settings } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useToast } from '@/hooks/use-toast';
import { AddProviderModal } from '@/components/common/AddProviderModal';
import { ConfigurationForm } from '@/components/common/ConfigurationForm';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';

const SystemProvidersTab = () => {
    const [categoryFilter, setCategoryFilter] = useState<string>('all');
    const [configToDelete, setConfigToDelete] = useState<Configuration | null>(null);
    const [configToEdit, setConfigToEdit] = useState<Configuration | null>(null);
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);

    const queryClient = useQueryClient();
    const { toast } = useToast();

    const { data: allConfigs, isLoading } = useQuery({
        queryKey: ['admin', 'config', 'system', categoryFilter],
        queryFn: () => adminService.getSystemConfigs(categoryFilter),
    });

    // Client-side pagination logic since API returns all system configs
    const paginatedData = useMemo(() => {
        if (!allConfigs) return [];
        const startIndex = (page - 1) * pageSize;
        return allConfigs.slice(startIndex, startIndex + pageSize);
    }, [allConfigs, page, pageSize]);

    const totalItems = allConfigs?.length || 0;

    const toggleMutation = useMutation({
        mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
            adminService.updateConfig(id, enabled),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['admin', 'config'] });
            toast({
                title: 'Configuration Updated',
                description: `Provider has been ${data.enabled ? 'enabled' : 'disabled'}.`,
            });
        },
        onError: () => {
            toast({
                title: 'Error',
                description: 'Failed to update configuration.',
                variant: 'destructive',
            });
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => adminService.deleteConfig(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin', 'config'] });
            toast({
                title: 'Configuration Deleted',
                description: 'Provider has been deleted successfully.',
            });
            setConfigToDelete(null);
        },
        onError: () => {
            toast({
                title: 'Error',
                description: 'Failed to delete configuration.',
                variant: 'destructive',
            });
        },
    });

    const handleToggle = (config: Configuration) => {
        toggleMutation.mutate({ id: config.id, enabled: !config.enabled });
    };

    const confirmDelete = () => {
        if (configToDelete) {
            deleteMutation.mutate(configToDelete.id);
        }
    };

    const columns: Column<Configuration>[] = [
        {
            header: 'Provider',
            render: (config) => (
                <div className="flex items-center space-x-3">
                    {config.logo_url ? (
                        <img src={config.logo_url} alt={config.provider_name} className="h-6 w-6 object-contain" />
                    ) : (
                        <div className="h-6 w-6 bg-secondary rounded-full flex items-center justify-center">
                            <Settings className="h-3 w-3" />
                        </div>
                    )}
                    <div className="flex flex-col">
                        <span className="font-medium">{config.display_name}</span>
                        <span className="text-xs text-muted-foreground">{config.provider_name}</span>
                    </div>
                    {config.is_builtin && (
                        <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                            Built-in
                        </span>
                    )}
                </div>
            )
        },
        {
            header: 'Category',
            accessorKey: 'category',
            render: (config) => <span className="capitalize">{config.category.replace('_', ' ')}</span>
        },
        {
            header: 'Last Updated',
            accessorKey: 'updated_at',
            render: (config) => (
                <span className="text-muted-foreground">
                    {formatDistanceToNow(new Date(config.updated_at), { addSuffix: true })}
                </span>
            )
        },
        {
            header: 'Status',
            render: (config) => (
                <div className="flex items-center space-x-2">
                    <Switch
                        checked={config.enabled}
                        onCheckedChange={() => handleToggle(config)}
                        disabled={toggleMutation.isPending}
                    />
                    <span className="text-sm text-muted-foreground">
                        {config.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                </div>
            )
        },
        {
            header: 'Actions',
            className: 'text-right',
            render: (config) => (
                <div className="flex justify-end space-x-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setConfigToEdit(config)}
                    >
                        <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        disabled={config.is_builtin}
                        onClick={() => setConfigToDelete(config)}
                        className="text-destructive hover:text-destructive"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <Select value={categoryFilter} onValueChange={(val) => {
                        setCategoryFilter(val);
                        setPage(1); // Reset page on filter change
                    }}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Filter by category" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Categories</SelectItem>
                            <SelectItem value="auth_providers">Auth Providers</SelectItem>
                            <SelectItem value="email_providers">Email Providers</SelectItem>
                            <SelectItem value="storage_providers">Storage Providers</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <Button onClick={() => setIsAddModalOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Add Provider
                </Button>
            </div>

            <DataTable
                data={paginatedData}
                columns={columns}
                keyExtractor={(item) => item.id}
                isLoading={isLoading}
                totalItems={totalItems}
                pagination={{
                    page,
                    pageSize,
                    onPageChange: setPage,
                    onPageSizeChange: (size) => {
                        setPageSize(size);
                        setPage(1);
                    }
                }}
                noDataMessage="No configurations found."
            />

            <AlertDialog open={!!configToDelete} onOpenChange={() => setConfigToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete the configuration for{' '}
                            <span className="font-medium text-foreground">
                                {configToDelete?.display_name}
                            </span>
                            . This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={confirmDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AddProviderModal
                open={isAddModalOpen}
                onOpenChange={setIsAddModalOpen}
                category={categoryFilter === 'all' ? undefined : categoryFilter}
                onConfigCreated={() => queryClient.invalidateQueries({ queryKey: ['admin', 'config'] })}
                existingConfigs={allConfigs || []}
            />

            <Dialog open={!!configToEdit} onOpenChange={() => setConfigToEdit(null)}>
                <DialogContent className="sm:max-w-xl flex flex-col max-h-[90vh]">
                    <DialogHeader>
                        <DialogTitle>Configure {configToEdit?.display_name}</DialogTitle>
                    </DialogHeader>
                    <div className="flex-1 overflow-hidden">
                        {configToEdit && (
                            <ConfigurationForm
                                category={configToEdit.category}
                                providerName={configToEdit.provider_name}
                                displayName={configToEdit.display_name}
                                configId={configToEdit.id}
                                onSuccess={() => {
                                    setConfigToEdit(null);
                                    queryClient.invalidateQueries({ queryKey: ['admin', 'config'] });
                                }}
                                onCancel={() => setConfigToEdit(null)}
                            />
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default SystemProvidersTab;
