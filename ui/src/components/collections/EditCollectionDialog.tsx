/**
 * Edit collection dialog (legacy/compat).
 * Primary edit UX is the Schema tab dirty-save flow.
 */

import { useState, useEffect } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Database, Shield, CheckCircle2, Loader2 } from 'lucide-react';
import SchemaColumnTable from './SchemaColumnTable';
import CollectionRulesTab from './CollectionRulesTab';
import SystemFieldsPanel from './SystemFieldsPanel';
import {
  prepareSchemaPayload,
  validateSchemaFields,
  type SchemaFieldErrors,
} from './schemaValidation';
import type {
  Collection,
  UpdateCollectionData,
  FieldDefinition,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';

interface EditCollectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collection: Collection | null;
  onSubmit: (collectionId: string, data: UpdateCollectionData) => Promise<void>;
  collections?: string[];
}

export default function EditCollectionDialog({
  open,
  onOpenChange,
  collection,
  onSubmit,
  collections = [],
}: EditCollectionDialogProps) {
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<SchemaFieldErrors>({});
  const [originalFieldCount, setOriginalFieldCount] = useState(0);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    if (open && collection) {
      setFields(collection.schema.map((f) => ({ ...f })));
      setOriginalFieldCount(collection.schema.length);
      setError(null);
      setFieldErrors({});
      setIsSuccess(false);
    } else if (!open) {
      setFields([]);
      setOriginalFieldCount(0);
      setError(null);
      setFieldErrors({});
      setIsSuccess(false);
    }
  }, [open, collection]);

  const handleClose = () => {
    onOpenChange(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!collection) return;

    setError(null);
    setFieldErrors({});

    const result = validateSchemaFields(fields);
    if (!result.valid) {
      setFieldErrors(result.fieldErrors);
      setError(result.formError ?? 'Schema validation failed');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(collection.id, { schema: prepareSchemaPayload(fields) });
      setIsSuccess(true);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!collection) return null;

  const title = isSuccess
    ? 'Collection Updated'
    : `Edit Collection: ${collection.name}`;
  const description = isSuccess
    ? 'Your collection has been updated successfully with all migrations applied.'
    : 'Add new fields or modify existing field properties. Type changes are not allowed for data safety.';

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
      <Button type="submit" form="edit-collection-form" disabled={isSubmitting}>
        {isSubmitting ? 'Updating...' : 'Update Schema'}
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
            <p className="font-medium">Updating schema and applying migrations...</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Please wait while the database changes are being applied.
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
              Collection &quot;{collection.name}&quot; updated successfully!
            </p>
            <p className="text-sm text-muted-foreground">
              Schema changes have been applied with migrations.
            </p>
          </div>
        </div>
      )}

      {!isSuccess && !isSubmitting && (
        <form id="edit-collection-form" onSubmit={handleSubmit} className="space-y-4">
          <Tabs defaultValue="schema" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="schema" className="gap-2">
                <Database className="h-4 w-4" />
                Schema
              </TabsTrigger>
              <TabsTrigger value="rules" className="gap-2">
                <Shield className="h-4 w-4" />
                Rules
              </TabsTrigger>
            </TabsList>
            <TabsContent value="schema" className="mt-4 space-y-4">
              <SystemFieldsPanel compact />
              <SchemaColumnTable
                fields={fields}
                onChange={setFields}
                originalFieldCount={originalFieldCount}
                collections={collections}
                fieldErrors={fieldErrors}
              />
            </TabsContent>
            <TabsContent value="rules" className="mt-4">
              <CollectionRulesTab collection={collection} />
            </TabsContent>
          </Tabs>

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
