/**
 * Dynamic field input component
 * Renders different input types based on field definition
 */

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { format } from 'date-fns';
import { CalendarIcon, Check, ChevronsUpDown, Eye, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData } from '@/types/records.types';
import { isoToDatetimeLocal, datetimeLocalToIso } from '@/lib/form-helpers';
import FileUploadInput from './FileUploadInput';
import { type FileMetadata } from '@/services/files.service';

interface DynamicFieldInputProps {
	field: FieldDefinition;
	value: unknown;
	onChange: (value: unknown) => void;
	error?: string;
	disabled?: boolean;
	referenceRecords?: RecordData[];
}

/** Returns a human-readable display value for a record (prefers 'name' field, then first text field). */
function getRecordDisplayValue(record: RecordData): string {
	if (typeof record['name'] === 'string' && record['name']) {
		return record['name'];
	}
	const systemKeys = ['id', 'account_id', 'created_at', 'updated_at', 'created_by', 'updated_by'];
	const textKey = Object.keys(record).find(
		(key) => !systemKeys.includes(key) && typeof record[key] === 'string' && record[key],
	);
	if (textKey) return String(record[textKey]);
	return String(record.id ?? '').slice(0, 12);
}

/** User-facing (non-system) fields from a record, up to `limit`. */
function getUserFields(record: RecordData, limit = 3): [string, unknown][] {
	const systemKeys = ['id', 'account_id', 'created_at', 'updated_at', 'created_by', 'updated_by'];
	return Object.entries(record)
		.filter(([key]) => !systemKeys.includes(key))
		.slice(0, limit);
}

// ---------------------------------------------------------------------------
// ReferenceCombobox — async-search combobox for reference fields
// ---------------------------------------------------------------------------

interface ReferenceComboboxProps {
	field: FieldDefinition;
	value: string;
	onChange: (value: unknown) => void;
	disabled?: boolean;
	error?: boolean;
	referenceRecords: RecordData[];
}

function ReferenceCombobox({
	field,
	value,
	onChange,
	disabled,
	error,
	referenceRecords,
}: ReferenceComboboxProps) {
	const [open, setOpen] = useState(false);
	const [query, setQuery] = useState('');
	const [viewOpen, setViewOpen] = useState(false);

	const selectedRecord = referenceRecords.find((r) => r.id === value) ?? null;
	const displayValue = selectedRecord ? getRecordDisplayValue(selectedRecord) : null;

	const filteredRecords = query
		? referenceRecords.filter((record) => {
				const dv = getRecordDisplayValue(record).toLowerCase();
				const id = String(record.id ?? '').toLowerCase();
				const q = query.toLowerCase();
				return dv.includes(q) || id.includes(q);
			})
		: referenceRecords;

	return (
		<div className="flex gap-1">
			{/* Combobox trigger */}
			<Popover open={open} onOpenChange={setOpen}>
				<PopoverTrigger asChild>
					<Button
						variant="outline"
						role="combobox"
						disabled={disabled}
						className={cn(
							'flex-1 justify-between font-normal min-w-0',
							!value && 'text-muted-foreground',
							error ? 'border-destructive' : '',
						)}
					>
						<span className="truncate">
							{displayValue ?? (value ? (
								<span className="font-mono text-xs">{String(value).slice(0, 12)}…</span>
							) : (
								`Select ${field.collection}…`
							))}
						</span>
						<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
					</Button>
				</PopoverTrigger>
				<PopoverContent className="w-[300px] p-0" align="start">
					<Command shouldFilter={false}>
						<CommandInput
							placeholder={`Search ${field.collection}…`}
							value={query}
							onValueChange={setQuery}
						/>
						<CommandList>
							<CommandEmpty>No records found.</CommandEmpty>
							<CommandGroup>
								{filteredRecords.map((record) => {
									const id = record.id as string;
									const dv = getRecordDisplayValue(record);
									return (
										<CommandItem
											key={id}
											value={id}
											onSelect={() => {
												onChange(id);
												setOpen(false);
												setQuery('');
											}}
										>
											<Check
												className={cn('mr-2 h-4 w-4 shrink-0', value === id ? 'opacity-100' : 'opacity-0')}
											/>
											<div className="flex flex-col min-w-0 flex-1">
												<span className="truncate text-sm">{dv}</span>
												<span className="font-mono text-xs text-muted-foreground truncate">
													{id.slice(0, 20)}…
												</span>
											</div>
										</CommandItem>
									);
								})}
							</CommandGroup>
						</CommandList>
					</Command>
				</PopoverContent>
			</Popover>

			{/* Clear button */}
			{value && !disabled && (
				<Button
					type="button"
					variant="ghost"
					size="icon"
					className="h-9 w-9 shrink-0"
					onClick={() => onChange(null)}
					title="Clear selection"
				>
					<X className="h-4 w-4" />
				</Button>
			)}

			{/* View popover — only when a record is found in the cache */}
			{value && selectedRecord && (
				<Popover open={viewOpen} onOpenChange={setViewOpen}>
					<PopoverTrigger asChild>
						<Button
							type="button"
							variant="ghost"
							size="icon"
							className="h-9 w-9 shrink-0"
							title="View referenced record"
						>
							<Eye className="h-4 w-4" />
						</Button>
					</PopoverTrigger>
					<PopoverContent className="w-64" align="end">
						<div className="space-y-2">
							<p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
								{field.collection} record
							</p>
							<p className="font-mono text-xs text-muted-foreground break-all">
								{selectedRecord.id as string}
							</p>
							<div className="space-y-1 pt-1 border-t">
								{getUserFields(selectedRecord).map(([key, val]) => (
									<div key={key} className="flex justify-between gap-2 text-sm">
										<span className="text-muted-foreground shrink-0">{key}:</span>
										<span className="font-medium truncate max-w-[130px]">
											{val === null || val === undefined ? (
												<span className="italic text-muted-foreground">null</span>
											) : (
												String(val)
											)}
										</span>
									</div>
								))}
							</div>
						</div>
					</PopoverContent>
				</Popover>
			)}
		</div>
	);
}

