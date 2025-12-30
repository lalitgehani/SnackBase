import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye } from 'lucide-react';
import { format } from 'date-fns';
import type { AuditLogItem } from '@/services/audit.service';
import { DataTable, type Column } from '@/components/common/DataTable';

interface AuditLogsTableProps {
    logs: AuditLogItem[];
    totalItems: number;
    page: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
    sortBy: string;
    sortOrder: 'asc' | 'desc';
    onSort: (column: string) => void;
    onView: (log: AuditLogItem) => void;
    isLoading?: boolean;
}

export default function AuditLogsTable({
    logs,
    totalItems,
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
    sortBy,
    sortOrder,
    onSort,
    onView,
    isLoading,
}: AuditLogsTableProps) {
    const getOperationBadge = (operation: string) => {
        switch (operation) {
            case 'CREATE':
                return <Badge variant="default" className="bg-green-500 hover:bg-green-600">CREATE</Badge>;
            case 'UPDATE':
                return <Badge variant="secondary" className="bg-blue-500 hover:bg-blue-600 text-white">UPDATE</Badge>;
            case 'DELETE':
                return <Badge variant="destructive">DELETE</Badge>;
            default:
                return <Badge variant="outline">{operation}</Badge>;
        }
    };

    const columns: Column<AuditLogItem>[] = [
        {
            header: 'Timestamp',
            accessorKey: 'occurred_at',
            sortable: true,
            render: (log) => <span className="whitespace-nowrap">{format(new Date(log.occurred_at), 'yyyy-MM-dd HH:mm:ss')}</span>
        },
        {
            header: 'Operation',
            accessorKey: 'operation',
            sortable: true,
            render: (log) => getOperationBadge(log.operation)
        },
        {
            header: 'Collection',
            accessorKey: 'table_name',
            sortable: true,
            className: 'font-medium'
        },
        {
            header: 'Record ID',
            accessorKey: 'record_id',
            className: 'font-mono text-xs'
        },
        {
            header: 'Column',
            accessorKey: 'column_name'
        },
        {
            header: 'Old Value',
            accessorKey: 'old_value',
            className: 'max-w-[200px] truncate',
            render: (log) => (
                <span className="text-muted-foreground italic" title={log.old_value || 'None'}>
                    {log.old_value || '-'}
                </span>
            )
        },
        {
            header: 'New Value',
            accessorKey: 'new_value',
            className: 'max-w-[200px] truncate',
            render: (log) => (
                <span title={log.new_value || 'None'}>
                    {log.new_value || '-'}
                </span>
            )
        },
        {
            header: 'User',
            accessorKey: 'user_name',
            render: (log) => (
                <div className="flex flex-col">
                    <span className="text-sm font-medium">{log.user_name}</span>
                    <span className="text-xs text-muted-foreground">{log.user_email}</span>
                </div>
            )
        },
        {
            header: 'Actions',
            className: 'text-right',
            render: (log) => (
                <div className="flex justify-end">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                            e.stopPropagation();
                            onView(log);
                        }}
                        title="View Details"
                    >
                        <Eye className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    return (
        <DataTable
            data={logs}
            columns={columns}
            keyExtractor={(log) => log.id}
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
            noDataMessage="No audit logs found."
        />
    );
}
