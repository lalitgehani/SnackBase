/**
 * Accounts table component
 * Displays list of accounts with sorting and actions
 */

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Eye, Pencil, Trash2, ArrowUpDown } from 'lucide-react';
import type { AccountListItem } from '@/services/accounts.service';

interface AccountsTableProps {
    accounts: AccountListItem[];
    sortBy: string;
    sortOrder: 'asc' | 'desc';
    onSort: (column: string) => void;
    onView: (account: AccountListItem) => void;
    onEdit: (account: AccountListItem) => void;
    onDelete: (account: AccountListItem) => void;
}

export default function AccountsTable({
    accounts,
    sortBy,
    sortOrder,
    onSort,
    onView,
    onEdit,
    onDelete,
}: AccountsTableProps) {
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString();
    };

    const SortableHeader = ({ column, label }: { column: string; label: string }) => (
        <TableHead>
            <Button
                variant="ghost"
                onClick={() => onSort(column)}
                className="h-8 px-2 lg:px-3"
            >
                {label}
                {sortBy === column && (
                    <ArrowUpDown className={`ml-2 h-4 w-4 ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />
                )}
                {sortBy !== column && <ArrowUpDown className="ml-2 h-4 w-4 opacity-50" />}
            </Button>
        </TableHead>
    );

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <SortableHeader column="id" label="ID" />
                        <SortableHeader column="slug" label="Slug" />
                        <SortableHeader column="name" label="Name" />
                        <SortableHeader column="created_at" label="Created At" />
                        <TableHead>User Count</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {accounts.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                                No accounts found
                            </TableCell>
                        </TableRow>
                    ) : (
                        accounts.map((account) => (
                            <TableRow key={account.id}>
                                <TableCell className="font-mono text-sm">{account.id}</TableCell>
                                <TableCell className="font-medium">{account.slug}</TableCell>
                                <TableCell>{account.name}</TableCell>
                                <TableCell className="text-muted-foreground">
                                    {formatDate(account.created_at)}
                                </TableCell>
                                <TableCell>{account.user_count}</TableCell>
                                <TableCell>
                                    <Badge variant="default">{account.status}</Badge>
                                </TableCell>
                                <TableCell className="text-right">
                                    <div className="flex justify-end gap-2">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => onView(account)}
                                            title="View details"
                                        >
                                            <Eye className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => onEdit(account)}
                                            title="Edit account"
                                        >
                                            <Pencil className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => onDelete(account)}
                                            title="Delete account"
                                            className="text-destructive hover:text-destructive"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        </div>
    );
}
