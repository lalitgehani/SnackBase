/**
 * Create record dialog component
 * Dynamic form for creating records in a collection
 */

import { useState, useEffect } from 'react';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select';
import { RefreshCw } from 'lucide-react';
import DynamicFieldInput from './DynamicFieldInput';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData } from '@/types/records.types';
import { initializeFormState, validateFormState } from '@/lib/form-helpers';
import { handleApiError } from '@/lib/api';
import { useAuthStore } from '@/stores/auth.store';
import { getAccounts, type AccountListItem } from '@/services/accounts.service';

interface CreateRecordDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onSubmit: (data: RecordData) => Promise<void>;
	schema: FieldDefinition[];
	collectionName: string;
	// For reference fields
	referenceRecords?: Record<string, RecordData[]>;
	onFetchReferenceRecords?: (collection: string) => Promise<void>;
}

export default function CreateRecordDialog({
	open,
	onOpenChange,
	onSubmit,
	schema,
	collectionName,
	referenceRecords = {},
	onFetchReferenceRecords,
}: CreateRecordDialogProps) {
	const { account } = useAuthStore();
	const [formState, setFormState] = useState(() => initializeFormState(schema));
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [fetchingReferences, setFetchingReferences] = useState<Set<string>>(new Set());

	// Account selection state (for superadmins only)
	const [accounts, setAccounts] = useState<AccountListItem[]>([]);
	const [selectedAccountId, setSelectedAccountId] = useState<string>('');
	const [loadingAccounts, setLoadingAccounts] = useState(false);
	const isSuperadmin = account?.id === '00000000-0000-0000-0000-000000000000';

	// Fetch accounts and reference records when dialog opens
	useEffect(() => {
		if (open) {
			// Fetch accounts for superadmins
			if (isSuperadmin) {
				const fetchAccountsList = async () => {
					setLoadingAccounts(true);
					try {
						const response = await getAccounts({ page_size: 100 });
						setAccounts(response.items);
						// Pre-select first account if available
						if (response.items.length > 0 && !selectedAccountId) {
							setSelectedAccountId(response.items[0].id);
						}
					} catch (err) {
						console.error('Failed to fetch accounts:', err);
					} finally {
						setLoadingAccounts(false);
					}
				};
				fetchAccountsList();
			}

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
		} else {
			// Reset form when dialog closes
			setFormState(initializeFormState(schema));
			setError(null);
			setSelectedAccountId('');
		}
	}, [open, schema, onFetchReferenceRecords, isSuperadmin, selectedAccountId]);

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

		// Add account_id for superadmins
		if (isSuperadmin) {
			if (!selectedAccountId) {
				setError('Please select an account');
				return;
			}
			recordData.account_id = selectedAccountId;
		}

		setIsSubmitting(true);
		try {
			await onSubmit(recordData);
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
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-2xl max-h-[90vh]">
				<DialogHeader>
					<DialogTitle>Create Record</DialogTitle>
					<DialogDescription>
						Add a new record to the <strong>{collectionName}</strong> collection.
					</DialogDescription>
				</DialogHeader>

				{isReferenceLoading ? (
					<div className="flex items-center justify-center py-8">
						<RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
						<span className="ml-2 text-muted-foreground">
							Loading reference data...
						</span>
					</div>
				) : (
					<form onSubmit={handleSubmit} className="space-y-6">
						{/* Account selector for superadmins */}
						{isSuperadmin && (
							<div className="space-y-2 pb-4 border-b">
								<Label htmlFor="account-select">Account *</Label>
								<Select
									value={selectedAccountId}
									onValueChange={setSelectedAccountId}
									disabled={loadingAccounts || isSubmitting}
								>
									<SelectTrigger id="account-select">
										<SelectValue placeholder="Select an account" />
									</SelectTrigger>
									<SelectContent>
										{accounts.map((account) => (
											<SelectItem key={account.id} value={account.id}>
												{account.name} ({account.account_code})
											</SelectItem>
										))}
									</SelectContent>
								</Select>
								{loadingAccounts && (
									<p className="text-sm text-muted-foreground">
										Loading accounts...
									</p>
								)}
							</div>
						)}

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
								{isSubmitting ? 'Creating...' : 'Create Record'}
							</Button>
						</DialogFooter>
					</form>
				)}
			</DialogContent>
		</Dialog>
	);
}
