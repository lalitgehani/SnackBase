/**
 * Schema tab — temporary read-only field list + edit dialog trigger.
 */

import { Pencil, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useCollectionDetail } from '../CollectionDetailContext';
import { useCollectionsWorkspace } from '../CollectionsWorkspaceContext';

export default function SchemaTabPage() {
  const { collection, loading, error, openEditSchema, refreshDetail } =
    useCollectionDetail();
  const { isSuperadmin } = useCollectionsWorkspace();

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
    <div className="space-y-6" data-testid="schema-tab">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Schema</h2>
          <p className="text-sm text-muted-foreground">
            {collection.schema.length} user-defined field
            {collection.schema.length !== 1 ? 's' : ''}
          </p>
        </div>
        {isSuperadmin && (
          <Button size="sm" className="gap-1.5" onClick={openEditSchema}>
            <Pencil className="h-3.5 w-3.5" />
            Edit schema
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">ID:</span>
          <span className="ml-2 font-mono text-xs">{collection.id}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Table:</span>
          <span className="ml-2 font-mono text-xs">{collection.table_name}</span>
        </div>
      </div>

      <div className="space-y-3">
        {collection.schema.map((field, index) => (
          <div key={`${field.name}-${index}`} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{field.name}</span>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="secondary">{field.type}</Badge>
                {field.required && <Badge>Required</Badge>}
                {field.unique && <Badge>Unique</Badge>}
                {field.pii && <Badge variant="destructive">PII</Badge>}
              </div>
            </div>
            {field.default !== null && field.default !== undefined && (
              <div className="text-sm text-muted-foreground">
                Default: <span className="font-mono">{String(field.default)}</span>
              </div>
            )}
            {field.type === 'reference' && field.collection && (
              <div className="text-sm text-muted-foreground">
                References: <span className="font-mono">{field.collection}</span>
                {field.on_delete && ` (on delete: ${field.on_delete})`}
              </div>
            )}
            {field.type === 'computed' && field.expression && (
              <div className="text-sm text-muted-foreground">
                Expression: <span className="font-mono">{field.expression}</span>
                {field.return_type && ` → ${field.return_type}`}
              </div>
            )}
            {field.pii && field.mask_type && (
              <div className="text-sm text-muted-foreground">
                Mask type: {field.mask_type}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="bg-muted/50 rounded-lg p-4">
        <h4 className="font-medium mb-2 text-sm">System Fields (Auto-added)</h4>
        <div className="text-sm text-muted-foreground space-y-1">
          <div>• id (TEXT PRIMARY KEY)</div>
          <div>• account_id (TEXT NOT NULL)</div>
          <div>• created_at (DATETIME)</div>
          <div>• created_by (TEXT)</div>
          <div>• updated_at (DATETIME)</div>
          <div>• updated_by (TEXT)</div>
        </div>
      </div>
    </div>
  );
}
