import React from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from '@/components/ui/pagination';
import { Button } from '@/components/ui/button';
import { ArrowUpDown, RefreshCw } from 'lucide-react';

export interface Column<T> {
    header: string;
    accessorKey?: keyof T;
    render?: (item: T) => React.ReactNode;
    sortable?: boolean;
    className?: string; // For setting width or alignment
}

export interface DispatchPagination {
    page: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
}

export interface DispatchSorting {
    sortBy: string;
    sortOrder: 'asc' | 'desc';
    onSort: (column: string) => void;
}

interface DataTableProps<T> {
    data: T[];
    columns: Column<T>[];
    keyExtractor: (item: T) => string | number;
    isLoading?: boolean;
    totalItems?: number; // Total items in DB for server-side pagination
    pagination?: DispatchPagination;
    sorting?: DispatchSorting;
    onRowClick?: (item: T) => void;
    noDataMessage?: string;
}

export function DataTable<T>({
    data,
    columns,
    keyExtractor,
    isLoading = false,
    totalItems = 0,
    pagination,
    sorting,
    onRowClick,
    noDataMessage = 'No data found',
}: DataTableProps<T>) {

    // Helper to resolve cell content
    const renderCell = (item: T, column: Column<T>) => {
        if (column.render) {
            return column.render(item);
        }
        if (column.accessorKey) {
            return item[column.accessorKey] as React.ReactNode;
        }
        return null;
    };

    // Calculate pagination values
    const currentPage = pagination?.page || 1;
    const pageSize = pagination?.pageSize || 10;
    const totalPages = Math.ceil(totalItems / pageSize) || 1;

    // Pagination helpers
    const canGoPrevious = currentPage > 1;
    const canGoNext = currentPage < totalPages;
    const showingStart = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const showingEnd = Math.min(currentPage * pageSize, totalItems);

    const handleSort = (column: Column<T>) => {
        if (sorting && column.sortable && column.accessorKey) {
            sorting.onSort(String(column.accessorKey));
        }
    };

    return (
        <div className="space-y-4">
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            {columns.map((col, index) => (
                                <TableHead key={index} className={col.className}>
                                    {sorting && col.sortable ? (
                                        <Button
                                            variant="ghost"
                                            onClick={() => handleSort(col)}
                                            className="-ml-4 h-8 px-4 data-[state=open]:bg-accent hover:bg-transparent hover:text-primary"
                                        >
                                            {col.header}
                                            {sorting.sortBy === col.accessorKey ? (
                                                <ArrowUpDown className={`ml-2 h-4 w-4 transform ${sorting.sortOrder === 'asc' ? 'rotate-180' : ''}`} />
                                            ) : (
                                                <ArrowUpDown className="ml-2 h-4 w-4 opacity-50" />
                                            )}
                                        </Button>
                                    ) : (
                                        col.header
                                    )}
                                </TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow>
                                <TableCell colSpan={columns.length} className="h-24 text-center">
                                    <div className="flex items-center justify-center py-4">
                                        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                                    </div>
                                </TableCell>
                            </TableRow>
                        ) : data.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                                    {noDataMessage}
                                </TableCell>
                            </TableRow>
                        ) : (
                            data.map((item) => (
                                <TableRow
                                    key={keyExtractor(item)}
                                    onClick={() => onRowClick && onRowClick(item)}
                                    className={onRowClick ? "cursor-pointer hover:bg-muted/50" : ""}
                                >
                                    {columns.map((col, cIndex) => (
                                        <TableCell key={cIndex} className={col.className}>
                                            {renderCell(item, col)}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination Controls */}
            {pagination && totalItems > 0 && (
                <div className="flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                        <span>Rows per page</span>
                        <Select
                            value={`${pageSize}`}
                            onValueChange={(value) => {
                                pagination.onPageSizeChange(Number(value));
                            }}
                        >
                            <SelectTrigger className="h-8 w-[70px]">
                                <SelectValue placeholder={pageSize} />
                            </SelectTrigger>
                            <SelectContent side="top">
                                {[10, 20, 30, 40, 50, 100].map((size) => (
                                    <SelectItem key={size} value={`${size}`}>
                                        {size}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <span className="hidden md:inline-block ml-4">
                            Showing {showingStart} to {showingEnd} of {totalItems} entries
                        </span>
                    </div>

                    <div className="flex items-center justify-center sm:justify-end">
                        <div className="md:hidden text-sm text-muted-foreground mr-4">
                            {currentPage} / {totalPages}
                        </div>
                        <Pagination>
                            <PaginationContent>
                                <PaginationItem>
                                    <PaginationPrevious
                                        onClick={() => canGoPrevious && pagination.onPageChange(currentPage - 1)}
                                        className={!canGoPrevious ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                                    />
                                </PaginationItem>

                                {/* Simple logic for now: show surrounding pages */}
                                {(() => {


                                    const items = [];

                                    // Always show first
                                    if (totalPages > 0) {
                                        // If many pages, logic needed
                                    }

                                    /* Simplified Logic for generic component */
                                    // Always show Page 1
                                    if (totalPages > 1) {
                                        items.push(1);
                                    }

                                    // If current is far from 1, ellipsis
                                    if (currentPage > 3) items.push('e1');

                                    // Surrounding
                                    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
                                        items.push(i);
                                    }

                                    // If current is far from end, ellipsis
                                    if (currentPage < totalPages - 2) items.push('e2');

                                    // Always show last
                                    items.push(totalPages);

                                    // Dedup and single page case
                                    const uniqueItems = Array.from(new Set(items));
                                    // Basic 1..N if totalPages is small
                                    const renderList = totalPages <= 7
                                        ? Array.from({ length: totalPages }, (_, i) => i + 1)
                                        : uniqueItems;

                                    return renderList.map((p, idx) => {
                                        if (p === 'e1' || p === 'e2') {
                                            return (
                                                <PaginationItem key={`ellipsis-${idx}`}>
                                                    <PaginationEllipsis />
                                                </PaginationItem>
                                            );
                                        }
                                        const pageNum = p as number;
                                        return (
                                            <PaginationItem key={pageNum} className="hidden sm:inline-block">
                                                <PaginationLink
                                                    isActive={currentPage === pageNum}
                                                    onClick={() => pagination.onPageChange(pageNum)}
                                                    className="cursor-pointer"
                                                >
                                                    {pageNum}
                                                </PaginationLink>
                                            </PaginationItem>
                                        );
                                    });
                                })()}

                                <PaginationItem>
                                    <PaginationNext
                                        onClick={() => canGoNext && pagination.onPageChange(currentPage + 1)}
                                        className={!canGoNext ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                                    />
                                </PaginationItem>
                            </PaginationContent>
                        </Pagination>
                    </div>
                </div>
            )}
        </div>
    );
}
