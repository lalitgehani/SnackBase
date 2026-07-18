/**
 * Collection detail shell: header summary, tab nav, and outlet.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useNavigate, useParams } from 'react-router';
import {
  BarChart2,
  Database,
  Pencil,
  RefreshCw,
  Shield,
  Table2,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import EditCollectionDialog from '@/components/collections/EditCollectionDialog';
import DeleteCollectionDialog from '@/components/collections/DeleteCollectionDialog';
import {
  deleteCollection,
  getCollectionByName,
  updateCollection,
  type Collection,
  type UpdateCollectionData,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useCollectionsWorkspace } from './CollectionsWorkspaceContext';
import {
  CollectionDetailProvider,
  type CollectionDetailContextValue,
} from './CollectionDetailContext';

const TABS = [
  { segment: 'schema', label: 'Schema', icon: Table2 },
  { segment: 'data', label: 'Data', icon: Database },
  { segment: 'rules', label: 'Rules', icon: Shield },
  { segment: 'analytics', label: 'Analytics', icon: BarChart2 },
] as const;

export default function CollectionDetailLayout() {
  const { collectionName = '' } = useParams<{ collectionName: string }>();
  const navigate = useNavigate();
  const {
    getListItem,
    refreshCollections,
    isSuperadmin,
    collectionNames,
  } = useCollectionsWorkspace();

  const listItem = getListItem(collectionName);

  const [collection, setCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const refreshDetail = useCallback(async () => {
    if (!collectionName) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getCollectionByName(collectionName);
      setCollection(data);
    } catch (err) {
      setError(handleApiError(err));
      setCollection(null);
    } finally {
      setLoading(false);
    }
  }, [collectionName]);

  useEffect(() => {
    void refreshDetail();
  }, [refreshDetail]);

  const openEditSchema = useCallback(() => {
    setEditOpen(true);
  }, []);

  const handleUpdate = async (collectionId: string, data: UpdateCollectionData) => {
    await updateCollection(collectionId, data);
    await Promise.all([refreshDetail(), refreshCollections()]);
  };

  const handleDelete = async (collectionId: string) => {
    await deleteCollection(collectionId);
    await refreshCollections();
    navigate('/admin/collections', { replace: true });
  };

  const detailValue = useMemo<CollectionDetailContextValue>(
    () => ({
      collection,
      listItem,
      collectionName,
      loading,
      error,
      refreshDetail,
      openEditSchema,
    }),
    [
      collection,
      listItem,
      collectionName,
      loading,
      error,
      refreshDetail,
      openEditSchema,
    ],
  );

  if (loading && !collection) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !collection) {
    return (
      <div className="p-8 text-center space-y-3" data-testid="collection-detail-error">
        <p className="text-destructive font-medium">Failed to load collection</p>
        <p className="text-sm text-muted-foreground">{error}</p>
        <Button size="sm" variant="outline" onClick={() => void refreshDetail()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <CollectionDetailProvider value={detailValue}>
      <div className="flex h-full min-h-0 flex-col" data-testid="collection-detail-layout">
        {/* Header */}
        <header className="shrink-0 border-b bg-background px-6 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold truncate">{collectionName}</h1>
                {(listItem?.has_public_access || false) && (
                  <Badge
                    variant="outline"
                    className="border-green-500 text-green-600"
                  >
                    Public
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {listItem?.fields_count ?? collection?.schema.length ?? 0} fields
                {' · '}
                {listItem?.records_count ?? 0} records
              </p>
            </div>
            {isSuperadmin && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => {
                    navigate(`/admin/collections/${collectionName}/schema`);
                    openEditSchema();
                  }}
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit schema
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-destructive hover:text-destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </Button>
              </div>
            )}
          </div>

          {/* Tabs */}
          <nav
            className="mt-4 flex gap-1 border-b -mb-px"
            aria-label="Collection tabs"
          >
            {TABS.map(({ segment, label, icon: Icon }) => (
              <NavLink
                key={segment}
                to={`/admin/collections/${collectionName}/${segment}`}
                className={({ isActive }) =>
                  cn(
                    'inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                    isActive
                      ? 'border-primary text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/40',
                  )
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </NavLink>
            ))}
          </nav>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          <Outlet />
        </div>
      </div>

      <EditCollectionDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        collection={collection}
        onSubmit={handleUpdate}
        collections={collectionNames}
      />

      <DeleteCollectionDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        collection={
          listItem ??
          (collection
            ? {
                id: collection.id,
                name: collection.name,
                table_name: collection.table_name,
                fields_count: collection.schema.length,
                records_count: 0,
                has_public_access: false,
                created_at: collection.created_at,
              }
            : null)
        }
        onConfirm={handleDelete}
      />
    </CollectionDetailProvider>
  );
}
