/**
 * Redirect /admin/collections/:name to default tab:
 * Data if records_count > 0, else Schema.
 */

import { Navigate, useParams } from 'react-router';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useCollectionsWorkspace } from './CollectionsWorkspaceContext';
import { resolveDefaultTab } from './defaultTab';

export default function CollectionDefaultTabRedirect() {
  const { collectionName } = useParams<{ collectionName: string }>();
  const { getListItem, loading, collections, error, refreshCollections } =
    useCollectionsWorkspace();

  const listItem = collectionName ? getListItem(collectionName) : undefined;

  if (loading && collections.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && collections.length === 0) {
    return (
      <div className="p-8 text-center space-y-2">
        <p className="text-destructive">{error}</p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void refreshCollections()}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (!collectionName) {
    return <Navigate to="/admin/collections" replace />;
  }

  // Wait for list to resolve default tab when item not yet present
  if (loading && !listItem) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!listItem) {
    return (
      <div className="p-8 text-center space-y-2" data-testid="collection-not-found">
        <p className="font-medium">Collection not found</p>
        <p className="text-sm text-muted-foreground">
          “{collectionName}” does not exist or you do not have access.
        </p>
      </div>
    );
  }

  const tab = resolveDefaultTab(listItem.records_count);
  return (
    <Navigate to={`/admin/collections/${collectionName}/${tab}`} replace />
  );
}
