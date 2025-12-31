/**
 * Create collection dialog component
 * Form with schema builder for creating new collections
 */

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import SchemaBuilder from './SchemaBuilder';
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

    useEffect(() => {
        if (!open) {
            // Reset form when dialog closes
            setName('');
            setFields([]);
            setError(null);
        }
    }, [open]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validation
        if (!name.trim()) {
            setError('Collection name is required');
            return;
        }

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
            await onSubmit({ name, schema: fields });
            onOpenChange(false);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Create Collection</DialogTitle>
                    <DialogDescription>
                        Create a new collection with custom schema. This will create a global database table.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-6">
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

                    <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg p-4">
                        <p className="text-sm text-amber-900 dark:text-amber-200">
                            <strong>⚠️ Warning:</strong> This will create a global database table accessible across all accounts.
                            System fields (id, account_id, created_at, etc.) will be added automatically.
                        </p>
                    </div>

                    <SchemaBuilder
                        fields={fields}
                        onChange={setFields}
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
                            {isSubmitting ? 'Creating...' : 'Create Collection'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
