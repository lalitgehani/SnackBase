/**
 * View collection dialog component
 * Displays collection schema in read-only mode
 */

import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Collection } from '@/services/collections.service';

interface ViewCollectionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    collection: Collection | null;
}

export default function ViewCollectionDialog({
    open,
    onOpenChange,
    collection,
}: ViewCollectionDialogProps) {
    if (!collection) return null;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title={collection.name}
            description={`Collection schema with ${collection.schema.length} fields`}
            className="max-w-2xl"
            footer={
                <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
            }
        >
            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-muted-foreground">ID:</span>
                        <span className="ml-2 font-mono">{collection.id}</span>
                    </div>
                    <div>
                        <span className="text-muted-foreground">Table:</span>
                        <span className="ml-2 font-mono">{collection.table_name}</span>
                    </div>
                </div>

                <div>
                    <h3 className="font-semibold mb-3">Fields</h3>
                    <div className="space-y-3">
                        {collection.schema.map((field, index) => (
                            <div
                                key={index}
                                className="border rounded-lg p-4 space-y-2"
                            >
                                <div className="flex items-center justify-between">
                                    <span className="font-medium">{field.name}</span>
                                    <div className="flex gap-2">
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
                                {field.pii && field.mask_type && (
                                    <div className="text-sm text-muted-foreground">
                                        Mask type: {field.mask_type}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
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
        </AppDialog>
    );
}
