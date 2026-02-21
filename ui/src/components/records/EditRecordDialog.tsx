/**
 * Edit record dialog component
 * Dynamic form for editing records in a collection
 */

import { useState, useEffect } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import DynamicFieldInput from './DynamicFieldInput';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData } from '@/types/records.types';
import { initializeFormState, validateFormState } from '@/lib/form-helpers';
import { handleApiError } from '@/lib/api';

interface EditRecordDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onSubmit: (recordId: string, data: RecordData) => Promise<void>;
	schema: FieldDefinition[];
	collectionName: string;
	record: RecordData | null;
	recordId: string;
	// For reference fields
	referenceRecords?: Record<string, RecordData[]>;
	onFetchReferenceRecords?: (collection: string) => Promise<void>;
}

export default function EditRecordDialog({
	open,
	onOpenChange,
	onSubmit,
	schema,
	collectionName,
	record,
	recordId,
	referenceRecords = {},
	onFetchReferenceRecords,
}: EditRecordDialogProps) {
	const [formState, setFormState] = useState(() => initializeFormState(schema));
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [fetchingReferences, setFetchingReferences] = useState<Set<string>>(new Set());

	// Initialize form with record data when record changes
	useEffect(() => {
		if (record) {
			setFormState(initializeFormState(schema, record));
		}
	}, [record, schema]);

	// Fetch reference records when dialog opens
	useEffect(() => {
		if (open) {
			// Fetch records for all reference fields
			schema.forEach(async (field) => {
				if (field.type === 'reference' && field.collection && onFetchReferenceRecords) {
					setFetchingReferences((prev) => new Set(prev).add(field.name));
					try {
						await onFetchReferenceRecords(field.collection);
					} finally {
						setFetchingReferences((prev) => {
							const next = new Set(prev);
							next.delete(field.name);
							return next;
						});
					}
				}
			});
		} else if (!open) {
			setError(null);
		}
	}, [open, schema, onFetchReferenceRecords]);

	const handleFieldChange = (fieldName: string, value: unknown) => {
		setFormState((prev) => ({
			...prev,
			fields: {
				...prev.fields,
				[fieldName]: {
					...prev.fields[fieldName],
					value,
					error: null, // Clear error on change
					touched: true,
				},
			},
		}));
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		// Validate all fields
		const validatedState = validateFormState(formState, schema);
		setFormState(validatedState);

		if (!validatedState.isValid) {
			setError('Please fix the validation errors before submitting');
			return;
		}

		// Build record data from form state
		const recordData: Record<string, unknown> = {};
		for (const field of schema) {
			recordData[field.name] = formState.fields[field.name]?.value;
		}

		setIsSubmitting(true);
		try {
			await onSubmit(recordId, recordData);
			onOpenChange(false);
		} catch (err) {
			setError(handleApiError(err));
		} finally {
			setIsSubmitting(false);
		}
	};

	const isReferenceLoading = schema.some(
		(field) => field.type === 'reference' && fetchingReferences.has(field.name),
	);

	return (
		<AppDialog
			open={open}
			onOpenChange={onOpenChange}
			title="Edit Record"
			description={<>Edit record in the <strong>{collectionName}</strong> collection.</>}
			className="max-w-2xl"
			footer={
				!isReferenceLoading ? (
					<>
						<Button
							type="button"
							variant="outline"
							onClick={() => onOpenChange(false)}
							disabled={isSubmitting}
						>
							Cancel
						</Button>
						<Button type="submit" form="edit-record-form" disabled={isSubmitting}>
							{isSubmitting ? 'Saving...' : 'Save Changes'}
						</Button>
					</>
				) : undefined
			}
		>
			{isReferenceLoading ? (
				<div className="flex items-center justify-center py-8">
					<RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
					<span className="ml-2 text-muted-foreground">
						Loading reference data...
					</span>
				</div>
			) : (
				<form id="edit-record-form" onSubmit={handleSubmit} className="space-y-6">
					<div className="max-h-[60vh] overflow-y-auto pr-4 space-y-4">
						{schema.map((field) => (
							<DynamicFieldInput
								key={field.name}
								field={field}
								value={formState.fields[field.name]?.value}
								onChange={(value) => handleFieldChange(field.name, value)}
								error={formState.fields[field.name]?.error || undefined}
								disabled={isSubmitting}
								referenceRecords={
									field.type === 'reference' && field.collection
										? (referenceRecords[field.collection] || [])
										: undefined
								}
							/>
						))}
					</div>

					{error && (
						<div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
							<p className="text-destructive text-sm">{error}</p>
						</div>
					)}
				</form>
			)}
		</AppDialog>
	);
}
