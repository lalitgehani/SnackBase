/**
 * Rules tab — first-class access rules editor (Phase 3).
 */

import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import CollectionRulesTab from '@/components/collections/CollectionRulesTab';
import { useCollectionDetail } from '../CollectionDetailContext';
import { useCollectionsWorkspace } from '../CollectionsWorkspaceContext';

export default function RulesTabPage() {
  const { collection, listItem, loading, error, refreshDetail } =
    useCollectionDetail();
  const { isSuperadmin, refreshCollections } = useCollectionsWorkspace();

  if (loading && !collection) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="space-y-2 py-8 text-center">
        <p className="text-destructive">{error ?? 'Collection not found'}</p>
        <Button size="sm" variant="outline" onClick={() => void refreshDetail()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div data-testid="rules-tab">
      <CollectionRulesTab
        collection={collection}
        readOnly={!isSuperadmin}
        hasPublicAccess={listItem?.has_public_access ?? false}
        onRulesSaved={() => {
          void refreshCollections();
        }}
      />
    </div>
  );
}
