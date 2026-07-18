/**
 * Create collection dialog (legacy/compat).
 * Primary create UX is the full-page flow at /admin/collections/new.
 */

import { useState, useEffect } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { CheckCircle2, Loader2 } from 'lucide-react';
import SchemaColumnTable from './SchemaColumnTable';
import SystemFieldsPanel from './SystemFieldsPanel';
import {
  prepareSchemaPayload,
  validateSchemaFields,
  type SchemaFieldErrors,
} from './schemaValidation';
import type { CreateCollectionData, FieldDefinition } from '@/services/collections.service';
import { handleApiError } from '@/lib/api';

interface CreateCollectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateCollectionData) => Promise<void>;
  collections?: string[];
}

export default function CreateCollectionDialog({
  open,
  onOpenChange,
  onSubmit,
  collections = [],
}: CreateCollectionDialogProps) {
  const [name, setName] = useState('');
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<SchemaFieldErrors>({});
  const [isSuccess, setIsSuccess] = useState(false);
  const [createdCollectionName, setCreatedCollectionName] = useState('');

  useEffect(() => {
    if (!open) {
      setName('');
      setFields([]);
      setError(null);
      setFieldErrors({});
      setIsSuccess(false);
      setCreatedCollectionName('');
    }
  }, [open]);

  const handleClose = () => {
    onOpenChange(false);
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
      await onSubmit({ name: name.trim(), schema: prepareSchemaPayload(fields) });
      setCreatedCollectionName(name.trim());
      setIsSuccess(true);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const title = isSuccess ? 'Collection Created' : 'Create Collection';
  const description = isSuccess
    ? 'Your collection has been created successfully with all migrations applied.'
    : 'Create a new collection with custom schema. This will create a global database table.';

  const footer = isSuccess ? (
    <Button onClick={handleClose}>Done</Button>
  ) : !isSubmitting ? (
    <>
      <Button
        type="button"
        variant="outline"
        onClick={() => onOpenChange(false)}
        disabled={isSubmitting}
      >
        Cancel
      </Button>
      <Button type="submit" form="create-collection-form" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create Collection'}
      </Button>
    </>
  ) : undefined;

  return (
    <AppDialog
      open={open}
      onOpenChange={isSubmitting ? undefined : onOpenChange}
      title={title}
      description={description}
      className="max-w-4xl"
      footer={footer}
    >
      {isSubmitting && (
        <div className="flex flex-col items-center justify-center space-y-4 py-12">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-medium">Creating collection and applying migrations...</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Please wait while the database table is being created.
            </p>
          </div>
        </div>
      )}

      {isSuccess && !isSubmitting && (
        <div className="flex flex-col items-center justify-center space-y-4 py-8">
          <div className="rounded-full bg-green-100 p-4 dark:bg-green-900/30">
            <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
          </div>
          <div className="space-y-2 text-center">
            <p className="text-lg font-medium">
              Collection &quot;{createdCollectionName}&quot; created successfully!
            </p>
            <p className="text-sm text-muted-foreground">
              The database table has been created and all migrations have been applied.
            </p>
          </div>
        </div>
      )}

      {!isSuccess && !isSubmitting && (
        <form id="create-collection-form" onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="collection-name">Collection Name *</Label>
            <Input
              id="collection-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="customers"
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              3-64 characters, alphanumeric and underscores only
            </p>
          </div>

          <SystemFieldsPanel compact />

          <SchemaColumnTable
            fields={fields}
            onChange={setFields}
            collections={collections}
            fieldErrors={fieldErrors}
          />

          {error && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </form>
      )}
    </AppDialog>
  );
}
