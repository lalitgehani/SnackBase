/**
 * Records management page
 * Full implementation with CRUD operations, search, and pagination
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Database,
    Download,
    Plus,
    Search,
    RefreshCw,
    ArrowLeft,
    Trash2,
    Upload,
    BarChart2,
    Table2,
    AlertTriangle,
} from 'lucide-react';
import RecordsTable from '@/components/records/RecordsTable';
import DataEmptyState from '@/components/records/DataEmptyState';
import CreateRecordDialog from '@/components/records/CreateRecordDialog';
import ViewRecordDialog from '@/components/records/ViewRecordDialog';
import EditRecordDialog from '@/components/records/EditRecordDialog';
import DeleteRecordDialog from '@/components/records/DeleteRecordDialog';
import BulkDeleteConfirmDialog from '@/components/records/BulkDeleteConfirmDialog';
import ImportDialog from '@/components/records/ImportDialog';
import ExportDialog from '@/components/records/ExportDialog';
import FilterBuilderPanel, {
    type FilterRow,
    compileFilterExpression,
} from '@/components/records/FilterBuilderPanel';
import AggregationSummaryBar from '@/components/records/AggregationSummaryBar';
import {
    getCollectionByName,
    type Collection,
} from '@/services/collections.service';
import {
    getRecords,
    getRecordById,
    createRecord,
    updateRecord,
    deleteRecord,
    batchDeleteRecords,
    type RecordData,
    type RecordListItem,
} from '@/services/records.service';
import { handleApiError } from '@/lib/errors';
import { useAuthStore } from '@/stores/auth.store';

interface RecordsPageProps {
    /** When true, hide standalone page chrome (back link, page title) for workspace embed. */
    embedded?: boolean;
}

