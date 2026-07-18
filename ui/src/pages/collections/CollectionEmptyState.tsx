/**
 * Empty / unselected main pane for the Collections workspace.
 */

import { Database, Plus, Upload } from 'lucide-react';
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCollectionsWorkspace } from './CollectionsWorkspaceContext';

export default function CollectionEmptyState() {
  const { collections, loading, isSuperadmin, setImportDialogOpen } =
    useCollectionsWorkspace();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-muted-foreground text-sm">
        Loading collections…
      </div>
    );
  }

  const zeroCollections = collections.length === 0;

  return (
    <div
      className="flex flex-1 flex-col items-center justify-center p-8 text-center"
      data-testid="collection-empty-state"
    >
      <div className="mx-auto max-w-md space-y-4">
        <Database className="mx-auto h-14 w-14 text-muted-foreground opacity-40" />

        {zeroCollections ? (
          <>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">No collections yet</h2>
              <Badge variant="secondary" className="font-normal">
                Global · multi-tenant
              </Badge>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Collections are global tables shared by all accounts. Each account&apos;s
                rows are isolated by <code className="text-xs bg-muted px-1 rounded">account_id</code>
                — not separate Postgres schemas.
              </p>
            </div>
            {isSuperadmin && (
              <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                <Button
                  className="gap-1.5"
                  onClick={() => navigate('/admin/collections/new')}
                >
                  <Plus className="h-4 w-4" />
                  Create collection
                </Button>
                <Button
                  variant="outline"
                  className="gap-1.5"
                  onClick={() => setImportDialogOpen(true)}
                >
                  <Upload className="h-4 w-4" />
                  Import from JSON
                </Button>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Select a collection</h2>
              <p className="text-sm text-muted-foreground">
                Choose a collection from the browser on the left to manage its schema,
                data, rules, and analytics.
              </p>
            </div>
            {isSuperadmin && (
              <Button
                className="gap-1.5"
                onClick={() => navigate('/admin/collections/new')}
              >
                <Plus className="h-4 w-4" />
                Create collection
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
