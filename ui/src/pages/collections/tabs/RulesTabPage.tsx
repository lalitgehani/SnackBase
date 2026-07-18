/**
 * Rules tab — embeds CollectionRulesTab.
 */

import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import CollectionRulesTab from '@/components/collections/CollectionRulesTab';
import { useCollectionDetail } from '../CollectionDetailContext';

export default function RulesTabPage() {
  const { collection, loading, error, refreshDetail } = useCollectionDetail();

  if (loading && !collection) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-destructive">{error ?? 'Collection not found'}</p>
        <Button size="sm" variant="outline" onClick={() => void refreshDetail()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div data-testid="rules-tab">
      <CollectionRulesTab collection={collection} />
    </div>
  );
}
