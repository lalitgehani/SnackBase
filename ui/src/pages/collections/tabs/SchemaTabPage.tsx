/**
 * Schema tab — inline column editor with dirty-state save (Phase 2).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Database, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ToastAction } from '@/components/ui/toast';
import SchemaColumnTable from '@/components/collections/SchemaColumnTable';
import SystemFieldsPanel from '@/components/collections/SystemFieldsPanel';
import {
  normalizeSchemaForCompare,
  prepareSchemaPayload,
  validateSchemaFields,
  type SchemaFieldErrors,
} from '@/components/collections/schemaValidation';
import {
  updateCollection,
  type FieldDefinition,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/errors';
import { useToast } from '@/hooks/use-toast';
import { useCollectionDetail } from '../CollectionDetailContext';
import { useCollectionsWorkspace } from '../CollectionsWorkspaceContext';

export default function SchemaTabPage() {
  const {
    collection,
    collectionName,
    loading,
    error: loadError,
    refreshDetail,
  } = useCollectionDetail();
  const { isSuperadmin, collectionNames, refreshCollections } =
    useCollectionsWorkspace();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [baseline, setBaseline] = useState<FieldDefinition[]>([]);
  const [draftFields, setDraftFields] = useState<FieldDefinition[]>([]);
  const [originalFieldCount, setOriginalFieldCount] = useState(0);
  const [fieldErrors, setFieldErrors] = useState<SchemaFieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const syncFromCollection = useCallback(() => {
    if (!collection) return;
    const schema = collection.schema.map((f) => ({ ...f }));
    setBaseline(schema);
    setDraftFields(schema.map((f) => ({ ...f })));
    setOriginalFieldCount(schema.length);
    setFieldErrors({});
    setError(null);
  }, [collection]);

  useEffect(() => {
    syncFromCollection();
  }, [syncFromCollection]);

  const isDirty = useMemo(() => {
    return (
      normalizeSchemaForCompare(draftFields) !==
      normalizeSchemaForCompare(baseline)
    );
  }, [draftFields, baseline]);

  const handleDiscard = () => {
    setDraftFields(baseline.map((f) => ({ ...f })));
    setFieldErrors({});
    setError(null);
  };

  const handleSave = async () => {
    if (!collection || !isDirty) return;

    const result = validateSchemaFields(draftFields);
    if (!result.valid) {
      setFieldErrors(result.fieldErrors);
      setError(result.formError ?? 'Schema validation failed');
      return;
    }

    setIsSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      await updateCollection(collection.id, {
        schema: prepareSchemaPayload(draftFields),
      });
      await Promise.all([refreshDetail(), refreshCollections()]);
      const dataPath = `/admin/collections/${collectionName || collection.name}/data`;
      toast({
        title: 'Schema updated',
        description: 'Migrations applied successfully.',
        action: (
          <ToastAction
            altText="View data"
            onClick={() => navigate(dataPath)}
          >
            View data
          </ToastAction>
        ),
      });
      // baseline will re-sync from refreshed collection via useEffect
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsSaving(false);
    }
  };

  if (loading && !collection) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError || !collection) {
    return (
      <div className="space-y-2 py-8 text-center">
        <p className="text-destructive">{loadError ?? 'Collection not found'}</p>
        <Button size="sm" variant="outline" onClick={() => void refreshDetail()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div
      className="relative space-y-6 pb-20"
      data-testid="schema-tab"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Schema</h2>
          <p className="text-sm text-muted-foreground">
            {draftFields.length} user-defined field
            {draftFields.length !== 1 ? 's' : ''}
            {isSuperadmin && isDirty ? ' · unsaved changes' : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-start gap-4">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
            <div>
              <span className="text-muted-foreground">ID:</span>
              <span className="ml-2 font-mono text-xs">{collection.id}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Table:</span>
              <span className="ml-2 font-mono text-xs">{collection.table_name}</span>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() =>
              navigate(
                `/admin/collections/${collectionName || collection.name}/data`,
              )
            }
            data-testid="schema-view-data"
          >
            <Database className="h-3.5 w-3.5" />
            View data
          </Button>
        </div>
      </div>

      {isSaving && (
        <div className="flex flex-col items-center justify-center space-y-3 rounded-lg border py-12">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-medium">Updating schema and applying migrations…</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Please wait while the database changes are applied.
            </p>
          </div>
        </div>
      )}

      {!isSaving && (
        <>
          <SystemFieldsPanel compact />

          <SchemaColumnTable
            fields={draftFields}
            onChange={setDraftFields}
            originalFieldCount={originalFieldCount}
            collections={collectionNames}
            fieldErrors={fieldErrors}
            readOnly={!isSuperadmin}
            showAddButton={isSuperadmin}
          />

          {isSuperadmin && originalFieldCount > 0 && (
            <p className="text-xs text-muted-foreground">
              Existing fields cannot be renamed, retyped, or deleted. Add new
              columns and save to apply migrations.
            </p>
          )}

          {error && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </>
      )}

      {isSuperadmin && isDirty && !isSaving && (
        <div
          className="sticky bottom-0 z-10 -mx-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-background px-4 py-3 shadow-md"
          data-testid="schema-dirty-bar"
        >
          <p className="text-sm font-medium">Unsaved schema changes</p>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={handleDiscard}>
              Discard
            </Button>
            <Button type="button" size="sm" onClick={() => void handleSave()}>
              Save
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
