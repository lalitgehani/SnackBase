import { useState, useMemo, useEffect } from 'react';
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
import { Trash2, Edit, Plus, Settings, Search } from 'lucide-react';
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
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from '@/components/ui/command';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { useToast } from '@/hooks/use-toast';
import { Check, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const AccountProvidersTab = () => {
    const [selectedAccountId, setSelectedAccountId] = useState<string>('');
    const [categoryFilter, setCategoryFilter] = useState<string>('all');
    const [configToDelete, setConfigToDelete] = useState<Configuration | null>(null);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [open, setOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const queryClient = useQueryClient();
    const { toast } = useToast();

    // Fetch accounts for the selector
    const { data: accountsData } = useQuery({
        queryKey: ['admin', 'accounts', searchQuery],
        queryFn: () => adminService.getAccounts(searchQuery || undefined, 1, 100),
    });

    const accounts = accountsData?.items || [];

    // Fetch configurations for selected account
    const { data: allConfigs, isLoading } = useQuery({
        queryKey: ['admin', 'config', 'account', selectedAccountId, categoryFilter],
        queryFn: () => adminService.getAccountConfigs(selectedAccountId, categoryFilter),
        enabled: !!selectedAccountId,
    });

    // Client-side pagination
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
                description: 'Account configuration has been deleted. System default will be used.',
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

    // Reset page when account or filter changes
    useEffect(() => {
        setPage(1);
    }, [selectedAccountId, categoryFilter]);

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
                        onClick={() => {
                            toast({
                                title: "Coming Soon",
                                description: "Feature F5.4: Configuration Form will implement this functionality.",
                            });
                        }}
                    >
                        <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setConfigToDelete(config)}
                        className="text-destructive hover:text-destructive"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    const selectedAccount = accounts.find((acc: any) => acc.id === selectedAccountId);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    {/* Account Selector */}
                    <Popover open={open} onOpenChange={setOpen}>
                        <PopoverTrigger asChild>
                            <Button
                                variant="outline"
                                role="combobox"
                                aria-expanded={open}
                                className="w-75 justify-between"
                            >
                                {selectedAccount ? (
                                    <span className="truncate">
                                        {selectedAccount.name} ({selectedAccount.slug})
                                    </span>
                                ) : (
                                    "Select account..."
                                )}
                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-75 p-0">
                            <Command shouldFilter={false}>
                                <CommandInput
                                    placeholder="Search accounts..."
                                    value={searchQuery}
                                    onValueChange={setSearchQuery}
                                />
                                <CommandList>
                                    <CommandEmpty>No account found.</CommandEmpty>
                                    <CommandGroup>
                                        {accounts.map((account: any) => (
                                            <CommandItem
                                                key={account.id}
                                                value={account.id}
                                                onSelect={(currentValue: string) => {
                                                    setSelectedAccountId(currentValue === selectedAccountId ? '' : currentValue);
                                                    setOpen(false);
                                                }}
                                            >
                                                <Check
                                                    className={cn(
                                                        "mr-2 h-4 w-4",
                                                        selectedAccountId === account.id ? "opacity-100" : "opacity-0"
                                                    )}
                                                />
                                                <div className="flex flex-col">
                                                    <span>{account.name}</span>
                                                    <span className="text-xs text-muted-foreground">{account.slug}</span>
                                                </div>
                                            </CommandItem>
                                        ))}
                                    </CommandGroup>
                                </CommandList>
                            </Command>
                        </PopoverContent>
                    </Popover>

                    {/* Category Filter */}
                    {selectedAccountId && (
                        <Select value={categoryFilter} onValueChange={(val) => {
                            setCategoryFilter(val);
                            setPage(1);
                        }}>
                            <SelectTrigger className="w-45">
                                <SelectValue placeholder="Filter by category" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Categories</SelectItem>
                                <SelectItem value="auth_providers">Auth Providers</SelectItem>
                                <SelectItem value="email_providers">Email Providers</SelectItem>
                                <SelectItem value="storage_providers">Storage Providers</SelectItem>
                            </SelectContent>
                        </Select>
                    )}
                </div>
                {selectedAccountId && (
                    <Button onClick={() => {
                        toast({
                            title: "Coming Soon",
                            description: "Feature F5.4: Configuration Form will implement this functionality.",
                        });
                    }}>
                        <Plus className="mr-2 h-4 w-4" /> Add Provider
                    </Button>
                )}
            </div>

            {!selectedAccountId ? (
                <div className="flex h-100 items-center justify-center rounded-md border border-dashed text-muted-foreground">
                    <div className="text-center">
                        <Search className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
                        <p className="text-lg font-medium">Select an account</p>
                        <p className="text-sm">Choose an account from the dropdown to view its provider configurations</p>
                    </div>
                </div>
            ) : (
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
                    noDataMessage="No account-level configurations found. This account is using system defaults."
                />
            )}

            <AlertDialog open={!!configToDelete} onOpenChange={() => setConfigToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete the account-level configuration for{' '}
                            <span className="font-medium text-foreground">
                                {configToDelete?.display_name}
                            </span>
                            . The account will fall back to using the system default configuration.
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
        </div>
    );
};

export default AccountProvidersTab;
