/**
 * Audit logs table component
 */

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, ArrowUpDown } from 'lucide-react';
import { format } from 'date-fns';
import type { AuditLogItem } from '@/services/audit.service';

interface AuditLogsTableProps {
    logs: AuditLogItem[];
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    onSort: (column: string) => void;
    onView: (log: AuditLogItem) => void;
}

export default function AuditLogsTable({
    logs,
    onSort,
    onView,
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

    const SortButton = ({ column, label }: { column: string; label: string }) => (
        <Button
            variant="ghost"
            size="sm"
            className="-ml-3 h-8 data-[state=open]:bg-accent"
            onClick={() => onSort(column)}
        >
            <span>{label}</span>
            <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
    );

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>
                            <SortButton column="occurred_at" label="Timestamp" />
                        </TableHead>
                        <TableHead>
                            <SortButton column="operation" label="Operation" />
                        </TableHead>
                        <TableHead>
                            <SortButton column="table_name" label="Collection" />
                        </TableHead>
                        <TableHead>Record ID</TableHead>
                        <TableHead>Column</TableHead>
                        <TableHead>User</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {logs.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                                No audit logs found.
                            </TableCell>
                        </TableRow>
                    ) : (
                        logs.map((log) => (
                            <TableRow key={log.id}>
                                <TableCell className="whitespace-nowrap">
                                    {format(new Date(log.occurred_at), 'yyyy-MM-dd HH:mm:ss')}
                                </TableCell>
                                <TableCell>{getOperationBadge(log.operation)}</TableCell>
                                <TableCell className="font-medium">{log.table_name}</TableCell>
                                <TableCell className="font-mono text-xs">{log.record_id}</TableCell>
                                <TableCell>{log.column_name}</TableCell>
                                <TableCell>
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium">{log.user_name}</span>
                                        <span className="text-xs text-muted-foreground">{log.user_email}</span>
                                    </div>
                                </TableCell>
                                <TableCell className="text-right">
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => onView(log)}
                                        title="View Details"
                                    >
                                        <Eye className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        </div>
    );
}
