/**
 * Records management page
 * Full implementation with CRUD operations, search, and pagination
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Database, Plus, Search, RefreshCw, ArrowLeft } from 'lucide-react';
import RecordsTable from '@/components/records/RecordsTable';
import CreateRecordDialog from '@/components/records/CreateRecordDialog';
import ViewRecordDialog from '@/components/records/ViewRecordDialog';
import EditRecordDialog from '@/components/records/EditRecordDialog';
import DeleteRecordDialog from '@/components/records/DeleteRecordDialog';
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
    type RecordData,
    type RecordListItem,
} from '@/services/records.service';
import { handleApiError } from '@/lib/api';
import { useAuthStore } from '@/stores/auth.store';

export default function RecordsPage() {
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

    // Reference records state
    const [referenceRecords, setReferenceRecords] = useState<Record<string, RecordData[]>>({});

    // Dialog state
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [viewDialogOpen, setViewDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedRecord, setSelectedRecord] = useState<RecordListItem | null>(null);
    const [selectedRecordFull, setSelectedRecordFull] = useState<RecordData | null>(null);

    // Check if user has PII access (admin or superadmin role)
    const hasPiiAccess = user?.role === 'admin' || user?.role === 'superadmin';

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
        setLoading(true);
        setError(null);

        try {
            const response = await getRecords({
                collection: collectionName,
                skip: (page - 1) * pageSize,
                limit: pageSize,
                sort: `${sortOrder === 'asc' ? '' : '-'}${sortBy}`,
                fields: '*',
            });
            setData(response.items);
            setTotal(response.total);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    }, [collectionName, page, pageSize, sortBy, sortOrder]);

    useEffect(() => {
        fetchCollection();
    }, [fetchCollection]);

    useEffect(() => {
        if (collection) {
            fetchRecords();
        }
    }, [collection, fetchRecords]);

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

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-2 mb-2">
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
                    <h1 className="text-3xl font-bold">{collectionName || 'Records'}</h1>
                    <p className="text-muted-foreground mt-2">
                        Manage records in the <strong>{collectionName}</strong> collection
                    </p>
                </div>
                {collection && collection.schema && collection.schema.length > 0 && (
                    <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
                        <Plus className="h-4 w-4" />
                        Create Record
                    </Button>
                )}
            </div>

            {/* Search and Actions */}
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
                <CardContent className="space-y-4">
                    {/* Search Bar */}
                    <form onSubmit={handleSearch} className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
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
                                onClick={() => {
                                    setSearch('');
                                    setSearchInput('');
                                    setPage(1);
                                }}
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

                    {/* Collection not found */}
                    {error && !collection && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load collection</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && !data && (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    )}

                    {/* Collection loaded but no schema */}
                    {collection && (!collection.schema || collection.schema.length === 0) && (
                        <div className="text-center py-12">
                            <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                            <h3 className="text-lg font-medium mb-2">No schema defined</h3>
                            <p className="text-muted-foreground mb-4">
                                This collection has no fields defined yet. Add fields to the schema to start creating records.
                            </p>
                        </div>
                    )}

                    {/* Table */}
                    {!loading && data && data.length > 0 && collection && collection.schema && collection.schema.length > 0 && (
                        <RecordsTable
                            records={data}
                            schema={collection.schema}
                            sortBy={sortBy}
                            sortOrder={sortOrder}
                            onSort={handleSort}
                            onView={handleView}
                            onEdit={handleEdit}
                            onDelete={handleDelete}
                            hasPiiAccess={hasPiiAccess}
                            totalItems={total}
                            page={page}
                            pageSize={pageSize}
                            onPageChange={setPage}
                            onPageSizeChange={(size) => {
                                setPageSize(size);
                                setPage(1);
                            }}
                        />
                    )}

                    {/* Empty State */}
                    {!loading && data && data.length === 0 && !search && collection && collection.schema && collection.schema.length > 0 && (
                        <div className="text-center py-12">
                            <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                            <h3 className="text-lg font-medium mb-2">No records yet</h3>
                            <p className="text-muted-foreground mb-4">
                                Get started by creating your first record in this collection
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="h-4 w-4 mr-2" />
                                Create Record
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

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
                </>
            )}
        </div>
    );
}
