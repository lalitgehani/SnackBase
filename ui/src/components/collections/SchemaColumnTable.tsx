/**
 * Dense schema column table with progressive disclosure for advanced field options.
 * Primary create/edit UX for collection schemas (Phase 2 + DnD reorder).
 */

import { useMemo, useState } from 'react';
import {
  Calculator,
  ChevronDown,
  ChevronRight,
  GripVertical,
  HelpCircle,
  MoveDown,
  MoveUp,
  Plus,
  Trash2,
} from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import {
  canMoveField,
  moveFieldByDirection,
  remapExpandedAfterReorder,
  remapExpandedAfterSwap,
  reorderFields,
} from '@/lib/schemaFieldReorder';
import { SCHEMA_ADD_FIELD_TEST_ID } from '@/hooks/useCollectionsWorkspaceShortcuts';
import type { FieldDefinition } from '@/services/collections.service';
import {
  FIELD_TYPES,
  ON_DELETE_OPTIONS,
  MASK_TYPE_OPTIONS,
  RETURN_TYPE_OPTIONS,
} from '@/services/collections.service';
import type { SchemaFieldErrors } from './schemaValidation';

function fieldSortableId(index: number): string {
  return `schema-field-${index}`;
}

export interface SchemaColumnTableProps {
  fields: FieldDefinition[];
  onChange: (fields: FieldDefinition[]) => void;
  originalFieldCount?: number;
  collections?: string[];
  fieldErrors?: SchemaFieldErrors;
  readOnly?: boolean;
  showAddButton?: boolean;
}