// ---------------------------------------------------------------------------
// DynamicFieldInput — main export
// ---------------------------------------------------------------------------

export default function DynamicFieldInput({
	field,
	value,
	onChange,
	error,
	disabled = false,
	referenceRecords = [],
}: DynamicFieldInputProps) {
	const [jsonError, setJsonError] = useState<string | null>(null);

	// JSON field validation
	const handleJsonChange = (newValue: string) => {
		setJsonError(null);
		onChange(newValue);
	};

	const handleJsonBlur = (currentValue: string) => {
		if (!currentValue.trim()) {
			setJsonError(null);
			return;
		}

		try {
			JSON.parse(currentValue);
			setJsonError(null);
		} catch {
			setJsonError('Invalid JSON format');
		}
	};

	// Render input based on field type
	const renderInput = () => {
		switch (field.type) {
			case 'text':
			case 'email':
			case 'url':
				return (
					<Input
						id={`field-${field.name}`}
						type={field.type === 'email' ? 'email' : field.type === 'url' ? 'url' : 'text'}
						value={(value as string | number) || ''}
						onChange={(e) => onChange(e.target.value)}
						disabled={disabled}
						placeholder={`Enter ${field.name}`}
						className={error ? 'border-destructive' : ''}
					/>
				);

			case 'number':
				return (
					<Input
						id={`field-${field.name}`}
						type="number"
						value={(value as string | number) ?? ''}
						onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
						disabled={disabled}
						placeholder={`Enter ${field.name}`}
						step="any"
						className={error ? 'border-destructive' : ''}
					/>
				);

			case 'boolean':
				return (
					<div className="flex items-center space-x-2">
						<input
							id={`field-${field.name}`}
							type="checkbox"
							checked={Boolean(value) || false}
							onChange={(e) => onChange(e.target.checked)}
							disabled={disabled}
							className="h-4 w-4 rounded border-gray-300"
						/>
						<Label htmlFor={`field-${field.name}`} className="cursor-pointer">
							{value ? 'Yes' : 'No'}
						</Label>
					</div>
				);

			case 'datetime':
				return (
					<Input
						id={`field-${field.name}`}
						type="datetime-local"
						value={typeof value === 'string' ? isoToDatetimeLocal(value) : ''}
						onChange={(e) =>
							onChange(e.target.value ? datetimeLocalToIso(e.target.value) : null)
						}
						disabled={disabled}
						className={error ? 'border-destructive' : ''}
					/>
				);

			case 'date':
				return (
					<Popover>
						<PopoverTrigger asChild>
							<Button
								variant={'outline'}
								className={cn(
									'w-full justify-start text-left font-normal',
									!value && 'text-muted-foreground',
									error ? 'border-destructive' : '',
								)}
								disabled={disabled}
							>
								<CalendarIcon className="mr-2 h-4 w-4" />
								{value ? (
									format(new Date(value as string), 'PPP')
								) : (
									<span>Pick a date</span>
								)}
							</Button>
						</PopoverTrigger>
						<PopoverContent className="w-auto p-0">
							<Calendar
								mode="single"
								selected={value ? new Date(value as string) : undefined}
								onSelect={(date) => {
									if (date) {
										// Format as YYYY-MM-DD for backend
										onChange(format(date, 'yyyy-MM-dd'));
									} else {
										onChange(null);
									}
								}}
								initialFocus
							/>
						</PopoverContent>
					</Popover>
				);

			case 'json': {
				const displayValue =
					typeof value === 'string'
						? value
						: value !== null && value !== undefined
							? JSON.stringify(value, null, 2)
							: '';

				return (
					<div className="space-y-2">
						<Textarea
							id={`field-${field.name}`}
							value={displayValue}
							onChange={(e) => handleJsonChange(e.target.value)}
							onBlur={(e) => handleJsonBlur(e.target.value)}
							disabled={disabled}
							placeholder={`Enter JSON for ${field.name}`}
							rows={4}
							className={`font-mono text-sm ${error || jsonError ? 'border-destructive' : ''}`}
						/>
						{jsonError && <p className="text-sm text-destructive">{jsonError}</p>}
					</div>
				);
			}

			case 'reference':
				return (
					<ReferenceCombobox
						field={field}
						value={(value as string) || ''}
						onChange={onChange}
						disabled={disabled}
						error={!!error}
						referenceRecords={referenceRecords}
					/>
				);

			case 'file':
				// File upload with drag-and-drop support
				return (
					<FileUploadInput
						value={value as FileMetadata | null}
						onChange={onChange}
						disabled={disabled}
						fieldName={field.name}
					/>
				);

			default:
				return (
					<Input
						id={`field-${field.name}`}
						type="text"
						value={(value as string | number) || ''}
						onChange={(e) => onChange(e.target.value)}
						disabled={disabled}
						placeholder={`Enter ${field.name}`}
						className={error ? 'border-destructive' : ''}
					/>
				);
		}
	};

	// Field info badge
	const getFieldTypeInfo = () => {
		const typeLabels: Record<string, string> = {
			text: 'Text',
			number: 'Number',
			boolean: 'Boolean',
			datetime: 'DateTime',
			email: 'Email',
			url: 'URL',
			json: 'JSON',
			reference: `Reference to ${field.collection}`,
			file: 'File',
			date: 'Date',
		};
		return typeLabels[field.type] || field.type;
	};

	return (
		<div className="space-y-2">
			<div className="flex items-center justify-between">
				<Label htmlFor={`field-${field.name}`} className="flex items-center gap-2">
					{field.name}
					{field.required && <span className="text-destructive">*</span>}
					{field.unique && (
						<Badge variant="outline" className="text-xs">
							Unique
						</Badge>
					)}
					{field.pii && (
						<Badge variant="secondary" className="text-xs">
							PII
						</Badge>
					)}
				</Label>
				<Badge variant="outline" className="text-xs">
					{getFieldTypeInfo()}
				</Badge>
			</div>

			{renderInput()}

			{error && !jsonError && <p className="text-sm text-destructive">{error}</p>}

			{field.type === 'json' && !jsonError && (
				<p className="text-xs text-muted-foreground">
					Enter valid JSON. Example: {`{"key": "value"}`}
				</p>
			)}

			{field.type === 'reference' && referenceRecords.length === 0 && (
				<p className="text-xs text-muted-foreground">
					No records found in target collection
				</p>
			)}

			{field.default !== undefined && !value && (
				<p className="text-xs text-muted-foreground">
					Default: {String(field.default)}
				</p>
			)}
		</div>
	);
}
