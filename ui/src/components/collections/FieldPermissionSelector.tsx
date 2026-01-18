import React from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Globe, ListFilter } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FieldPermissionSelectorProps {
    label: string;
    description: string;
    value: string;
    fields: string[];
    onChange: (value: string) => void;
}

export default function FieldPermissionSelector({
    label,
    description,
    value,
    fields,
    onChange,
}: FieldPermissionSelectorProps) {
    const isAll = value === '*';
    const selectedFields = React.useMemo(() => {
        if (isAll) return [];
        try {
            const parsed = JSON.parse(value);
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }, [value, isAll]);

    const handleToggleField = (fieldName: string) => {
        let next: string[];
        if (selectedFields.includes(fieldName)) {
            next = selectedFields.filter(f => f !== fieldName);
        } else {
            next = [...selectedFields, fieldName];
        }

        if (next.length === 0) {
            onChange('*');
        } else {
            onChange(JSON.stringify(next));
        }
    };

    return (
        <div className="space-y-3">
            <div>
                <Label className="text-base font-semibold">{label}</Label>
                <p className="text-sm text-muted-foreground">{description}</p>
            </div>

            <div className="flex flex-col gap-3 p-4 border rounded-lg bg-card text-card-foreground shadow-sm">
                <div className="flex items-center gap-2">
                    <Button
                        type="button"
                        variant={isAll ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => onChange('*')}
                        className="flex-1 gap-2"
                    >
                        <Globe className="h-4 w-4" />
                        All Fields (*)
                    </Button>
                    <Button
                        type="button"
                        variant={!isAll ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => {
                            if (isAll) onChange('[]');
                        }}
                        className="flex-1 gap-2"
                    >
                        <ListFilter className="h-4 w-4" />
                        Specific Fields
                    </Button>
                </div>

                {!isAll && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-2 p-3 bg-muted/30 rounded-md border border-dashed">
                        {fields.map((field) => (
                            <div key={field} className="flex items-center space-x-2">
                                <Checkbox
                                    id={`${label}-${field}`}
                                    checked={selectedFields.includes(field)}
                                    onCheckedChange={() => handleToggleField(field)}
                                />
                                <label
                                    htmlFor={`${label}-${field}`}
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                >
                                    {field}
                                </label>
                            </div>
                        ))}
                    </div>
                )}

                <p className="text-xs text-muted-foreground text-center">
                    {isAll
                        ? "All existing and future fields will be accessible."
                        : `${selectedFields.length} of ${fields.length} fields selected.`}
                </p>
            </div>
        </div>
    );
}
