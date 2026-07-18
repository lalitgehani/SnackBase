/**
 * /admin/collections/new — full-page create collection flow (Phase 2).
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import SchemaColumnTable from '@/components/collections/SchemaColumnTable';
import SystemFieldsPanel from '@/components/collections/SystemFieldsPanel';
import {
  prepareSchemaPayload,
  validateSchemaFields,
  type SchemaFieldErrors,
} from '@/components/collections/schemaValidation';
import {
  createCollection,
  type FieldDefinition,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { useCollectionsWorkspace } from './CollectionsWorkspaceContext';

export default function CollectionNewPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { collectionNames, refreshCollections, isSuperadmin } =
    useCollectionsWorkspace();

  const [name, setName] = useState('');
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<SchemaFieldErrors>({});

  useEffect(() => {
    if (!isSuperadmin) {
      navigate('/admin/collections', { replace: true });
    }
  }, [isSuperadmin, navigate]);

  if (!isSuperadmin) {
    return null;
  }

  const handleCancel = () => {
    navigate('/admin/collections');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    if (!name.trim()) {
      setError('Collection name is required');
      return;
    }

    const result = validateSchemaFields(fields);
    if (!result.valid) {
      setFieldErrors(result.fieldErrors);
      setError(result.formError ?? 'Schema validation failed');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await createCollection({
        name: name.trim(),
        schema: prepareSchemaPayload(fields),
      });
      await refreshCollections();
      toast({
        title: 'Collection created',
        description: `"${created.name}" is ready. Configure access rules on the Rules tab or start adding data.`,
      });
      navigate(`/admin/collections/${created.name}/schema`, { replace: true });
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="mx-auto flex max-w-5xl flex-col gap-6 p-6 pb-28"
      data-testid="collection-new-page"
    >
      <div>
        <h1 className="text-2xl font-bold">Create collection</h1>
        <p className="text-sm text-muted-foreground">
          Define a global multi-tenant table with custom columns. System fields
          are added automatically.
        </p>
      </div>

      {isSubmitting ? (
        <div className="flex flex-col items-center justify-center space-y-4 py-16">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-medium">
              Creating collection and applying migrations…
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Please wait while the database table is being created.
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6" id="create-collection-form">
          <div className="space-y-2">
            <Label htmlFor="collection-name">Collection name *</Label>
            <Input
              id="collection-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="customers"
              disabled={isSubmitting}
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              3–64 characters, alphanumeric and underscores only
            </p>
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/20">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              <strong>Access model:</strong> Every collection is a global table
              isolated by <code className="font-mono text-xs">account_id</code>.
              Row-level access is enforced by collection rules (list / view /
              create / update / delete), not a Postgres RLS toggle. Configure
              rules on the Rules tab after create.
            </p>
          </div>

          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-300" />
            <p className="text-sm text-amber-900 dark:text-amber-200">
              This creates a global database table shared across accounts (data
              isolated by <code className="font-mono text-xs">account_id</code>).
              Migrations run immediately on create.
            </p>
          </div>

          <SystemFieldsPanel />

          <SchemaColumnTable
            fields={fields}
            onChange={setFields}
            collections={collectionNames}
            fieldErrors={fieldErrors}
          />

          {error && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </form>
      )}

      {!isSubmitting && (
        <div className="fixed bottom-0 left-0 right-0 z-10 border-t bg-background/95 px-6 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:left-[var(--sidebar-width,0px)]">
          <div className="mx-auto flex max-w-5xl justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="create-collection-form"
              disabled={isSubmitting}
            >
              Create collection
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