export default function RecordsPage({ embedded = false }: RecordsPageProps) {
    const { collectionName } = useParams<{ collectionName: string }>();
    const navigate = useNavigate();
    const { user } = useAuthStore();

    const [collection, setCollection] = useState<Collection | null>(null);
    const [data, setData] = useState<RecordListItem[] | null>(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Pagination and filtering state
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [sortBy, setSortBy] = useState('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [search, setSearch] = useState('');
    const [searchInput, setSearchInput] = useState('');

    // Filter state
    const [filterExpression, setFilterExpression] = useState('');
    const [appliedFilterRows, setAppliedFilterRows] = useState<FilterRow[]>([]);

    // Reference records state
    const [referenceRecords, setReferenceRecords] = useState<Record<string, RecordData[]>>({});

    // Pagination mode state (with localStorage persistence)
    const [paginationMode, setPaginationModeState] = useState<'page' | 'scroll'>(() => {
        if (!collectionName) return 'page';
        const stored = localStorage.getItem(`pagination_mode_${collectionName}`);
        return (stored as 'page' | 'scroll') || 'page';
    });

    // Cursor pagination state
    const [cursor, setCursor] = useState<string | null>(null);
    const [hasMore, setHasMore] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [autoLoad, setAutoLoad] = useState(false);

    // Helper to set pagination mode with localStorage persistence
    const setPaginationMode = (mode: 'page' | 'scroll') => {
        setPaginationModeState(mode);
        if (collectionName) {
            localStorage.setItem(`pagination_mode_${collectionName}`, mode);
        }
    };

    // Dialog state
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [viewDialogOpen, setViewDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
    const [importDialogOpen, setImportDialogOpen] = useState(false);
    const [exportDialogOpen, setExportDialogOpen] = useState(false);
    const [selectedRecord, setSelectedRecord] = useState<RecordListItem | null>(null);
    const [selectedRecordFull, setSelectedRecordFull] = useState<RecordData | null>(null);

    // Multi-select state
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    // Check if user has PII access (admin or superadmin role)
    const hasPiiAccess = user?.role === 'admin' || user?.role === 'superadmin';

    const hasSchema =
        !!collection?.schema && collection.schema.length > 0;

    const schemaFieldNames = useMemo(
        () => new Set((collection?.schema ?? []).map((f) => f.name)),
        [collection?.schema],
    );

    const brokenFilterFields = useMemo(() => {
        if (!hasSchema || appliedFilterRows.length === 0) return [];
        const missing = appliedFilterRows
            .map((r) => r.field)
            .filter((name) => name && !schemaFieldNames.has(name));
        return [...new Set(missing)];
    }, [appliedFilterRows, hasSchema, schemaFieldNames]);

    const fetchCollection = useCallback(async () => {
        if (!collectionName) return;
        setLoading(true);
        setError(null);

        try {
            const collectionData = await getCollectionByName(collectionName);
            setCollection(collectionData);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    }, [collectionName]);

    const fetchRecords = useCallback(async () => {
        if (!collectionName) return;

        if (paginationMode === 'page') {
            // Offset-based pagination mode
            setLoading(true);
            setError(null);

            try {
                const params: Parameters<typeof getRecords>[0] = {
                    collection: collectionName,
                    skip: (page - 1) * pageSize,
                    limit: pageSize,
                    sort: `${sortOrder === 'asc' ? '' : '-'}${sortBy}`,
                    fields: '*',
                };
                if (filterExpression) {
                    params.filter = filterExpression;
                }
                const response = await getRecords(params);
                setData(response.items);
                setTotal(response.total);
                // Clear selection when records are refreshed
                setSelectedIds(new Set());
            } catch (err) {
                setError(handleApiError(err));
            } finally {
                setLoading(false);
            }
        } else {
            // Cursor-based pagination mode - initial load
            // Pass cursor="" so the backend activates cursor mode and returns has_more/next_cursor
            setLoading(true);
            setError(null);

            try {
                const params: Parameters<typeof getRecords>[0] = {
                    collection: collectionName,
                    cursor: '',
                    limit: pageSize,
                    sort: `${sortOrder === 'asc' ? '' : '-'}${sortBy}`,
                    fields: '*',
                };
                if (filterExpression) {
                    params.filter = filterExpression;
                }
                const response = await getRecords(params);
                setData(response.items);
                // response is CursorListResponse when cursor param is passed
                const cursorResponse = response as {
                    items: typeof response.items;
                    next_cursor: string | null;
                    has_more: boolean;
                };
                setCursor(cursorResponse.next_cursor || null);
                setHasMore(cursorResponse.has_more || false);
                // Clear selection when records are refreshed
                setSelectedIds(new Set());
            } catch (err) {
                setError(handleApiError(err));
            } finally {
                setLoading(false);
            }
        }
    }, [collectionName, paginationMode, page, pageSize, sortBy, sortOrder, filterExpression]);

    useEffect(() => {
        fetchCollection();
    }, [fetchCollection]);

    useEffect(() => {
        if (collection) {
            fetchRecords();
        }
    }, [collection, fetchRecords]);

    // Handle pagination mode changes
    useEffect(() => {
        if (collection && paginationMode) {
            // Reset pagination state when mode changes
            setPage(1);
            setCursor(null);
            setAutoLoad(false);
            setHasMore(true);
            fetchRecords();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [paginationMode, collectionName]);

    // Load more records in cursor scroll mode
    const loadMoreRecords = useCallback(async () => {
        if (!collectionName || !cursor || isLoadingMore) return;
        setIsLoadingMore(true);
        setError(null);

        try {
            const params: Parameters<typeof getRecords>[0] = {
                collection: collectionName,
                cursor: cursor,
                limit: pageSize,
                sort: `${sortOrder === 'asc' ? '' : '-'}${sortBy}`,
                fields: '*',
            };
            if (filterExpression) {
                params.filter = filterExpression;
            }
            const response = await getRecords(params);
            setData((prev) => [...(prev || []), ...response.items]);
            setCursor(response.next_cursor || null);
            setHasMore(response.has_more || false);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setIsLoadingMore(false);
        }
    }, [collectionName, cursor, pageSize, sortBy, sortOrder, filterExpression, isLoadingMore]);

    // Pre-fetch reference records for all reference fields so the table and view dialog
    // can display display values without waiting for a dialog to open.
    useEffect(() => {
        if (!collection?.schema) return;
        collection.schema
            .filter((f) => f.type === 'reference' && f.collection)
            .forEach((f) => handleFetchReferenceRecords(f.collection!));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [collection?.name]);

    const handleSort = (column: string) => {
        if (sortBy === column) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(column);
            setSortOrder('desc');
        }
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSearch(searchInput);
        setPage(1);
    };

    const handleClearSearch = () => {
        setSearch('');
        setSearchInput('');
        setPage(1);
    };

    const handleFetchReferenceRecords = async (refCollection: string) => {
        if (referenceRecords[refCollection]) {
            return; // Already fetched
        }

        try {
            const response = await getRecords({
                collection: refCollection,
                skip: 0,
                limit: 100,
                sort: '-created_at',
            });
            setReferenceRecords((prev) => ({
                ...prev,
                [refCollection]: response.items,
            }));
        } catch (err) {
            console.error(`Failed to fetch reference records for ${refCollection}:`, err);
        }
    };

    const handleCreateRecord = async (data: RecordData) => {
        if (!collectionName) throw new Error('Collection name is required');
        await createRecord(collectionName, data);
        await fetchRecords();
    };

    const handleView = async (record: RecordListItem) => {
        if (!collectionName) return;
        try {
            const fullRecord = await getRecordById(collectionName, record.id);
            setSelectedRecordFull(fullRecord);
            setViewDialogOpen(true);
        } catch (err) {
            setError(handleApiError(err));
        }
    };

    const handleEdit = async (record: RecordListItem) => {
        if (!collectionName) return;
        try {
            const fullRecord = await getRecordById(collectionName, record.id);
            setSelectedRecordFull(fullRecord);
            setEditDialogOpen(true);
        } catch (err) {
            setError(handleApiError(err));
        }
    };

    const handleUpdateRecord = async (recordId: string, data: RecordData) => {
        if (!collectionName) throw new Error('Collection name is required');
        await updateRecord(collectionName, recordId, data);
        await fetchRecords();
    };

    const handleDelete = (record: RecordListItem) => {
        setSelectedRecord(record);
        setDeleteDialogOpen(true);
    };

    const handleDeleteRecord = async (recordId: string) => {
        if (!collectionName) throw new Error('Collection name is required');
        await deleteRecord(collectionName, recordId);
        await fetchRecords();
    };

    const handleBulkDelete = async () => {
        if (!collectionName || selectedIds.size === 0) return;
        await batchDeleteRecords(collectionName, Array.from(selectedIds));
        setSelectedIds(new Set());
        await fetchRecords();
    };

    const handleNavigateToRecord = (refCollection: string) => {
        navigate(`/admin/collections/${refCollection}/data`);
    };

    const openSchema = () => {
        if (!collectionName) return;
        navigate(`/admin/collections/${collectionName}/schema`);
    };

    const openRules = () => {
        if (!collectionName) return;
        navigate(`/admin/collections/${collectionName}/rules`);
    };

    const handleApplyFilters = (expression: string, rows: FilterRow[]) => {
        setFilterExpression(expression);
        setAppliedFilterRows(rows);
        setPage(1);
        setCursor(null);
        setHasMore(true);
    };

    const handleClearFilters = () => {
        setFilterExpression('');
        setAppliedFilterRows([]);
        setPage(1);
        setCursor(null);
        setHasMore(true);
    };

    const handleRemoveFilterPill = (id: string) => {
        if (!collection) return;
        const remaining = appliedFilterRows.filter((r) => r.id !== id);
        const expression = compileFilterExpression(remaining, [
            ...(collection.schema ?? []),
        ]);
        setAppliedFilterRows(remaining);
        setFilterExpression(expression);
        setPage(1);
        setCursor(null);
        setHasMore(true);
    };

    const actionButtons =
        hasSchema ? (
            <>
                {embedded && (
                    <Button
                        variant="outline"
                        size={embedded ? 'sm' : 'default'}
                        onClick={openSchema}
                        className="gap-2"
                        data-testid="data-open-schema"
                    >
                        <Table2 className="h-4 w-4" />
                        Schema
                    </Button>
                )}
                {!embedded && (
                    <Button
                        variant="outline"
                        onClick={() =>
                            navigate(`/admin/collections/${collectionName}/analytics`)
                        }
                        className="gap-2"
                    >
                        <BarChart2 className="h-4 w-4" />
                        Analytics
                    </Button>
                )}
                <Button
                    variant="outline"
                    size={embedded ? 'sm' : 'default'}
                    onClick={() => setExportDialogOpen(true)}
                    className="gap-2"
                >
                    <Download className="h-4 w-4" />
                    Export
                </Button>
                <Button
                    variant="outline"
                    size={embedded ? 'sm' : 'default'}
                    onClick={() => setImportDialogOpen(true)}
                    className="gap-2"
                >
                    <Upload className="h-4 w-4" />
                    Import
                </Button>
                <Button
                    size={embedded ? 'sm' : 'default'}
                    onClick={() => setCreateDialogOpen(true)}
                    className="gap-2"
                >
                    <Plus className="h-4 w-4" />
                    Create Record
                </Button>
            </>
        ) : null;

    const mainContent = (
        <div className="space-y-4">
            {/* Search Bar + Refresh */}
            <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        placeholder="Search records..."
                        className="pl-9"
                    />
                </div>
                <Button type="submit" variant="secondary">
                    Search
                </Button>
                {search && (
                    <Button
                        type="button"
                        variant="outline"
                        onClick={handleClearSearch}
                    >
                        Clear
                    </Button>
                )}
                <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={fetchRecords}
                    disabled={loading}
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
            </form>

            {/* Filter Builder Panel */}
            {hasSchema && collection && (
                <FilterBuilderPanel
                    schema={collection.schema}
                    appliedRows={appliedFilterRows}
                    onApply={handleApplyFilters}
                    onClear={handleClearFilters}
                    onRemovePill={handleRemoveFilterPill}
                />
            )}

            {/* Broken filter fields hint */}
            {brokenFilterFields.length > 0 && (
                <div
                    className="flex flex-wrap items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3"
                    data-testid="broken-filter-hint"
                >
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <div className="min-w-0 flex-1 space-y-1">
                        <p className="text-sm font-medium">
                            Filter references unknown field
                            {brokenFilterFields.length > 1 ? 's' : ''}:{' '}
                            <span className="font-mono">
                                {brokenFilterFields.join(', ')}
                            </span>
                        </p>
                        <p className="text-sm text-muted-foreground">
                            These fields may have been removed or renamed. Update filters
                            or review the schema.
                        </p>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={openSchema}
                        className="gap-1.5"
                    >
                        <Table2 className="h-3.5 w-3.5" />
                        Open Schema
                    </Button>
                </div>
            )}

            {/* Aggregation Summary Bar */}
            {hasSchema && collection && (
                <AggregationSummaryBar
                    collection={collection}
                    filterExpression={filterExpression}
                />
            )}

            {/* Collection not found */}
            {error && !collection && (
                <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
                    <p className="font-medium text-destructive">Failed to load collection</p>
                    <p className="mt-1 text-sm text-muted-foreground">{error}</p>
                </div>
            )}

            {/* Loading State */}
            {loading && !data && (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            )}

            {/* Empty: no schema */}
            {collection && !hasSchema && (
                <DataEmptyState
                    variant="no-schema"
                    collectionName={collectionName || collection.name}
                    onOpenSchema={openSchema}
                />
            )}

            {/* Floating bulk action bar — shown when records are selected */}
            {selectedIds.size > 0 && (
                <div className="flex items-center gap-3 rounded-lg border bg-muted px-4 py-2">
                    <span className="text-sm font-medium">
                        {selectedIds.size} record{selectedIds.size === 1 ? '' : 's'} selected
                    </span>
                    <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setBulkDeleteDialogOpen(true)}
                        className="gap-1"
                    >
                        <Trash2 className="h-4 w-4" />
                        Delete
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedIds(new Set())}
                    >
                        Deselect all
                    </Button>
                </div>
            )}

            {/* Table */}
            {!loading &&
                data &&
                data.length > 0 &&
                hasSchema &&
                collection && (
                    <RecordsTable
                        records={data}
                        schema={collection.schema}
                        collectionName={collectionName || collection.name}
                        sortBy={sortBy}
                        sortOrder={sortOrder}
                        onSort={handleSort}
                        onView={handleView}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        hasPiiAccess={hasPiiAccess}
                        referenceRecords={referenceRecords}
                        selectedIds={selectedIds}
                        onSelectionChange={setSelectedIds}
                        totalItems={total}
                        page={page}
                        pageSize={pageSize}
                        onPageChange={setPage}
                        onPageSizeChange={(size) => {
                            setPageSize(size);
                            setPage(1);
                        }}
                        paginationMode={paginationMode}
                        onPaginationModeChange={setPaginationMode}
                        hasMore={hasMore}
                        onLoadMore={loadMoreRecords}
                        isLoadingMore={isLoadingMore}
                        autoLoad={autoLoad}
                        onAutoLoadChange={setAutoLoad}
                    />
                )}

            {/* Empty: filters */}
            {!loading &&
                data &&
                data.length === 0 &&
                !!filterExpression &&
                hasSchema && (
                    <DataEmptyState
                        variant="filtered"
                        collectionName={collectionName || ''}
                        onClearFilters={handleClearFilters}
                    />
                )}

            {/* Empty: search only */}
            {!loading &&
                data &&
                data.length === 0 &&
                !filterExpression &&
                !!search &&
                hasSchema && (
                    <DataEmptyState
                        variant="search"
                        collectionName={collectionName || ''}
                        onClearSearch={handleClearSearch}
                        onCreateRecord={() => setCreateDialogOpen(true)}
                    />
                )}

            {/* Empty: no records */}
            {!loading &&
                data &&
                data.length === 0 &&
                !filterExpression &&
                !search &&
                hasSchema && (
                    <DataEmptyState
                        variant="no-records"
                        collectionName={collectionName || collection?.name || ''}
                        onCreateRecord={() => setCreateDialogOpen(true)}
                        onOpenSchema={openSchema}
                        onOpenRules={openRules}
                    />
                )}
        </div>
    );

    return (
        <div className="space-y-6" data-testid="records-page">
            {/* Standalone header only — workspace shell owns title/tabs when embedded */}
            {!embedded && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <div className="mb-2 flex items-center gap-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => navigate('/admin/collections')}
                                className="gap-1"
                            >
                                <ArrowLeft className="h-4 w-4" />
                                Collections
                            </Button>
                        </div>
                        <h1 className="text-3xl font-bold">
                            {collectionName || 'Records'}
                        </h1>
                        <p className="mt-2 text-muted-foreground">
                            Manage records in the <strong>{collectionName}</strong>{' '}
                            collection
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        {actionButtons}
                    </div>
                </div>
            )}

            {embedded ? (
                <div className="space-y-4" data-testid="records-embedded-panel">
                    <div className="flex flex-wrap items-center justify-end gap-2">
                        {actionButtons}
                    </div>
                    {mainContent}
                </div>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Database className="h-5 w-5 text-primary" />
                            Records Management
                        </CardTitle>
                        <CardDescription>
                            View, create, edit, and delete records
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">{mainContent}</CardContent>
                </Card>
            )}

            {/* Dialogs */}
            {collection && (
                <>
                    <CreateRecordDialog
                        open={createDialogOpen}
                        onOpenChange={setCreateDialogOpen}
                        onSubmit={handleCreateRecord}
                        schema={collection.schema}
                        collectionName={collection.name}
                        referenceRecords={referenceRecords}
                        onFetchReferenceRecords={handleFetchReferenceRecords}
                    />

                    <ViewRecordDialog
                        open={viewDialogOpen}
                        onOpenChange={setViewDialogOpen}
                        schema={collection.schema}
                        collectionName={collection.name}
                        record={selectedRecordFull}
                        hasPiiAccess={hasPiiAccess}
                        referenceRecords={referenceRecords}
                        onNavigateToRecord={handleNavigateToRecord}
                    />

                    <EditRecordDialog
                        open={editDialogOpen}
                        onOpenChange={setEditDialogOpen}
                        onSubmit={handleUpdateRecord}
                        schema={collection.schema}
                        collectionName={collection.name}
                        record={selectedRecordFull}
                        recordId={(selectedRecordFull?.id as string) || ''}
                        referenceRecords={referenceRecords}
                        onFetchReferenceRecords={handleFetchReferenceRecords}
                    />

                    <DeleteRecordDialog
                        open={deleteDialogOpen}
                        onOpenChange={setDeleteDialogOpen}
                        onConfirm={handleDeleteRecord}
                        schema={collection.schema}
                        collectionName={collection.name}
                        record={selectedRecordFull}
                        recordId={selectedRecord?.id || ''}
                    />

                    <BulkDeleteConfirmDialog
                        open={bulkDeleteDialogOpen}
                        onOpenChange={setBulkDeleteDialogOpen}
                        onConfirm={handleBulkDelete}
                        count={selectedIds.size}
                        collectionName={collection.name}
                    />

                    <ImportDialog
                        open={importDialogOpen}
                        onOpenChange={setImportDialogOpen}
                        collection={collection.name}
                        schema={collection.schema}
                        onSuccess={() => fetchRecords()}
                    />

                    <ExportDialog
                        open={exportDialogOpen}
                        onOpenChange={setExportDialogOpen}
                        collection={collection.name}
                        filterExpression={filterExpression}
                        total={total}
                    />
                </>
            )}
        </div>
    );
}
