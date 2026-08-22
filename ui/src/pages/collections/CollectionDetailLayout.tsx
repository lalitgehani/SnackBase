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
import DeleteCollectionDialog from '@/components/collections/DeleteCollectionDialog';
import {
  deleteCollection,
  getCollectionByName,
  type Collection,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/errors';
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
  } = useCollectionsWorkspace();

  const listItem = getListItem(collectionName);

  const [collection, setCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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
    }),
    [collection, listItem, collectionName, loading, error, refreshDetail],
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
      <div className="space-y-3 p-8 text-center" data-testid="collection-detail-error">
        <p className="font-medium text-destructive">Failed to load collection</p>
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
        <header className="shrink-0 border-b bg-background px-6 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-2xl font-bold">{collectionName}</h1>
                {(listItem?.has_public_access || false) && (
                  <Badge
                    variant="outline"
                    className="border-green-500 text-green-600 dark:text-green-400 dark:border-green-700"
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

          <nav
            className="-mb-px mt-4 flex gap-1 border-b"
            aria-label="Collection tabs"
          >
            {TABS.map(({ segment, label, icon: Icon }) => (
              <NavLink
                key={segment}
                to={`/admin/collections/${collectionName}/${segment}`}
                className={({ isActive }) =>
                  cn(
                    'inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium -mb-px transition-colors',
                    isActive
                      ? 'border-primary text-foreground'
                      : 'border-transparent text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground',
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
