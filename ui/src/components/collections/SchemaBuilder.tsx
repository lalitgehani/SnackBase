/**
 * Schema builder component
 * Visual field management for collections
 */


import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, MoveUp, MoveDown } from 'lucide-react';
import type { FieldDefinition } from '@/services/collections.service';
import { FIELD_TYPES, ON_DELETE_OPTIONS, MASK_TYPE_OPTIONS } from '@/services/collections.service';

interface SchemaBuilderProps {
    fields: FieldDefinition[];
    onChange: (fields: FieldDefinition[]) => void;
    originalFieldCount?: number;
    collections?: string[];
}

export default function SchemaBuilder({
    fields,
    onChange,
    originalFieldCount = 0,
    collections = [],
}: SchemaBuilderProps) {
    const addField = () => {
        onChange([
            ...fields,
            {
                name: '',
                type: 'text',
                required: false,
                unique: false,
                pii: false,
            },
        ]);
    };

    const removeField = (index: number) => {
        onChange(fields.filter((_, i) => i !== index));
    };

    const moveField = (index: number, direction: 'up' | 'down') => {
        const newFields = [...fields];
        const targetIndex = direction === 'up' ? index - 1 : index + 1;
        [newFields[index], newFields[targetIndex]] = [newFields[targetIndex], newFields[index]];
        onChange(newFields);
    };

    const updateField = (index: number, updates: Partial<FieldDefinition>) => {
        const newFields = [...fields];
        newFields[index] = { ...newFields[index], ...updates };

        // Clear reference-specific fields if type is not reference
        if (updates.type && updates.type !== 'reference') {
            delete newFields[index].collection;
            delete newFields[index].on_delete;
        }

        // Clear PII-specific fields if pii is false
        if (updates.pii === false) {
            delete newFields[index].mask_type;
        }

        onChange(newFields);
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="font-semibold">Fields</h3>
                <Button type="button" onClick={addField} size="sm" variant="outline">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Field
                </Button>
            </div>

            {fields.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                    No fields yet. Click "Add Field" to get started.
                </div>
            ) : (
                <div className="space-y-4">
                    {fields.map((field, index) => {
                        // A field is "existing" if it was part of the original schema (index < originalFieldCount)
                        const isExisting = index < originalFieldCount;
                        const isFirst = index === 0;
                        const isLast = index === fields.length - 1;

                        return (
                            <div key={index} className="border rounded-lg p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="font-medium text-sm">
                                        Field {index + 1}
                                        {isExisting && <span className="ml-2 text-xs text-muted-foreground">(existing)</span>}
                                    </span>
                                    <div className="flex gap-1">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => moveField(index, 'up')}
                                            disabled={isFirst}
                                        >
                                            <MoveUp className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => moveField(index, 'down')}
                                            disabled={isLast}
                                        >
                                            <MoveDown className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => removeField(index)}
                                            disabled={isExisting}
                                        >
                                            <Trash2 className="h-4 w-4 text-destructive" />
                                        </Button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-2">
                                        <Label htmlFor={`field-${index}-name`}>Name *</Label>
                                        <Input
                                            id={`field-${index}-name`}
                                            value={field.name}
                                            onChange={(e) => updateField(index, { name: e.target.value })}
                                            placeholder="field_name"
                                            disabled={isExisting}
                                            className={isExisting ? "bg-muted" : ""}
                                        />
                                        {isExisting && (
                                            <p className="text-xs text-muted-foreground">
                                                Field name cannot be changed for existing fields
                                            </p>
                                        )}
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor={`field-${index}-type`}>Type *</Label>
                                        <Select
                                            value={field.type}
                                            onValueChange={(value) => updateField(index, { type: value })}
                                            disabled={isExisting}
                                        >
                                            <SelectTrigger id={`field-${index}-type`}>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {FIELD_TYPES.map((type) => (
                                                    <SelectItem key={type.value} value={type.value}>
                                                        {type.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-3">
                                    <label className="flex items-center space-x-2">
                                        <input
                                            type="checkbox"
                                            checked={field.required || false}
                                            onChange={(e) => updateField(index, { required: e.target.checked })}
                                            className="rounded"
                                        />
                                        <span className="text-sm">Required</span>
                                    </label>
                                    <label className="flex items-center space-x-2">
                                        <input
                                            type="checkbox"
                                            checked={field.unique || false}
                                            onChange={(e) => updateField(index, { unique: e.target.checked })}
                                            className="rounded"
                                        />
                                        <span className="text-sm">Unique</span>
                                    </label>
                                    <label className="flex items-center space-x-2">
                                        <input
                                            type="checkbox"
                                            checked={field.pii || false}
                                            onChange={(e) => updateField(index, { pii: e.target.checked })}
                                            className="rounded"
                                        />
                                        <span className="text-sm">PII</span>
                                    </label>
                                </div>

                                {field.type === 'reference' && (
                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="space-y-2">
                                            <Label htmlFor={`field-${index}-collection`}>Target Collection *</Label>
                                            <Select
                                                value={field.collection || ''}
                                                onValueChange={(value) => updateField(index, { collection: value })}
                                            >
                                                <SelectTrigger id={`field-${index}-collection`}>
                                                    <SelectValue placeholder="Select collection" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {collections.map((col) => (
                                                        <SelectItem key={col} value={col}>
                                                            {col}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor={`field-${index}-on-delete`}>On Delete</Label>
                                            <Select
                                                value={field.on_delete || 'restrict'}
                                                onValueChange={(value) => updateField(index, { on_delete: value })}
                                            >
                                                <SelectTrigger id={`field-${index}-on-delete`}>
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {ON_DELETE_OPTIONS.map((option) => (
                                                        <SelectItem key={option.value} value={option.value}>
                                                            {option.label}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                )}

                                {field.pii && (
                                    <div className="space-y-2">
                                        <Label htmlFor={`field-${index}-mask-type`}>Mask Type</Label>
                                        <Select
                                            value={field.mask_type || ''}
                                            onValueChange={(value) => updateField(index, { mask_type: value })}
                                        >
                                            <SelectTrigger id={`field-${index}-mask-type`}>
                                                <SelectValue placeholder="Select mask type" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {MASK_TYPE_OPTIONS.map((option) => (
                                                    <SelectItem key={option.value} value={option.value}>
                                                        {option.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
