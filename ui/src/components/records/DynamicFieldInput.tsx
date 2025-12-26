/**
 * Dynamic field input component
 * Renders different input types based on field definition
 */

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData } from '@/types/records.types';
import { isoToDatetimeLocal, datetimeLocalToIso } from '@/lib/form-helpers';

interface DynamicFieldInputProps {
	field: FieldDefinition;
	value: any;
	onChange: (value: any) => void;
	error?: string;
	disabled?: boolean;
	referenceRecords?: RecordData[];
}

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
		if (!newValue.trim()) {
			setJsonError(null);
			onChange(newValue);
			return;
		}

		try {
			JSON.parse(newValue);
			setJsonError(null);
			onChange(newValue);
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
						value={value || ''}
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
						value={value ?? ''}
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
							checked={value || false}
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
						value={value ? isoToDatetimeLocal(value) : ''}
						onChange={(e) =>
							onChange(e.target.value ? datetimeLocalToIso(e.target.value) : null)
						}
						disabled={disabled}
						className={error ? 'border-destructive' : ''}
					/>
				);

			case 'json':
				return (
					<div className="space-y-2">
						<Textarea
							id={`field-${field.name}`}
							value={value || ''}
							onChange={(e) => handleJsonChange(e.target.value)}
							disabled={disabled}
							placeholder={`Enter JSON for ${field.name}`}
							rows={4}
							className={`font-mono text-sm ${error || jsonError ? 'border-destructive' : ''}`}
						/>
						{jsonError && <p className="text-sm text-destructive">{jsonError}</p>}
					</div>
				);

			case 'reference':
				return (
					<Select
						value={value || ''}
						onValueChange={onChange}
						disabled={disabled}
					>
						<SelectTrigger id={`field-${field.name}`} className={error ? 'border-destructive' : ''}>
							<SelectValue placeholder={`Select ${field.collection}`} />
						</SelectTrigger>
						<SelectContent>
							{referenceRecords.map((record) => {
								// Try to find a display field (first text field that's not id)
								const displayField = Object.keys(record).find(
									(key) =>
										key !== 'id' &&
										key !== 'account_id' &&
										key !== 'created_at' &&
										key !== 'updated_at' &&
										typeof record[key] === 'string',
								);
								const displayValue = displayField ? record[displayField] : record.id;
								const truncatedValue =
									String(displayValue).length > 30
										? String(displayValue).substring(0, 30) + '...'
										: displayValue;

								return (
									<SelectItem key={record.id} value={record.id}>
										{record.id.slice(0, 8)}... ({truncatedValue})
									</SelectItem>
								);
							})}
							{referenceRecords.length === 0 && (
								<SelectItem value="" disabled>
									No records available
								</SelectItem>
							)}
						</SelectContent>
					</Select>
				);

			default:
				return (
					<Input
						id={`field-${field.name}`}
						type="text"
						value={value || ''}
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
