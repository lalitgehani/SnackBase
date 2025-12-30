import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Pencil, Trash2 } from 'lucide-react';
import type { AccountListItem } from '@/services/accounts.service';
import { DataTable, type Column } from '@/components/common/DataTable';

interface AccountsTableProps {
    accounts: AccountListItem[];
    totalItems: number;
    page: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
    sortBy: string;
    sortOrder: 'asc' | 'desc';
    onSort: (column: string) => void;
    onView: (account: AccountListItem) => void;
    onEdit: (account: AccountListItem) => void;
    onDelete: (account: AccountListItem) => void;
    isLoading?: boolean;
}

export default function AccountsTable({
    accounts,
    totalItems,
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
    sortBy,
    sortOrder,
    onSort,
    onView,
    onEdit,
    onDelete,
    isLoading
}: AccountsTableProps) {
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString();
    };

    const columns: Column<AccountListItem>[] = [
        {
            header: 'Code',
            accessorKey: 'account_code',
            sortable: true,
            className: 'font-mono text-sm'
        },
        {
            header: 'Slug',
            accessorKey: 'slug',
            sortable: true,
            className: 'font-medium'
        },
        {
            header: 'Name',
            accessorKey: 'name',
            sortable: true
        },
        {
            header: 'Created At',
            accessorKey: 'created_at',
            sortable: true,
            render: (account) => <span className="text-muted-foreground">{formatDate(account.created_at)}</span>
        },
        {
            header: 'User Count',
            accessorKey: 'user_count',
            sortable: false
        },
        {
            header: 'Status',
            accessorKey: 'status',
            sortable: true,
            render: (account) => <Badge variant="default">{account.status}</Badge>
        },
        {
            header: 'Actions',
            className: 'text-right',
            render: (account) => (
                <div className="flex justify-end gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                            e.stopPropagation();
                            onView(account);
                        }}
                        title="View details"
                    >
                        <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                            e.stopPropagation();
                            onEdit(account);
                        }}
                        title="Edit account"
                    >
                        <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDelete(account);
                        }}
                        title="Delete account"
                        className="text-destructive hover:text-destructive"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    return (
        <DataTable
            data={accounts}
            columns={columns}
            keyExtractor={(account) => account.id}
            isLoading={isLoading}
            totalItems={totalItems}
            pagination={{
                page,
                pageSize,
                onPageChange,
                onPageSizeChange
            }}
            sorting={{
                sortBy,
                sortOrder,
                onSort
            }}
            onRowClick={onView}
            noDataMessage="No accounts found."
        />
    );
}
