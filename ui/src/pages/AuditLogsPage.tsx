/**
 * Audit logs viewer page
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileText, Search, RefreshCw, Download, Filter } from 'lucide-react';
import AuditLogsTable from '@/components/audit-logs/AuditLogsTable';
import AuditLogDetailDialog from '@/components/audit-logs/AuditLogDetailDialog';
import {
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from '@/components/ui/pagination';
import {
    getAuditLogs,
    exportAuditLogs,
    type AuditLogItem,
    type AuditLogListResponse,
    type AuditLogFilters,
} from '@/services/audit.service';
import { handleApiError } from '@/lib/api';

export default function AuditLogsPage() {
    const [data, setData] = useState<AuditLogListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Pagination and filtering state
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [sortBy, setSortBy] = useState('occurred_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    // Filters
    const [tableName, setTableName] = useState('');
    const [operation, setOperation] = useState('all');
    const [recordId, setRecordId] = useState('');
    const [showFilters, setShowFilters] = useState(false);

    // Dialog state
    const [detailDialogOpen, setDetailDialogOpen] = useState(false);
    const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

    const fetchLogs = async () => {
        setLoading(true);
        setError(null);

        try {
            const filters: AuditLogFilters = {
                skip: (page - 1) * pageSize,
                limit: pageSize,
                sort_by: sortBy,
                sort_order: sortOrder,
                table_name: tableName || undefined,
                operation: operation !== 'all' ? operation : undefined,
                record_id: recordId || undefined,
                // user_id is backend, but we might filter by user_email if we add it to router
                // for now we stick to what the router supports
            };

            const response = await getAuditLogs(filters);
            setData(response);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, [page, pageSize, sortBy, sortOrder]); // Only refetch on page/sort/size change automatically

    const handleSearch = (e?: React.FormEvent) => {
        e?.preventDefault();
        setPage(1);
        fetchLogs();
    };

    const handleSort = (column: string) => {
        if (sortBy === column) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(column);
            setSortOrder('desc');
        }
    };

    const handleExport = async (format: 'csv' | 'json') => {
        try {
            const filters: AuditLogFilters = {
                table_name: tableName || undefined,
                operation: operation !== 'all' ? operation : undefined,
                record_id: recordId || undefined,
            };
            await exportAuditLogs(format, filters);
        } catch (err) {
            alert('Failed to export: ' + handleApiError(err));
        }
    };

    const handleView = (log: AuditLogItem) => {
        setSelectedLog(log);
        setDetailDialogOpen(true);
    };

    const totalPages = data ? Math.ceil(data.total / pageSize) : 1;
    const canGoPrevious = page > 1;
    const canGoNext = page < totalPages;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Audit Logs</h1>
                    <p className="text-muted-foreground mt-2">View and export GxP-compliant audit trails</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => handleExport('csv')} className="gap-2">
                        <Download className="h-4 w-4" />
                        Export CSV
                    </Button>
                    <Button variant="outline" onClick={() => handleExport('json')} className="gap-2">
                        <Download className="h-4 w-4" />
                        Export JSON
                    </Button>
                </div>
            </div>

            {/* Filters and Actions */}
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-primary" />
                            Audit Log Viewer
                        </CardTitle>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowFilters(!showFilters)}
                            className="gap-2"
                        >
                            <Filter className="h-4 w-4" />
                            {showFilters ? 'Hide Filters' : 'Show Filters'}
                        </Button>
                    </div>
                    <CardDescription>
                        Track all data changes with column-level granularity and integrity protection
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Filter Bar */}
                    <form onSubmit={handleSearch} className={`grid gap-4 transition-all ${showFilters ? 'grid-cols-4' : 'hidden'}`}>
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground uppercase">Collection</label>
                            <Input
                                value={tableName}
                                onChange={(e) => setTableName(e.target.value)}
                                placeholder="Filter by collection..."
                                size={1}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground uppercase">Operation</label>
                            <Select value={operation} onValueChange={setOperation}>
                                <SelectTrigger>
                                    <SelectValue placeholder="All Operations" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Operations</SelectItem>
                                    <SelectItem value="CREATE">CREATE</SelectItem>
                                    <SelectItem value="UPDATE">UPDATE</SelectItem>
                                    <SelectItem value="DELETE">DELETE</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground uppercase">Record ID</label>
                            <Input
                                value={recordId}
                                onChange={(e) => setRecordId(e.target.value)}
                                placeholder="Filter by record ID..."
                            />
                        </div>
                        <div className="flex items-end gap-2">
                            <Button type="submit" variant="secondary" className="flex-1">
                                <Search className="h-4 w-4 mr-2" />
                                Filter
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setTableName('');
                                    setOperation('all');
                                    setRecordId('');
                                    setPage(1);
                                    setTimeout(() => handleSearch(), 0);
                                }}
                            >
                                Reset
                            </Button>
                        </div>
                    </form>

                    {!showFilters && (
                        <div className="flex justify-end">
                            <Button
                                type="button"
                                variant="outline"
                                size="icon"
                                onClick={fetchLogs}
                                disabled={loading}
                            >
                                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                            </Button>
                        </div>
                    )}

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load audit logs</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchLogs} className="mt-4" size="sm">
                                Try Again
                            </Button>
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && !data && (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    )}

                    {/* Table */}
                    {!loading && data && (
                        <>
                            <AuditLogsTable
                                logs={data.items}
                                sortBy={sortBy}
                                sortOrder={sortOrder}
                                onSort={handleSort}
                                onView={handleView}
                            />

                            {/* Pagination */}
                            <div className="flex items-center justify-between mt-4">
                                <div className="flex items-center space-x-6 lg:space-x-8">
                                    <div className="flex items-center space-x-2">
                                        <p className="text-sm font-medium">Rows per page</p>
                                        <Select
                                            value={`${pageSize}`}
                                            onValueChange={(value) => {
                                                setPageSize(Number(value));
                                                setPage(1);
                                            }}
                                        >
                                            <SelectTrigger className="h-8 w-[70px]">
                                                <SelectValue placeholder={pageSize} />
                                            </SelectTrigger>
                                            <SelectContent side="top">
                                                {[10, 20, 30, 40, 50].map((pageSize) => (
                                                    <SelectItem key={pageSize} value={`${pageSize}`}>
                                                        {pageSize}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="flex w-[100px] items-center justify-center text-sm font-medium">
                                        Page {page} of {totalPages}
                                    </div>
                                </div>
                                <p className="text-sm text-muted-foreground hidden md:block">
                                    Showing {data.items.length === 0 ? 0 : data.skip + 1} to{' '}
                                    {Math.min(data.skip + data.limit, data.total)} of {data.total} entries
                                </p>

                                <Pagination className="justify-end w-auto">
                                    <PaginationContent>
                                        <PaginationItem>
                                            <PaginationPrevious
                                                onClick={() => canGoPrevious && setPage(page - 1)}
                                                className={!canGoPrevious ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                                            />
                                        </PaginationItem>

                                        {/* Dynamic Pagination Items */}
                                        {(() => {
                                            const items = [];
                                            const maxVisiblePages = 5;

                                            if (totalPages <= maxVisiblePages) {
                                                for (let i = 1; i <= totalPages; i++) {
                                                    items.push(
                                                        <PaginationItem key={i}>
                                                            <PaginationLink
                                                                isActive={page === i}
                                                                onClick={() => setPage(i)}
                                                                className="cursor-pointer"
                                                            >
                                                                {i}
                                                            </PaginationLink>
                                                        </PaginationItem>
                                                    );
                                                }
                                            } else {
                                                // Always show first page
                                                items.push(
                                                    <PaginationItem key={1}>
                                                        <PaginationLink
                                                            isActive={page === 1}
                                                            onClick={() => setPage(1)}
                                                            className="cursor-pointer"
                                                        >
                                                            1
                                                        </PaginationLink>
                                                    </PaginationItem>
                                                );

                                                // Show ellipsis if far from start
                                                if (page > 3) {
                                                    items.push(
                                                        <PaginationItem key="ellipsis-start">
                                                            <PaginationEllipsis />
                                                        </PaginationItem>
                                                    );
                                                }

                                                // Show current page and neighbors
                                                const start = Math.max(2, page - 1);
                                                const end = Math.min(totalPages - 1, page + 1);

                                                for (let i = start; i <= end; i++) {
                                                    items.push(
                                                        <PaginationItem key={i}>
                                                            <PaginationLink
                                                                isActive={page === i}
                                                                onClick={() => setPage(i)}
                                                                className="cursor-pointer"
                                                            >
                                                                {i}
                                                            </PaginationLink>
                                                        </PaginationItem>
                                                    );
                                                }

                                                // Show ellipsis if far from end
                                                if (page < totalPages - 2) {
                                                    items.push(
                                                        <PaginationItem key="ellipsis-end">
                                                            <PaginationEllipsis />
                                                        </PaginationItem>
                                                    );
                                                }

                                                // Always show last page
                                                items.push(
                                                    <PaginationItem key={totalPages}>
                                                        <PaginationLink
                                                            isActive={page === totalPages}
                                                            onClick={() => setPage(totalPages)}
                                                            className="cursor-pointer"
                                                        >
                                                            {totalPages}
                                                        </PaginationLink>
                                                    </PaginationItem>
                                                );
                                            }

                                            return items;
                                        })()}

                                        <PaginationItem>
                                            <PaginationNext
                                                onClick={() => canGoNext && setPage(page + 1)}
                                                className={!canGoNext ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                                            />
                                        </PaginationItem>
                                    </PaginationContent>
                                </Pagination>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>

            {/* Detail Dialog */}
            <AuditLogDetailDialog
                open={detailDialogOpen}
                onOpenChange={setDetailDialogOpen}
                log={selectedLog}
            />
        </div>
    );
}
