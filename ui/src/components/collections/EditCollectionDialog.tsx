/**
 * Edit collection dialog component
 * Allows adding new fields to existing collections
 */

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Database, Shield, CheckCircle2, Loader2 } from 'lucide-react';
import SchemaBuilder from './SchemaBuilder';
import CollectionRulesTab from './CollectionRulesTab';
import type { Collection, UpdateCollectionData, FieldDefinition } from '@/services/collections.service';
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
    const [originalFieldCount, setOriginalFieldCount] = useState(0);
    const [isSuccess, setIsSuccess] = useState(false);

    useEffect(() => {
        if (open && collection) {
            // Initialize with existing schema
            setFields([...collection.schema]);
            setOriginalFieldCount(collection.schema.length);
            setError(null);
            setIsSuccess(false);
        } else if (!open) {
            setFields([]);
            setOriginalFieldCount(0);
            setError(null);
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

        // Validation
        if (fields.length === 0) {
            setError('At least one field is required');
            return;
        }

        // Validate all fields have names and types
        const fieldNames = new Set<string>();
        for (const field of fields) {
            if (!field.name.trim()) {
                setError('All fields must have a name');
                return;
            }

            // Check for duplicate field names (case-insensitive)
            const normalizedName = field.name.toLowerCase();
            if (fieldNames.has(normalizedName)) {
                setError(`Duplicate field name: "${field.name}"`);
                return;
            }
            fieldNames.add(normalizedName);

            if (!field.type) {
                setError('All fields must have a type');
                return;
            }
            if (field.type === 'reference' && !field.collection) {
                setError(`Field "${field.name}" is a reference but has no target collection`);
                return;
            }
            if (field.pii && !field.mask_type) {
                setError(`Field "${field.name}" is marked as PII but has no mask type`);
                return;
            }
        }

        setIsSubmitting(true);
        try {
            await onSubmit(collection.id, { schema: fields });
            setIsSuccess(true);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!collection) return null;

    return (
        <Dialog open={open} onOpenChange={isSubmitting ? undefined : onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {isSuccess ? 'Collection Updated' : `Edit Collection: ${collection.name}`}
                    </DialogTitle>
                    <DialogDescription>
                        {isSuccess
                            ? 'Your collection has been updated successfully with all migrations applied.'
                            : 'Add new fields or modify existing field properties. Type changes are not allowed for data safety.'}
                    </DialogDescription>
                </DialogHeader>

                {isSubmitting && (
                    <div className="flex flex-col items-center justify-center py-12 space-y-4">
                        <Loader2 className="h-12 w-12 animate-spin text-primary" />
                        <div className="text-center">
                            <p className="font-medium">Updating schema and applying migrations...</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                Please wait while the database changes are being applied.
                            </p>
                        </div>
                    </div>
                )}

                {isSuccess && !isSubmitting && (
                    <div className="flex flex-col items-center justify-center py-8 space-y-4">
                        <div className="rounded-full bg-green-100 dark:bg-green-900/30 p-4">
                            <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
                        </div>
                        <div className="text-center space-y-2">
                            <p className="font-medium text-lg">
                                Collection "{collection.name}" updated successfully!
                            </p>
                            <p className="text-sm text-muted-foreground">
                                The schema changes have been applied and all migrations are complete.
                            </p>
                        </div>
                        <DialogFooter className="mt-4">
                            <Button onClick={handleClose}>Done</Button>
                        </DialogFooter>
                    </div>
                )}

                {!isSuccess && !isSubmitting && (
                    <Tabs defaultValue="schema" className="w-full">
                        <TabsList className="grid w-full grid-cols-2 mb-6">
                            <TabsTrigger value="schema" className="gap-2">
                                <Database className="h-4 w-4" />
                                Schema
                            </TabsTrigger>
                            <TabsTrigger value="rules" className="gap-2">
                                <Shield className="h-4 w-4" />
                                Rules
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="schema">
                            <form onSubmit={handleSubmit} className="space-y-6">
                                <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 rounded-lg p-4">
                                    <p className="text-sm text-blue-900 dark:text-blue-200">
                                        <strong>ℹ️ Note:</strong> You can add new fields and modify properties of existing fields.
                                        However, changing field types or deleting fields is not allowed to protect existing data.
                                    </p>
                                </div>

                                <SchemaBuilder
                                    fields={fields}
                                    onChange={setFields}
                                    originalFieldCount={originalFieldCount}
                                    collections={collections}
                                />

                                {error && (
                                    <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                                        <p className="text-destructive text-sm">{error}</p>
                                    </div>
                                )}

                                <DialogFooter>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={() => onOpenChange(false)}
                                        disabled={isSubmitting}
                                    >
                                        Cancel
                                    </Button>
                                    <Button type="submit" disabled={isSubmitting}>
                                        {isSubmitting ? 'Updating...' : 'Update Schema'}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </TabsContent>

                        <TabsContent value="rules">
                            <CollectionRulesTab collection={collection} />
                        </TabsContent>
                    </Tabs>
                )}
            </DialogContent>
        </Dialog>
    );
}

