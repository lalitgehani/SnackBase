/**
 * Filter Builder Panel
 * Collapsible panel for building advanced filter expressions on collection records
 */

import { useState, useCallback } from 'react';
import { Filter, Plus, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { FieldDefinition } from '@/services/collections.service';

// ── Types ────────────────────────────────────────────────────────────────────

type Operator = '=' | '!=' | '>' | '>=' | '<' | '<=' | '~' | '!~' | 'null' | '!null';

export interface FilterRow {
    id: string;
    field: string;
    operator: Operator;
    value: string;
}

export interface FilterBuilderPanelProps {
    schema: FieldDefinition[];
    appliedRows: FilterRow[];
    onApply: (filterExpression: string, rows: FilterRow[]) => void;
    onClear: () => void;
    onRemovePill: (id: string) => void;
}

// ── Operator definitions ──────────────────────────────────────────────────────

interface OperatorDef {
    value: Operator;
    label: string;
}

const TEXT_OPERATORS: OperatorDef[] = [
    { value: '=', label: 'equals' },
    { value: '!=', label: 'not equals' },
    { value: '~', label: 'contains' },
    { value: '!~', label: 'not contains' },
    { value: 'null', label: 'is empty' },
    { value: '!null', label: 'is not empty' },
];

const NUMBER_OPERATORS: OperatorDef[] = [
    { value: '=', label: 'equals' },
    { value: '!=', label: 'not equals' },
    { value: '>', label: 'greater than' },
    { value: '>=', label: 'greater than or equal' },
    { value: '<', label: 'less than' },
    { value: '<=', label: 'less than or equal' },
    { value: 'null', label: 'is empty' },
    { value: '!null', label: 'is not empty' },
];

const BOOLEAN_OPERATORS: OperatorDef[] = [
    { value: '=', label: 'equals' },
    { value: '!=', label: 'not equals' },
];

const REFERENCE_OPERATORS: OperatorDef[] = [
    { value: '=', label: 'equals' },
    { value: '!=', label: 'not equals' },
    { value: 'null', label: 'is empty' },
    { value: '!null', label: 'is not empty' },
];

const NULL_ONLY_OPERATORS: OperatorDef[] = [
    { value: 'null', label: 'is empty' },
    { value: '!null', label: 'is not empty' },
];

function getOperatorsForType(fieldType: string): OperatorDef[] {
    switch (fieldType) {
        case 'text':
        case 'email':
        case 'url':
            return TEXT_OPERATORS;
        case 'number':
            return NUMBER_OPERATORS;
        case 'boolean':
            return BOOLEAN_OPERATORS;
        case 'date':
        case 'datetime':
            return NUMBER_OPERATORS; // same comparisons as number
        case 'reference':
            return REFERENCE_OPERATORS;
        case 'file':
        case 'json':
            return NULL_ONLY_OPERATORS;
        default:
            return TEXT_OPERATORS;
    }
}

// ── System fields always available for filtering ──────────────────────────────

const SYSTEM_FIELDS: FieldDefinition[] = [
    { name: 'id', type: 'text' },
    { name: 'created_at', type: 'datetime' },
    { name: 'updated_at', type: 'datetime' },
    { name: 'created_by', type: 'text' },
    { name: 'updated_by', type: 'text' },
];

// ── Filter expression compiler ────────────────────────────────────────────────

function escapeValue(value: string): string {
    return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function compileRow(row: FilterRow, allFields: FieldDefinition[]): string | null {
    const { field, operator, value } = row;
    if (!field || !operator) return null;

    const fieldDef = allFields.find((f) => f.name === field);
    const fieldType = fieldDef?.type ?? 'text';

    if (operator === 'null') return `${field} IS NULL`;
    if (operator === '!null') return `${field} IS NOT NULL`;

    if (!value.trim()) return null;

    switch (fieldType) {
        case 'number':
            return `${field} ${operator} ${value}`;
        case 'boolean':
            return `${field} ${operator} ${value.toLowerCase()}`;
        case 'date':
        case 'datetime': {
            const escaped = escapeValue(value);
            return `${field} ${operator} "${escaped}"`;
        }
        case 'text':
        case 'email':
        case 'url':
        default: {
            if (operator === '~') return `${field} ~ "%${escapeValue(value)}%"`;
            if (operator === '!~') return `${field} !~ "%${escapeValue(value)}%"`;
            return `${field} ${operator} "${escapeValue(value)}"`;
        }
    }
}

export function compileFilterExpression(rows: FilterRow[], allFields: FieldDefinition[]): string {
    const parts = rows.map((r) => compileRow(r, allFields)).filter(Boolean) as string[];
    return parts.join(' && ');
}

// ── Pill label builder ────────────────────────────────────────────────────────

function pillLabel(row: FilterRow): string {
    if (row.operator === 'null') return `${row.field} is empty`;
    if (row.operator === '!null') return `${row.field} is not empty`;
    if (row.operator === '~') return `${row.field} contains "${row.value}"`;
    if (row.operator === '!~') return `${row.field} not contains "${row.value}"`;
    return `${row.field} ${row.operator} "${row.value}"`;
}

// ── Value input by field type ─────────────────────────────────────────────────

interface ValueInputProps {
    fieldType: string;
    operator: Operator;
    value: string;
    onChange: (v: string) => void;
}

function ValueInput({ fieldType, operator, value, onChange }: ValueInputProps) {
    if (operator === 'null' || operator === '!null') {
        return <div className="flex-1 h-9" />; // spacer
    }

    if (fieldType === 'boolean') {
        return (
            <Select value={value} onValueChange={onChange}>
                <SelectTrigger className="flex-1 h-9">
                    <SelectValue placeholder="Select value" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="true">true</SelectItem>
                    <SelectItem value="false">false</SelectItem>
                </SelectContent>
            </Select>
        );
    }

    if (fieldType === 'number') {
        return (
            <Input
                type="number"
                className="flex-1 h-9"
                placeholder="Value"
                value={value}
                onChange={(e) => onChange(e.target.value)}
            />
        );
    }

    if (fieldType === 'date') {
        return (
            <Input
                type="date"
                className="flex-1 h-9"
                value={value}
                onChange={(e) => onChange(e.target.value)}
            />
        );
    }

    if (fieldType === 'datetime') {
        return (
            <Input
                type="datetime-local"
                className="flex-1 h-9"
                value={value}
                onChange={(e) => onChange(e.target.value)}
            />
        );
    }

    return (
        <Input
            type="text"
            className="flex-1 h-9"
            placeholder="Value"
            value={value}
            onChange={(e) => onChange(e.target.value)}
        />
    );
}

// ── Main component ────────────────────────────────────────────────────────────

let rowCounter = 0;
function newRow(): FilterRow {
    return { id: `row-${++rowCounter}`, field: '', operator: '=', value: '' };
}

export default function FilterBuilderPanel({
    schema,
    appliedRows,
    onApply,
    onClear,
    onRemovePill,
}: FilterBuilderPanelProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [draftRows, setDraftRows] = useState<FilterRow[]>([]);

    const allFields = [...schema, ...SYSTEM_FIELDS];

    const addRow = () => setDraftRows((prev) => [...prev, newRow()]);

    const removeRow = (id: string) =>
        setDraftRows((prev) => prev.filter((r) => r.id !== id));

    const updateRow = useCallback((id: string, patch: Partial<FilterRow>) => {
        setDraftRows((prev) =>
            prev.map((r) => (r.id === id ? { ...r, ...patch } : r)),
        );
    }, []);

    const handleApply = () => {
        const validRows = draftRows.filter(
            (r) => r.field && (r.operator === 'null' || r.operator === '!null' || r.value.trim()),
        );
        const expression = compileFilterExpression(validRows, allFields);
        onApply(expression, validRows);
        setIsOpen(false);
    };

    const handleClear = () => {
        setDraftRows([]);
        onClear();
        setIsOpen(false);
    };

    const handleToggle = () => {
        if (!isOpen) {
            // Pre-populate draft with applied rows on open
            setDraftRows(appliedRows.length ? [...appliedRows] : []);
        }
        setIsOpen((v) => !v);
    };

    const activeCount = appliedRows.length;

    return (
        <div className="space-y-2">
            {/* Toggle Button */}
            <div className="flex items-center gap-2">
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleToggle}
                    className="gap-2"
                >
                    <Filter className="h-4 w-4" />
                    Filters
                    {activeCount > 0 && (
                        <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                            {activeCount}
                        </Badge>
                    )}
                    {isOpen ? (
                        <ChevronUp className="h-3 w-3 ml-1" />
                    ) : (
                        <ChevronDown className="h-3 w-3 ml-1" />
                    )}
                </Button>
                {activeCount > 0 && !isOpen && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground h-8 px-2 text-xs"
                        onClick={handleClear}
                    >
                        Clear all
                    </Button>
                )}
            </div>

            {/* Collapsible Panel */}
            {isOpen && (
                <div className="border rounded-lg p-4 space-y-3 bg-muted/20">
                    {draftRows.length === 0 && (
                        <p className="text-sm text-muted-foreground">
                            No filters added. Click "Add Filter" to start filtering records.
                        </p>
                    )}

                    {draftRows.map((row) => {
                        const fieldDef = allFields.find((f) => f.name === row.field);
                        const fieldType = fieldDef?.type ?? 'text';
                        const operators = getOperatorsForType(fieldType);

                        return (
                            <div key={row.id} className="flex items-center gap-2">
                                {/* Field selector */}
                                <Select
                                    value={row.field}
                                    onValueChange={(v) =>
                                        updateRow(row.id, {
                                            field: v,
                                            operator: getOperatorsForType(
                                                allFields.find((f) => f.name === v)?.type ?? 'text',
                                            )[0].value,
                                            value: '',
                                        })
                                    }
                                >
                                    <SelectTrigger className="w-40 h-9">
                                        <SelectValue placeholder="Field" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {schema.length > 0 && (
                                            <>
                                                <div className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                                    Fields
                                                </div>
                                                {schema.map((f) => (
                                                    <SelectItem key={f.name} value={f.name}>
                                                        {f.name}
                                                    </SelectItem>
                                                ))}
                                                <div className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide mt-1">
                                                    System
                                                </div>
                                            </>
                                        )}
                                        {SYSTEM_FIELDS.map((f) => (
                                            <SelectItem key={f.name} value={f.name}>
                                                {f.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>

                                {/* Operator selector */}
                                <Select
                                    value={row.operator}
                                    onValueChange={(v) =>
                                        updateRow(row.id, { operator: v as Operator, value: '' })
                                    }
                                    disabled={!row.field}
                                >
                                    <SelectTrigger className="w-44 h-9">
                                        <SelectValue placeholder="Operator" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {operators.map((op) => (
                                            <SelectItem key={op.value} value={op.value}>
                                                {op.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>

                                {/* Value input */}
                                <ValueInput
                                    fieldType={fieldType}
                                    operator={row.operator}
                                    value={row.value}
                                    onChange={(v) => updateRow(row.id, { value: v })}
                                />

                                {/* Remove button */}
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive"
                                    onClick={() => removeRow(row.id)}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            </div>
                        );
                    })}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-1">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={addRow}
                            className="gap-1"
                        >
                            <Plus className="h-3 w-3" />
                            Add Filter
                        </Button>
                        <div className="flex-1" />
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={handleClear}
                            className="text-muted-foreground"
                        >
                            Clear All
                        </Button>
                        <Button
                            type="button"
                            size="sm"
                            onClick={handleApply}
                            disabled={draftRows.length === 0}
                        >
                            Apply Filters
                        </Button>
                    </div>
                </div>
            )}

            {/* Filter Pills */}
            {appliedRows.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                    {appliedRows.map((row) => (
                        <Badge
                            key={row.id}
                            variant="secondary"
                            className="gap-1 pr-1 font-normal text-xs"
                        >
                            <span>{pillLabel(row)}</span>
                            <button
                                type="button"
                                className="ml-0.5 rounded-sm hover:bg-muted-foreground/20 p-0.5"
                                onClick={() => onRemovePill(row.id)}
                                aria-label={`Remove filter: ${pillLabel(row)}`}
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </Badge>
                    ))}
                </div>
            )}
        </div>
    );
}
