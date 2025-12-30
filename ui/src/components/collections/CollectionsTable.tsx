/**
 * Collections table component
 * Displays collections with sorting and actions
 */

import { Button } from '@/components/ui/button';
import { Eye, Pencil, Trash2, Database } from 'lucide-react';
import type { CollectionListItem } from '@/services/collections.service';
import { DataTable, type Column, type DispatchPagination, type DispatchSorting } from '@/components/common/DataTable';

interface CollectionsTableProps {
    collections: CollectionListItem[];
    sortBy: string;
    sortOrder: 'asc' | 'desc';
    onSort: (column: string) => void;
    onView: (collection: CollectionListItem) => void;
    onEdit: (collection: CollectionListItem) => void;
    onDelete: (collection: CollectionListItem) => void;
    onManageRecords?: (collection: CollectionListItem) => void;

    // Pagination props
    totalItems: number;
    page: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
}

export default function CollectionsTable({
    collections,
    sortBy,
    sortOrder,
    onSort,
    onView,
    onEdit,
    onDelete,
    onManageRecords,
    totalItems,
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
}: CollectionsTableProps) {

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    const columns: Column<CollectionListItem>[] = [
        {
            header: 'Name',
            accessorKey: 'name',
            sortable: true,
            className: 'font-medium',
        },
        {
            header: 'ID',
            accessorKey: 'id',
            className: 'w-[100px]',
            render: (collection) => (
                <span className="font-mono text-xs text-muted-foreground">
                    {collection.id.substring(0, 8)}...
                </span>
            ),
        },
        {
            header: 'Fields',
            accessorKey: 'fields_count',
            sortable: true,
            className: 'text-right',
        },
        {
            header: 'Records',
            accessorKey: 'records_count',
            sortable: true,
            className: 'text-right',
        },
        {
            header: 'Created',
            accessorKey: 'created_at',
            sortable: true,
            render: (collection) => <span>{formatDate(collection.created_at)}</span>,
        },
        {
            header: 'Actions',
            className: 'text-right',
            render: (collection) => (
                <div className="flex justify-end gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onManageRecords?.(collection)}
                        title="Manage records"
                    >
                        <Database className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onView(collection)}
                        title="View schema"
                    >
                        <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onEdit(collection)}
                        title="Edit schema"
                    >
                        <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onDelete(collection)}
                        title="Delete collection"
                    >
                        <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                </div>
            ),
        },
    ];

    const pagination: DispatchPagination = {
        page,
        pageSize,
        onPageChange,
        onPageSizeChange,
    };

    const sorting: DispatchSorting = {
        sortBy,
        sortOrder,
        onSort,
    };

    return (
        <DataTable
            data={collections}
            columns={columns}
            keyExtractor={(item) => item.id}
            pagination={pagination}
            sorting={sorting}
            totalItems={totalItems}
            noDataMessage="No collections found"
        />
    );
}
