/**
 * Collections management page
 * Full implementation with CRUD operations, search, and pagination
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Database, Plus, Search, RefreshCw, Download, Upload } from 'lucide-react';
import CollectionsTable from '@/components/collections/CollectionsTable';
import CreateCollectionDialog from '@/components/collections/CreateCollectionDialog';
import ViewCollectionDialog from '@/components/collections/ViewCollectionDialog';
import EditCollectionDialog from '@/components/collections/EditCollectionDialog';
import DeleteCollectionDialog from '@/components/collections/DeleteCollectionDialog';
import ImportCollectionsDialog from '@/components/collections/ImportCollectionsDialog';
import {
    getCollections,
    getCollectionById,
    createCollection,
    updateCollection,
    deleteCollection,
    type Collection,
    type CollectionListItem,
    type CollectionListResponse,
    type CreateCollectionData,
    type UpdateCollectionData,
    exportCollections,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export default function CollectionsPage() {
    const navigate = useNavigate();
    const { toast } = useToast();

    const [data, setData] = useState<CollectionListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Pagination and filtering state
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [sortBy, setSortBy] = useState('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [search, setSearch] = useState('');
    const [searchInput, setSearchInput] = useState('');

    // Dialog state
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [viewDialogOpen, setViewDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedCollection, setSelectedCollection] = useState<CollectionListItem | null>(null);
    const [selectedCollectionFull, setSelectedCollectionFull] = useState<Collection | null>(null);
    const [importDialogOpen, setImportDialogOpen] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    const fetchCollections = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await getCollections({
                page,
                page_size: pageSize,
                sort_by: sortBy,
                sort_order: sortOrder,
                search: search || undefined,
            });
            setData(response);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    }, [page, pageSize, sortBy, sortOrder, search]);

    useEffect(() => {
        fetchCollections();
    }, [fetchCollections]);

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

    const handleCreateCollection = async (data: CreateCollectionData) => {
        await createCollection(data);
        await fetchCollections();
    };

    const handleView = async (collection: CollectionListItem) => {
        try {
            const fullCollection = await getCollectionById(collection.id);
            setSelectedCollectionFull(fullCollection);
            setViewDialogOpen(true);
        } catch (err) {
            setError(handleApiError(err));
        }
    };

    const handleEdit = async (collection: CollectionListItem) => {
        try {
            const fullCollection = await getCollectionById(collection.id);
            setSelectedCollectionFull(fullCollection);
            setEditDialogOpen(true);
        } catch (err) {
            setError(handleApiError(err));
        }
    };

    const handleUpdateCollection = async (collectionId: string, data: UpdateCollectionData) => {
        await updateCollection(collectionId, data);
        await fetchCollections();
    };

    const handleDelete = (collection: CollectionListItem) => {
        setSelectedCollection(collection);
        setDeleteDialogOpen(true);
    };

    const handleDeleteCollection = async (collectionId: string) => {
        await deleteCollection(collectionId);
        await fetchCollections();
    };

    const handleManageRecords = (collection: CollectionListItem) => {
        navigate(`/admin/collections/${collection.name}/records`);
    };

    const handleExport = async () => {
        setIsExporting(true);
        try {
            await exportCollections();
            toast({
                title: 'Export successful',
                description: 'Collections exported to JSON file',
            });
        } catch (err) {
            toast({
                variant: 'destructive',
                title: 'Export failed',
                description: handleApiError(err),
            });
        } finally {
            setIsExporting(false);
        }
    };

    // Get list of collection names for reference field selector
    const collectionNames = data?.items.map(c => c.name) || [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Collections</h1>
                    <p className="text-muted-foreground mt-2">Manage data collections and schemas</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={handleExport} disabled={isExporting} className="gap-2">
                        <Download className="h-4 w-4" />
                        {isExporting ? 'Exporting...' : 'Export'}
                    </Button>
                    <Button variant="outline" onClick={() => setImportDialogOpen(true)} className="gap-2">
                        <Upload className="h-4 w-4" />
                        Import
                    </Button>
                    <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
                        <Plus className="h-4 w-4" />
                        Create Collection
                    </Button>
                </div>
            </div>

            {/* Search and Actions */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5 text-primary" />
                        Collection Management
                    </CardTitle>
                    <CardDescription>
                        View, create, edit, and delete collections
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
                                placeholder="Search by name or ID..."
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
                            onClick={fetchCollections}
                            disabled={loading}
                        >
                            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                    </form>

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load collections</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchCollections} className="mt-4" size="sm">
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
                    {!loading && data && data.items.length > 0 && (
                        <CollectionsTable
                            collections={data.items}
                            sortBy={sortBy}
                            sortOrder={sortOrder}
                            onSort={handleSort}
                            onView={handleView}
                            onEdit={handleEdit}
                            onDelete={handleDelete}
                            onManageRecords={handleManageRecords}
                            totalItems={data.total}
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
                    {!loading && data && data.items.length === 0 && !search && (
                        <div className="text-center py-12">
                            <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                            <h3 className="text-lg font-medium mb-2">No collections yet</h3>
                            <p className="text-muted-foreground mb-4">
                                Get started by creating your first collection
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="h-4 w-4 mr-2" />
                                Create Collection
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Dialogs */}
            <CreateCollectionDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onSubmit={handleCreateCollection}
                collections={collectionNames}
            />

            <ViewCollectionDialog
                open={viewDialogOpen}
                onOpenChange={setViewDialogOpen}
                collection={selectedCollectionFull}
            />

            <EditCollectionDialog
                open={editDialogOpen}
                onOpenChange={setEditDialogOpen}
                collection={selectedCollectionFull}
                onSubmit={handleUpdateCollection}
                collections={collectionNames}
            />

            <DeleteCollectionDialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
                collection={selectedCollection}
                onConfirm={handleDeleteCollection}
            />

            <ImportCollectionsDialog
                open={importDialogOpen}
                onOpenChange={setImportDialogOpen}
                onSuccess={fetchCollections}
            />
        </div>
    );
}