function ExpressionHelp({ fields }: { fields: FieldDefinition[] }) {
  const available = fields.filter((f) => f.name && f.type !== 'computed');
  return (
    <div className="space-y-3 text-sm">
      <p className="font-semibold">Expression Reference</p>
      <div>
        <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">String</p>
        <div className="space-y-1 font-mono text-xs">
          <div>concat(a, b, ...) → &quot;hello world&quot;</div>
          <div>upper(a) / lower(a)</div>
          <div>trim(a) / length(a)</div>
          <div>substring(a, start, len)</div>
        </div>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">Math</p>
        <div className="space-y-1 font-mono text-xs">
          <div>price * quantity</div>
          <div>round(a, decimals)</div>
          <div>abs(a) / ceil(a) / floor(a)</div>
        </div>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">Logic</p>
        <div className="space-y-1 font-mono text-xs">
          <div>if(condition, then, else)</div>
          <div>coalesce(a, b, ...)</div>
          <div>nullif(a, b)</div>
        </div>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">Date</p>
        <div className="space-y-1 font-mono text-xs">
          <div>now()</div>
          <div>date_diff(a, b, &apos;days&apos;)</div>
          <div>date_add(a, value, &apos;days&apos;)</div>
        </div>
      </div>
      {available.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">
            Available Fields
          </p>
          <div className="space-y-1 font-mono text-xs">
            {available.map((f) => (
              <div key={f.name}>
                {f.name}{' '}
                <span className="text-muted-foreground">({f.type})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SchemaColumnTable({
  fields,
  onChange,
  originalFieldCount = 0,
  collections = [],
  fieldErrors = {},
  readOnly = false,
  showAddButton = true,
}: SchemaColumnTableProps) {
  const [expanded, setExpanded] = useState<Set<number>>(() => {
    const initial = new Set<number>();
    fields.forEach((field, index) => {
      if (
        field.type === 'reference' ||
        field.type === 'computed' ||
        field.pii ||
        field.encrypted
      ) {
        initial.add(index);
      }
    });
    return initial;
  });

  const toggleExpand = (index: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const addField = () => {
    onChange([
      ...fields,
      {
        name: '',
        type: 'text',
        required: false,
        unique: false,
        pii: false,
        encrypted: false,
      },
    ]);
  };

  const removeField = (index: number) => {
    if (index < originalFieldCount) return;
    onChange(fields.filter((_, i) => i !== index));
    setExpanded((prev) => {
      const next = new Set<number>();
      for (const i of prev) {
        if (i < index) next.add(i);
        else if (i > index) next.add(i - 1);
      }
      return next;
    });
  };

  const canMove = (index: number, direction: 'up' | 'down'): boolean =>
    canMoveField(fields.length, index, direction, originalFieldCount);

  const moveField = (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const newFields = moveFieldByDirection(
      fields,
      index,
      direction,
      originalFieldCount,
    );
    if (newFields === fields) return;
    onChange(newFields);
    setExpanded((prev) => remapExpandedAfterSwap(prev, index, targetIndex));
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const sortableIds = useMemo(
    () => fields.map((_, index) => fieldSortableId(index)),
    [fields],
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const fromIndex = sortableIds.indexOf(String(active.id));
    const toIndex = sortableIds.indexOf(String(over.id));
    if (fromIndex < 0 || toIndex < 0) return;

    const newFields = reorderFields(
      fields,
      fromIndex,
      toIndex,
      originalFieldCount,
    );
    if (newFields === fields) return;
    onChange(newFields);
    setExpanded((prev) =>
      remapExpandedAfterReorder(prev, fromIndex, toIndex),
    );
  };

  const updateField = (index: number, updates: Partial<FieldDefinition>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...updates };

    if (updates.type && updates.type !== 'reference') {
      delete newFields[index].collection;
      delete newFields[index].on_delete;
    }

    if (updates.pii === false) {
      delete newFields[index].mask_type;
    }

    if (updates.type && updates.type !== 'computed') {
      delete newFields[index].expression;
      delete newFields[index].return_type;
    }

    if (updates.type === 'computed') {
      newFields[index].required = false;
      newFields[index].unique = false;
      newFields[index].pii = false;
      newFields[index].encrypted = false;
      delete newFields[index].mask_type;
      delete newFields[index].default;
    }

    // Encryption only for text/json; clear when type becomes unsupported
    if (updates.type && updates.type !== 'text' && updates.type !== 'json') {
      newFields[index].encrypted = false;
    }
    if (updates.encrypted === true) {
      newFields[index].unique = false;
    }

    if (updates.default === '') {
      delete newFields[index].default;
    }

    // Auto-expand when advanced options become relevant
    if (
      updates.type === 'reference' ||
      updates.type === 'computed' ||
      updates.pii === true ||
      updates.encrypted === true
    ) {
      setExpanded((prev) => new Set(prev).add(index));
    }

    onChange(newFields);
  };

  const needsExpand = (field: FieldDefinition) =>
    field.type === 'reference' ||
    field.type === 'computed' ||
    Boolean(field.pii) ||
    Boolean(field.encrypted);

  return (
    <div className="space-y-3" data-testid="schema-column-table">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold">Columns</h3>
          <p className="text-xs text-muted-foreground">
            User-defined fields. Expand a row for reference, computed, or PII options.
          </p>
        </div>
        {!readOnly && showAddButton && (
          <Button
            type="button"
            onClick={addField}
            size="sm"
            variant="outline"
            data-testid={SCHEMA_ADD_FIELD_TEST_ID}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Field
          </Button>
        )}
      </div>

      {fields.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed py-8 text-center text-muted-foreground">
          No fields yet. Click &quot;Add Field&quot; to get started.
        </div>
      ) : (
        <div className="rounded-md border">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={readOnly ? undefined : handleDragEnd}
          >
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  {!readOnly && <TableHead className="w-24 px-1" />}
                  <TableHead className="min-w-[140px]">Name</TableHead>
                  <TableHead className="min-w-[120px]">Type</TableHead>
                  <TableHead className="min-w-[100px]">Default</TableHead>
                  <TableHead className="w-16 text-center">Req</TableHead>
                  <TableHead className="w-16 text-center">Uniq</TableHead>
                  <TableHead className="w-16 text-center">PII</TableHead>
                  <TableHead className="w-16 text-center">Enc</TableHead>
                  <TableHead className="w-10" />
                  {!readOnly && <TableHead className="w-10" />}
                </TableRow>
              </TableHeader>
              <SortableContext
                items={sortableIds}
                strategy={verticalListSortingStrategy}
                disabled={readOnly}
              >
                <TableBody>
                  {fields.map((field, index) => {
                    const isExisting = index < originalFieldCount;
                    const isNew = !isExisting && originalFieldCount > 0;
                    const isExpanded = expanded.has(index);
                    const errors = fieldErrors[index] ?? {};
                    const isComputed = field.type === 'computed';
                    const showExpand = needsExpand(field) || isExpanded;

                    return (
                      <FieldRows
                        key={fieldSortableId(index)}
                        id={fieldSortableId(index)}
                        field={field}
                        index={index}
                        isExisting={isExisting}
                        isNew={isNew}
                        isExpanded={isExpanded}
                        isComputed={isComputed}
                        showExpand={showExpand}
                        errors={errors}
                        readOnly={readOnly}
                        collections={collections}
                        fields={fields}
                        canDrag={!readOnly && !isExisting}
                        canMoveUp={canMove(index, 'up')}
                        canMoveDown={canMove(index, 'down')}
                        onToggleExpand={() => toggleExpand(index)}
                        onMoveUp={() => moveField(index, 'up')}
                        onMoveDown={() => moveField(index, 'down')}
                        onRemove={() => removeField(index)}
                        onUpdate={(updates) => updateField(index, updates)}
                      />
                    );
                  })}
                </TableBody>
              </SortableContext>
            </Table>
          </DndContext>
        </div>
      )}
    </div>
  );
}

interface FieldRowsProps {
  id: string;
  field: FieldDefinition;
  index: number;
  isExisting: boolean;
  isNew: boolean;
  isExpanded: boolean;
  isComputed: boolean;
  showExpand: boolean;
  errors: Partial<Record<string, string>>;
  readOnly: boolean;
  collections: string[];
  fields: FieldDefinition[];
  canDrag: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onToggleExpand: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
  onUpdate: (updates: Partial<FieldDefinition>) => void;
}

function FieldRows({
  id,
  field,
  index,
  isExisting,
  isNew,
  isExpanded,
  isComputed,
  showExpand,
  errors,
  readOnly,
  collections,
  fields,
  canDrag,
  canMoveUp,
  canMoveDown,
  onToggleExpand,
  onMoveUp,
  onMoveDown,
  onRemove,
  onUpdate,
}: FieldRowsProps) {
  const nameLocked = readOnly || isExisting;
  const typeLocked = readOnly || isExisting;
  const deleteDisabled = readOnly || isExisting;
  const colSpan = readOnly ? 8 : 10;

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled: !canDrag });

  const rowStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : undefined,
    position: isDragging ? ('relative' as const) : undefined,
    zIndex: isDragging ? 10 : undefined,
  };

  return (
    <>
      <TableRow
        ref={setNodeRef}
        style={rowStyle}
        className={cn(
          isNew && 'bg-primary/5',
          Object.keys(errors).length > 0 && 'bg-destructive/5',
          isDragging && 'bg-muted/40 shadow-sm',
        )}
        data-testid={`schema-field-row-${index}`}
        data-existing={isExisting || undefined}
        data-new={isNew || undefined}
      >
        {!readOnly && (
          <TableCell className="px-1">
            <div className="flex items-center gap-0.5">
              <button
                type="button"
                className={cn(
                  'inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground',
                  canDrag
                    ? 'cursor-grab hover:bg-accent active:cursor-grabbing'
                    : 'cursor-not-allowed opacity-30',
                )}
                disabled={!canDrag}
                aria-label={`Drag to reorder field ${index + 1}`}
                data-testid={`schema-field-drag-${index}`}
                {...(canDrag ? { ...attributes, ...listeners } : {})}
              >
                <GripVertical className="h-3.5 w-3.5" />
              </button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={onMoveUp}
                disabled={!canMoveUp}
                aria-label={`Move field ${index + 1} up`}
              >
                <MoveUp className="h-3.5 w-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={onMoveDown}
                disabled={!canMoveDown}
                aria-label={`Move field ${index + 1} down`}
              >
                <MoveDown className="h-3.5 w-3.5" />
              </Button>
            </div>
          </TableCell>
        )}

        <TableCell>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <Input
                id={`field-${index}-name`}
                value={field.name}
                onChange={(e) => onUpdate({ name: e.target.value })}
                placeholder="field_name"
                disabled={nameLocked}
                className={cn(
                  'h-8 font-mono text-sm',
                  nameLocked && 'bg-muted',
                  errors.name && 'border-destructive',
                )}
                aria-label={`Field ${index + 1} name`}
              />
              {isExisting && (
                <span className="text-xs text-muted-foreground">(existing)</span>
              )}
              {isNew && (
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  New
                </Badge>
              )}
              {isComputed && (
                <Badge variant="secondary" className="gap-1 text-[10px] px-1.5 py-0">
                  <Calculator className="h-3 w-3" />
                  Computed
                </Badge>
              )}
              {field.type === 'reference' && field.collection && (
                <Badge variant="outline" className="font-mono text-[10px] px-1.5 py-0">
                  → {field.collection}
                </Badge>
              )}
              {field.pii && (
                <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                  PII
                </Badge>
              )}
            </div>
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>
        </TableCell>

        <TableCell>
          <Select
            value={field.type}
            onValueChange={(value) => onUpdate({ type: value })}
            disabled={typeLocked}
          >
            <SelectTrigger
              id={`field-${index}-type`}
              className="h-8"
              aria-label={`Field ${index + 1} type`}
            >
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
          {errors.type && (
            <p className="mt-1 text-xs text-destructive">{errors.type}</p>
          )}
        </TableCell>

        <TableCell>
          {isComputed || readOnly ? (
            <span className="text-xs text-muted-foreground">
              {isComputed ? '—' : field.default != null ? String(field.default) : '—'}
            </span>
          ) : (
            <Input
              id={`field-${index}-default`}
              value={
                field.default === undefined || field.default === null
                  ? ''
                  : String(field.default)
              }
              onChange={(e) => onUpdate({ default: e.target.value })}
              placeholder="—"
              className="h-8 font-mono text-sm"
              aria-label={`Field ${index + 1} default`}
              disabled={isComputed}
            />
          )}
        </TableCell>

        <TableCell className="text-center">
          <input
            type="checkbox"
            checked={field.required || false}
            onChange={(e) => onUpdate({ required: e.target.checked })}
            disabled={readOnly || isComputed}
            className="rounded"
            aria-label={`Field ${index + 1} required`}
          />
        </TableCell>

        <TableCell className="text-center">
          <input
            type="checkbox"
            checked={field.unique || false}
            onChange={(e) => onUpdate({ unique: e.target.checked })}
            disabled={readOnly || isComputed}
            className="rounded"
            aria-label={`Field ${index + 1} unique`}
          />
        </TableCell>

        <TableCell className="text-center">
          <input
            type="checkbox"
            checked={field.pii || false}
            onChange={(e) => onUpdate({ pii: e.target.checked })}
            disabled={readOnly || isComputed}
            className="rounded"
            aria-label={`Field ${index + 1} pii`}
          />
        </TableCell>

        <TableCell className="text-center">
          <input
            type="checkbox"
            checked={field.encrypted || false}
            onChange={(e) => onUpdate({ encrypted: e.target.checked })}
            disabled={
              readOnly ||
              isComputed ||
              (field.type !== 'text' && field.type !== 'json')
            }
            className="rounded"
            aria-label={`Field ${index + 1} encrypted`}
            title={
              field.type === 'text' || field.type === 'json'
                ? 'Encrypt at rest (server-only, non-queryable)'
                : 'Encryption is only available for text and json fields'
            }
          />
        </TableCell>

        <TableCell>
          {showExpand && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onToggleExpand}
              aria-label={
                isExpanded
                  ? `Collapse field ${index + 1} options`
                  : `Expand field ${index + 1} options`
              }
              aria-expanded={isExpanded}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          )}
        </TableCell>

        {!readOnly && (
          <TableCell>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onRemove}
              disabled={deleteDisabled}
              aria-label={
                isExisting
                  ? `Cannot delete existing field ${index + 1}`
                  : `Delete field ${index + 1}`
              }
              title={
                isExisting
                  ? 'Existing fields cannot be removed after creation'
                  : 'Remove field'
              }
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </TableCell>
        )}
      </TableRow>

      {isExpanded && (
        <TableRow
          className="hover:bg-transparent bg-muted/20"
          data-testid={`schema-field-expand-${index}`}
        >
          <TableCell colSpan={colSpan} className="p-3 whitespace-normal">
            <div className="space-y-3 max-w-3xl">
              {field.type === 'reference' && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor={`field-${index}-collection`}>
                      Target Collection *
                    </Label>
                    <Select
                      value={field.collection || ''}
                      onValueChange={(value) => onUpdate({ collection: value })}
                      disabled={readOnly}
                    >
                      <SelectTrigger
                        id={`field-${index}-collection`}
                        className={cn(errors.collection && 'border-destructive')}
                      >
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
                    {errors.collection && (
                      <p className="text-xs text-destructive">{errors.collection}</p>
                    )}
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor={`field-${index}-on-delete`}>On Delete</Label>
                    <Select
                      value={field.on_delete || 'restrict'}
                      onValueChange={(value) => onUpdate({ on_delete: value })}
                      disabled={readOnly}
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

              {field.type === 'computed' && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`field-${index}-expression`}>
                        Expression *
                      </Label>
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            aria-label="Expression help"
                          >
                            <HelpCircle className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent
                          className="max-h-96 w-80 overflow-y-auto"
                          align="start"
                        >
                          <ExpressionHelp fields={fields} />
                        </PopoverContent>
                      </Popover>
                    </div>
                    <Textarea
                      id={`field-${index}-expression`}
                      value={field.expression || ''}
                      onChange={(e) => onUpdate({ expression: e.target.value })}
                      placeholder="concat(first_name, ' ', last_name)"
                      rows={2}
                      className={cn(
                        'font-mono text-sm',
                        errors.expression && 'border-destructive',
                      )}
                      disabled={readOnly}
                    />
                    {errors.expression && (
                      <p className="text-xs text-destructive">{errors.expression}</p>
                    )}
                  </div>
                  <div className="space-y-1.5 max-w-xs">
                    <Label htmlFor={`field-${index}-return-type`}>
                      Return Type *
                    </Label>
                    <Select
                      value={field.return_type || ''}
                      onValueChange={(value) => onUpdate({ return_type: value })}
                      disabled={readOnly}
                    >
                      <SelectTrigger
                        id={`field-${index}-return-type`}
                        className={cn(errors.return_type && 'border-destructive')}
                      >
                        <SelectValue placeholder="Select return type" />
                      </SelectTrigger>
                      <SelectContent>
                        {RETURN_TYPE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.return_type && (
                      <p className="text-xs text-destructive">{errors.return_type}</p>
                    )}
                  </div>
                </div>
              )}

              {field.pii && !isComputed && (
                <div className="space-y-1.5 max-w-xs">
                  <Label htmlFor={`field-${index}-mask-type`}>Mask Type *</Label>
                  <Select
                    value={field.mask_type || ''}
                    onValueChange={(value) => onUpdate({ mask_type: value })}
                    disabled={readOnly}
                  >
                    <SelectTrigger
                      id={`field-${index}-mask-type`}
                      className={cn(errors.mask_type && 'border-destructive')}
                    >
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
                  {errors.mask_type && (
                    <p className="text-xs text-destructive">{errors.mask_type}</p>
                  )}
                  <p className="text-xs text-amber-700 dark:text-amber-300">
                    PII fields are masked in API responses according to the selected
                    mask type.
                  </p>
                </div>
              )}

              {field.encrypted && !isComputed && (
                <div className="space-y-1.5 max-w-md rounded-md border border-amber-300 bg-amber-50 p-3 dark:border-amber-700 dark:bg-amber-950/40">
                  <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                    Encrypted field (server-only)
                  </p>
                  <p className="text-xs text-amber-800 dark:text-amber-200">
                    Values are encrypted at rest and returned as •••••••• in normal
                    API responses. Encrypted fields cannot be filtered, sorted,
                    searched, indexed, or unique. Plaintext is only available via a
                    service API key with the <code>records:secrets:read</code> scope.
                  </p>
                </div>
              )}

              {isExisting && (
                <p className="text-xs text-muted-foreground">
                  Existing field name and type cannot be changed. Fields cannot be
                  removed after creation.
                </p>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
