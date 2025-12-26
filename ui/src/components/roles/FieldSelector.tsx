/**
 * Field Selector component
 * Multi-select dropdown for field selection with "All Fields" option
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Settings2, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FieldOption {
  name: string;
  isSystem?: boolean;
}

interface FieldSelectorProps {
  value: string[] | '*';
  onChange: (value: string[] | '*') => void;
  fields: FieldOption[];
  disabled?: boolean;
  label?: string;
}

// System fields that are always readable
const SYSTEM_FIELDS = ['id', 'account_id', 'created_at', 'updated_at', 'created_by', 'updated_by'];

export default function FieldSelector({
  value,
  onChange,
  fields,
  disabled = false,
  label = 'Allowed Fields',
}: FieldSelectorProps) {
  const [open, setOpen] = useState(false);
  const [tempValue, setTempValue] = useState<string[] | '*'>(value);

  const isAllFields = value === '*';
  const selectedFields = isAllFields ? fields.map(f => f.name) : (value as string[]);

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setTempValue(value);
    }
    setOpen(newOpen);
  };

  const handleToggleAll = () => {
    if (tempValue === '*') {
      setTempValue([]);
    } else {
      setTempValue('*');
    }
  };

  const handleToggleField = (fieldName: string) => {
    if (tempValue === '*') {
      // Switching from "all" to specific fields
      const newFields = fields.filter(f => f.name !== fieldName).map(f => f.name);
      setTempValue(newFields.length > 0 ? newFields : []);
    } else {
      // Toggle individual field
      if (tempValue.includes(fieldName)) {
        const newFields = tempValue.filter(f => f !== fieldName);
        setTempValue(newFields.length > 0 ? newFields : []);
      } else {
        setTempValue([...tempValue, fieldName]);
      }
    }
  };

  const handleApply = () => {
    onChange(tempValue);
    setOpen(false);
  };

  const handleCancel = () => {
    setTempValue(value);
    setOpen(false);
  };

  const displayValue = isAllFields
    ? 'All Fields'
    : selectedFields.length === 0
      ? 'None'
      : selectedFields.length === 1
        ? selectedFields[0]
        : `${selectedFields.length} fields`;

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogTrigger asChild>
          <Button
            type="button"
            variant="outline"
            className={cn(
              'w-full justify-start font-normal',
              !selectedFields.length && !isAllFields && 'text-muted-foreground'
            )}
            disabled={disabled}
          >
            <Settings2 className="mr-2 h-4 w-4" />
            {displayValue}
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Select Allowed Fields</DialogTitle>
            <DialogDescription>
              Choose which fields this role can access. System fields are always readable.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* All Fields Toggle */}
            <div className="flex items-center space-x-2 border-b pb-4">
              <Checkbox
                id="all-fields"
                checked={tempValue === '*'}
                onCheckedChange={handleToggleAll}
                disabled={disabled}
              />
              <label
                htmlFor="all-fields"
                className="flex-1 text-sm font-medium cursor-pointer flex items-center gap-2"
              >
                All Fields
                {tempValue === '*' && (
                  <Badge variant="secondary" className="text-xs">
                    <Check className="h-3 w-3 mr-1" />
                    Selected
                  </Badge>
                )}
              </label>
            </div>

            {/* Individual Fields */}
            {tempValue !== '*' && (
              <ScrollArea className="h-64 pr-4">
                <div className="space-y-2">
                  {fields.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No fields available
                    </p>
                  ) : (
                    fields.map((field) => {
                      const isSelected = tempValue.includes(field.name);
                      return (
                        <div
                          key={field.name}
                          className={cn(
                            'flex items-center space-x-2 rounded-md border p-3 transition-colors',
                            isSelected ? 'bg-primary/5 border-primary/20' : 'hover:bg-muted/50'
                          )}
                        >
                          <Checkbox
                            id={`field-${field.name}`}
                            checked={isSelected}
                            onCheckedChange={() => handleToggleField(field.name)}
                            disabled={disabled}
                          />
                          <label
                            htmlFor={`field-${field.name}`}
                            className="flex-1 text-sm cursor-pointer flex items-center justify-between"
                          >
                            <span className={cn(field.isSystem && 'text-muted-foreground')}>
                              {field.name}
                            </span>
                            {field.isSystem && (
                              <Badge variant="outline" className="text-xs ml-2">
                                System
                              </Badge>
                            )}
                          </label>
                        </div>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            )}

            {tempValue === '*' && (
              <div className="text-sm text-muted-foreground text-center py-8">
                All fields are currently selected. Users with this permission will be able to access all fields.
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button type="button" onClick={handleApply}>
              Apply
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Selected Fields Display */}
      {!isAllFields && selectedFields.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {selectedFields.slice(0, 5).map((field) => {
            const isSystem = SYSTEM_FIELDS.includes(field);
            return (
              <Badge
                key={field}
                variant={isSystem ? 'outline' : 'secondary'}
                className="text-xs"
              >
                {field}
              </Badge>
            );
          })}
          {selectedFields.length > 5 && (
            <Badge variant="secondary" className="text-xs">
              +{selectedFields.length - 5} more
            </Badge>
          )}
        </div>
      )}

      {/* System Fields Note */}
      <p className="text-xs text-muted-foreground">
        System fields (id, account_id, created_at, etc.) are always readable.
      </p>
    </div>
  );
}
