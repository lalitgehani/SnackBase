/**
 * Collections table component
 * Displays collections with sorting and actions
 */

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Eye, Pencil, Trash2, ArrowUp, ArrowDown } from 'lucide-react';
import type { CollectionListItem } from '@/services/collections.service';

interface CollectionsTableProps {
    collections: CollectionListItem[];
    sortBy: string;
    sortOrder: 'asc' | 'desc';
    onSort: (column: string) => void;
    onView: (collection: CollectionListItem) => void;
    onEdit: (collection: CollectionListItem) => void;
    onDelete: (collection: CollectionListItem) => void;
}

export default function CollectionsTable({
    collections,
    sortBy,
    sortOrder,
    onSort,
    onView,
    onEdit,
    onDelete,
}: CollectionsTableProps) {
    const SortIcon = ({ column }: { column: string }) => {
        if (sortBy !== column) return null;
        return sortOrder === 'asc' ? (
            <ArrowUp className="h-3 w-3 inline ml-1" />
        ) : (
            <ArrowDown className="h-3 w-3 inline ml-1" />
        );
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    return (
        <div className="border rounded-lg">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => onSort('name')}
                        >
                            Name <SortIcon column="name" />
                        </TableHead>
                        <TableHead>ID</TableHead>
                        <TableHead
                            className="cursor-pointer hover:bg-muted/50 text-right"
                            onClick={() => onSort('fields_count')}
                        >
                            Fields <SortIcon column="fields_count" />
                        </TableHead>
                        <TableHead
                            className="cursor-pointer hover:bg-muted/50 text-right"
                            onClick={() => onSort('records_count')}
                        >
                            Records <SortIcon column="records_count" />
                        </TableHead>
                        <TableHead
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => onSort('created_at')}
                        >
                            Created <SortIcon column="created_at" />
                        </TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {collections.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                                No collections found
                            </TableCell>
                        </TableRow>
                    ) : (
                        collections.map((collection) => (
                            <TableRow key={collection.id}>
                                <TableCell className="font-medium">{collection.name}</TableCell>
                                <TableCell className="font-mono text-xs text-muted-foreground">
                                    {collection.id.substring(0, 8)}...
                                </TableCell>
                                <TableCell className="text-right">{collection.fields_count}</TableCell>
                                <TableCell className="text-right">{collection.records_count}</TableCell>
                                <TableCell>{formatDate(collection.created_at)}</TableCell>
                                <TableCell className="text-right">
                                    <div className="flex justify-end gap-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => onView(collection)}
                                            title="View schema"
                                        >
                                            <Eye className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => onEdit(collection)}
                                            title="Edit schema"
                                        >
                                            <Pencil className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => onDelete(collection)}
                                            title="Delete collection"
                                        >
                                            <Trash2 className="h-4 w-4 text-destructive" />
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
